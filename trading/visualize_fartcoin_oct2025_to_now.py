"""
Show FARTCOIN equity curve from October 2025 to December 2025
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

print("="*100)
print("FARTCOIN EQUITY CURVE - OCTOBER 2025 TO DECEMBER 2025")
print("="*100)

# Filter for October 2025 onwards
start_date = pd.to_datetime('2025-10-01')
df_oct_onwards = df[df['timestamp'] >= start_date].copy()
df_oct_onwards = df_oct_onwards.reset_index(drop=True)

print(f"\nOctober-December Data Range: {df_oct_onwards['timestamp'].min().strftime('%Y-%m-%d %H:%M')} to {df_oct_onwards['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
print(f"Total Candles in Oct-Dec: {len(df_oct_onwards)}")

# But we need to calculate indicators on full dataset
df['ema_3'] = calculate_ema(df, 3)
df['ema_15'] = calculate_ema(df, 15)
df['momentum_7d'] = df['close'].pct_change(336) * 100
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['rsi'] = calculate_rsi(df)
df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

# Run backtest on FULL dataset to get proper equity evolution
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

            stop_loss = entry_price * 1.03
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

# Filter trades to October onwards
trades_oct = trades_df[trades_df['exit_date'] >= start_date].copy()
trades_oct = trades_oct.reset_index(drop=True)

print(f"\nTotal Trades (Oct-Dec only): {len(trades_oct)}")
if len(trades_oct) > 0:
    print(f"Winners: {len(trades_oct[trades_oct['win']])} ({len(trades_oct[trades_oct['win']])/len(trades_oct)*100:.1f}%)")
    print(f"Losers: {len(trades_oct[~trades_oct['win']])} ({len(trades_oct[~trades_oct['win']])/len(trades_oct)*100:.1f}%)")

    # Calculate equity from START OF OCTOBER with proper position size carryover
    # First, we need to know what the equity and position size were at Oct 1st

    # Calculate equity up to Oct 1st
    trades_before_oct = trades_df[trades_df['exit_date'] < start_date]

    equity_at_oct = 1.0
    position_size_at_oct = 1.0

    for _, trade in trades_before_oct.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size_at_oct
        equity_at_oct *= (1 + trade_pnl / 100)

        if trade['pnl_pct'] > 0:
            position_size_at_oct = min(position_size_at_oct + 0.25, 2.0)
        else:
            position_size_at_oct = max(position_size_at_oct - 0.03, 0.5)

    print(f"\nEquity at Oct 1st: {equity_at_oct:.2f}x")
    print(f"Position Size at Oct 1st: {position_size_at_oct:.2f}x")

    # Now calculate from Oct 1st onwards
    equity = equity_at_oct
    position_size = position_size_at_oct
    equity_curve = [equity]
    dates = [trades_oct.iloc[0]['entry_date']]
    position_sizes = [position_size]

    for _, trade in trades_oct.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)
        dates.append(trade['exit_date'])

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + 0.25, 2.0)
        else:
            position_size = max(position_size - 0.03, 0.5)

        position_sizes.append(position_size)

    # Calculate metrics for Oct-Dec period
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    max_dd_idx = drawdown.idxmin()

    # Return from Oct 1st to now
    oct_dec_return = (equity / equity_at_oct - 1) * 100
    total_return_from_start = (equity - 1) * 100

    print(f"\n{'='*100}")
    print("OCTOBER - DECEMBER 2025 PERFORMANCE")
    print(f"{'='*100}")
    print(f"\nReturn (Oct-Dec): {oct_dec_return:.2f}%")
    print(f"Total Return (from Jan 1st): {total_return_from_start:.2f}%")
    print(f"Final Equity: {equity:.2f}x")
    print(f"Max Drawdown (Oct-Dec): {max_dd:.2f}%")
    print(f"Risk-Reward Ratio: {oct_dec_return / abs(max_dd):.2f}")
    print(f"\nAvg Win: {trades_oct[trades_oct['pnl_pct'] > 0]['pnl_pct'].mean():.2f}%")
    print(f"Avg Loss: {trades_oct[trades_oct['pnl_pct'] < 0]['pnl_pct'].mean():.2f}%")

    max_dd_date = dates[max_dd_idx]
    print(f"\nMax Drawdown occurred at: {max_dd_date.strftime('%Y-%m-%d %H:%M')}")

    # Create visualization
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 2, height_ratios=[3, 1.5, 1])

    ax1 = fig.add_subplot(gs[0, :])  # Equity curve
    ax2 = fig.add_subplot(gs[1, :])  # Drawdown
    ax3 = fig.add_subplot(gs[2, 0])  # Position size
    ax4 = fig.add_subplot(gs[2, 1])  # Trade PnL

    # Plot 1: Equity Curve
    ax1.plot(dates, equity_curve, linewidth=3, color='#2E86AB', alpha=0.9, label='Equity')
    ax1.fill_between(dates, equity_at_oct, equity_curve, alpha=0.2, color='#2E86AB')

    # Mark starting point
    ax1.scatter(dates[0], equity_at_oct, s=300, color='green', zorder=5,
               marker='o', edgecolors='black', linewidths=2, label='Oct 1st Start')
    ax1.annotate(f'Start: {equity_at_oct:.2f}x\nOct 1st',
                xy=(dates[0], equity_at_oct),
                xytext=(20, 20), textcoords='offset points',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))

    # Mark ending point
    ax1.scatter(dates[-1], equity, s=300, color='blue', zorder=5,
               marker='*', edgecolors='black', linewidths=2, label='Dec 5th End')
    ax1.annotate(f'End: {equity:.2f}x\nDec 5th',
                xy=(dates[-1], equity),
                xytext=(-80, -30), textcoords='offset points',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))

    # Mark max drawdown
    ax1.scatter(max_dd_date, equity_curve[max_dd_idx], s=300, color='red', zorder=5,
               marker='v', edgecolors='black', linewidths=2, label='Max DD')

    ax1.set_ylabel('Equity Multiple', fontsize=13, fontweight='bold')
    ax1.set_title(f'FARTCOIN Complete Optimized Strategy: Oct 1st - Dec 5th, 2025\n' +
                  f'{equity_at_oct:.2f}x → {equity:.2f}x ({oct_dec_return:+.1f}%) | Max DD: {max_dd:.1f}% | R:R: {oct_dec_return/abs(max_dd):.2f}',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.legend(loc='upper left', fontsize=11)
    ax1.grid(True, alpha=0.3)

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
    ax2.set_title('Drawdown Over Time (Oct-Dec)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Position Size
    ax3.plot(dates, position_sizes, linewidth=2, color='#F18F01', alpha=0.9)
    ax3.fill_between(dates, position_size_at_oct, position_sizes, alpha=0.3, color='#F18F01')
    ax3.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax3.axhline(y=0.5, color='red', linestyle=':', alpha=0.5, linewidth=1, label='Min (0.5x)')
    ax3.axhline(y=2.0, color='green', linestyle=':', alpha=0.5, linewidth=1, label='Max (2.0x)')
    ax3.set_ylabel('Position Size (x)', fontsize=11, fontweight='bold')
    ax3.set_title('Dynamic Position Sizing (+25%/-3%)', fontsize=12, fontweight='bold')
    ax3.set_ylim([0.4, 2.1])
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlabel('Date', fontsize=11)
    ax3.tick_params(axis='x', rotation=45)

    # Plot 4: Trade PnL Distribution
    winners = trades_oct[trades_oct['pnl_pct'] > 0]['pnl_pct']
    losers = trades_oct[trades_oct['pnl_pct'] < 0]['pnl_pct']

    if len(winners) > 0 and len(losers) > 0:
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
        ax4.set_title('Trade PnL Distribution (Oct-Dec)', fontsize=12, fontweight='bold')
        ax4.legend(loc='upper right', fontsize=9)
        ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('results/fartcoin_equity_oct2025_to_dec.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization to results/fartcoin_equity_oct2025_to_dec.png")

    print("\n" + "="*100)
    print("STRATEGY COMPONENTS")
    print("="*100)
    print("\n✅ Entry: EMA 3 crosses below EMA 15 (SHORT)")
    print("✅ Filters: Mom7d<0 + ATR<6% + RSI<60")
    print("✅ Position Sizing: +25% on wins, -3% on losses (0.5x-2.0x caps)")
    print("✅ Fixed SL: 3%")
    print("✅ Adaptive TP: 3x ATR (4-15% range)")
    print("✅ Fees: 0.01% total (0.005% per side)")

else:
    print("\n❌ No trades found in October-December 2025 period")

print("\n" + "="*100)
