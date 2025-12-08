"""
Show FARTCOIN equity curve from October 1st to today
Using the complete optimized strategy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = ranges.max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter from October 1st onwards
start_date = pd.to_datetime('2024-10-01')
df = df[df['timestamp'] >= start_date].copy()
df = df.reset_index(drop=True)

print("="*100)
print("FARTCOIN EQUITY CURVE - OCTOBER 1ST TO NOW")
print("="*100)
print(f"\nData Range: {df['timestamp'].min().strftime('%Y-%m-%d %H:%M')} to {df['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
print(f"Total Candles: {len(df)}")

# Calculate indicators
df['ema_3'] = calculate_ema(df, 3)
df['ema_15'] = calculate_ema(df, 15)
df['momentum_7d'] = df['close'].pct_change(336) * 100
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['rsi'] = calculate_rsi(df)

# Optimized filter
df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

# Run backtest
trades = []
in_position = False
entry_price = 0
entry_date = None
entry_atr = 0
stop_loss = 0
take_profit = 0
fee = 0.0001

for i in range(1, len(df)):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    if not in_position:
        if (row['ema_3'] < row['ema_15'] and
            prev_row['ema_3'] >= prev_row['ema_15'] and
            row['allow_short']):

            in_position = True
            entry_price = row['close']
            entry_date = row['timestamp']
            entry_atr = row['atr_pct']

            # Fixed SL: 3%
            stop_loss = entry_price * 1.03

            # Adaptive TP: 3x ATR (4-15% range)
            tp_ratio = min(max(entry_atr / 100 * 3.0, 0.04), 0.15)
            take_profit = entry_price * (1 - tp_ratio)

    else:
        exit_type = None
        exit_price = None

        if row['high'] >= stop_loss:
            exit_price = stop_loss
            exit_type = 'SL'
            pnl = (entry_price - stop_loss) / entry_price - fee
        elif row['low'] <= take_profit:
            exit_price = take_profit
            exit_type = 'TP'
            pnl = (entry_price - take_profit) / entry_price - fee

        if exit_type:
            trades.append({
                'entry_date': entry_date,
                'exit_date': row['timestamp'],
                'pnl_pct': pnl * 100,
                'exit_type': exit_type,
                'win': pnl > 0
            })
            in_position = False

trades_df = pd.DataFrame(trades)
trades_df = trades_df.sort_values('exit_date').reset_index(drop=True)

print(f"\nTotal Trades: {len(trades_df)}")
print(f"Winners: {len(trades_df[trades_df['win']])} ({len(trades_df[trades_df['win']])/len(trades_df)*100:.1f}%)")
print(f"Losers: {len(trades_df[~trades_df['win']])} ({len(trades_df[~trades_df['win']])/len(trades_df)*100:.1f}%)")

# Calculate equity with dynamic position sizing
equity = 1.0
position_size = 1.0
equity_curve = [equity]
dates = [trades_df.iloc[0]['entry_date']]
position_sizes = [position_size]

for _, trade in trades_df.iterrows():
    trade_pnl = trade['pnl_pct'] * position_size
    equity *= (1 + trade_pnl / 100)
    equity_curve.append(equity)
    dates.append(trade['exit_date'])

    # Dynamic sizing: +25%/-3%
    if trade['pnl_pct'] > 0:
        position_size = min(position_size + 0.25, 2.0)
    else:
        position_size = max(position_size - 0.03, 0.5)

    position_sizes.append(position_size)

# Calculate metrics
equity_series = pd.Series(equity_curve)
running_max = equity_series.expanding().max()
drawdown = (equity_series - running_max) / running_max * 100
max_dd = drawdown.min()
max_dd_idx = drawdown.idxmin()
total_return = (equity - 1) * 100

print(f"\n{'='*100}")
print("COMPLETE OPTIMIZED STRATEGY PERFORMANCE")
print(f"{'='*100}")
print(f"\nTotal Return: {total_return:.2f}%")
print(f"Final Equity: {equity:.2f}x")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Risk-Reward Ratio: {total_return / abs(max_dd):.2f}")
print(f"\nAvg Win: {trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean():.2f}%")
print(f"Avg Loss: {trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean():.2f}%")

# Find max drawdown date
max_dd_date = dates[max_dd_idx]
print(f"\nMax Drawdown occurred at: {max_dd_date.strftime('%Y-%m-%d %H:%M')}")

# Create visualization
fig = plt.figure(figsize=(20, 14))
gs = fig.add_gridspec(4, 2, height_ratios=[3, 1.5, 1.5, 1])

ax1 = fig.add_subplot(gs[0, :])  # Equity curve (full width)
ax2 = fig.add_subplot(gs[1, :])  # Drawdown (full width)
ax3 = fig.add_subplot(gs[2, 0])  # Position size
ax4 = fig.add_subplot(gs[2, 1])  # Trade PnL distribution
ax5 = fig.add_subplot(gs[3, :])  # Key metrics table

# Plot 1: Equity Curve with milestones
ax1.plot(dates, equity_curve, linewidth=3, color='#2E86AB', alpha=0.9, label='Equity')
ax1.fill_between(dates, 1, equity_curve, alpha=0.2, color='#2E86AB')

# Mark 2x, 5x, 10x levels
milestones = [2, 5, 10]
for milestone in milestones:
    if equity >= milestone:
        milestone_idx = next(i for i, e in enumerate(equity_curve) if e >= milestone)
        milestone_date = dates[milestone_idx]
        ax1.axhline(y=milestone, color='gray', linestyle='--', alpha=0.4, linewidth=1)
        ax1.scatter(milestone_date, milestone, s=200, color='gold', zorder=5, edgecolors='black', linewidths=2)
        ax1.annotate(f'{milestone}x\n{milestone_date.strftime("%b %d")}',
                    xy=(milestone_date, milestone),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

# Mark max drawdown point
ax1.scatter(max_dd_date, equity_curve[max_dd_idx], s=300, color='red', zorder=5,
           marker='v', edgecolors='black', linewidths=2, label='Max DD')

ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
ax1.set_ylabel('Equity Multiple', fontsize=13, fontweight='bold')
ax1.set_title(f'FARTCOIN Complete Optimized Strategy: Oct 1st - {df["timestamp"].max().strftime("%b %d, %Y")}\n' +
              f'Final: {equity:.2f}x ({total_return:.1f}%) | Max DD: {max_dd:.1f}% | R:R: {total_return/abs(max_dd):.2f}',
              fontsize=16, fontweight='bold', pad=20)
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, alpha=0.3)
ax1.set_xticks([])

# Plot 2: Drawdown
ax2.fill_between(dates, 0, drawdown, color='#C73E1D', alpha=0.6)
ax2.plot(dates, drawdown, linewidth=2, color='#C73E1D', alpha=0.9)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5, linewidth=1)
ax2.scatter(max_dd_date, max_dd, s=200, color='red', zorder=5, marker='v',
           edgecolors='black', linewidths=2)
ax2.annotate(f'Max DD: {max_dd:.1f}%\n{max_dd_date.strftime("%b %d")}',
            xy=(max_dd_date, max_dd),
            xytext=(20, -20), textcoords='offset points',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.3),
            arrowprops=dict(arrowstyle='->', color='red', lw=2))
ax2.set_ylabel('Drawdown %', fontsize=11, fontweight='bold')
ax2.set_title('Drawdown Over Time', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_xticks([])

# Plot 3: Position Size Evolution
ax3.plot(dates, position_sizes, linewidth=2, color='#F18F01', alpha=0.9)
ax3.fill_between(dates, 0.5, position_sizes, alpha=0.3, color='#F18F01')
ax3.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax3.axhline(y=0.5, color='red', linestyle=':', alpha=0.5, linewidth=1)
ax3.axhline(y=2.0, color='green', linestyle=':', alpha=0.5, linewidth=1)
ax3.set_ylabel('Position Size (x)', fontsize=11, fontweight='bold')
ax3.set_title('Dynamic Position Sizing (+25%/-3%)', fontsize=12, fontweight='bold')
ax3.set_ylim([0.4, 2.1])
ax3.grid(True, alpha=0.3)
ax3.set_xlabel('Date', fontsize=11)

# Format x-axis
ax3.tick_params(axis='x', rotation=45)

# Plot 4: Trade PnL Distribution
winners = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct']
losers = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct']

bins = np.linspace(-4, 16, 40)
ax4.hist(winners, bins=bins, alpha=0.7, color='green', label=f'Winners ({len(winners)})', edgecolor='black')
ax4.hist(losers, bins=bins, alpha=0.7, color='red', label=f'Losers ({len(losers)})', edgecolor='black')
ax4.axvline(x=0, color='black', linestyle='-', linewidth=2)
ax4.axvline(x=winners.mean(), color='green', linestyle='--', linewidth=2, alpha=0.7,
           label=f'Avg Win: {winners.mean():.2f}%')
ax4.axvline(x=losers.mean(), color='red', linestyle='--', linewidth=2, alpha=0.7,
           label=f'Avg Loss: {losers.mean():.2f}%')
ax4.set_xlabel('Trade PnL %', fontsize=11)
ax4.set_ylabel('Frequency', fontsize=11)
ax4.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
ax4.legend(loc='upper right', fontsize=9)
ax4.grid(True, alpha=0.3, axis='y')

# Plot 5: Key Metrics Table
ax5.axis('tight')
ax5.axis('off')

# Split trades by month
trades_df['month'] = trades_df['exit_date'].dt.to_period('M')
monthly_stats = []

for month in sorted(trades_df['month'].unique()):
    month_trades = trades_df[trades_df['month'] == month]
    month_winners = len(month_trades[month_trades['win']])
    month_wr = month_winners / len(month_trades) * 100 if len(month_trades) > 0 else 0

    # Calculate monthly return
    month_equity = 1.0
    month_pos_size = 1.0
    for _, trade in month_trades.iterrows():
        trade_pnl = trade['pnl_pct'] * month_pos_size
        month_equity *= (1 + trade_pnl / 100)
        if trade['pnl_pct'] > 0:
            month_pos_size = min(month_pos_size + 0.25, 2.0)
        else:
            month_pos_size = max(month_pos_size - 0.03, 0.5)

    month_return = (month_equity - 1) * 100

    monthly_stats.append([
        str(month),
        len(month_trades),
        f"{month_wr:.0f}%",
        f"{month_return:+.1f}%"
    ])

table_data = [['Month', 'Trades', 'Win Rate', 'Return']] + monthly_stats

table = ax5.table(cellText=table_data, cellLoc='center', loc='center',
                 colWidths=[0.3, 0.2, 0.25, 0.25])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)

# Style header row
for i in range(4):
    table[(0, i)].set_facecolor('#2E86AB')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Color rows by performance
for i in range(1, len(table_data)):
    return_val = float(table_data[i][3].rstrip('%'))
    color = '#90EE90' if return_val > 0 else '#FFB6C1'
    for j in range(4):
        table[(i, j)].set_facecolor(color)
        table[(i, j)].set_alpha(0.3)

plt.tight_layout()
plt.savefig('results/fartcoin_equity_oct_to_now.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Saved visualization to results/fartcoin_equity_oct_to_now.png")

print("\n" + "="*100)
print("STRATEGY COMPONENTS")
print("="*100)
print("\n✅ Entry: EMA 3 crosses below EMA 15 (SHORT)")
print("✅ Filters: Mom7d<0 + ATR<6% + RSI<60")
print("✅ Position Sizing: +25% on wins, -3% on losses (0.5x-2.0x caps)")
print("✅ Fixed SL: 3%")
print("✅ Adaptive TP: 3x ATR (4-15% range)")
print("✅ Fees: 0.01% total (0.005% per side)")

print("\n" + "="*100)
