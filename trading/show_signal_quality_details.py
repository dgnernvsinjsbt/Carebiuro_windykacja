"""
Show detailed breakdown of Signal Quality Filter (threshold = 0.0)
97 trades, +638% return
"""
import pandas as pd
import numpy as np

def backtest_with_signal_quality(df, month_name, threshold=0.0):
    """Backtest with signal quality regime filter"""

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

    # Track signals and forward returns
    df['signal'] = 0
    df.loc[(df['rsi'].shift(1) < 35) & (df['rsi'] >= 35), 'signal'] = 1
    df.loc[(df['rsi'].shift(1) > 65) & (df['rsi'] <= 65), 'signal'] = -1

    # Calculate forward return 12 bars ahead (3 hours)
    df['fwd_ret_12'] = (df['close'].shift(-12) - df['close']) / df['close'] * 100

    # Rolling signal quality (last 4 days of signals)
    signal_quality = []
    for i in range(len(df)):
        if i < 100:
            signal_quality.append(False)
            continue

        recent_signals = df.iloc[max(0, i-384):i]  # Last 4 days (384 bars)
        signal_rows = recent_signals[recent_signals['signal'] != 0]

        if len(signal_rows) >= 5:
            avg_fwd = signal_rows['fwd_ret_12'].mean()
            signal_quality.append(avg_fwd > threshold)
        else:
            signal_quality.append(False)

    df['regime_active'] = signal_quality

    trades = []
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
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

        # Generate signals with SIGNAL QUALITY FILTER
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
                # REGIME FILTER: Skip if recent signals haven't been working
                if not row['regime_active']:
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

    # Calculate regime active time
    regime_active_pct = (df['regime_active'].sum() / len(df) * 100) if len(df) > 0 else 0

    if not trades:
        return {
            'month': month_name,
            'trades': 0,
            'regime_active_pct': regime_active_pct,
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
        'trades': len(df_t),
        'regime_active_pct': regime_active_pct,
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
print('SIGNAL QUALITY FILTER: threshold = 0.0')
print('Only trade when recent signals (last 4 days) have avg forward return > 0%')
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

results = []

for month_name, filename, category in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_with_signal_quality(df.copy(), month_name)
    result['category'] = category
    results.append(result)

# MONTHLY BREAKDOWN
print(f"\n{'Month':<12} {'Cat':<7} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} "
      f"{'Regime%':<10} {'Return':<10} {'MaxDD':<9} {'R/DD':<9}")
print('-' * 140)

for r in results:
    status = '✅' if r['total_return'] > 0 else '❌'
    print(f"{r['month']:<12} {r['category']:<7} {r['trades']:<8} {r.get('winners', 0):<4} {r.get('losers', 0):<4} "
          f"{r.get('win_rate', 0):>5.1f}% {r.get('tp_rate', 0):>5.1f}% {r['regime_active_pct']:>9.1f}% "
          f"{r['total_return']:>+9.1f}% {r.get('max_dd', 0):>+8.2f}% {r.get('return_dd', 0):>8.2f}x {status}")

# EQUITY PROGRESSION
print('\n' + '=' * 140)
print('EQUITY PROGRESSION')
print('=' * 140)
print(f"\n{'Month':<12} {'Starting':<12} {'Ending':<14} {'Monthly':<10} {'Cumulative':<12}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting = cumulative_equity
    ending = starting * (1 + r['total_return'] / 100)
    cumulative_return = ((ending - 100) / 100) * 100

    status = '🚀' if r['total_return'] > 200 else '📈' if r['total_return'] > 0 else '📉'
    print(f"{r['month']:<12} ${starting:>10.2f} ${ending:>12.2f} {r['total_return']:>+9.1f}% "
          f"{cumulative_return:>+11.1f}% {status}")

    cumulative_equity = ending

# SUMMARY
print('\n' + '=' * 140)
print('SUMMARY')
print('=' * 140)

total_trades = sum(r['trades'] for r in results)
total_winners = sum(r.get('winners', 0) for r in results)
losers = [r for r in results if r['category'] == 'LOSER']
winners = [r for r in results if r['category'] == 'WINNER']

loser_trades = sum(r['trades'] for r in losers)
winner_trades = sum(r['trades'] for r in winners)

print(f"\n📊 OVERALL:")
print(f"  Total trades: {total_trades}")
print(f"  Win rate: {(total_winners / total_trades * 100):.1f}%")
print(f"  Final equity: ${cumulative_equity:,.2f}")
print(f"  Total return: {((cumulative_equity - 100) / 100 * 100):+.1f}%")
print(f"  Loser month trades: {loser_trades} ({(loser_trades/total_trades*100):.1f}%)")
print(f"  Winner month trades: {winner_trades} ({(winner_trades/total_trades*100):.1f}%)")

print(f"\n💡 REGIME FILTER EFFECTIVENESS:")
avg_loser_regime = sum(r['regime_active_pct'] for r in losers) / len(losers)
avg_winner_regime = sum(r['regime_active_pct'] for r in winners) / len(winners)
print(f"  Loser months: {avg_loser_regime:.1f}% time regime active")
print(f"  Winner months: {avg_winner_regime:.1f}% time regime active")

print('\n' + '=' * 140)
