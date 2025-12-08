#!/usr/bin/env python3
"""
Visualize PEPE's best strategy to understand why it failed to meet 2.0 R:R target
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Loading data and running best strategy...")
df = pd.read_csv('pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()

df = df.dropna().reset_index(drop=True)

# Run best strategy: BB Mean Reversion ATR 1.5x3
print("Running BB_MR_ATR1.5x3 strategy...")
entry = df['close'] < df['bb_lower']

trades = []
pos = None

for i in range(len(df)):
    r = df.iloc[i]

    if pos is None and entry.iloc[i]:
        pos = {
            'entry_time': r['timestamp'],
            'entry': r['close'],
            'sl': r['close'] - r['atr'] * 1.5,
            'tp': r['close'] + r['atr'] * 3.0,
            'idx': i
        }
    elif pos is not None:
        if r['low'] <= pos['sl']:
            pnl = ((pos['sl'] / pos['entry']) - 1) * 100 - 0.1
            trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': r['timestamp'],
                'pnl': pnl,
                'exit': 'SL',
                'duration': i - pos['idx']
            })
            pos = None
        elif r['high'] >= pos['tp']:
            pnl = ((pos['tp'] / pos['entry']) - 1) * 100 - 0.1
            trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': r['timestamp'],
                'pnl': pnl,
                'exit': 'TP',
                'duration': i - pos['idx']
            })
            pos = None

trades_df = pd.DataFrame(trades)
print(f"\nTrades: {len(trades_df)}")
print(f"Win Rate: {len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100:.1f}%")
print(f"Total PnL: {trades_df['pnl'].sum():.2f}%")

# Create visualization
fig, axes = plt.subplots(4, 1, figsize=(16, 12))

# 1. Equity Curve
trades_df['cumulative'] = trades_df['pnl'].cumsum()
trades_df['drawdown'] = trades_df['cumulative'] - trades_df['cumulative'].expanding().max()

ax1 = axes[0]
ax1.plot(trades_df.index, trades_df['cumulative'], linewidth=2, color='blue')
ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
ax1.fill_between(trades_df.index, 0, trades_df['cumulative'],
                  where=trades_df['cumulative'] >= 0, alpha=0.3, color='green', label='Profit')
ax1.fill_between(trades_df.index, 0, trades_df['cumulative'],
                  where=trades_df['cumulative'] < 0, alpha=0.3, color='red', label='Loss')
ax1.set_title('PEPE Best Strategy: BB Mean Reversion 1.5x/3x ATR - Equity Curve', fontsize=14, fontweight='bold')
ax1.set_ylabel('Cumulative PnL (%)', fontsize=11)
ax1.legend()
ax1.grid(alpha=0.3)

# Add stats text
stats_text = f"Total PnL: {trades_df['pnl'].sum():.1f}%\nMax DD: {abs(trades_df['drawdown'].min()):.1f}%\nR:R: {trades_df['pnl'].sum() / abs(trades_df['drawdown'].min()):.2f}"
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
         verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
         fontsize=10)

# 2. Drawdown
ax2 = axes[1]
ax2.fill_between(trades_df.index, 0, trades_df['drawdown'], alpha=0.5, color='red')
ax2.set_ylabel('Drawdown (%)', fontsize=11)
ax2.set_title('Drawdown Analysis', fontsize=12, fontweight='bold')
ax2.grid(alpha=0.3)

max_dd_idx = trades_df['drawdown'].idxmin()
ax2.annotate(f'Max DD: {trades_df["drawdown"].min():.1f}%',
             xy=(max_dd_idx, trades_df['drawdown'].min()),
             xytext=(max_dd_idx + 50, trades_df['drawdown'].min() + 5),
             arrowprops=dict(arrowstyle='->', color='red', lw=2),
             fontsize=10, color='red', fontweight='bold')

# 3. PnL Distribution
ax3 = axes[2]
wins = trades_df[trades_df['pnl'] > 0]['pnl']
losses = trades_df[trades_df['pnl'] <= 0]['pnl']

ax3.hist(wins, bins=30, alpha=0.7, color='green', label=f'Wins ({len(wins)})')
ax3.hist(losses, bins=30, alpha=0.7, color='red', label=f'Losses ({len(losses)})')
ax3.axvline(x=wins.mean(), color='darkgreen', linestyle='--', linewidth=2, label=f'Avg Win: {wins.mean():.2f}%')
ax3.axvline(x=losses.mean(), color='darkred', linestyle='--', linewidth=2, label=f'Avg Loss: {losses.mean():.2f}%')
ax3.set_xlabel('PnL per Trade (%)', fontsize=11)
ax3.set_ylabel('Frequency', fontsize=11)
ax3.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(alpha=0.3)

# 4. Exit Reasons
ax4 = axes[3]
exit_counts = trades_df['exit'].value_counts()
colors = ['green' if reason == 'TP' else 'red' for reason in exit_counts.index]
bars = ax4.bar(exit_counts.index, exit_counts.values, color=colors, alpha=0.7)
ax4.set_ylabel('Count', fontsize=11)
ax4.set_title('Exit Reasons (TP vs SL)', fontsize=12, fontweight='bold')
ax4.grid(alpha=0.3, axis='y')

# Add counts on bars
for bar, count in zip(bars, exit_counts.values):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'{count}\n({count/len(trades_df)*100:.1f}%)',
             ha='center', va='bottom', fontweight='bold', fontsize=11)

plt.tight_layout()
plt.savefig('results/pepe_best_strategy_analysis.png', dpi=150, bbox_inches='tight')
print("\nVisualization saved: results/pepe_best_strategy_analysis.png")

# Additional analysis
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)

print("\nTrade Duration:")
print(f"  Average: {trades_df['duration'].mean():.0f} minutes")
print(f"  Median: {trades_df['duration'].median():.0f} minutes")
print(f"  Min: {trades_df['duration'].min():.0f} minutes")
print(f"  Max: {trades_df['duration'].max():.0f} minutes")

print("\nWinning Trades:")
print(f"  Count: {len(wins)}")
print(f"  Average: {wins.mean():.2f}%")
print(f"  Median: {wins.median():.2f}%")
print(f"  Best: {wins.max():.2f}%")

print("\nLosing Trades:")
print(f"  Count: {len(losses)}")
print(f"  Average: {losses.mean():.2f}%")
print(f"  Median: {losses.median():.2f}%")
print(f"  Worst: {losses.min():.2f}%")

print("\nExit Analysis:")
tp_trades = trades_df[trades_df['exit'] == 'TP']
sl_trades = trades_df[trades_df['exit'] == 'SL']
print(f"  Take Profit hits: {len(tp_trades)} ({len(tp_trades)/len(trades_df)*100:.1f}%)")
print(f"  Stop Loss hits: {len(sl_trades)} ({len(sl_trades)/len(trades_df)*100:.1f}%)")

print("\nWhy R:R is only 0.74:")
print(f"  1. Win Rate too low: {len(wins)/len(trades_df)*100:.1f}% (need ~50%+)")
print(f"  2. Avg Win/Loss ratio: {abs(wins.mean()/losses.mean()):.2f}x (need 2.0x+)")
print(f"  3. Max DD too large: {abs(trades_df['drawdown'].min()):.1f}% relative to total PnL {trades_df['pnl'].sum():.1f}%")

print("\n" + "="*80)
print("Done!")
