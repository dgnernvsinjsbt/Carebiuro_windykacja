"""
Complete trading metrics breakdown by month - FIXED VERSION
Correct equity curve and max DD calculation
"""
import pandas as pd
import numpy as np

def backtest_month(df, month_name):
    """Backtest single month with CORRECT metrics"""

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

    # Backtest - track equity CORRECTLY
    trades = []
    equity = 100.0
    equity_curve = [100.0]  # Track actual equity progression
    position = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Manage position
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
                # Calculate P&L in dollars
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

    # Calculate CORRECT max drawdown from actual equity curve
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Calculate other metrics
    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    total_return = ((equity - 100) / 100) * 100
    win_rate = len(winners) / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    largest_win = winners['pnl_pct'].max() if len(winners) > 0 else 0
    largest_loss = losers['pnl_pct'].min() if len(losers) > 0 else 0

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    # LONG vs SHORT breakdown
    longs = df_t[df_t['direction'] == 'LONG']
    shorts = df_t[df_t['direction'] == 'SHORT']

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
        'shorts': len(shorts),
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
print('COMPLETE TRADING METRICS BREAKDOWN BY MONTH (FIXED)')
print('Strategy: RSI 35/65 + ret_20 > 0 filter, SL 2.0x ATR, TP 3.0x ATR')
print('=' * 120)

results = []

for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_month(df.copy(), month_name)
    if result:
        results.append(result)

# Print detailed table
print('\n' + '=' * 120)
print('OVERVIEW TABLE (CORRECTED MAX DD)')
print('=' * 120)
print(f"\n{'Month':<10} {'Trades':<7} {'W':<4} {'L':<4} {'WR%':<6} {'Return':<9} {'MaxDD':<9} {'R/DD':<8}")
print('-' * 120)

for r in results:
    print(f"{r['month']:<10} {r['trades']:<7} {r['winners']:<4} {r['losers']:<4} "
          f"{r['win_rate']:>5.1f}% {r['total_return']:>+8.1f}% {r['max_dd']:>+8.2f}% {r['return_dd']:>7.2f}x")

# Totals
total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
total_losers = sum(r['losers'] for r in results)
total_return = sum(r['total_return'] for r in results)
avg_wr = total_winners / total_trades * 100

print('-' * 120)
print(f"{'TOTAL':<10} {total_trades:<7} {total_winners:<4} {total_losers:<4} "
      f"{avg_wr:>5.1f}% {total_return:>+8.1f}% {'':>9} {'':>8}")

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

print('\n💾 Saved to: monthly_breakdown_FIXED.csv')
df_results = pd.DataFrame(results)
df_results.to_csv('monthly_breakdown_FIXED.csv', index=False)
