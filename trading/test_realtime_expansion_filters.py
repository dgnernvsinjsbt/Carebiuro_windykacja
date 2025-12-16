"""
Test Real-Time Volatility Expansion Filters
Compare different baseline methods that can be calculated live (no hindsight)
"""
import pandas as pd
import numpy as np

def backtest_with_expansion_filter(df, month_name, baseline_period, expansion_threshold):
    """
    Backtest with real-time ATR expansion filter
    baseline_period: how many bars to calculate ATR baseline (20, 50, 100, 200)
    expansion_threshold: multiplier (1.3, 1.5, 1.7, 2.0)
    """

    # Calculate indicators
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

    # REAL-TIME ATR EXPANSION FILTER
    # Rolling baseline (uses only past data)
    df['atr_baseline'] = df['atr'].rolling(baseline_period).mean()
    df['atr_expansion'] = df['atr'] / df['atr_baseline']

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
        if pd.isna(row['atr_expansion']):
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
            bar = row
            pnl_pct = None
            exit_type = None

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'SL'
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'TP'
            else:
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    exit_type = 'SL'
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    exit_type = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type})
                position = None
                continue

        # Generate new signals with EXPANSION FILTER
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            # Base signal conditions
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

                # FILTER: Check if ATR is expanded
                if row['atr_expansion'] < expansion_threshold:
                    signals_filtered += 1
                    continue  # Skip this signal - no volatility expansion

                # Signal passed filter - take trade
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

    if not trades:
        return {
            'month': month_name,
            'baseline': baseline_period,
            'threshold': expansion_threshold,
            'trades': 0,
            'signals_total': signals_total,
            'signals_filtered': signals_filtered,
            'filter_rate': (signals_filtered / signals_total * 100) if signals_total > 0 else 0,
            'total_return': 0,
            'max_dd': 0,
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
        'baseline': baseline_period,
        'threshold': expansion_threshold,
        'trades': len(df_t),
        'signals_total': signals_total,
        'signals_filtered': signals_filtered,
        'filter_rate': (signals_filtered / signals_total * 100) if signals_total > 0 else 0,
        'winners': len(winners),
        'losers': len(df_t) - len(winners),
        'win_rate': len(winners) / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity
    }

print('=' * 160)
print('REAL-TIME VOLATILITY EXPANSION FILTER TESTING')
print('Testing different baseline periods and expansion thresholds')
print('=' * 160)

months = [
    ('June', 'melania_june_2025_15m.csv', 'LOSER'),
    ('July', 'melania_july_2025_15m.csv', 'LOSER'),
    ('August', 'melania_august_2025_15m.csv', 'LOSER'),
    ('September', 'melania_september_2025_15m.csv', 'LOSER'),
    ('October', 'melania_october_2025_15m.csv', 'WINNER'),
    ('November', 'melania_november_2025_15m.csv', 'WINNER'),
    ('December', 'melania_december_2025_15m.csv', 'WINNER'),
]

# Test grid
baseline_periods = [20, 50, 100, 200]  # bars (5h, 12.5h, 25h, 50h on 15m)
expansion_thresholds = [1.2, 1.3, 1.5, 1.7, 2.0]

all_results = []

for baseline in baseline_periods:
    for threshold in expansion_thresholds:
        print(f'\nTesting Baseline={baseline} bars, Threshold={threshold}x')

        config_results = []
        for month_name, filename, category in months:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            result = backtest_with_expansion_filter(df.copy(), month_name, baseline, threshold)
            result['category'] = category
            config_results.append(result)

        # Calculate aggregate metrics
        losers = [r for r in config_results if r['category'] == 'LOSER']
        winners = [r for r in config_results if r['category'] == 'WINNER']

        loser_trades = sum(r['trades'] for r in losers)
        winner_trades = sum(r['trades'] for r in winners)

        # Cumulative equity
        cumulative_equity = 100.0
        for r in config_results:
            cumulative_equity = cumulative_equity * (1 + r['total_return'] / 100)

        total_return = ((cumulative_equity - 100) / 100) * 100

        summary = {
            'baseline': baseline,
            'threshold': threshold,
            'loser_trades': loser_trades,
            'winner_trades': winner_trades,
            'total_trades': loser_trades + winner_trades,
            'total_return': total_return,
            'final_equity': cumulative_equity,
            'configs': config_results
        }
        all_results.append(summary)

        print(f'  Loser months: {loser_trades} trades | Winner months: {winner_trades} trades | '
              f'Total Return: {total_return:+.1f}%')

# Find best configs
print('\n' + '=' * 160)
print('TOP 10 CONFIGURATIONS (by total return)')
print('=' * 160)
print(f"\n{'Baseline':<10} {'Threshold':<10} {'Loser Trades':<13} {'Winner Trades':<14} "
      f"{'Total':<8} {'Final $':<12} {'Return':<10}")
print('-' * 160)

sorted_results = sorted(all_results, key=lambda x: x['total_return'], reverse=True)[:10]

for r in sorted_results:
    print(f"{r['baseline']:<10} {r['threshold']:<10.1f} {r['loser_trades']:<13} "
          f"{r['winner_trades']:<14} {r['total_trades']:<8} ${r['final_equity']:<11,.2f} "
          f"{r['total_return']:>+9.1f}%")

# Analyze best config in detail
best = sorted_results[0]
print('\n' + '=' * 160)
print(f"BEST CONFIG DETAILS: Baseline={best['baseline']} bars, Threshold={best['threshold']}x")
print('=' * 160)
print(f"\n{'Month':<12} {'Cat':<7} {'Signals':<9} {'Filtered':<10} {'Filter%':<9} "
      f"{'Trades':<8} {'WR%':<6} {'Return':<10}")
print('-' * 160)

for r in best['configs']:
    wr = r.get('win_rate', 0)
    print(f"{r['month']:<12} {r['category']:<7} {r['signals_total']:<9} "
          f"{r['signals_filtered']:<10} {r['filter_rate']:>8.1f}% "
          f"{r['trades']:<8} {wr:>5.1f}% {r['total_return']:>+9.1f}%")

# Save results
df_all = []
for summary in all_results:
    for config in summary['configs']:
        df_all.append(config)

pd.DataFrame(df_all).to_csv('expansion_filter_results.csv', index=False)
print(f'\n💾 Saved all results to: expansion_filter_results.csv')
print('=' * 160)
