#!/usr/bin/env python3
"""
Backtest comparison: Current vs Optimized configuration
Current: time_8 + ema5 + US_late (16-22 UTC)
Optimized: time_4 + ema8 + US_evening (18-23 UTC)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['ema20'] = df['close'].ewm(span=20).mean()
df['is_green'] = df['close'] > df['open']
df['hour'] = df['timestamp'].dt.hour
df['date'] = df['timestamp'].dt.date

# Daily data for daily EMA
daily_df = df.groupby('date').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last'
}).reset_index()
daily_df.columns = ['date', 'daily_open', 'daily_high', 'daily_low', 'daily_close']

def backtest_config(df, daily_df, time_exit, daily_ema_period, session_start, session_end, leverage=10, config_name=""):
    """Run backtest with specific configuration"""

    # Calculate daily EMA
    daily_df = daily_df.copy()
    daily_df['daily_ema'] = daily_df['daily_close'].ewm(span=daily_ema_period).mean()
    daily_df['daily_above_ema'] = daily_df['daily_close'].shift(1) > daily_df['daily_ema'].shift(1)

    # Merge daily filter to main df
    df = df.copy()
    df = df.merge(daily_df[['date', 'daily_above_ema']], on='date', how='left')

    # Session filter
    if session_end > session_start:
        df['in_session'] = (df['hour'] >= session_start) & (df['hour'] < session_end)
    else:
        df['in_session'] = (df['hour'] >= session_start) | (df['hour'] < session_end)

    # Entry signals
    df['signal'] = (
        (df['close'] > df['ema20']) &
        (df['low'] <= df['ema20'] * 1.005) &
        df['is_green'] &
        df['daily_above_ema'].fillna(False) &
        df['in_session']
    ).astype(int)

    # Backtest
    capital = 10000
    fee_rate = 0.001

    trades = []
    equity_curve = []
    in_position = False
    entry_idx = 0
    entry_p = 0

    for i, row in df.iterrows():
        current_date = row['date']

        # Close at end of day
        if in_position:
            if row['hour'] == 23 and row['timestamp'].minute == 45:
                exit_p = row['close']
                gross_ret = (exit_p - entry_p) / entry_p
                net_ret = gross_ret * leverage - fee_rate
                capital *= (1 + net_ret)
                trades.append({
                    'entry_time': df.loc[entry_idx, 'timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_p': entry_p,
                    'exit_p': exit_p,
                    'pnl_pct': net_ret * 100,
                    'capital': capital,
                    'reason': 'EOD'
                })
                in_position = False

        # Time exit
        if in_position:
            if i - entry_idx >= time_exit:
                exit_p = row['close']
                gross_ret = (exit_p - entry_p) / entry_p
                net_ret = gross_ret * leverage - fee_rate
                capital *= (1 + net_ret)
                trades.append({
                    'entry_time': df.loc[entry_idx, 'timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_p': entry_p,
                    'exit_p': exit_p,
                    'pnl_pct': net_ret * 100,
                    'capital': capital,
                    'reason': 'TIME'
                })
                in_position = False

        # Entry
        if not in_position and row['signal'] == 1:
            entry_p = row['close']
            entry_idx = i
            in_position = True

        equity_curve.append({
            'timestamp': row['timestamp'],
            'capital': capital
        })

    # Calculate metrics
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    equity_df = pd.DataFrame(equity_curve)

    if len(trades_df) > 0:
        wins = len(trades_df[trades_df['pnl_pct'] > 0])
        wr = wins / len(trades_df) * 100

        # Max drawdown
        equity_df['peak'] = equity_df['capital'].cummax()
        equity_df['drawdown'] = (equity_df['peak'] - equity_df['capital']) / equity_df['peak'] * 100
        max_dd = equity_df['drawdown'].max()

        final_capital = capital
        total_return = (final_capital - 10000) / 10000 * 100
        avg_pnl = trades_df['pnl_pct'].mean()

        print(f"\n{'='*60}")
        print(f"CONFIG: {config_name}")
        print(f"{'='*60}")
        print(f"Time Exit: {time_exit} candles | Daily EMA: {daily_ema_period} | Session: {session_start}:00-{session_end}:00 UTC")
        print(f"{'='*60}")
        print(f"Final Capital: ${final_capital:,.2f}")
        print(f"Total Return: {total_return:,.1f}%")
        print(f"Trades: {len(trades_df)}")
        print(f"Win Rate: {wr:.1f}%")
        print(f"Max Drawdown: {max_dd:.1f}%")
        print(f"Avg PnL: {avg_pnl:.2f}%")
        print(f"Sharpe (Ret/DD): {total_return/max_dd:.1f}")

        return equity_df, trades_df, {
            'config': config_name,
            'final_capital': final_capital,
            'return': total_return,
            'trades': len(trades_df),
            'wr': wr,
            'max_dd': max_dd,
            'avg_pnl': avg_pnl,
            'sharpe': total_return/max_dd
        }

    return None, None, None

# Run both configurations
print("Running backtest comparison...")

# Current config
eq_current, trades_current, stats_current = backtest_config(
    df, daily_df,
    time_exit=8,
    daily_ema_period=5,
    session_start=16,
    session_end=22,
    leverage=10,
    config_name="CURRENT (time_8 + ema5 + US_late)"
)

# Optimized low-risk config
eq_optimized, trades_optimized, stats_optimized = backtest_config(
    df, daily_df,
    time_exit=4,
    daily_ema_period=8,
    session_start=18,
    session_end=23,
    leverage=10,
    config_name="OPTIMIZED (time_4 + ema8 + US_evening)"
)

# Alternative: Best return config
eq_best, trades_best, stats_best = backtest_config(
    df, daily_df,
    time_exit=6,
    daily_ema_period=3,
    session_start=14,
    session_end=22,
    leverage=10,
    config_name="HIGH-RETURN (time_6 + ema3 + US)"
)

# Create comparison plot
fig, axes = plt.subplots(3, 1, figsize=(14, 12))

# Plot 1: Equity curves comparison
ax1 = axes[0]
ax1.plot(eq_current['timestamp'], eq_current['capital'], 'b-', alpha=0.7, linewidth=1, label=f"Current: {stats_current['return']:,.0f}%")
ax1.plot(eq_optimized['timestamp'], eq_optimized['capital'], 'g-', alpha=0.9, linewidth=1.5, label=f"Optimized (Low Risk): {stats_optimized['return']:,.0f}%")
ax1.plot(eq_best['timestamp'], eq_best['capital'], 'r-', alpha=0.5, linewidth=1, label=f"High Return: {stats_best['return']:,.0f}%")
ax1.set_yscale('log')
ax1.set_ylabel('Capital ($, log scale)')
ax1.set_title('FARTCOIN Strategy Comparison - Equity Curves (10x Leverage)', fontsize=12, fontweight='bold')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Initial $10k')

# Plot 2: Drawdown comparison
ax2 = axes[1]
eq_current['dd'] = (eq_current['capital'].cummax() - eq_current['capital']) / eq_current['capital'].cummax() * 100
eq_optimized['dd'] = (eq_optimized['capital'].cummax() - eq_optimized['capital']) / eq_optimized['capital'].cummax() * 100
eq_best['dd'] = (eq_best['capital'].cummax() - eq_best['capital']) / eq_best['capital'].cummax() * 100

ax2.fill_between(eq_current['timestamp'], eq_current['dd'], alpha=0.3, color='blue', label=f"Current DD: {stats_current['max_dd']:.1f}%")
ax2.fill_between(eq_optimized['timestamp'], eq_optimized['dd'], alpha=0.5, color='green', label=f"Optimized DD: {stats_optimized['max_dd']:.1f}%")
ax2.set_ylabel('Drawdown (%)')
ax2.set_title('Drawdown Comparison', fontsize=11)
ax2.legend(loc='lower right')
ax2.grid(True, alpha=0.3)
ax2.invert_yaxis()

# Plot 3: Stats comparison bar chart
ax3 = axes[2]
configs = ['Current\n(time_8+ema5+US_late)', 'Optimized\n(time_4+ema8+US_evening)', 'High Return\n(time_6+ema3+US)']
max_dds = [stats_current['max_dd'], stats_optimized['max_dd'], stats_best['max_dd']]
sharpes = [stats_current['sharpe'], stats_optimized['sharpe'], stats_best['sharpe']]

x = np.arange(len(configs))
width = 0.35

bars1 = ax3.bar(x - width/2, max_dds, width, label='Max Drawdown (%)', color=['blue', 'green', 'red'], alpha=0.7)
ax3.set_ylabel('Max Drawdown (%)')
ax3.set_ylim(0, 100)

ax3_twin = ax3.twinx()
bars2 = ax3_twin.bar(x + width/2, sharpes, width, label='Sharpe Ratio', color=['lightblue', 'lightgreen', 'salmon'], alpha=0.7)
ax3_twin.set_ylabel('Sharpe Ratio (Return/DD)')

ax3.set_xticks(x)
ax3.set_xticklabels(configs)
ax3.set_title('Risk-Adjusted Performance Comparison', fontsize=11)
ax3.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='80% DD threshold')

# Add value labels
for bar, val in zip(bars1, max_dds):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{val:.1f}%', ha='center', va='bottom', fontsize=9)
for bar, val in zip(bars2, sharpes):
    ax3_twin.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, f'{val:.0f}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/config_comparison.png', dpi=150, bbox_inches='tight')
print(f"\nChart saved to: /workspaces/Carebiuro_windykacja/trading/results/config_comparison.png")

# Summary comparison table
print("\n" + "="*80)
print("CONFIGURATION COMPARISON SUMMARY")
print("="*80)
print(f"{'Config':<35} {'Return':<15} {'MaxDD':<10} {'Trades':<10} {'WR':<10} {'Sharpe':<10}")
print("-"*80)
print(f"{'Current (time_8+ema5+US_late)':<35} {stats_current['return']:>12,.0f}% {stats_current['max_dd']:>8.1f}% {stats_current['trades']:>8} {stats_current['wr']:>8.1f}% {stats_current['sharpe']:>8.0f}")
print(f"{'Optimized (time_4+ema8+US_evening)':<35} {stats_optimized['return']:>12,.0f}% {stats_optimized['max_dd']:>8.1f}% {stats_optimized['trades']:>8} {stats_optimized['wr']:>8.1f}% {stats_optimized['sharpe']:>8.0f}")
print(f"{'High-Return (time_6+ema3+US)':<35} {stats_best['return']:>12,.0f}% {stats_best['max_dd']:>8.1f}% {stats_best['trades']:>8} {stats_best['wr']:>8.1f}% {stats_best['sharpe']:>8.0f}")
print("="*80)

# Risk improvement
dd_improvement = stats_current['max_dd'] - stats_optimized['max_dd']
print(f"\nOPTIMIZED CONFIG RISK IMPROVEMENT:")
print(f"  - Max Drawdown reduced by: {dd_improvement:.1f} percentage points")
print(f"  - From {stats_current['max_dd']:.1f}% to {stats_optimized['max_dd']:.1f}%")
print(f"  - Return sacrifice: {stats_current['return']:,.0f}% → {stats_optimized['return']:,.0f}% ({(stats_optimized['return']/stats_current['return']*100):.1f}% of original)")
print(f"  - Better Sharpe: {stats_optimized['sharpe']:.0f} vs {stats_current['sharpe']:.0f}")
