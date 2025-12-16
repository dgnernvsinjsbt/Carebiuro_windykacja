"""
Complete trading metrics breakdown by month
Show what makes Nov 69x R/DD and analyze all losses
"""
import pandas as pd
import numpy as np

def backtest_month(df, month_name):
    """Backtest single month with full metrics"""

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

    # Backtest
    trades = []
    equity = 100.0
    position = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Manage position
        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    continue
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    continue
            else:  # SHORT
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    continue
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    continue

        # New signals
        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:  # LONG
                    entry = row['close']
                    sl = entry - (row['atr'] * 2.0)
                    tp = entry + (row['atr'] * 3.0)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:  # SHORT
                    entry = row['close']
                    sl = entry + (row['atr'] * 2.0)
                    tp = entry - (row['atr'] * 3.0)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

    if not trades:
        return None

    df_t = pd.DataFrame(trades)

    # Calculate metrics
    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    total_return = ((equity - 100) / 100) * 100
    win_rate = len(winners) / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    largest_win = winners['pnl_pct'].max() if len(winners) > 0 else 0
    largest_loss = losers['pnl_pct'].min() if len(losers) > 0 else 0

    # Equity curve for max DD
    eq = [100.0]
    cum_eq = 100.0
    for pnl in df_t['pnl_pct']:
        cum_eq += (cum_eq * 0.12) * (pnl / 100) - (cum_eq * 0.12) * 0.001
        eq.append(cum_eq)
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    # LONG vs SHORT breakdown
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
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'longs': len(longs),
        'long_wr': long_wr,
        'long_pnl': long_pnl,
        'shorts': len(shorts),
        'short_wr': short_wr,
        'short_pnl': short_pnl
    }

# Load and backtest all months
months = [
    ('July', 'melania_july_2025_15m_fresh.csv'),
    ('August', 'melania_august_2025_15m_fresh.csv'),
    ('September', 'melania_september_2025_15m_fresh.csv'),
    ('October', 'melania_october_2025_15m_fresh.csv'),
    ('November', 'melania_november_2025_15m_fresh.csv'),
    ('December', 'melania_december_2025_15m_fresh.csv'),
]

print('=' * 120)
print('COMPLETE TRADING METRICS BREAKDOWN BY MONTH')
print('Strategy: RSI 35/65 + ret_20 > 0 filter, SL 2.0x ATR, TP 3.0x ATR')
print('=' * 120)

results = []

for month_name, filename in months:
    print(f'\nProcessing {month_name}...')
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_month(df.copy(), month_name)
    if result:
        results.append(result)

# Print detailed table
print('\n' + '=' * 120)
print('OVERVIEW TABLE')
print('=' * 120)
print(f"\n{'Month':<10} {'Trades':<7} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} {'Return':<9} {'MaxDD':<8} {'R/DD':<8}")
print('-' * 120)

for r in results:
    print(f"{r['month']:<10} {r['trades']:<7} {r['winners']:<4} {r['losers']:<4} "
          f"{r['win_rate']:>5.1f}% {r['tp_rate']:>5.1f}% {r['total_return']:>+8.1f}% "
          f"{r['max_dd']:>7.2f}% {r['return_dd']:>7.2f}x")

# Totals
total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
total_losers = sum(r['losers'] for r in results)
total_return = sum(r['total_return'] for r in results)
avg_wr = total_winners / total_trades * 100

print('-' * 120)
print(f"{'TOTAL':<10} {total_trades:<7} {total_winners:<4} {total_losers:<4} "
      f"{avg_wr:>5.1f}% {'':>6} {total_return:>+8.1f}% {'':>8} {'':>8}")

# Win/Loss Analysis
print('\n' + '=' * 120)
print('WIN/LOSS ANALYSIS')
print('=' * 120)
print(f"\n{'Month':<10} {'Avg Win':<10} {'Avg Loss':<10} {'Win/Loss':<10} {'Largest Win':<12} {'Largest Loss':<12}")
print('-' * 120)

for r in results:
    wl_ratio = abs(r['avg_win'] / r['avg_loss']) if r['avg_loss'] != 0 else 0
    print(f"{r['month']:<10} {r['avg_win']:>+9.2f}% {r['avg_loss']:>+9.2f}% "
          f"{wl_ratio:>9.2f}x {r['largest_win']:>+11.2f}% {r['largest_loss']:>+11.2f}%")

# LONG vs SHORT
print('\n' + '=' * 120)
print('LONG vs SHORT BREAKDOWN')
print('=' * 120)
print(f"\n{'Month':<10} {'Longs':<7} {'L-WR%':<7} {'L-P&L':<10} {'Shorts':<7} {'S-WR%':<7} {'S-P&L':<10}")
print('-' * 120)

for r in results:
    print(f"{r['month']:<10} {r['longs']:<7} {r['long_wr']:>6.1f}% {r['long_pnl']:>+9.1f}% "
          f"{r['shorts']:<7} {r['short_wr']:>6.1f}% {r['short_pnl']:>+9.1f}%")

total_longs = sum(r['longs'] for r in results)
total_shorts = sum(r['shorts'] for r in results)
total_long_pnl = sum(r['long_pnl'] for r in results)
total_short_pnl = sum(r['short_pnl'] for r in results)

print('-' * 120)
print(f"{'TOTAL':<10} {total_longs:<7} {'':>7} {total_long_pnl:>+9.1f}% "
      f"{total_shorts:<7} {'':>7} {total_short_pnl:>+9.1f}%")

# What makes November 69x?
print('\n' + '=' * 120)
print('WHAT MAKES NOVEMBER 69x R/DD?')
print('=' * 120)

nov = [r for r in results if r['month'] == 'November'][0]
print(f"\nReturn: {nov['total_return']:+.1f}%")
print(f"Max Drawdown: {nov['max_dd']:.2f}%")
print(f"Return/DD Ratio: {nov['return_dd']:.2f}x")
print(f"\n💡 The equity curve was EXTREMELY SMOOTH:")
print(f"   - Generated {nov['total_return']:+.1f}% profit")
print(f"   - With only {abs(nov['max_dd']):.2f}% maximum pullback")
print(f"   - That's a {nov['return_dd']:.0f}:1 profit-to-drawdown ratio!")
print(f"\n📊 Why so smooth?")
print(f"   - {nov['win_rate']:.0f}% win rate ({nov['winners']}W / {nov['losers']}L)")
print(f"   - Average winner: {nov['avg_win']:+.2f}%")
print(f"   - Average loser: {nov['avg_loss']:+.2f}%")
print(f"   - Largest loss: {nov['largest_loss']:+.2f}% (well-controlled)")
print(f"   - Largest win: {nov['largest_win']:+.2f}% (explosive SHORT)")

# Save
df_results = pd.DataFrame(results)
df_results.to_csv('monthly_breakdown_clean_data.csv', index=False)
print(f'\n💾 Saved to: monthly_breakdown_clean_data.csv')
