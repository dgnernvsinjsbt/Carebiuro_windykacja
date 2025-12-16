"""
Generate equity curve for risk-based portfolio
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load both portfolios
df_fixed = pd.read_csv('portfolio_SIMPLE.csv')
df_fixed['exit_time'] = pd.to_datetime(df_fixed['exit_time'])

df_risk = pd.read_csv('portfolio_RISK_BASED.csv')
df_risk['exit_time'] = pd.to_datetime(df_risk['exit_time'])

print('Generating comparison equity curve...')

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

# Add starting points
start_time = df_fixed['exit_time'].min()
fixed_with_start = pd.concat([
    pd.DataFrame({'exit_time': [start_time], 'equity': [1000.0], 'drawdown_pct': [0.0]}),
    df_fixed[['exit_time', 'equity', 'drawdown_pct']]
], ignore_index=True)

risk_with_start = pd.concat([
    pd.DataFrame({'exit_time': [start_time], 'equity': [1000.0], 'drawdown_pct': [0.0]}),
    df_risk[['exit_time', 'equity', 'drawdown_pct']]
], ignore_index=True)

# Plot 1: Equity Curves Comparison
ax1.plot(fixed_with_start['exit_time'], fixed_with_start['equity'],
         linewidth=2.5, color='steelblue', label='Fixed 10% Sizing', alpha=0.9)
ax1.plot(risk_with_start['exit_time'], risk_with_start['equity'],
         linewidth=2.5, color='orangered', label='Risk-Based 1%', alpha=0.9)
ax1.axhline(y=1000, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')

# Mark max drawdowns
fixed_max_dd_idx = df_fixed['drawdown_pct'].idxmin()
fixed_max_dd = df_fixed.loc[fixed_max_dd_idx]
ax1.scatter([fixed_max_dd['exit_time']], [fixed_max_dd['equity']],
           color='blue', s=200, marker='v', zorder=3)

risk_max_dd_idx = df_risk['drawdown_pct'].idxmin()
risk_max_dd = df_risk.loc[risk_max_dd_idx]
ax1.scatter([risk_max_dd['exit_time']], [risk_max_dd['equity']],
           color='darkred', s=200, marker='v', zorder=3)

ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('Portfolio Comparison: Fixed 10% vs Risk-Based 1%',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# Stats box for Fixed
fixed_final = df_fixed['equity'].iloc[-1]
fixed_return = ((fixed_final - 1000) / 1000) * 100
fixed_max_dd_val = df_fixed['drawdown_pct'].min()

fixed_stats = f"FIXED 10%:\n"
fixed_stats += f"Final: ${fixed_final:,.2f}\n"
fixed_stats += f"Return: +{fixed_return:.2f}%\n"
fixed_stats += f"Max DD: {fixed_max_dd_val:.2f}%\n"
fixed_stats += f"R/R: {abs(fixed_return/fixed_max_dd_val):.2f}x"

ax1.text(0.02, 0.98, fixed_stats, transform=ax1.transAxes,
         fontsize=10, verticalalignment='top', horizontalalignment='left',
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))

# Stats box for Risk-Based
risk_final = df_risk['equity'].iloc[-1]
risk_return = ((risk_final - 1000) / 1000) * 100
risk_max_dd_val = df_risk['drawdown_pct'].min()

risk_stats = f"RISK-BASED 1%:\n"
risk_stats += f"Final: ${risk_final:,.2f}\n"
risk_stats += f"Return: +{risk_return:.2f}%\n"
risk_stats += f"Max DD: {risk_max_dd_val:.2f}%\n"
risk_stats += f"R/R: {abs(risk_return/risk_max_dd_val):.2f}x"

ax1.text(0.98, 0.98, risk_stats, transform=ax1.transAxes,
         fontsize=10, verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

# Plot 2: Drawdown Comparison
ax2.fill_between(fixed_with_start['exit_time'], 0, fixed_with_start['drawdown_pct'],
                  color='steelblue', alpha=0.3, label='Fixed 10%')
ax2.fill_between(risk_with_start['exit_time'], 0, risk_with_start['drawdown_pct'],
                  color='orangered', alpha=0.3, label='Risk-Based 1%')

ax2.plot(fixed_with_start['exit_time'], fixed_with_start['drawdown_pct'],
         color='steelblue', linewidth=1.5, alpha=0.9)
ax2.plot(risk_with_start['exit_time'], risk_with_start['drawdown_pct'],
         color='orangered', linewidth=1.5, alpha=0.9)

# Mark max DDs
ax2.scatter([fixed_max_dd['exit_time']], [fixed_max_dd['drawdown_pct']],
           color='blue', s=150, marker='v', zorder=3)
ax2.scatter([risk_max_dd['exit_time']], [risk_max_dd['drawdown_pct']],
           color='darkred', s=150, marker='v', zorder=3)

ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')

# Format x-axis
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('equity_COMPARISON.png', dpi=150, bbox_inches='tight')
print('✅ Saved: equity_COMPARISON.png')
plt.close()

print()
print('='*80)
print('📊 COMPARISON SUMMARY')
print('='*80)
print()
print(f'{"Metric":<20} {"Fixed 10%":<15} {"Risk-Based 1%":<15} {"Difference"}')
print('-'*80)
print(f'{"Final Equity":<20} ${fixed_final:>13,.2f} ${risk_final:>13,.2f} ${risk_final-fixed_final:>+13,.2f}')
print(f'{"Return":<20} {fixed_return:>13.2f}% {risk_return:>13.2f}% {risk_return-fixed_return:>+13.2f}%')
print(f'{"Max Drawdown":<20} {fixed_max_dd_val:>13.2f}% {risk_max_dd_val:>13.2f}% {risk_max_dd_val-fixed_max_dd_val:>+13.2f}%')
print(f'{"R/R Ratio":<20} {abs(fixed_return/fixed_max_dd_val):>13.2f}x {abs(risk_return/risk_max_dd_val):>13.2f}x')
print()
print('Max DD events:')
print(f'  Fixed 10%: {fixed_max_dd["exit_time"].strftime("%Y-%m-%d %H:%M")} - {fixed_max_dd["coin"]} - {fixed_max_dd["exit_reason"]}')
print(f'  Risk-Based: {risk_max_dd["exit_time"].strftime("%Y-%m-%d %H:%M")} - {risk_max_dd["coin"]} - {risk_max_dd["exit_reason"]}')
