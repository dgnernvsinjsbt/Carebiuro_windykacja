#!/usr/bin/env python3
"""
Continue the Sep 15 - Dec 7 backtest forward through Dec 8-15
Starting capital: $134.93 (ending capital from Dec 7)
Peak capital: $134.93 (from Dec 7)

This will show the TRUE portfolio drawdown including the Dec 8-15 period.
"""

import pandas as pd
import numpy as np

# Load Dec 8-15 trades
dec_trades = pd.read_csv('dec8_15_all_trades.csv')
dec_trades['entry_time'] = pd.to_datetime(dec_trades['entry_time'])

# Starting state from Sep 15 - Dec 7 backtest
starting_capital = 134.92779520095166  # Ending capital from Dec 7
peak_capital = 134.92779520095166  # Peak from entire Sep-Dec 7 period

print("=" * 80)
print("CONTINUATION: Dec 8-15 Portfolio Performance")
print("=" * 80)
print(f"Starting Capital (from Dec 7): ${starting_capital:.2f}")
print(f"Peak Capital (from Sep-Dec 7): ${peak_capital:.2f}")
print()

# Sort trades chronologically
dec_trades = dec_trades.sort_values('entry_time').reset_index(drop=True)

capital = starting_capital
current_peak = peak_capital
max_dd_pct = 0.0

for idx, trade in dec_trades.iterrows():
    position_size = capital * 0.10
    pnl_usd = position_size * (trade['pnl_pct'] / 100)
    capital += pnl_usd

    # Update peak
    if capital > current_peak:
        current_peak = capital

    # Calculate drawdown
    dd_pct = ((capital - current_peak) / current_peak) * 100
    if dd_pct < max_dd_pct:
        max_dd_pct = dd_pct

# Final metrics
final_capital = capital
total_return_pct = ((final_capital - starting_capital) / starting_capital) * 100
overall_return_from_start = ((final_capital - 100) / 100) * 100

# Max DD from original Sep-Dec 7 period
original_max_dd = -1.08

# Combined max DD
combined_max_dd = min(original_max_dd, max_dd_pct)

print(f"\n📊 DEC 8-15 PERFORMANCE (Continuation):")
print(f"  Starting Capital: ${starting_capital:.2f}")
print(f"  Final Capital: ${final_capital:.2f}")
print(f"  Return (Dec 8-15 only): {total_return_pct:+.2f}%")
print(f"  Max DD (Dec 8-15 only): {max_dd_pct:.2f}%")

print(f"\n📊 COMBINED PORTFOLIO (Sep 15 - Dec 15):")
print(f"  Starting Capital: $100.00")
print(f"  Final Capital: ${final_capital:.2f}")
print(f"  Total Return: {overall_return_from_start:+.2f}%")
print(f"  Max DD (Sep-Dec 7): {original_max_dd:.2f}%")
print(f"  Max DD (Dec 8-15): {max_dd_pct:.2f}%")
print(f"  **COMBINED MAX DD: {combined_max_dd:.2f}%**")
print(f"  Return/DD Ratio: {abs(overall_return_from_start / combined_max_dd):.2f}x")

print(f"\n⚠️ ANALYSIS:")
if abs(max_dd_pct) > abs(original_max_dd):
    print(f"  The Dec 8-15 period WAS WORSE than the entire Sep-Dec 7 period.")
    print(f"  New max DD: {max_dd_pct:.2f}% (vs {original_max_dd:.2f}% previously)")
    print(f"  This represents a {abs((max_dd_pct / original_max_dd - 1) * 100):.1f}% increase in max drawdown.")
else:
    print(f"  The Dec 8-15 period was NOT worse than Sep-Dec 7.")
    print(f"  Max DD remains: {original_max_dd:.2f}%")
