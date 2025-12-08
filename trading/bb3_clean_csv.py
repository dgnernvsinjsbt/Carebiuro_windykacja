#!/usr/bin/env python3
"""Generate clean CSV with profit already including fees"""
import pandas as pd

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_final_optimized.csv')

# Rename and select columns for clarity
clean = pd.DataFrame({
    'trade': df['trade_num'],
    'entry_time': df['entry_time'],
    'exit_time': df['exit_time'],
    'type': df['type'],
    'entry_price': df['signal_price'],
    'stop_loss': df['stop'],
    'take_profit': df['target'],
    'filled': df['filled'],
    'result': df['result'],
    'position_size': df['size'],
    'profit_pct': df['net_pnl_pct'].round(4),  # ALREADY INCLUDES 0.07% FEES
    'profit_usd': df['pnl_dollar'].round(2),   # ALREADY INCLUDES FEES
    'balance': df['running_balance'].round(2),
    'winner': df['winner']
})

# Add summary row
filled = clean[clean['filled'] == 'YES']
wins = len(filled[filled['winner'] == 'WIN'])
losses = len(filled[filled['winner'] == 'LOSS'])

print("=" * 80)
print("BB3 OPTIMIZED STRATEGY - CLEAN CSV")
print("=" * 80)
print(f"\nAll profits ALREADY INCLUDE 0.07% round-trip fees (0.02% maker + 0.05% taker)")
print(f"\nTotal trades: {len(filled)} ({len(clean[clean['type']=='LONG'])} LONG / {len(clean[clean['type']=='SHORT'])} SHORT)")
print(f"Wins/Losses: {wins}/{losses} ({wins/len(filled)*100:.1f}% win rate)")
print(f"Total profit: ${filled['profit_usd'].sum():+,.2f}")
print(f"Final balance: ${clean['balance'].iloc[-1]:,.2f}")

# Calculate max drawdown
import numpy as np
bal = np.array([10000] + list(clean['balance']))
peak = np.maximum.accumulate(bal)
dd = (bal - peak) / peak * 100
print(f"Max drawdown: {dd.min():.2f}%")
print(f"Risk:Reward: {filled['profit_usd'].sum() / abs(dd.min() * 100):.2f}x")

clean.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_optimized_clean.csv', index=False)
print(f"\nSaved: results/bb3_optimized_clean.csv")
print("=" * 80)

# Show first and last few trades
print("\nFirst 5 trades:")
print(clean.head().to_string(index=False))
print("\nLast 5 trades:")
print(clean.tail().to_string(index=False))
