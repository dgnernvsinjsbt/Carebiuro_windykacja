#!/usr/bin/env python3
"""
Deep analysis of 4% risk per trade strategy
- Track profit contribution by coin
- Generate equity curve
- Compare to 3% risk baseline
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

print("=" * 100)
print("4% RISK PER TRADE - DETAILED ANALYSIS")
print("=" * 100)

# Load trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Combine all trades
df_sep_dec['symbol'] = df_sep_dec['coin'].apply(lambda x: x if 'USDT' in str(x) else f"{x}-USDT")

all_trades = []

for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Map symbols
symbol_map = {
    'AIXBT-USDT': 'AIXBT-USDT', 'AIXBT': 'AIXBT-USDT',
    'MELANIA-USDT': 'MELANIA-USDT', 'MELANIA': 'MELANIA-USDT',
    'MOODENG-USDT': 'MOODENG-USDT', 'MOODENG': 'MOODENG-USDT',
    'PEPE-USDT': 'PEPE-USDT', 'PEPE': 'PEPE-USDT', '1000PEPE-USDT': 'PEPE-USDT',
    'DOGE-USDT': 'DOGE-USDT', 'DOGE': 'DOGE-USDT',
    'CRV-USDT': 'CRV-USDT', 'CRV': 'CRV-USDT',
    'TRUMPSOL-USDT': 'TRUMPSOL-USDT', 'TRUMPSOL': 'TRUMPSOL-USDT',
    'UNI-USDT': 'UNI-USDT', 'UNI': 'UNI-USDT',
    'XLM-USDT': 'XLM-USDT', 'XLM': 'XLM-USDT',
}

trades_df['symbol'] = trades_df['symbol'].map(symbol_map)

# Simulate with 4% risk
RISK_PCT = 4.0
ASSUMED_SL_DISTANCE_PCT = 3.0
LEVERAGE = 10.0

capital = 100.0
initial_capital = 100.0
peak_capital = 100.0
max_dd_pct = 0.0

trade_log = []
coin_profits = {}

for idx, trade in trades_df.iterrows():
    # Calculate position size
    position_size_pct = (RISK_PCT / (ASSUMED_SL_DISTANCE_PCT * LEVERAGE)) * 100
    position_size = capital * (position_size_pct / 100)

    # Apply leverage to P&L
    leveraged_pnl_pct = trade['pnl_pct'] * LEVERAGE

    # Calculate P&L in USD
    pnl_usd = position_size * (leveraged_pnl_pct / 100)

    # Update capital
    capital += pnl_usd

    # Track peak and drawdown
    if capital > peak_capital:
        peak_capital = capital

    dd_pct = ((capital - peak_capital) / peak_capital) * 100
    if dd_pct < max_dd_pct:
        max_dd_pct = dd_pct

    # Track profit by coin
    if trade['symbol'] not in coin_profits:
        coin_profits[trade['symbol']] = {
            'total_pnl': 0,
            'trades': 0,
            'winners': 0,
            'losers': 0,
            'total_pnl_pct': 0,
        }

    coin_profits[trade['symbol']]['total_pnl'] += pnl_usd
    coin_profits[trade['symbol']]['trades'] += 1
    coin_profits[trade['symbol']]['total_pnl_pct'] += trade['pnl_pct']

    if pnl_usd > 0:
        coin_profits[trade['symbol']]['winners'] += 1
    else:
        coin_profits[trade['symbol']]['losers'] += 1

    # Log trade
    trade_log.append({
        'trade_num': idx + 1,
        'date': trade['date'],
        'symbol': trade['symbol'],
        'capital_before': capital - pnl_usd,
        'position_size': position_size,
        'position_size_pct': position_size_pct,
        'pnl_pct': trade['pnl_pct'],
        'leveraged_pnl_pct': leveraged_pnl_pct,
        'pnl_usd': pnl_usd,
        'capital_after': capital,
        'exit_reason': trade['exit_reason'],
    })

trade_log_df = pd.DataFrame(trade_log)

# Calculate profit contribution percentages
total_profit = capital - initial_capital
coin_contribution = []

for symbol, stats in coin_profits.items():
    contribution_pct = (stats['total_pnl'] / total_profit) * 100 if total_profit > 0 else 0
    win_rate = (stats['winners'] / stats['trades']) * 100 if stats['trades'] > 0 else 0

    coin_contribution.append({
        'symbol': symbol,
        'profit_usd': stats['total_pnl'],
        'contribution_pct': contribution_pct,
        'trades': stats['trades'],
        'winners': stats['winners'],
        'losers': stats['losers'],
        'win_rate': win_rate,
        'avg_pnl_pct': stats['total_pnl_pct'] / stats['trades'] if stats['trades'] > 0 else 0,
    })

contribution_df = pd.DataFrame(coin_contribution).sort_values('profit_usd', ascending=False)

# Display results
print(f"\n💰 TOTAL PROFIT: ${total_profit:,.2f} (+{(total_profit/initial_capital)*100:.2f}%)")
print(f"   Max Drawdown: {max_dd_pct:.2f}%")
print(f"   Return/DD: {abs(total_profit/initial_capital*100 / max_dd_pct):.2f}x")
print(f"   Peak Capital: ${peak_capital:,.2f}")

print("\n" + "=" * 100)
print("PROFIT CONTRIBUTION BY COIN (4% Risk Per Trade)")
print("=" * 100)
print(f"{'Rank':<6} {'Coin':<15} {'Profit':>12} {'% of Total':>12} {'Trades':>8} {'Win%':>8} {'AvgP&L%':>10}")
print("-" * 100)

for idx, row in contribution_df.iterrows():
    rank = contribution_df.index.get_loc(idx) + 1
    print(f"{rank:<6} {row['symbol']:<15} ${row['profit_usd']:>11,.2f} {row['contribution_pct']:>11.2f}% "
          f"{row['trades']:>8} {row['win_rate']:>7.1f}% {row['avg_pnl_pct']:>+9.2f}%")

print("-" * 100)
print(f"{'TOTAL':<6} {'ALL COINS':<15} ${total_profit:>11,.2f} {'100.00%':>12} "
      f"{len(trade_log_df):>8}")

# Now load the baseline (3% risk = 10% fixed position) for comparison
print("\n" + "=" * 100)
print("COMPARISON: 4% RISK vs 3% RISK (BASELINE)")
print("=" * 100)

# Load baseline trade log
baseline_df = pd.read_csv('portfolio_10x_leverage_log.csv')
baseline_df['date'] = pd.to_datetime(baseline_df['date'])

# Calculate baseline profit by coin
baseline_coin_profits = {}
for _, trade in baseline_df.iterrows():
    if trade['symbol'] not in baseline_coin_profits:
        baseline_coin_profits[trade['symbol']] = 0
    baseline_coin_profits[trade['symbol']] += trade['pnl_usd']

baseline_total = baseline_df['capital_after'].iloc[-1] - 100.0

print(f"\n{'Coin':<15} {'3% Risk (10% Pos)':>20} {'4% Risk (13.3% Pos)':>20} {'Difference':>15}")
print("-" * 75)

for symbol in sorted(coin_profits.keys()):
    baseline_profit = baseline_coin_profits.get(symbol, 0)
    risk4_profit = coin_profits[symbol]['total_pnl']
    diff = risk4_profit - baseline_profit
    diff_pct = (diff / baseline_profit * 100) if baseline_profit != 0 else 0

    print(f"{symbol:<15} ${baseline_profit:>18,.2f} ${risk4_profit:>18,.2f} "
          f"${diff:>+13,.2f} ({diff_pct:+.1f}%)")

print("-" * 75)
print(f"{'TOTAL':<15} ${baseline_total:>18,.2f} ${total_profit:>18,.2f} "
      f"${total_profit - baseline_total:>+13,.2f} ({(total_profit - baseline_total)/baseline_total*100:+.1f}%)")

# Create equity curve visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])
fig.suptitle('4% Risk Per Trade - Equity Curve (Sep 15 - Dec 15, 2025)',
             fontsize=16, fontweight='bold')

# Calculate drawdown
trade_log_df['peak'] = trade_log_df['capital_after'].cummax()
trade_log_df['drawdown_pct'] = ((trade_log_df['capital_after'] - trade_log_df['peak']) / trade_log_df['peak']) * 100

# Top subplot: Equity curve
ax1.plot(trade_log_df['date'], trade_log_df['capital_after'], linewidth=2, color='#2E86DE', label='4% Risk Portfolio')
ax1.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5, label='Starting Capital ($100)')
ax1.fill_between(trade_log_df['date'], initial_capital, trade_log_df['capital_after'],
                  where=(trade_log_df['capital_after'] >= initial_capital),
                  color='green', alpha=0.1, label='Profit Zone')

# Mark key points
peak_idx = trade_log_df['capital_after'].idxmax()
peak_date = trade_log_df.loc[peak_idx, 'date']
peak_value = trade_log_df.loc[peak_idx, 'capital_after']

worst_dd_idx = trade_log_df['drawdown_pct'].idxmin()
worst_dd_value = trade_log_df.loc[worst_dd_idx, 'capital_after']
worst_dd_date = trade_log_df.loc[worst_dd_idx, 'date']

final_value = trade_log_df['capital_after'].iloc[-1]
final_date = trade_log_df['date'].iloc[-1]

ax1.scatter([peak_date], [peak_value], color='gold', s=200, zorder=5, marker='*',
            edgecolors='black', linewidths=2, label=f'Peak: ${peak_value:,.0f}')
ax1.scatter([worst_dd_date], [worst_dd_value], color='red', s=200, zorder=5, marker='v',
            edgecolors='black', linewidths=2, label=f'Max DD: ${worst_dd_value:,.0f}')
ax1.scatter([final_date], [final_value], color='blue', s=200, zorder=5, marker='o',
            edgecolors='black', linewidths=2, label=f'Final: ${final_value:,.0f}')

# Annotations
ax1.annotate(f'Peak\n${peak_value:,.0f}',
             xy=(peak_date, peak_value),
             xytext=(10, 30), textcoords='offset points',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='gold', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=2))

ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
ax1.set_title(f'4% Risk: ${initial_capital:.0f} → ${final_value:,.0f} (+{((final_value-initial_capital)/initial_capital*100):.1f}%)',
              fontsize=13, fontweight='bold', pad=10)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(trade_log_df['date'].min(), trade_log_df['date'].max())

# Format x-axis
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Bottom subplot: Drawdown
ax2.fill_between(trade_log_df['date'], 0, trade_log_df['drawdown_pct'],
                  color='red', alpha=0.3, label='Drawdown from Peak')
ax2.plot(trade_log_df['date'], trade_log_df['drawdown_pct'], linewidth=2, color='darkred')
ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
ax2.axhline(y=max_dd_pct, color='red', linestyle='--', alpha=0.5)

ax2.scatter([worst_dd_date], [max_dd_pct], color='red', s=150, zorder=5, marker='v',
            edgecolors='black', linewidths=2)

ax2.set_ylabel('Drawdown %', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_title(f'Drawdown from Peak (Max: {max_dd_pct:.2f}%)', fontsize=13, fontweight='bold', pad=10)
ax2.legend(loc='lower left', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(trade_log_df['date'].min(), trade_log_df['date'].max())

# Format x-axis
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Add stats box
stats_text = f"""PERFORMANCE STATS (4% Risk):
Starting: ${initial_capital:.0f}
Peak: ${peak_value:,.0f} ({((peak_value-initial_capital)/initial_capital*100):.1f}%)
Final: ${final_value:,.0f} (+{((final_value-initial_capital)/initial_capital*100):.1f}%)
Max DD: {max_dd_pct:.2f}%
Return/DD: {abs((final_value-initial_capital)/initial_capital*100 / max_dd_pct):.1f}x
Win Rate: {(trade_log_df['pnl_usd'] > 0).sum() / len(trade_log_df) * 100:.1f}%
Trades: {len(trade_log_df)}
Position: 13.33% (avg)"""

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=9,
         verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()
plt.savefig('equity_curve_4pct_risk.png', dpi=300, bbox_inches='tight')
print(f"\n✅ Equity curve saved to: equity_curve_4pct_risk.png")

# Save detailed trade log
trade_log_df.to_csv('trade_log_4pct_risk.csv', index=False)
print(f"✅ Trade log saved to: trade_log_4pct_risk.csv")

plt.close()

print("\n" + "=" * 100)
print("KEY INSIGHTS:")
print("=" * 100)

print(f"\n🎯 POSITION SIZING:")
print(f"   • Fixed at 13.33% of capital per trade (4% risk ÷ (3% SL × 10x) = 13.33%)")
print(f"   • vs 10.00% in baseline (3% risk)")
print(f"   • +33.3% larger positions = more exposure per trade")

print(f"\n💡 PROFIT SHIFT:")
best_3pct = max(baseline_coin_profits.items(), key=lambda x: x[1])
best_4pct = contribution_df.iloc[0]

print(f"   • 3% Risk Top Performer: {best_3pct[0]} (${best_3pct[1]:,.2f})")
print(f"   • 4% Risk Top Performer: {best_4pct['symbol']} (${best_4pct['profit_usd']:,.2f})")

# Find biggest gainers/losers from the increase
comparison = []
for symbol in coin_profits.keys():
    baseline_profit = baseline_coin_profits.get(symbol, 0)
    risk4_profit = coin_profits[symbol]['total_pnl']
    diff = risk4_profit - baseline_profit
    diff_pct = (diff / baseline_profit * 100) if baseline_profit != 0 else 0
    comparison.append({'symbol': symbol, 'diff': diff, 'diff_pct': diff_pct})

comparison_df = pd.DataFrame(comparison).sort_values('diff', ascending=False)

print(f"\n📈 BIGGEST GAINERS (from 3% → 4% risk):")
for _, row in comparison_df.head(3).iterrows():
    print(f"   • {row['symbol']}: +${row['diff']:,.2f} ({row['diff_pct']:+.1f}%)")

print(f"\n📉 BIGGEST LOSERS (from 3% → 4% risk):")
for _, row in comparison_df.tail(3).iterrows():
    print(f"   • {row['symbol']}: ${row['diff']:,.2f} ({row['diff_pct']:+.1f}%)")
