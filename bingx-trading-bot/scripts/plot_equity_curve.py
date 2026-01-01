"""
Plot equity curve from portfolio simulation
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_equity_curve():
    """Plot equity curve with drawdown"""

    # Load equity curve data
    equity_file = Path("trading/results/portfolio_leverage_equity_curve.csv")

    if not equity_file.exists():
        print(f"❌ Error: {equity_file} not found")
        return

    df = pd.read_csv(equity_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # Plot 1: Equity curve
    ax1.plot(df['timestamp'], df['equity'], linewidth=2, color='#2ecc71', label='Portfolio Equity')
    ax1.plot(df['timestamp'], df['peak'], linewidth=1, color='#e74c3c', linestyle='--', alpha=0.6, label='Peak Equity')
    ax1.fill_between(df['timestamp'], df['equity'], alpha=0.3, color='#2ecc71')

    ax1.set_ylabel('Equity (USDT)', fontsize=12, fontweight='bold')
    ax1.set_title('Portfolio Equity Curve - All 10 Strategies\n$100 Start → $170.92 End (+70.92%)',
                  fontsize=14, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=10)

    # Add starting and ending equity annotations
    ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.5)
    ax1.text(df['timestamp'].iloc[0], 100, ' $100 (Start)',
             verticalalignment='bottom', fontsize=9, color='gray')
    ax1.text(df['timestamp'].iloc[-1], df['equity'].iloc[-1],
             f' ${df["equity"].iloc[-1]:.2f} (End)',
             verticalalignment='bottom', fontsize=9, color='#2ecc71', fontweight='bold')

    # Plot 2: Drawdown
    ax2.fill_between(df['timestamp'], 0, df['drawdown_pct'],
                     color='#e74c3c', alpha=0.4, label='Drawdown')
    ax2.plot(df['timestamp'], df['drawdown_pct'], linewidth=1.5, color='#c0392b')

    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Drawdown from Peak', fontsize=12, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower right', fontsize=10)

    # Add max drawdown annotation
    max_dd_idx = df['drawdown_pct'].idxmin()
    ax2.plot(df['timestamp'].iloc[max_dd_idx], df['drawdown_pct'].iloc[max_dd_idx],
             'ro', markersize=8)
    ax2.text(df['timestamp'].iloc[max_dd_idx], df['drawdown_pct'].iloc[max_dd_idx],
             f' Max DD: {df["drawdown_pct"].iloc[max_dd_idx]:.2f}%',
             verticalalignment='top', fontsize=9, color='#c0392b', fontweight='bold')

    # Format
    plt.tight_layout()

    # Save
    output_file = Path("trading/results/portfolio_equity_curve.png")
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Equity curve saved to {output_file}")

    # Also create a simple summary stats box
    fig2, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')

    # Calculate stats
    starting = df['equity'].iloc[0]
    ending = df['equity'].iloc[-1]
    total_return = ((ending / starting) - 1) * 100
    max_dd = df['drawdown_pct'].min()
    return_dd = abs(total_return / max_dd)

    stats_text = f"""
    PORTFOLIO PERFORMANCE SUMMARY
    {'='*50}

    💰 Capital:
       Starting:          ${starting:.2f} USDT
       Ending:            ${ending:.2f} USDT
       Net Profit:        ${ending - starting:.2f} USDT

    📊 Returns:
       Total Return:      {total_return:.2f}%
       Max Drawdown:      {max_dd:.2f}%
       Return/DD Ratio:   {return_dd:.2f}x

    🎯 Trading:
       Completed Trades:  {len(df)}
       Avg Concurrent:    {df['open_positions'].mean():.1f} positions
       Max Concurrent:    {int(df['open_positions'].max())} positions

    📈 Method:
       Each trade: 10% of current equity
       Leverage: YES (all signals filled)
       Fees: 0.07% round-trip
    """

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    summary_file = Path("trading/results/portfolio_summary.png")
    plt.savefig(summary_file, dpi=150, bbox_inches='tight')
    print(f"✅ Summary saved to {summary_file}")

    plt.close('all')

if __name__ == '__main__':
    plot_equity_curve()
