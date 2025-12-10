#!/usr/bin/env python3
"""
MOODENG HYBRID Strategy - Equity Curve Visualization
Shows complete journey from $100 to $126.62 over 28 trades
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime

def generate_equity_curve():
    # Load trade log
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_hybrid_complete_log.csv')

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])
    fig.suptitle('MOODENG HYBRID Strategy - Equity Curve & Drawdown', fontsize=16, fontweight='bold')

    # Prepare data
    trade_nums = range(len(df) + 1)
    equity_curve = [100] + df['equity_after'].tolist()
    peak_curve = [100] + df['peak_equity'].tolist()

    # ========================================
    # SUBPLOT 1: EQUITY CURVE
    # ========================================

    # Plot equity line
    ax1.plot(trade_nums, equity_curve, color='#2E86AB', linewidth=2.5, label='Account Equity', zorder=3)

    # Plot peak equity (dotted)
    ax1.plot(trade_nums, peak_curve, color='#A23B72', linewidth=1.5, linestyle='--',
             label='Peak Equity', alpha=0.7, zorder=2)

    # Mark trades as points
    for i, row in df.iterrows():
        trade_num = i + 1
        equity_after = row['equity_after']

        if row['result'] == 'TP':
            color = '#06A77D'  # Green for TP
            marker = '^'
            size = 100
        elif row['result'] == 'SL':
            color = '#D81159'  # Red for SL
            marker = 'v'
            size = 80
        else:  # TIME
            color = '#FFBC42'  # Yellow for TIME
            marker = 'o'
            size = 60

        ax1.scatter(trade_num, equity_after, color=color, marker=marker, s=size,
                   edgecolors='black', linewidths=0.5, zorder=4, alpha=0.8)

    # Shade profitable vs underwater regions
    ax1.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=1)
    ax1.fill_between(trade_nums, 100, equity_curve, where=[e >= 100 for e in equity_curve],
                      color='#06A77D', alpha=0.1, label='Profit Zone')
    ax1.fill_between(trade_nums, 100, equity_curve, where=[e < 100 for e in equity_curve],
                      color='#D81159', alpha=0.1, label='Drawdown Zone')

    # Labels and formatting
    ax1.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Account Equity ($)', fontsize=12, fontweight='bold')
    ax1.set_title('Account Growth: $100 → $126.62 (+26.62%)', fontsize=13, pad=10)
    ax1.grid(True, alpha=0.3, linestyle=':', zorder=0)
    ax1.set_xlim(-0.5, len(df) + 0.5)

    # Add statistics box
    final_equity = df.iloc[-1]['equity_after']
    max_dd = df['max_dd_so_far'].max()
    win_rate = df.iloc[-1]['running_win_rate']
    max_loss_streak = df['consecutive_losses'].max()

    stats_text = f"""PERFORMANCE SUMMARY
Final Equity: ${final_equity:.2f}
Net Return: +{final_equity - 100:.2f}%
Max Drawdown: {max_dd:.2f}%
Return/DD: {(final_equity - 100) / max_dd:.2f}x
Win Rate: {win_rate:.1f}%
Max Loss Streak: {int(max_loss_streak)} trades"""

    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
             fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             family='monospace')

    # Create custom legend
    tp_patch = mpatches.Patch(color='#06A77D', label=f'TP Wins ({len(df[df["result"] == "TP"])})')
    sl_patch = mpatches.Patch(color='#D81159', label=f'SL Losses ({len(df[df["result"] == "SL"])})')
    time_patch = mpatches.Patch(color='#FFBC42', label=f'Time Exits ({len(df[df["result"] == "TIME"])})')

    ax1.legend(handles=[tp_patch, sl_patch, time_patch], loc='upper left',
              fontsize=10, framealpha=0.9)

    # ========================================
    # SUBPLOT 2: DRAWDOWN
    # ========================================

    # Plot drawdown over time
    dd_values = [0] + df['dd_pct'].tolist()

    ax2.fill_between(trade_nums, 0, [-dd for dd in dd_values], color='#D81159', alpha=0.3)
    ax2.plot(trade_nums, [-dd for dd in dd_values], color='#D81159', linewidth=2)

    # Mark max DD point
    max_dd_idx = df['dd_pct'].idxmax() + 1
    max_dd_val = -df['dd_pct'].max()
    ax2.scatter(max_dd_idx, max_dd_val, color='darkred', s=150, marker='X',
               edgecolors='black', linewidths=1.5, zorder=5, label=f'Max DD: {max_dd:.2f}%')

    ax2.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Drawdown from Peak', fontsize=13, pad=10)
    ax2.grid(True, alpha=0.3, linestyle=':', zorder=0)
    ax2.set_xlim(-0.5, len(df) + 0.5)
    ax2.legend(loc='lower left', fontsize=10)

    # Adjust layout
    plt.tight_layout()

    # Save figure
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/moodeng_hybrid_equity_curve.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Equity curve saved to: {output_path}")

    # Show plot
    plt.show()

    # ========================================
    # TRADE-BY-TRADE BREAKDOWN
    # ========================================

    print("\n" + "=" * 100)
    print("TRADE-BY-TRADE EQUITY PROGRESSION")
    print("=" * 100)
    print(f"\n{'#':<4} {'Exit Time':<18} {'Result':<7} {'P&L':<10} {'Equity':<12} {'Peak':<12} {'DD%':<8} {'Streak'}")
    print("-" * 100)

    for i, row in df.iterrows():
        trade_num = int(row['trade_num'])
        exit_time = pd.to_datetime(row['exit_time']).strftime('%Y-%m-%d %H:%M')
        result = row['result']
        pnl = row['pnl_pct']
        equity_after = row['equity_after']
        peak = row['peak_equity']
        dd = row['dd_pct']

        # Streak indicator
        if row['consecutive_losses'] > 0:
            streak = f"🔴 L{int(row['consecutive_losses'])}"
        elif row['consecutive_wins'] > 0:
            streak = f"🟢 W{int(row['consecutive_wins'])}"
        else:
            streak = "-"

        # Color coding
        marker = "🟢" if pnl > 0 else "🔴"

        print(f"{trade_num:<4} {exit_time:<18} {result:<7} {pnl:>+8.2f}% ${equity_after:>9.2f} ${peak:>9.2f} {dd:>6.2f}% {streak}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    generate_equity_curve()
