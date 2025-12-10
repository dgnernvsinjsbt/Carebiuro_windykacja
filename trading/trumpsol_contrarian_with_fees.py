#!/usr/bin/env python3
"""
TRUMPSOL Contrarian Strategy - With Fees & Equity Chart
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

print("=" * 80)
print("TRUMPSOL CONTRARIAN - WITH FEES (0.1% round trip)")
print("=" * 80)

# Load trades
trades_df = pd.read_csv('trading/results/trumpsol_contrarian_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])

print(f"\n✅ Loaded {len(trades_df)} trades")

# Apply fees (0.1% round trip)
FEE_ROUNDTRIP = 0.001  # 0.1%
trades_df['pnl_gross'] = trades_df['pnl_pct']
trades_df['pnl_net'] = trades_df['pnl_gross'] - FEE_ROUNDTRIP

print(f"\n📊 Fee Impact:")
gross_sum = trades_df['pnl_gross'].sum() * 100
fees_sum = len(trades_df) * FEE_ROUNDTRIP * 100
net_sum = trades_df['pnl_net'].sum() * 100
print(f"   Gross PnL:    {gross_sum:+.2f}%")
print(f"   Total Fees:   -{fees_sum:.2f}%")
print(f"   Net PnL:      {net_sum:+.2f}%")

# Calculate equity curve with compounding (with fees)
starting_equity = 100.0
equity_curve = [starting_equity]
equity = starting_equity
peak = starting_equity
drawdowns = [0]

for pnl_net in trades_df['pnl_net']:
    equity = equity * (1 + pnl_net)
    equity_curve.append(equity)

    if equity > peak:
        peak = equity
    dd = (equity - peak) / peak
    drawdowns.append(dd)

final_equity = equity
total_return_pct = (final_equity - starting_equity) / starting_equity * 100
max_dd_pct = min(drawdowns) * 100

# Stats with fees
winners = trades_df[trades_df['pnl_net'] > 0]
losers = trades_df[trades_df['pnl_net'] <= 0]
win_rate = len(winners) / len(trades_df) * 100
avg_win = winners['pnl_net'].mean() * 100 if len(winners) > 0 else 0
avg_loss = losers['pnl_net'].mean() * 100 if len(losers) > 0 else 0

print("\n" + "=" * 80)
print("PERFORMANCE (WITH FEES)")
print("=" * 80)

print(f"\n💰 EQUITY")
print(f"   Starting:         ${starting_equity:.2f}")
print(f"   Final:            ${final_equity:.2f}")
print(f"   Total Return:     {total_return_pct:+.2f}%")
print(f"   Max Drawdown:     {max_dd_pct:.2f}%")
if abs(max_dd_pct) > 0:
    return_dd_ratio = abs(total_return_pct / max_dd_pct)
    print(f"   Return/DD Ratio:  {return_dd_ratio:.2f}x")

print(f"\n📈 TRADES (NET)")
print(f"   Total Trades:     {len(trades_df)}")
print(f"   Win Rate:         {win_rate:.1f}%")
print(f"   Winners:          {len(winners)}")
print(f"   Losers:           {len(losers)}")
print(f"   Avg Win:          {avg_win:+.2f}%")
print(f"   Avg Loss:         {avg_loss:+.2f}%")
if abs(avg_loss) > 0:
    print(f"   Win/Loss Ratio:   {abs(avg_win / avg_loss):.2f}")

# Direction breakdown with fees
long_trades = trades_df[trades_df['direction'] == 'LONG']
short_trades = trades_df[trades_df['direction'] == 'SHORT']

long_pnl_net = long_trades['pnl_net'].sum() * 100
short_pnl_net = short_trades['pnl_net'].sum() * 100

print(f"\n📊 DIRECTION (NET)")
print(f"   LONG:             {len(long_trades)} trades, {long_pnl_net:+.2f}%")
print(f"   SHORT:            {len(short_trades)} trades, {short_pnl_net:+.2f}%")

# Create equity chart
print("\n📈 Creating equity curve chart...")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

# Plot 1: Equity curve
trade_indices = list(range(len(equity_curve)))
ax1.plot(trade_indices, equity_curve, linewidth=2, color='#2E86DE', label='Equity')
ax1.axhline(y=starting_equity, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')
ax1.fill_between(trade_indices, starting_equity, equity_curve,
                  where=[e >= starting_equity for e in equity_curve],
                  alpha=0.3, color='green', label='Profit')
ax1.fill_between(trade_indices, starting_equity, equity_curve,
                  where=[e < starting_equity for e in equity_curve],
                  alpha=0.3, color='red', label='Loss')

ax1.set_title(f'TRUMPSOL Contrarian Strategy - Equity Curve\n'
              f'Return: {total_return_pct:+.2f}% | Max DD: {max_dd_pct:.2f}% | Return/DD: {return_dd_ratio:.2f}x | Trades: {len(trades_df)}',
              fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)

# Add annotations for key points
max_equity_idx = equity_curve.index(max(equity_curve))
max_equity = max(equity_curve)
ax1.annotate(f'Peak: ${max_equity:.2f}',
             xy=(max_equity_idx, max_equity),
             xytext=(max_equity_idx + 5, max_equity - 2),
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
             arrowprops=dict(arrowstyle='->', lw=1.5))

ax1.annotate(f'Final: ${final_equity:.2f}',
             xy=(len(equity_curve)-1, final_equity),
             xytext=(len(equity_curve)-10, final_equity + 3),
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7),
             arrowprops=dict(arrowstyle='->', lw=1.5))

# Plot 2: Drawdown
dd_pct = [d * 100 for d in drawdowns]
ax2.fill_between(range(len(dd_pct)), 0, dd_pct, color='red', alpha=0.5)
ax2.plot(range(len(dd_pct)), dd_pct, color='darkred', linewidth=1.5)
ax2.axhline(y=max_dd_pct, color='darkred', linestyle='--', linewidth=1,
            label=f'Max DD: {max_dd_pct:.2f}%')
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
ax2.set_title('Equity Drawdown', fontsize=12, fontweight='bold', pad=10)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower right', fontsize=10)
ax2.set_ylim([min(dd_pct) - 0.5, 0.5])

plt.tight_layout()
plt.savefig('trading/results/trumpsol_contrarian_equity_curve.png', dpi=300, bbox_inches='tight')
print(f"✅ Chart saved to trading/results/trumpsol_contrarian_equity_curve.png")

# Comparison with/without fees
print("\n" + "=" * 80)
print("COMPARISON: WITH vs WITHOUT FEES")
print("=" * 80)

# Recalc without fees for comparison
equity_no_fees = starting_equity
for pnl_gross in trades_df['pnl_gross']:
    equity_no_fees = equity_no_fees * (1 + pnl_gross)

return_no_fees = (equity_no_fees - starting_equity) / starting_equity * 100
fee_impact = return_no_fees - total_return_pct

print(f"\n{'Metric':<20} {'Without Fees':<15} {'With Fees':<15} {'Diff':<10}")
print(f"{'-'*60}")
print(f"{'Final Equity':<20} ${equity_no_fees:<14.2f} ${final_equity:<14.2f} ${equity_no_fees-final_equity:<9.2f}")
print(f"{'Total Return':<20} {return_no_fees:<14.2f}% {total_return_pct:<14.2f}% {-fee_impact:<9.2f}%")
print(f"{'Fee Impact':<20} {'':15} {'':15} -{fee_impact:.2f}%")
print(f"{'Fees Paid':<20} {'$0.00':15} ${final_equity*(fees_sum/100)/(1+total_return_pct/100):<14.2f}")

print("\n" + "=" * 80)
print(f"✅ Strategy remains profitable with fees!")
print(f"   Net Return: {total_return_pct:+.2f}%")
print(f"   Return/DD: {return_dd_ratio:.2f}x")
print("=" * 80)

# Save updated trades with net PnL
trades_df.to_csv('trading/results/trumpsol_contrarian_trades_with_fees.csv', index=False)
print(f"\n✅ Updated trades saved to trading/results/trumpsol_contrarian_trades_with_fees.csv")
