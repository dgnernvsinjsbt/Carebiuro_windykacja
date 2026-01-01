"""
Final Optimized Config: Monthly Breakdown
Offset 0.1 ATR, SL 1.2x ATR, TP 3.0x ATR
Show detailed trading metrics for each month Sept-Dec
"""
import pandas as pd
import numpy as np

def backtest_month(df, month_name, offset_atr=0.1, sl_atr=1.2, tp_atr=3.0, max_wait_bars=8):
    """
    Backtest single month with final optimized config
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
            else:  # SHORT
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
            else:  # SHORT
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
        return None

    df_t = pd.DataFrame(trades)

    # Calculate metrics
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    total_return = ((equity - 100) / 100) * 100
    win_rate = len(winners) / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100
    sl_rate = (df_t['exit'] == 'SL').sum() / len(df_t) * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    largest_win = winners['pnl_pct'].max() if len(winners) > 0 else 0
    largest_loss = losers['pnl_pct'].min() if len(losers) > 0 else 0

    fill_rate = (len(trades) / signals * 100) if signals > 0 else 0

    # LONG vs SHORT
    longs = df_t[df_t['direction'] == 'LONG']
    shorts = df_t[df_t['direction'] == 'SHORT']

    long_wins = len(longs[longs['pnl_pct'] > 0]) if len(longs) > 0 else 0
    long_wr = (long_wins / len(longs) * 100) if len(longs) > 0 else 0
    long_pnl = longs['pnl_pct'].sum() if len(longs) > 0 else 0

    short_wins = len(shorts[shorts['pnl_pct'] > 0]) if len(shorts) > 0 else 0
    short_wr = (short_wins / len(shorts) * 100) if len(shorts) > 0 else 0
    short_pnl = shorts['pnl_pct'].sum() if len(shorts) > 0 else 0

    return {
        'month': month_name,
        'trades': len(df_t),
        'signals': signals,
        'fill_rate': fill_rate,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity,
        'longs': len(longs),
        'long_wr': long_wr,
        'long_pnl': long_pnl,
        'shorts': len(shorts),
        'short_wr': short_wr,
        'short_pnl': short_pnl
    }

print('=' * 140)
print('FINAL OPTIMIZED CONFIG - MONTHLY BREAKDOWN')
print('Offset: 0.1 ATR | SL: 1.2x ATR | TP: 3.0x ATR | Max wait: 2 hours')
print('Strategy: RSI 35/65 + ret_20 > 0 filter + LIMIT orders')
print('=' * 140)

# Load each month
months = [
    ('September', 'melania_september_2025_15m_fresh.csv'),
    ('October', 'melania_october_2025_15m_fresh.csv'),
    ('November', 'melania_november_2025_15m_fresh.csv'),
    ('December', 'melania_december_2025_15m_fresh.csv'),
]

results = []

for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_month(df.copy(), month_name)
    if result:
        results.append(result)

# OVERVIEW TABLE
print('\n' + '=' * 140)
print('OVERVIEW - PERFORMANCE BY MONTH')
print('=' * 140)
print(f"\n{'Month':<12} {'Trades':<8} {'Sigs':<6} {'Fill%':<7} {'W':<4} {'L':<4} {'WR%':<6} "
      f"{'TP%':<6} {'Return':<10} {'MaxDD':<9} {'R/DD':<9}")
print('-' * 140)

for r in results:
    print(f"{r['month']:<12} {r['trades']:<8} {r['signals']:<6} {r['fill_rate']:>6.1f}% "
          f"{r['winners']:<4} {r['losers']:<4} {r['win_rate']:>5.1f}% {r['tp_rate']:>5.1f}% "
          f"{r['total_return']:>+9.1f}% {r['max_dd']:>+8.2f}% {r['return_dd']:>8.2f}x")

# Totals
total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
total_losers = sum(r['losers'] for r in results)
avg_wr = (total_winners / total_trades * 100) if total_trades > 0 else 0
avg_tp = sum(r['tp_rate'] * r['trades'] for r in results) / total_trades if total_trades > 0 else 0

print('-' * 140)
print(f"{'TOTAL':<12} {total_trades:<8} {'':>6} {'':>7} {total_winners:<4} {total_losers:<4} "
      f"{avg_wr:>5.1f}% {avg_tp:>5.1f}%")

# WIN/LOSS ANALYSIS
print('\n' + '=' * 140)
print('WIN/LOSS ANALYSIS')
print('=' * 140)
print(f"\n{'Month':<12} {'Avg Win':<10} {'Avg Loss':<10} {'Win/Loss':<10} {'Largest Win':<12} {'Largest Loss':<12}")
print('-' * 140)

for r in results:
    wl_ratio = abs(r['avg_win'] / r['avg_loss']) if r['avg_loss'] != 0 else 0
    print(f"{r['month']:<12} {r['avg_win']:>+9.2f}% {r['avg_loss']:>+9.2f}% "
          f"{wl_ratio:>9.2f}x {r['largest_win']:>+11.2f}% {r['largest_loss']:>+11.2f}%")

# LONG vs SHORT
print('\n' + '=' * 140)
print('LONG vs SHORT BREAKDOWN')
print('=' * 140)
print(f"\n{'Month':<12} {'Longs':<7} {'L-WR%':<7} {'L-P&L':<10} {'Shorts':<7} {'S-WR%':<7} {'S-P&L':<10}")
print('-' * 140)

for r in results:
    print(f"{r['month']:<12} {r['longs']:<7} {r['long_wr']:>6.1f}% {r['long_pnl']:>+9.1f}% "
          f"{r['shorts']:<7} {r['short_wr']:>6.1f}% {r['short_pnl']:>+9.1f}%")

total_longs = sum(r['longs'] for r in results)
total_shorts = sum(r['shorts'] for r in results)
total_long_pnl = sum(r['long_pnl'] for r in results)
total_short_pnl = sum(r['short_pnl'] for r in results)

print('-' * 140)
print(f"{'TOTAL':<12} {total_longs:<7} {'':>7} {total_long_pnl:>+9.1f}% "
      f"{total_shorts:<7} {'':>7} {total_short_pnl:>+9.1f}%")

# MONTHLY EQUITY PROGRESSION
print('\n' + '=' * 140)
print('MONTHLY EQUITY PROGRESSION')
print('=' * 140)
print(f"\n{'Month':<12} {'Starting':<12} {'Ending':<12} {'Return':<10} {'Cumulative':<12}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting = cumulative_equity
    ending = starting * (1 + r['total_return'] / 100)
    cumulative_return = ((ending - 100) / 100) * 100

    print(f"{r['month']:<12} ${starting:>10.2f} ${ending:>10.2f} {r['total_return']:>+9.1f}% ${ending:>10.2f} ({cumulative_return:>+8.1f}%)")

    cumulative_equity = ending

# SUMMARY
print('\n' + '=' * 140)
print('SUMMARY')
print('=' * 140)

total_return_simple = sum(r['total_return'] for r in results)
avg_return = total_return_simple / len(results)
best_month = max(results, key=lambda x: x['total_return'])
worst_month = min(results, key=lambda x: x['total_return'])
best_rdd = max(results, key=lambda x: x['return_dd'])

print(f"\n📊 OVERALL PERFORMANCE:")
print(f"   Total trades: {total_trades}")
print(f"   Win rate: {avg_wr:.1f}%")
print(f"   TP hit rate: {avg_tp:.1f}%")
print(f"   Cumulative return: {((cumulative_equity - 100) / 100 * 100):+.1f}%")
print(f"   Avg return per month: {avg_return:+.1f}%")

print(f"\n🏆 BEST MONTH:")
print(f"   {best_month['month']}: {best_month['total_return']:+.1f}% return, {best_month['return_dd']:.2f}x R/DD")

print(f"\n📉 WORST MONTH:")
print(f"   {worst_month['month']}: {worst_month['total_return']:+.1f}% return, {worst_month['return_dd']:.2f}x R/DD")

print(f"\n🎯 BEST R/DD MONTH:")
print(f"   {best_rdd['month']}: {best_rdd['return_dd']:.2f}x R/DD, {best_rdd['total_return']:+.1f}% return")

print(f"\n📈 STRATEGY DIRECTION:")
print(f"   LONG trades: {total_longs} ({(total_longs/total_trades*100):.1f}%), P&L: {total_long_pnl:+.1f}%")
print(f"   SHORT trades: {total_shorts} ({(total_shorts/total_trades*100):.1f}%), P&L: {total_short_pnl:+.1f}%")

# Save
df_results = pd.DataFrame(results)
df_results.to_csv('final_config_monthly_breakdown.csv', index=False)
print(f'\n💾 Saved to: final_config_monthly_breakdown.csv')
