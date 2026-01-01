"""
Test Final Optimized Config on ALL Available 2025 Data
June-December (7 months)
Offset 0.1 ATR, SL 1.2x ATR, TP 3.0x ATR
"""
import pandas as pd
import numpy as np

def backtest_month(df, month_name, offset_atr=0.1, sl_atr=1.2, tp_atr=3.0, max_wait_bars=8):
    """Backtest single month with final optimized config"""

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

    trades = []
    signals = 0
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
            if bars_waiting > max_wait_bars:
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

                trades.append({
                    'pnl_pct': pnl_pct,
                    'exit': exit_type,
                    'direction': position['direction']
                })
                position = None
                continue

        # Generate new signals
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                signal_price = row['close']
                atr = row['atr']

                if prev_row['rsi'] < 35 and row['rsi'] >= 35:  # LONG signal
                    signals += 1
                    limit_price = signal_price - (atr * offset_atr)
                    sl_price = limit_price - (atr * sl_atr)
                    tp_price = limit_price + (atr * tp_atr)
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

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:  # SHORT signal
                    signals += 1
                    limit_price = signal_price + (atr * offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)
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
            'trades': 0,
            'signals': signals,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'final_equity': equity
        }

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    return {
        'month': month_name,
        'trades': len(df_t),
        'signals': signals,
        'fill_rate': (len(trades) / signals * 100) if signals > 0 else 0,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'avg_win': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loss': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'return_dd': (((equity - 100) / 100) * 100) / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

print('=' * 140)
print('FINAL CONFIG - ALL AVAILABLE 2025 DATA (JUN-DEC)')
print('Offset: 0.1 ATR | SL: 1.2x ATR | TP: 3.0x ATR')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv'),
    ('July', 'melania_july_2025_15m.csv'),
    ('August', 'melania_august_2025_15m.csv'),
    ('September', 'melania_september_2025_15m.csv'),
    ('October', 'melania_october_2025_15m.csv'),
    ('November', 'melania_november_2025_15m.csv'),
    ('December', 'melania_december_2025_15m.csv'),
]

results = []

for month_name, filename in months:
    print(f'\nProcessing {month_name} 2025...')
    try:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f'  Loaded: {len(df)} bars')
        result = backtest_month(df.copy(), month_name)
        if result:
            results.append(result)
            print(f'  Result: {result["trades"]} trades, {result["total_return"]:+.1f}% return')
    except FileNotFoundError:
        print(f'  ⚠️  File not found: {filename}')
    except Exception as e:
        print(f'  ❌ Error: {e}')

# MONTHLY OVERVIEW
print('\n' + '=' * 140)
print('MONTHLY OVERVIEW - ALL 2025')
print('=' * 140)
print(f"\n{'Month':<12} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} "
      f"{'Return':<10} {'MaxDD':<9} {'R/DD':<9} {'Status'}")
print('-' * 140)

for r in results:
    status = '✅' if r['total_return'] > 0 else '❌' if r['total_return'] < -10 else '➖'
    print(f"{r['month']:<12} {r['trades']:<8} {r['winners']:<4} {r['losers']:<4} "
          f"{r['win_rate']:>5.1f}% {r['tp_rate']:>5.1f}% {r['total_return']:>+9.1f}% "
          f"{r['max_dd']:>+8.2f}% {r['return_dd']:>8.2f}x {status}")

# EQUITY CURVE
print('\n' + '=' * 140)
print('EQUITY PROGRESSION THROUGH 2025')
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
print('2025 SUMMARY (ALL AVAILABLE DATA)')
print('=' * 140)

total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
profitable_months = len([r for r in results if r['total_return'] > 0])
losing_months = len([r for r in results if r['total_return'] < 0])

print(f"\n📊 OVERALL:")
print(f"  Available months: {len(results)}/12 (Jun-Dec 2025)")
print(f"  Final equity: ${cumulative_equity:,.2f}")
print(f"  Total return: {((cumulative_equity - 100) / 100 * 100):+.1f}%")
print(f"  Total trades: {total_trades}")
print(f"  Win rate: {(total_winners / total_trades * 100):.1f}%")
print(f"  Profitable months: {profitable_months}/{len(results)}")
print(f"  Losing months: {losing_months}/{len(results)}")

if results:
    best_month = max(results, key=lambda x: x['total_return'])
    worst_month = min(results, key=lambda x: x['total_return'])

    print(f"\n🏆 Best month: {best_month['month']} ({best_month['total_return']:+.1f}%)")
    print(f"📉 Worst month: {worst_month['month']} ({worst_month['total_return']:+.1f}%)")

# Save
df_results = pd.DataFrame(results)
df_results.to_csv('all_2025_results.csv', index=False)
print(f'\n💾 Saved to: all_2025_results.csv')
print('=' * 140)
