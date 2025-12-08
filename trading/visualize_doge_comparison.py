"""
Create comprehensive comparison visualizations for DOGE optimization
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load all trade data
configs = {
    'Baseline\n(6.10%)': None,  # Will calculate from baseline
    'Best R:R\n(4.55x)': '/workspaces/Carebiuro_windykacja/trading/results/doge_best_rr_trades.csv',
    'Best Return\n(14.72%)': '/workspaces/Carebiuro_windykacja/trading/results/doge_best_return_trades.csv',
    'Best WR\n(71.4%)': '/workspaces/Carebiuro_windykacja/trading/results/doge_best_winrate_trades.csv',
    'Balanced\n(9.65%)': '/workspaces/Carebiuro_windykacja/trading/results/doge_balanced_trades.csv'
}

# Baseline metrics (from original report)
baseline_metrics = {
    'total_return': 6.10,
    'win_rate': 55.56,
    'rr_ratio': 1.42,
    'max_dd': 2.59,
    'profit_factor': 1.74,
    'trades': 27
}

# Create comprehensive comparison chart
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('DOGE/USDT Strategy Optimization - Complete Comparison', fontsize=16, fontweight='bold')

# Data for plotting
config_names = []
returns = []
win_rates = []
rr_ratios = []
max_dds = []
profit_factors = []
trade_counts = []

# Add baseline
config_names.append('Baseline')
returns.append(baseline_metrics['total_return'])
win_rates.append(baseline_metrics['win_rate'])
rr_ratios.append(baseline_metrics['rr_ratio'])
max_dds.append(baseline_metrics['max_dd'])
profit_factors.append(baseline_metrics['profit_factor'])
trade_counts.append(baseline_metrics['trades'])

# Process each config
for name, path in configs.items():
    if path is None:
        continue

    df = pd.read_csv(path)

    # Calculate metrics
    total_return = ((df['cumulative_capital'].iloc[-1] - 10000) / 10000) * 100
    win_rate = len(df[df['net_pnl'] > 0]) / len(df) * 100

    winners = df[df['net_pnl'] > 0]
    losers = df[df['net_pnl'] < 0]
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    gross_wins = winners['net_pnl'].sum() if len(winners) > 0 else 0
    gross_losses = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    pf = gross_wins / gross_losses if gross_losses > 0 else 0

    running_max = df['cumulative_capital'].cummax()
    drawdown = (df['cumulative_capital'] - running_max) / running_max
    max_dd = abs(drawdown.min()) * 100

    config_names.append(name.split('\n')[0])
    returns.append(total_return)
    win_rates.append(win_rate)
    rr_ratios.append(rr)
    max_dds.append(max_dd)
    profit_factors.append(pf)
    trade_counts.append(len(df))

# 1. Total Return Comparison
ax1 = axes[0, 0]
colors = ['gray', '#2E86AB', '#06A77D', '#F77F00', '#D62828']
bars1 = ax1.bar(range(len(returns)), returns, color=colors)
ax1.set_xticks(range(len(config_names)))
ax1.set_xticklabels(config_names, rotation=45, ha='right')
ax1.set_ylabel('Total Return (%)', fontweight='bold')
ax1.set_title('Total Return Comparison', fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

# Add value labels
for i, (bar, val) in enumerate(zip(bars1, returns)):
    ax1.text(bar.get_x() + bar.get_width()/2, val + 0.5, f'{val:.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 2. Win Rate Comparison
ax2 = axes[0, 1]
bars2 = ax2.bar(range(len(win_rates)), win_rates, color=colors)
ax2.set_xticks(range(len(config_names)))
ax2.set_xticklabels(config_names, rotation=45, ha='right')
ax2.set_ylabel('Win Rate (%)', fontweight='bold')
ax2.set_title('Win Rate Comparison', fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
ax2.set_ylim(0, 80)

for i, (bar, val) in enumerate(zip(bars2, win_rates)):
    ax2.text(bar.get_x() + bar.get_width()/2, val + 1, f'{val:.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 3. R:R Ratio Comparison
ax3 = axes[0, 2]
bars3 = ax3.bar(range(len(rr_ratios)), rr_ratios, color=colors)
ax3.set_xticks(range(len(config_names)))
ax3.set_xticklabels(config_names, rotation=45, ha='right')
ax3.set_ylabel('R:R Ratio', fontweight='bold')
ax3.set_title('Risk:Reward Ratio', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

for i, (bar, val) in enumerate(zip(bars3, rr_ratios)):
    ax3.text(bar.get_x() + bar.get_width()/2, val + 0.1, f'{val:.2f}',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 4. Max Drawdown Comparison
ax4 = axes[1, 0]
bars4 = ax4.bar(range(len(max_dds)), max_dds, color=colors)
ax4.set_xticks(range(len(config_names)))
ax4.set_xticklabels(config_names, rotation=45, ha='right')
ax4.set_ylabel('Max Drawdown (%)', fontweight='bold')
ax4.set_title('Maximum Drawdown (Lower is Better)', fontweight='bold')
ax4.grid(axis='y', alpha=0.3)

for i, (bar, val) in enumerate(zip(bars4, max_dds)):
    ax4.text(bar.get_x() + bar.get_width()/2, val + 0.1, f'{val:.1f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 5. Profit Factor Comparison
ax5 = axes[1, 1]
bars5 = ax5.bar(range(len(profit_factors)), profit_factors, color=colors)
ax5.set_xticks(range(len(config_names)))
ax5.set_xticklabels(config_names, rotation=45, ha='right')
ax5.set_ylabel('Profit Factor', fontweight='bold')
ax5.set_title('Profit Factor (Gross Wins / Gross Losses)', fontweight='bold')
ax5.grid(axis='y', alpha=0.3)

for i, (bar, val) in enumerate(zip(bars5, profit_factors)):
    ax5.text(bar.get_x() + bar.get_width()/2, val + 0.1, f'{val:.2f}',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

# 6. Trade Count
ax6 = axes[1, 2]
bars6 = ax6.bar(range(len(trade_counts)), trade_counts, color=colors)
ax6.set_xticks(range(len(config_names)))
ax6.set_xticklabels(config_names, rotation=45, ha='right')
ax6.set_ylabel('Number of Trades', fontweight='bold')
ax6.set_title('Total Trades Executed', fontweight='bold')
ax6.grid(axis='y', alpha=0.3)

for i, (bar, val) in enumerate(zip(bars6, trade_counts)):
    ax6.text(bar.get_x() + bar.get_width()/2, val + 0.3, f'{int(val)}',
            ha='center', va='bottom', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/doge_complete_comparison.png', dpi=150, bbox_inches='tight')
print("✓ Complete comparison chart saved to results/doge_complete_comparison.png")

# Create radar chart for holistic view
fig2, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))

# Normalize metrics to 0-100 scale for radar chart
categories = ['Return', 'Win Rate', 'R:R Ratio', 'Low Drawdown', 'Profit Factor']
N = len(categories)

# Normalize values
def normalize(values, reverse=False):
    """Normalize to 0-100 scale"""
    arr = np.array(values)
    if reverse:  # For drawdown (lower is better)
        arr = max(arr) - arr
    normalized = (arr - arr.min()) / (arr.max() - arr.min()) * 100
    return normalized.tolist()

# Angles for radar chart
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]

# Plot each config
configs_to_plot = [
    ('Baseline', 0),
    ('Best Return', 2),
    ('Best R:R', 1),
    ('Best WR', 3),
    ('Balanced', 4)
]

for label, idx in configs_to_plot:
    values = [
        normalize(returns)[idx],
        normalize(win_rates)[idx],
        normalize(rr_ratios)[idx],
        normalize(max_dds, reverse=True)[idx],
        normalize(profit_factors)[idx]
    ]
    values += values[:1]

    ax.plot(angles, values, 'o-', linewidth=2, label=label, color=colors[idx])
    ax.fill(angles, values, alpha=0.15, color=colors[idx])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, size=11, fontweight='bold')
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(['20', '40', '60', '80', '100'], size=9)
ax.grid(True, linestyle='--', alpha=0.5)
ax.set_title('DOGE/USDT Strategy Optimization - Radar Comparison\n(All metrics normalized to 0-100)',
             size=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/doge_radar_comparison.png', dpi=150, bbox_inches='tight')
print("✓ Radar comparison chart saved to results/doge_radar_comparison.png")

# Print summary table
print("\n" + "="*80)
print("OPTIMIZATION SUMMARY TABLE")
print("="*80)
print(f"\n{'Config':<15} {'Return':>10} {'WinRate':>10} {'R:R':>8} {'MaxDD':>10} {'PF':>8} {'Trades':>8}")
print("-" * 80)

for i, name in enumerate(config_names):
    print(f"{name:<15} {returns[i]:>9.2f}% {win_rates[i]:>9.1f}% {rr_ratios[i]:>7.2f} {max_dds[i]:>9.2f}% {profit_factors[i]:>7.2f} {trade_counts[i]:>8.0f}")

print("\n" + "="*80)
print("IMPROVEMENTS VS BASELINE")
print("="*80)

for i in range(1, len(config_names)):
    print(f"\n{config_names[i]}:")
    print(f"  Return: {returns[i] - returns[0]:+.2f}% ({((returns[i] / returns[0]) - 1) * 100:+.1f}% change)")
    print(f"  Win Rate: {win_rates[i] - win_rates[0]:+.2f}%")
    print(f"  R:R: {rr_ratios[i] - rr_ratios[0]:+.2f} ({((rr_ratios[i] / rr_ratios[0]) - 1) * 100:+.1f}% change)")
    print(f"  Max DD: {max_dds[i] - max_dds[0]:+.2f}%")
    print(f"  Profit Factor: {profit_factors[i] - profit_factors[0]:+.2f}")

print("\n" + "="*80)
