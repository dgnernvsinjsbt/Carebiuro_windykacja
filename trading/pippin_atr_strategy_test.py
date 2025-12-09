"""
PIPPIN ATR Expansion Strategy Test
Replicates FARTCOIN strategy (8.44x Return/DD) on PIPPIN/USDT data
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ========================================
# 1. LOAD DATA
# ========================================
print("=" * 70)
print("PIPPIN ATR EXPANSION STRATEGY TEST")
print("Replicating FARTCOIN strategy (8.44x R/DD baseline)")
print("=" * 70)

data_path = Path(__file__).parent / 'pippin_7d_bingx.csv'
df = pd.read_csv(data_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData Loaded:")
print(f"  Candles: {len(df):,}")
print(f"  Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
print(f"  Duration: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days} days")
print(f"  Price Range: ${df['close'].min():.5f} - ${df['close'].max():.5f}")

# ========================================
# 2. CALCULATE INDICATORS
# ========================================
print("\nCalculating indicators...")

# True Range
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(
        row['high'] - row['low'],
        abs(row['high'] - row['close']),
        abs(row['low'] - row['close'])
    ), axis=1
)

# ATR(14)
df['atr_14'] = df['tr'].rolling(window=14).mean()

# 20-bar rolling average of ATR
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()

# EMA(20)
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

# Drop NaN rows from indicator calculation
df = df.dropna().reset_index(drop=True)
print(f"  Candles after warmup: {len(df):,}")

# ========================================
# 3. GENERATE SIGNALS
# ========================================
print("\nGenerating signals...")

signals = []

for i in range(20, len(df)):  # Start after lookback periods
    row = df.iloc[i]

    # 1. ATR Expansion Filter (current ATR > 1.5x rolling 20-bar average)
    atr_expansion = row['atr_14'] > 1.5 * row['atr_avg_20']
    if not atr_expansion:
        continue

    # 2. EMA Distance Filter (must be within 3% of EMA)
    ema_distance_pct = abs(row['close'] - row['ema_20']) / row['ema_20'] * 100
    if ema_distance_pct > 3.0:
        continue

    # 3. Directional Candle
    is_bullish = row['close'] > row['open']
    is_bearish = row['close'] < row['open']

    if is_bullish:
        signals.append({
            'index': i,
            'timestamp': row['timestamp'],
            'direction': 'LONG',
            'signal_price': row['close'],
            'limit_price': row['close'] * 1.01,  # +1% for LONG
            'atr': row['atr_14']
        })
    elif is_bearish:
        signals.append({
            'index': i,
            'timestamp': row['timestamp'],
            'direction': 'SHORT',
            'signal_price': row['close'],
            'limit_price': row['close'] * 0.99,  # -1% for SHORT
            'atr': row['atr_14']
        })

print(f"  Total signals: {len(signals)}")
print(f"  LONG signals: {sum(1 for s in signals if s['direction'] == 'LONG')}")
print(f"  SHORT signals: {sum(1 for s in signals if s['direction'] == 'SHORT')}")

# ========================================
# 4. SIMULATE LIMIT ORDER FILLS
# ========================================
print("\nSimulating limit order fills...")

filled_trades = []

for signal in signals:
    entry_index = signal['index']
    limit_price = signal['limit_price']
    direction = signal['direction']

    # Look ahead max 3 bars for fill
    filled = False
    fill_price = None
    fill_index = None

    for j in range(1, 4):  # Check next 3 bars
        if entry_index + j >= len(df):
            break

        future_bar = df.iloc[entry_index + j]

        if direction == 'LONG':
            # LONG fill: price must go ABOVE limit
            if future_bar['high'] >= limit_price:
                fill_price = limit_price
                fill_index = entry_index + j
                filled = True
                break

        elif direction == 'SHORT':
            # SHORT fill: price must go BELOW limit
            if future_bar['low'] <= limit_price:
                fill_price = limit_price
                fill_index = entry_index + j
                filled = True
                break

    if filled:
        filled_trades.append({
            'signal_index': entry_index,
            'fill_index': fill_index,
            'direction': direction,
            'signal_price': signal['signal_price'],
            'fill_price': fill_price,
            'atr': signal['atr'],
            'timestamp': df.iloc[fill_index]['timestamp']
        })

fill_rate = len(filled_trades) / len(signals) * 100 if len(signals) > 0 else 0
print(f"  Filled: {len(filled_trades)} / {len(signals)} ({fill_rate:.1f}%)")
print(f"  LONG fills: {sum(1 for t in filled_trades if t['direction'] == 'LONG')}")
print(f"  SHORT fills: {sum(1 for t in filled_trades if t['direction'] == 'SHORT')}")

# ========================================
# 5. BACKTEST TRADES
# ========================================
print("\nBacktesting trades...")

equity = 10000  # Starting capital
trades_log = []

for trade in filled_trades:
    entry_index = trade['fill_index']
    entry_price = trade['fill_price']
    direction = trade['direction']
    atr = trade['atr']

    # Calculate SL/TP
    if direction == 'LONG':
        stop_loss = entry_price - (2.0 * atr)
        take_profit = entry_price + (8.0 * atr)
    else:  # SHORT
        stop_loss = entry_price + (2.0 * atr)
        take_profit = entry_price - (8.0 * atr)

    # Simulate trade
    exit_price = None
    exit_reason = None
    bars_held = 0

    for j in range(1, 201):  # Max 200 bars
        if entry_index + j >= len(df):
            exit_price = df.iloc[-1]['close']
            exit_reason = 'END'
            bars_held = j - 1
            break

        bar = df.iloc[entry_index + j]
        bars_held = j

        # Check SL/TP (SL checked first per FARTCOIN guide)
        if direction == 'LONG':
            if bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                break
            elif bar['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                break
        else:  # SHORT
            if bar['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                break
            elif bar['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                break

    # Time exit if neither SL/TP hit
    if exit_price is None:
        exit_price = df.iloc[entry_index + bars_held]['close']
        exit_reason = 'TIME'

    # Calculate P&L with fees
    if direction == 'LONG':
        pnl_pct = (exit_price - entry_price) / entry_price
    else:  # SHORT
        pnl_pct = (entry_price - exit_price) / entry_price

    # Subtract fees (0.1% round-trip: 0.05% entry + 0.05% exit)
    pnl_pct -= 0.001

    # Update equity
    equity *= (1 + pnl_pct)

    trades_log.append({
        'timestamp': trade['timestamp'],
        'direction': direction,
        'signal_price': trade['signal_price'],
        'entry': entry_price,
        'exit': exit_price,
        'exit_reason': exit_reason,
        'pnl_pct': pnl_pct * 100,
        'bars_held': bars_held,
        'equity': equity,
        'atr': atr,
        'stop_loss': stop_loss,
        'take_profit': take_profit
    })

# Convert to DataFrame
trades_df = pd.DataFrame(trades_log)

# ========================================
# 6. CALCULATE PERFORMANCE METRICS
# ========================================
print("\n" + "=" * 70)
print("PERFORMANCE METRICS")
print("=" * 70)

if len(trades_df) == 0:
    print("\n⚠️  NO TRADES EXECUTED - Strategy did not generate any filled orders")
    print("\nPossible reasons:")
    print("  - Insufficient volatility (ATR expansion threshold not met)")
    print("  - Limit orders never filled (price didn't reach limit price)")
    print("  - Very short dataset (7 days vs FARTCOIN's 32 days)")
    exit(0)

# Total Return
total_return = (equity - 10000) / 10000 * 100

# Max Drawdown
equity_curve = trades_df['equity'].values
running_max = np.maximum.accumulate(equity_curve)
drawdown = (equity_curve - running_max) / running_max * 100
max_drawdown = drawdown.min()

# Return/DD Ratio
return_dd_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

# Win Rate
winners = trades_df[trades_df['pnl_pct'] > 0]
win_rate = len(winners) / len(trades_df) * 100

# Average Win/Loss
avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
losers = trades_df[trades_df['pnl_pct'] <= 0]
avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

# Best/Worst Trades
best_trade = trades_df['pnl_pct'].max()
worst_trade = trades_df['pnl_pct'].min()

print(f"\n{'Metric':<25} {'PIPPIN':<15} {'FARTCOIN (Baseline)'}")
print("-" * 70)
print(f"{'Total Return':<25} {total_return:>+10.2f}%    {'+101.11%'}")
print(f"{'Max Drawdown':<25} {max_drawdown:>10.2f}%    {'-11.98%'}")
print(f"{'Return/DD Ratio':<25} {return_dd_ratio:>10.2f}x    {'8.44x'}")
print(f"{'Trades':<25} {len(trades_df):>10}       {'94'}")
print(f"{'Win Rate':<25} {win_rate:>10.1f}%    {'42.6%'}")
print(f"{'Avg Win':<25} {avg_win:>+10.2f}%    {'+4.97%'}")
print(f"{'Avg Loss':<25} {avg_loss:>10.2f}%    {'-2.23%'}")
print(f"{'Best Trade':<25} {best_trade:>+10.2f}%    {'N/A'}")
print(f"{'Worst Trade':<25} {worst_trade:>10.2f}%    {'N/A'}")
print(f"{'Fill Rate':<25} {fill_rate:>10.1f}%    {'21.2%'}")

# Exit Breakdown
print("\n" + "=" * 70)
print("EXIT BREAKDOWN")
print("=" * 70)
exit_counts = trades_df['exit_reason'].value_counts()
for reason, count in exit_counts.items():
    pct = count / len(trades_df) * 100
    baseline = {'TP': 40, 'SL': 47, 'TIME': 13}.get(reason, 0)
    print(f"  {reason:<10} {count:>3} ({pct:>5.1f}%)    Baseline: {baseline}%")

# Directional Breakdown
print("\n" + "=" * 70)
print("DIRECTIONAL BREAKDOWN")
print("=" * 70)
for direction in ['LONG', 'SHORT']:
    dir_trades = trades_df[trades_df['direction'] == direction]
    if len(dir_trades) == 0:
        continue
    dir_return = (dir_trades.iloc[-1]['equity'] / (dir_trades.iloc[0]['equity'] / (1 + dir_trades.iloc[0]['pnl_pct']/100)) - 1) * 100 if len(dir_trades) > 0 else 0
    dir_wr = (dir_trades['pnl_pct'] > 0).sum() / len(dir_trades) * 100
    print(f"\n{direction}:")
    print(f"  Trades: {len(dir_trades)}")
    print(f"  Win Rate: {dir_wr:.1f}%")
    print(f"  Avg P&L: {dir_trades['pnl_pct'].mean():+.2f}%")

# ========================================
# 7. SAVE RESULTS
# ========================================
print("\n" + "=" * 70)
print("SAVING RESULTS")
print("=" * 70)

results_dir = Path(__file__).parent / 'results'
results_dir.mkdir(exist_ok=True)

# Save trade log CSV
trades_csv_path = results_dir / 'pippin_atr_trades.csv'
trades_df.to_csv(trades_csv_path, index=False)
print(f"✓ Trade log saved: {trades_csv_path}")

# Generate markdown report
report_path = results_dir / 'PIPPIN_ATR_STRATEGY_REPORT.md'
with open(report_path, 'w') as f:
    f.write("# PIPPIN ATR Expansion Strategy - Test Results\n\n")
    f.write("## Executive Summary\n\n")

    if return_dd_ratio >= 5.0:
        verdict = "✅ **DEPLOY TO BOT** - Strategy shows strong risk-adjusted returns"
    elif return_dd_ratio >= 3.0:
        verdict = "⚠️ **CONSIDER DEPLOYMENT** - Moderate risk-adjusted returns, monitor closely"
    else:
        verdict = "❌ **DO NOT DEPLOY** - Insufficient risk-adjusted returns"

    f.write(f"The FARTCOIN ATR Expansion strategy (8.44x Return/DD baseline) was tested on PIPPIN/USDT ")
    f.write(f"over {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days} days of 1-minute data. ")
    f.write(f"The strategy achieved a **{return_dd_ratio:.2f}x Return/DD ratio** with {len(trades_df)} trades ")
    f.write(f"and a {win_rate:.1f}% win rate.\n\n")
    f.write(f"**Verdict:** {verdict}\n\n")

    f.write("---\n\n")
    f.write("## Performance Metrics\n\n")
    f.write("| Metric | PIPPIN | FARTCOIN (Baseline) |\n")
    f.write("|--------|--------|---------------------|\n")
    f.write(f"| **Return/DD Ratio** | **{return_dd_ratio:.2f}x** | **8.44x** |\n")
    f.write(f"| Total Return | {total_return:+.2f}% | +101.11% |\n")
    f.write(f"| Max Drawdown | {max_drawdown:.2f}% | -11.98% |\n")
    f.write(f"| Win Rate | {win_rate:.1f}% | 42.6% |\n")
    f.write(f"| Trades | {len(trades_df)} | 94 |\n")
    f.write(f"| Fill Rate | {fill_rate:.1f}% | 21.2% |\n")
    f.write(f"| Avg Win | {avg_win:+.2f}% | +4.97% |\n")
    f.write(f"| Avg Loss | {avg_loss:.2f}% | -2.23% |\n")
    f.write(f"| Best Trade | {best_trade:+.2f}% | N/A |\n")
    f.write(f"| Worst Trade | {worst_trade:.2f}% | N/A |\n\n")

    f.write("### Exit Breakdown\n\n")
    f.write("| Exit Type | PIPPIN | FARTCOIN Baseline |\n")
    f.write("|-----------|--------|-------------------|\n")
    for reason in ['TP', 'SL', 'TIME', 'END']:
        count = exit_counts.get(reason, 0)
        pct = count / len(trades_df) * 100 if len(trades_df) > 0 else 0
        baseline = {'TP': 40, 'SL': 47, 'TIME': 13}.get(reason, 0)
        f.write(f"| {reason} | {count} ({pct:.1f}%) | {baseline}% |\n")

    f.write("\n---\n\n")
    f.write("## Strategy Configuration\n\n")
    f.write("**Entry Conditions (ALL must be true):**\n")
    f.write("- ATR(14) > 1.5x rolling 20-bar average (volatility breakout)\n")
    f.write("- Price within 3% of EMA(20) (prevents late entries)\n")
    f.write("- Directional candle (bullish for LONG, bearish for SHORT)\n")
    f.write("- Limit order: LONG at +1%, SHORT at -1% from signal price\n")
    f.write("- Max wait: 3 bars for fill\n\n")
    f.write("**Exit Rules:**\n")
    f.write("- Stop Loss: 2.0x ATR(14) from fill price\n")
    f.write("- Take Profit: 8.0x ATR(14) from fill price (R:R = 4:1)\n")
    f.write("- Time Exit: 200 bars (3.3 hours)\n")
    f.write("- Fees: 0.1% round-trip (0.05% entry + 0.05% exit)\n\n")

    f.write("---\n\n")
    f.write("## Analysis\n\n")
    f.write(f"### Dataset Size Note\n\n")
    f.write(f"⚠️ **Limited Sample:** PIPPIN data covers only {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days} days ")
    f.write(f"compared to FARTCOIN's 32-day baseline. With only {len(trades_df)} trades, results may not be ")
    f.write(f"statistically significant. Longer testing period recommended before live deployment.\n\n")

    f.write("### Why It Worked (or Didn't)\n\n")
    if return_dd_ratio >= 5.0:
        f.write("**Strategy performed well on PIPPIN:**\n")
        f.write("- ATR expansion filter caught genuine volatility breakouts\n")
        f.write("- Limit orders successfully filtered fake breakouts\n")
        f.write("- Wide TP (8x ATR) captured explosive moves\n")
        f.write("- Tight SL (2x ATR) limited downside\n")
    elif return_dd_ratio >= 3.0:
        f.write("**Strategy showed moderate performance:**\n")
        f.write("- Some volatility breakouts identified but inconsistent follow-through\n")
        f.write("- Fill rate may need adjustment for PIPPIN's price action\n")
        f.write("- Consider testing with different parameters\n")
    else:
        f.write("**Strategy underperformed on PIPPIN:**\n")
        f.write("- PIPPIN may have different volatility characteristics than FARTCOIN\n")
        f.write("- Possible mean-reversion behavior instead of trending breakouts\n")
        f.write("- Limited fill rate or excessive stop-outs\n")

    f.write("\n### Comparison to FARTCOIN Baseline\n\n")
    rdd_diff = ((return_dd_ratio / 8.44) - 1) * 100
    f.write(f"- Return/DD: {return_dd_ratio:.2f}x vs 8.44x ({rdd_diff:+.0f}%)\n")
    f.write(f"- Total Return: {total_return:+.2f}% vs +101.11% ({((total_return/101.11)-1)*100:+.0f}%)\n")
    f.write(f"- Max Drawdown: {max_drawdown:.2f}% vs -11.98% ({'better' if abs(max_drawdown) < 11.98 else 'worse'})\n")
    f.write(f"- Win Rate: {win_rate:.1f}% vs 42.6% ({win_rate - 42.6:+.1f}pp)\n")
    f.write(f"- Trades: {len(trades_df)} vs 94 ({((len(trades_df)/94)-1)*100:+.0f}%)\n")

    f.write("\n---\n\n")
    f.write("## Recommendation\n\n")
    if return_dd_ratio >= 5.0:
        f.write("### ✅ DEPLOY TO BOT\n\n")
        f.write("The strategy shows strong risk-adjusted returns on PIPPIN data. ")
        f.write("However, note the limited sample size (7 days). Consider:\n\n")
        f.write("1. **Paper trading** for 2-4 weeks to validate results\n")
        f.write("2. **Start with small position sizes** (10-20% of normal)\n")
        f.write("3. **Monitor closely** for first 50 trades\n")
        f.write("4. **Compare live results** to backtest metrics\n\n")
        f.write("**Risk:** Sample size is 4x smaller than FARTCOIN baseline.\n")
    elif return_dd_ratio >= 3.0:
        f.write("### ⚠️ CONSIDER DEPLOYMENT (With Caution)\n\n")
        f.write("The strategy shows moderate risk-adjusted returns. Recommendations:\n\n")
        f.write("1. **Extend backtest** to 30+ days of data if available\n")
        f.write("2. **Paper trade first** to validate consistency\n")
        f.write("3. **Consider parameter optimization** for PIPPIN specifically\n")
        f.write("4. **Monitor drawdowns closely** in live trading\n\n")
        f.write("**Risk:** Performance below FARTCOIN baseline suggests different market behavior.\n")
    else:
        f.write("### ❌ DO NOT DEPLOY\n\n")
        f.write("The strategy shows insufficient risk-adjusted returns on PIPPIN. Issues:\n\n")
        f.write(f"1. **Low Return/DD ratio** ({return_dd_ratio:.2f}x vs 8.44x target)\n")
        f.write(f"2. **{len(trades_df)} trades may not be statistically significant**\n")
        f.write("3. **PIPPIN volatility profile may not suit this strategy**\n\n")
        f.write("**Alternative approaches:**\n")
        f.write("- Test mean-reversion strategies instead (DOGE-style)\n")
        f.write("- Try volume zone strategies (TRUMP/PEPE-style)\n")
        f.write("- Optimize parameters specifically for PIPPIN\n")
        f.write("- Collect more data (30+ days) for proper analysis\n")

    f.write("\n---\n\n")
    f.write("## Data Files\n\n")
    f.write(f"- **Data:** `trading/pippin_7d_bingx.csv` ({len(df):,} candles)\n")
    f.write(f"- **Code:** `trading/pippin_atr_strategy_test.py`\n")
    f.write(f"- **Trades:** `trading/results/pippin_atr_trades.csv` ({len(trades_df)} trades)\n")
    f.write(f"- **Report:** `trading/results/PIPPIN_ATR_STRATEGY_REPORT.md`\n")

print(f"✓ Report saved: {report_path}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print(f"\nRead the full report at: {report_path}")
print(f"View trade log at: {trades_csv_path}")
