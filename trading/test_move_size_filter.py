"""
Test Move Size Filter: Only trade when market has big moves
Filter: Rolling avg of 4-hour absolute moves > threshold
"""
import pandas as pd
import numpy as np

def backtest_with_move_size_filter(df, month_name, threshold=1.8):
    """Only trade when recent moves are large enough"""

    # Basic indicators
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    # MOVE SIZE FILTER
    # Calculate 4-hour absolute return (16 bars on 15m)
    df['ret_4h_abs'] = abs((df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100)

    # Rolling average of move size (last 96 bars = 1 day)
    df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

    # Regime active when moves are big enough
    df['regime_active'] = df['avg_move_size'] > threshold

    trades = []
    signals_total = 0
    signals_filtered = 0
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue
        if pd.isna(row['avg_move_size']):
            continue

        # Check pending limit order
        if pending_order:
            bars_waiting = i - pending_order['signal_bar']
            if bars_waiting > 8:
                pending_order = None
                continue

            if pending_order['direction'] == 'LONG':
                if row['low'] <= pending_order['limit_price']:
                    position = {
                        'direction': 'LONG',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None
            else:
                if row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None

        # Manage active position
        if position:
            pnl_pct = None
            exit_type = None

            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'TP'
            else:
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    exit_type = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type})
                position = None
                continue

        # Generate signals with MOVE SIZE FILTER
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= 0:
                continue
            if pd.isna(prev_row['rsi']):
                continue

            signal_triggered = False
            direction = None

            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                signal_triggered = True
                direction = 'LONG'
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                signal_triggered = True
                direction = 'SHORT'

            if signal_triggered:
                signals_total += 1

                # FILTER: Skip if moves too small
                if not row['regime_active']:
                    signals_filtered += 1
                    continue

                # Take trade
                signal_price = row['close']
                atr = row['atr']

                if direction == 'LONG':
                    limit_price = signal_price - (atr * 0.1)
                    sl_price = limit_price - (atr * 1.2)
                    tp_price = limit_price + (atr * 3.0)
                    sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'LONG',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }
                else:
                    limit_price = signal_price + (atr * 0.1)
                    sl_price = limit_price + (atr * 1.2)
                    tp_price = limit_price - (atr * 3.0)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'SHORT',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    # Calculate regime stats
    regime_active_pct = (df['regime_active'].sum() / len(df) * 100) if len(df) > 0 else 0
    avg_move_size = df['avg_move_size'].mean()

    if not trades:
        return {
            'month': month_name,
            'threshold': threshold,
            'trades': 0,
            'signals_total': signals_total,
            'signals_filtered': signals_filtered,
            'regime_active_pct': regime_active_pct,
            'avg_move_size': avg_move_size,
            'total_return': 0,
            'final_equity': equity
        }

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]

    return {
        'month': month_name,
        'threshold': threshold,
        'trades': len(df_t),
        'signals_total': signals_total,
        'signals_filtered': signals_filtered,
        'regime_active_pct': regime_active_pct,
        'avg_move_size': avg_move_size,
        'winners': len(winners),
        'losers': len(df_t) - len(winners),
        'win_rate': len(winners) / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'return_dd': (((equity - 100) / 100) * 100) / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

print('=' * 140)
print('MOVE SIZE FILTER: Only trade when market has big moves')
print('Testing thresholds: 1.5%, 1.6%, 1.7%, 1.8%, 1.9%, 2.0%')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv', 'LOSER'),
    ('July', 'melania_july_2025_15m.csv', 'LOSER'),
    ('August', 'melania_august_2025_15m.csv', 'LOSER'),
    ('September', 'melania_september_2025_15m.csv', 'LOSER'),
    ('October', 'melania_october_2025_15m.csv', 'WINNER'),
    ('November', 'melania_november_2025_15m.csv', 'WINNER'),
    ('December', 'melania_december_2025_15m.csv', 'WINNER'),
]

thresholds = [1.5, 1.6, 1.7, 1.8, 1.9, 2.0]

all_results = []

for threshold in thresholds:
    print(f'\nTesting threshold = {threshold}%')

    config_results = []
    for month_name, filename, category in months:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        result = backtest_with_move_size_filter(df.copy(), month_name, threshold)
        result['category'] = category
        config_results.append(result)

    # Aggregate
    losers = [r for r in config_results if r['category'] == 'LOSER']
    winners = [r for r in config_results if r['category'] == 'WINNER']

    loser_trades = sum(r['trades'] for r in losers)
    winner_trades = sum(r['trades'] for r in winners)
    total_trades = loser_trades + winner_trades

    # Cumulative equity
    cumulative_equity = 100.0
    for r in config_results:
        cumulative_equity = cumulative_equity * (1 + r['total_return'] / 100)

    total_return = ((cumulative_equity - 100) / 100) * 100

    summary = {
        'threshold': threshold,
        'loser_trades': loser_trades,
        'winner_trades': winner_trades,
        'total_trades': total_trades,
        'total_return': total_return,
        'final_equity': cumulative_equity,
        'configs': config_results
    }
    all_results.append(summary)

    print(f'  Loser={loser_trades:3d} | Winner={winner_trades:3d} | Total={total_trades:3d} | Return={total_return:+7.1f}%')

# Show best configs
print('\n' + '=' * 140)
print('RESULTS SUMMARY')
print('=' * 140)
print(f"\n{'Threshold':<12} {'Loser':<8} {'Winner':<8} {'Total':<8} {'Final $':<12} {'Return':<10}")
print('-' * 140)

sorted_results = sorted(all_results, key=lambda x: x['total_return'], reverse=True)

for r in sorted_results:
    print(f"{r['threshold']:<12.1f} {r['loser_trades']:<8} {r['winner_trades']:<8} {r['total_trades']:<8} "
          f"${r['final_equity']:<11,.2f} {r['total_return']:>+9.1f}%")

# Show monthly detail for best threshold
best = sorted_results[0]
print('\n' + '=' * 140)
print(f"BEST: Move Size > {best['threshold']}%")
print('=' * 140)
print(f"\n{'Month':<12} {'Cat':<7} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} "
      f"{'Regime%':<10} {'AvgMove%':<10} {'Return':<10}")
print('-' * 140)

for r in best['configs']:
    wr = r.get('win_rate', 0)
    tp = r.get('tp_rate', 0)
    status = '✅' if r['total_return'] > 0 else '❌'
    print(f"{r['month']:<12} {r['category']:<7} {r['trades']:<8} {r.get('winners', 0):<4} "
          f"{r.get('losers', 0):<4} {wr:>5.1f}% {tp:>5.1f}% {r['regime_active_pct']:>9.1f}% "
          f"{r['avg_move_size']:>9.2f}% {r['total_return']:>+9.1f}% {status}")

# Equity progression
print('\n' + '=' * 140)
print('EQUITY PROGRESSION')
print('=' * 140)
print(f"\n{'Month':<12} {'Starting':<12} {'Ending':<14} {'Monthly':<10} {'Cumulative':<12}")
print('-' * 140)

cumulative_equity = 100.0
for r in best['configs']:
    starting = cumulative_equity
    ending = starting * (1 + r['total_return'] / 100)
    cumulative_return = ((ending - 100) / 100) * 100

    status = '🚀' if r['total_return'] > 200 else '📈' if r['total_return'] > 0 else '📉'
    print(f"{r['month']:<12} ${starting:>10.2f} ${ending:>12.2f} {r['total_return']:>+9.1f}% "
          f"{cumulative_return:>+11.1f}% {status}")

    cumulative_equity = ending

print(f'\n💰 FINAL: ${cumulative_equity:,.2f} ({((cumulative_equity-100)/100*100):+.1f}%)')
print('=' * 140)
