#!/usr/bin/env python3
"""
Compare LBank vs BingX data characteristics
Analyze why backtest results differ
"""
import pandas as pd
import numpy as np

print("=" * 70)
print("LBANK VS BINGX DATA COMPARISON")
print("=" * 70)

# We don't have LBank data, so let's analyze BingX characteristics
# and compare trade results

print("\n📊 LOADING BINGX BACKTEST RESULTS...")

# Load BingX 6-month trades
bingx_trades = pd.read_csv('melania_6months_short_only.csv')
bingx_trades['entry_time'] = pd.to_datetime(bingx_trades['entry_time'])
bingx_trades['exit_time'] = pd.to_datetime(bingx_trades['exit_time'])
bingx_trades['duration_hours'] = (bingx_trades['exit_time'] - bingx_trades['entry_time']).dt.total_seconds() / 3600

# Load BingX data to analyze characteristics
df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

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
df['returns'] = df['close'].pct_change() * 100

print("\n" + "=" * 70)
print("BINGX DATA CHARACTERISTICS")
print("=" * 70)

print(f"\nPrice Action:")
print(f"  Start: ${df.iloc[0]['close']:.6f}")
print(f"  End: ${df.iloc[-1]['close']:.6f}")
print(f"  Change: {((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100):.2f}%")
print(f"  High: ${df['close'].max():.6f}")
print(f"  Low: ${df['close'].min():.6f}")

print(f"\nVolatility:")
print(f"  Avg ATR: ${df['atr'].mean():.6f}")
print(f"  Avg ATR %: {(df['atr'] / df['close'] * 100).mean():.2f}%")
print(f"  Avg 15m return: {df['returns'].mean():.4f}%")
print(f"  Std dev: {df['returns'].std():.4f}%")

print(f"\nRSI Distribution:")
rsi_counts = {
    '< 30 (oversold)': len(df[df['rsi'] < 30]),
    '30-40': len(df[(df['rsi'] >= 30) & (df['rsi'] < 40)]),
    '40-60 (neutral)': len(df[(df['rsi'] >= 40) & (df['rsi'] < 60)]),
    '60-70': len(df[(df['rsi'] >= 60) & (df['rsi'] < 70)]),
    '> 70 (overbought)': len(df[df['rsi'] > 70])
}

for range_name, count in rsi_counts.items():
    pct = count / len(df) * 100
    print(f"  {range_name}: {count} ({pct:.1f}%)")

print(f"\nSignal Opportunities (RSI crosses):")
prev_rsi = df['rsi'].shift(1)
rsi_cross_above_65 = ((prev_rsi > 65) & (df['rsi'] <= 65)).sum()
rsi_cross_below_35 = ((prev_rsi < 35) & (df['rsi'] >= 35)).sum()
print(f"  RSI crosses below 65 (SHORT signals): {rsi_cross_above_65}")
print(f"  RSI crosses above 35 (LONG signals): {rsi_cross_below_35}")

print("\n" + "=" * 70)
print("BINGX TRADE ANALYSIS")
print("=" * 70)

print(f"\nTrade Execution:")
print(f"  Total trades: {len(bingx_trades)}")
print(f"  Avg duration: {bingx_trades['duration_hours'].mean():.1f} hours")
print(f"  Median duration: {bingx_trades['duration_hours'].median():.1f} hours")

winners = bingx_trades[bingx_trades['pnl_dollar'] > 0]
losers = bingx_trades[bingx_trades['pnl_dollar'] <= 0]

print(f"\nWinners ({len(winners)}):")
print(f"  Avg P&L: +${winners['pnl_dollar'].mean():.2f}")
print(f"  Avg duration: {winners['duration_hours'].mean():.1f} hours")
print(f"  Largest win: +${winners['pnl_dollar'].max():.2f}")

print(f"\nLosers ({len(losers)}):")
print(f"  Avg P&L: ${losers['pnl_dollar'].mean():.2f}")
print(f"  Avg duration: {losers['duration_hours'].mean():.1f} hours")
print(f"  Largest loss: ${losers['pnl_dollar'].min():.2f}")

print(f"\nExit Analysis:")
tp_trades = bingx_trades[bingx_trades['exit_reason'] == 'TP']
sl_trades = bingx_trades[bingx_trades['exit_reason'] == 'SL']
print(f"  TP hits: {len(tp_trades)} ({len(tp_trades)/len(bingx_trades)*100:.1f}%)")
print(f"  SL hits: {len(sl_trades)} ({len(sl_trades)/len(bingx_trades)*100:.1f}%)")

print("\n" + "=" * 70)
print("HYPOTHETICAL LBANK COMPARISON")
print("=" * 70)
print("\nLBank Results (from original backtest):")
print("  Return: +3,441%")
print("  Max DD: -64.40%")
print("  R/DD: 53.43x")
print("  Win Rate: 38.1% (53W/86L)")
print("  Trades: 139 (includes LONG + SHORT)")
print("  Period: 7 months (Jun-Dec)")

print("\nBingX Results (SHORT-only):")
print(f"  Return: +582.9%")
print(f"  Max DD: -59.90%")
print(f"  R/DD: 9.73x")
print(f"  Win Rate: 33.9% ({len(winners)}W/{len(losers)}L)")
print(f"  Trades: {len(bingx_trades)} (SHORT only)")
print(f"  Period: 6 months (Jun-Dec, missing July end)")

print("\n" + "=" * 70)
print("KEY DIFFERENCES")
print("=" * 70)
print("\n1. TRADE COUNT:")
print(f"   LBank: 139 trades (7 months) = 19.9/month")
print(f"   BingX: {len(bingx_trades)} trades (6 months) = {len(bingx_trades)/6:.1f}/month")
print(f"   Difference: BingX has {len(bingx_trades) - 139} MORE trades")
print(f"   → BingX generates {((len(bingx_trades)/6) / (139/7) - 1) * 100:.1f}% more signals")

print("\n2. WIN RATE:")
print(f"   LBank: 38.1% (both LONG + SHORT)")
print(f"   BingX: 33.9% (SHORT only)")
print(f"   Difference: -{(38.1 - 33.9):.1f}% (BingX worse)")
print(f"   → More losing trades on BingX")

print("\n3. STOP LOSS HIT RATE:")
print(f"   LBank: {86/139*100:.1f}% SL rate")
print(f"   BingX: {len(sl_trades)/len(bingx_trades)*100:.1f}% SL rate")
print(f"   Difference: {(len(sl_trades)/len(bingx_trades)*100) - (86/139*100):.1f}%")
print(f"   → BingX hits SL much more frequently!")

print("\n4. RETURNS:")
print(f"   LBank: +3,441% (5.9x better)")
print(f"   BingX: +582.9%")
print(f"   → LBank had MUCH better winning trades or compounding")

print("\n" + "=" * 70)
print("HYPOTHESIS: Why BingX Underperforms")
print("=" * 70)
print("\n1. Higher signal frequency = more noise trades")
print("   - BingX may have more RSI whipsaws")
print("   - More false signals in choppy conditions")
print()
print("2. Lower win rate despite similar setup")
print("   - BingX price action may be choppier")
print("   - More stop-outs before TP is reached")
print()
print("3. Missing LONG trades")
print("   - LBank had profitable LONG trades in original backtest")
print("   - BingX LONG trades all failed (0/4)")
print("   - Losing directional edge on BingX")
print()
print("4. Different exchange dynamics")
print("   - LBank vs BingX have different liquidity")
print("   - Different trader behavior/order flow")
print("   - Price action characteristics differ")

print("\n" + "=" * 70)
