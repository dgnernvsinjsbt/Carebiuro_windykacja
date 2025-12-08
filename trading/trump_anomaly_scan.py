"""
TRUMP Strategy - Data Anomaly Scan
Checks for backtest artifacts before optimization
"""

import pandas as pd
import numpy as np

# Load results
trades = pd.read_csv('results/TRUMP_strategy_results.csv')
data = pd.read_csv('trump_usdt_1m_mexc.csv')

print("="*80)
print("TRUMP STRATEGY - DATA ANOMALY SCAN")
print("="*80)

# ============================================================================
# 1. PROFIT CONCENTRATION CHECK
# ============================================================================
print("\n1. PROFIT CONCENTRATION ANALYSIS")
print("-"*80)

trades_sorted = trades.sort_values('pnl_dollars', ascending=False)
total_pnl = trades['pnl_dollars'].sum()

print(f"Total PnL: ${total_pnl:.2f}")
print(f"Total Trades: {len(trades)}")
print(f"Winning Trades: {len(trades[trades['pnl_dollars'] > 0])}")
print(f"Losing Trades: {len(trades[trades['pnl_dollars'] < 0])}")

# Top 5 winners
top5_winners = trades_sorted.head(5)
top5_pnl = top5_winners['pnl_dollars'].sum()
top5_pct = (top5_pnl / total_pnl * 100) if total_pnl != 0 else 0

print(f"\nTop 5 Winning Trades:")
for idx, trade in top5_winners.iterrows():
    pnl_contribution = (trade['pnl_dollars'] / total_pnl * 100) if total_pnl != 0 else 0
    print(f"  {trade['entry_time']} → ${trade['pnl_dollars']:.2f} ({trade['pnl_pct']:.2f}%) [{trade['exit_reason']}]")

print(f"\nTop 5 contribute: ${top5_pnl:.2f}")

# Bottom 5 losers
bottom5_losers = trades_sorted.tail(5)
bottom5_pnl = bottom5_losers['pnl_dollars'].sum()

print(f"\nTop 5 Losing Trades:")
for idx, trade in bottom5_losers.iterrows():
    print(f"  {trade['entry_time']} → ${trade['pnl_dollars']:.2f} ({trade['pnl_pct']:.2f}%) [{trade['exit_reason']}]")

print(f"\nBottom 5 contribute: ${bottom5_pnl:.2f}")

# Check if profitable without top 5
pnl_without_top5 = total_pnl - top5_pnl
print(f"\nPnL WITHOUT top 5 winners: ${pnl_without_top5:.2f}")
print(f"{'✓ PASS' if pnl_without_top5 > 0 else '✗ FAIL'} - Strategy {'IS' if pnl_without_top5 > 0 else 'NOT'} profitable without outliers")

# Check for trades >5% of total
trades['pnl_contribution'] = trades['pnl_dollars'].abs() / abs(total_pnl) * 100 if total_pnl != 0 else 0
big_trades = trades[trades['pnl_contribution'] > 5]
print(f"\nTrades contributing >5% of |total PnL|: {len(big_trades)}")
if len(big_trades) > 0:
    for idx, trade in big_trades.iterrows():
        print(f"  {trade['entry_time']}: ${trade['pnl_dollars']:.2f} ({trade['pnl_contribution']:.1f}%)")

# ============================================================================
# 2. DATA GAP DETECTION
# ============================================================================
print("\n\n2. DATA GAP & QUALITY CHECK")
print("-"*80)

data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.sort_values('timestamp').reset_index(drop=True)

# Check for duplicates
duplicates = data.duplicated(subset=['timestamp']).sum()
print(f"Duplicate timestamps: {duplicates}")

# Check for zero volume
zero_vol = (data['volume'] == 0).sum()
print(f"Zero volume candles: {zero_vol} ({zero_vol/len(data)*100:.2f}%)")

# Check for missing candles (gaps >1 minute)
data['time_diff'] = data['timestamp'].diff().dt.total_seconds() / 60
gaps = data[data['time_diff'] > 1.5]
print(f"Time gaps (>1 min): {len(gaps)}")
if len(gaps) > 0:
    print("  Largest gaps:")
    for _, row in gaps.nlargest(min(3, len(gaps)), 'time_diff').iterrows():
        print(f"    {row['timestamp']}: {row['time_diff']:.0f} minutes")

# Check for unrealistic price spikes
data['body_pct'] = abs(data['close'] - data['open']) / data['open'] * 100
spikes = data[data['body_pct'] > 10]
print(f"\nPrice spikes >10%: {len(spikes)}")
if len(spikes) > 0:
    for _, row in spikes.head(5).iterrows():
        print(f"  {row['timestamp']}: {row['body_pct']:.2f}% (${row['open']:.3f} → ${row['close']:.3f})")

# ============================================================================
# 3. TRADE CALCULATION AUDIT
# ============================================================================
print("\n\n3. TRADE CALCULATION AUDIT (5 Random Trades)")
print("-"*80)

sample_trades = trades.sample(min(5, len(trades)), random_state=42)
for idx, trade in sample_trades.iterrows():
    entry = trade['entry_price']
    exit_price = trade['exit_price']
    sl = trade['stop_loss']
    tp = trade['take_profit']
    pnl_pct = trade['pnl_pct']

    # Infer direction from SL/TP
    if sl < entry and tp > entry:
        direction = 'LONG'
        expected_pnl = ((exit_price - entry) / entry) * 100
    else:
        direction = 'SHORT'
        expected_pnl = ((entry - exit_price) / entry) * 100

    # Account for fees (~0.1% total)
    pnl_match = abs(expected_pnl - pnl_pct) < 0.15

    print(f"\n{direction} @ ${entry:.3f} [{trade['exit_reason']}]")
    print(f"  Exit: ${exit_price:.3f} | SL: ${sl:.3f} | TP: ${tp:.3f}")
    print(f"  PnL: {pnl_pct:.2f}% (Expected: {expected_pnl:.2f}%)")
    print(f"  ✓ VALID" if pnl_match else f"  ✗ MISMATCH")

# ============================================================================
# 4. TIME DISTRIBUTION
# ============================================================================
print("\n\n4. TIME DISTRIBUTION ANALYSIS")
print("-"*80)

trades['entry_time'] = pd.to_datetime(trades['entry_time'])
trades['date'] = trades['entry_time'].dt.date
trades['hour'] = trades['entry_time'].dt.hour

# Daily PnL
daily_pnl = trades.groupby('date')['pnl_dollars'].sum().sort_values(ascending=False)
print(f"\nBest trading day: {daily_pnl.index[0]} → ${daily_pnl.iloc[0]:.2f} ({daily_pnl.iloc[0]/total_pnl*100:.1f}% of total)")
print(f"Worst trading day: {daily_pnl.index[-1]} → ${daily_pnl.iloc[-1]:.2f}")

# Check concentration
days_positive = (daily_pnl > 0).sum()
days_negative = (daily_pnl < 0).sum()
print(f"\nPositive days: {days_positive} | Negative days: {days_negative}")

# Hourly PnL
hourly_pnl = trades.groupby('hour')['pnl_dollars'].sum().sort_values(ascending=False)
print(f"\nBest hour: {hourly_pnl.index[0]:02d}:00 → ${hourly_pnl.iloc[0]:.2f}")
print(f"Worst hour: {hourly_pnl.index[-1]:02d}:00 → ${hourly_pnl.iloc[-1]:.2f}")

# ============================================================================
# 5. EXIT REASON ANALYSIS
# ============================================================================
print("\n\n5. EXIT REASON ANALYSIS")
print("-"*80)

exit_stats = trades.groupby('exit_reason').agg({
    'pnl_dollars': ['sum', 'mean', 'count']
}).round(2)

print(exit_stats)

# ============================================================================
# 6. ANOMALY SUMMARY TABLE
# ============================================================================
print("\n\n6. ANOMALY SUMMARY")
print("="*80)

anomalies = {
    'Total Return': f"${total_pnl:.2f}",
    'Profitable without top 5': 'YES' if pnl_without_top5 > 0 else 'NO',
    'Trades >5% of total PnL': len(big_trades),
    'Duplicate candles': duplicates,
    'Zero volume candles': zero_vol,
    'Time gaps detected': len(gaps),
    'Price spikes >10%': len(spikes),
    'Best day % of total': f"{(daily_pnl.iloc[0] / total_pnl * 100) if total_pnl != 0 else 0:.1f}%",
    'Positive days': days_positive,
    'Negative days': days_negative
}

for key, value in anomalies.items():
    print(f"{key:<30} {value:>15}")

print("\n" + "="*80)
print("VERDICT:")
print("="*80)

issues = []
if abs(top5_pct) > 80:
    issues.append("⚠️  Strategy relies heavily on outlier trades")
if duplicates > 0 or len(spikes) > 0:
    issues.append("⚠️  Data quality issues detected")
if pnl_without_top5 < 0 and total_pnl > 0:
    issues.append("⚠️  Strategy unprofitable without top trades")
if total_pnl < 0:
    issues.append("⚠️  STRATEGY IS UNPROFITABLE OVERALL")
if days_negative > days_positive:
    issues.append("⚠️  More losing days than winning days")

if issues:
    for issue in issues:
        print(issue)
else:
    print("✓ CLEAN: No major data anomalies detected")

print("="*80)

# Save summary
summary_data = {
    'metric': list(anomalies.keys()),
    'value': list(anomalies.values())
}
pd.DataFrame(summary_data).to_csv('results/TRUMP_anomaly_scan.csv', index=False)
print("\nAnomaly scan saved to: results/TRUMP_anomaly_scan.csv")
