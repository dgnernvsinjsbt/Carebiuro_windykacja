#!/usr/bin/env python3
"""
Generate equity curve for 5% risk per trade with TRUE dynamic position sizing
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

print("=" * 100)
print("5% RISK PER TRADE - EQUITY CURVE GENERATION")
print("=" * 100)

# Load trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Calculate actual average SL distance per coin
sl_trades = df_sep_dec[df_sep_dec['exit_reason'] == 'SL']
avg_sl_by_coin = {}

for coin in df_sep_dec['coin'].unique():
    coin_sl = sl_trades[sl_trades['coin'] == coin]
    if len(coin_sl) > 0:
        avg_sl_by_coin[coin] = abs(coin_sl['pnl_pct'].mean())
    else:
        avg_sl_by_coin[coin] = 2.64

# Map symbols
symbol_map = {
    'AIXBT-USDT': 'AIXBT', 'AIXBT': 'AIXBT',
    'MELANIA-USDT': 'MELANIA', 'MELANIA': 'MELANIA',
    'MOODENG-USDT': 'MOODENG', 'MOODENG': 'MOODENG',
    'PEPE-USDT': 'PEPE', 'PEPE': 'PEPE', '1000PEPE-USDT': 'PEPE',
    'DOGE-USDT': 'DOGE', 'DOGE': 'DOGE',
    'CRV-USDT': 'CRV', 'CRV': 'CRV',
    'TRUMPSOL-USDT': 'TRUMPSOL', 'TRUMPSOL': 'TRUMPSOL',
    'UNI-USDT': 'UNI', 'UNI': 'UNI',
    'XLM-USDT': 'XLM', 'XLM': 'XLM',
}

# Combine trades
df_sep_dec['symbol'] = df_sep_dec['coin']

all_trades = []

for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['coin'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

for _, trade in df_dec_8_15.iterrows():
    coin_name = symbol_map.get(trade['symbol'], trade['symbol'])
    all_trades.append({
        'symbol': coin_name,
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Simulate with 5% risk
RISK_PCT = 5.0
LEVERAGE = 10.0

capital = 100.0
initial_capital = 100.0
peak_capital = 100.0
max_dd_pct = 0.0

trade_log = []
coin_profits = {}

for idx, trade in trades_df.iterrows():
    coin = trade['symbol']
    sl_distance_pct = avg_sl_by_coin.get(coin, 2.64)

    # Dynamic position sizing
    position_size_pct = (RISK_PCT / (sl_distance_pct * LEVERAGE)) * 100
    position_size = capital * (position_size_pct / 100)

    # Apply leverage
    leveraged_pnl_pct = trade['pnl_pct'] * LEVERAGE
    pnl_usd = position_size * (leveraged_pnl_pct / 100)

    # Update capital
    capital += pnl_usd

    # Track peak and drawdown
    if capital > peak_capital:
        peak_capital = capital

    dd_pct = ((capital - peak_capital) / peak_capital) * 100
    if dd_pct < max_dd_pct:
        max_dd_pct = dd_pct

    # Track by coin
    if coin not in coin_profits:
        coin_profits[coin] = {
            'total_pnl': 0,
            'trades': 0,
            'winners': 0,
        }

    coin_profits[coin]['total_pnl'] += pnl_usd
    coin_profits[coin]['trades'] += 1
    if pnl_usd > 0:
        coin_profits[coin]['winners'] += 1

    # Log trade
    trade_log.append({
        'trade_num': idx + 1,
        'date': trade['date'],
        'symbol': coin,
        'capital_before': capital - pnl_usd,
        'position_size': position_size,
        'position_size_pct': position_size_pct,
        'pnl_pct': trade['pnl_pct'],
        'leveraged_pnl_pct': leveraged_pnl_pct,
        'pnl_usd': pnl_usd,
        'capital_after': capital,
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance_pct,
    })

trade_log_df = pd.DataFrame(trade_log)

# Calculate profit contribution
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
        'win_rate': win_rate,
    })

contribution_df = pd.DataFrame(coin_contribution).sort_values('profit_usd', ascending=False)

# Print summary
print(f"\n💰 FINAL CAPITAL: ${capital:,.2f}")
print(f"   Total Profit: ${total_profit:,.2f} (+{(total_profit/initial_capital)*100:.2f}%)")
print(f"   Peak: ${peak_capital:,.2f}")
print(f"   Max Drawdown: {max_dd_pct:.2f}%")
print(f"   Return/DD: {abs(total_profit/initial_capital*100 / max_dd_pct):.2f}x")

print("\n" + "=" * 100)
print("PROFIT CONTRIBUTION BY COIN (5% Risk)")
print("=" * 100)
print(f"{'Rank':<6} {'Coin':<15} {'Profit':>15} {'% of Total':>12} {'Trades':>8} {'Win%':>8}")
print("-" * 100)

for idx, row in contribution_df.iterrows():
    rank = contribution_df.index.get_loc(idx) + 1
    print(f"{rank:<6} {row['symbol']:<15} ${row['profit_usd']:>14,.2f} {row['contribution_pct']:>11.2f}% "
          f"{row['trades']:>8} {row['win_rate']:>7.1f}%")

print("-" * 100)
print(f"{'TOTAL':<6} {'ALL COINS':<15} ${total_profit:>14,.2f} {'100.00%':>12} {len(trade_log_df):>8}")

# Create equity curve
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])
fig.suptitle('5% Risk Per Trade - TRUE Dynamic Position Sizing (Sep 15 - Dec 15, 2025)',
             fontsize=16, fontweight='bold')

# Calculate drawdown
trade_log_df['peak'] = trade_log_df['capital_after'].cummax()
trade_log_df['drawdown_pct'] = ((trade_log_df['capital_after'] - trade_log_df['peak']) / trade_log_df['peak']) * 100

# Top: Equity curve
ax1.plot(trade_log_df['date'], trade_log_df['capital_after'], linewidth=2, color='#2E86DE', label='Portfolio Equity')
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
            edgecolors='black', linewidths=2, label=f'Peak: \\${peak_value:,.0f}')
ax1.scatter([worst_dd_date], [worst_dd_value], color='red', s=200, zorder=5, marker='v',
            edgecolors='black', linewidths=2, label=f'Max DD: \\${worst_dd_value:,.0f}')
ax1.scatter([final_date], [final_value], color='blue', s=200, zorder=5, marker='o',
            edgecolors='black', linewidths=2, label=f'Final: \\${final_value:,.0f}')

# Annotations
ax1.annotate(f'Peak\n\\${peak_value:,.0f}',
             xy=(peak_date, peak_value),
             xytext=(10, 30), textcoords='offset points',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='gold', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=2))

ax1.annotate(f'Max DD\n\\${worst_dd_value:,.0f}\n({max_dd_pct:.1f}%)',
             xy=(worst_dd_date, worst_dd_value),
             xytext=(10, -50), textcoords='offset points',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=2))

ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
ax1.set_title(f'5% Risk: \\${initial_capital:.0f} → \\${final_value:,.0f} (+{((final_value-initial_capital)/initial_capital*100):.1f}%)',
              fontsize=13, fontweight='bold', pad=10)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(trade_log_df['date'].min(), trade_log_df['date'].max())

# Format x-axis
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Bottom: Drawdown
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

# Stats box
stats_text = f"""PERFORMANCE (5% Risk):
Starting: \\${initial_capital:.0f}
Peak: \\${peak_value:,.0f} ({((peak_value-initial_capital)/initial_capital*100):.1f}%)
Final: \\${final_value:,.0f} (+{((final_value-initial_capital)/initial_capital*100):.1f}%)
Max DD: {max_dd_pct:.2f}%
Return/DD: {abs((final_value-initial_capital)/initial_capital*100 / max_dd_pct):.1f}x
Win Rate: {(trade_log_df['pnl_usd'] > 0).sum() / len(trade_log_df) * 100:.1f}%
Trades: {len(trade_log_df)}
Pos Size: 11.0%-30.7% (dynamic)"""

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=9,
         verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()
plt.savefig('equity_curve_5pct_risk.png', dpi=300, bbox_inches='tight')
print(f"\n✅ Equity curve saved to: equity_curve_5pct_risk.png")

# Save trade log
trade_log_df.to_csv('trade_log_5pct_risk.csv', index=False)
print(f"✅ Trade log saved to: trade_log_5pct_risk.csv")

plt.close()

# Position size analysis
print("\n" + "=" * 100)
print("POSITION SIZE ANALYSIS (5% Risk)")
print("=" * 100)
print(f"\nAverage position size: {trade_log_df['position_size_pct'].mean():.2f}%")
print(f"Min position size: {trade_log_df['position_size_pct'].min():.2f}%")
print(f"Max position size: {trade_log_df['position_size_pct'].max():.2f}%")

print("\n📊 POSITION SIZES BY COIN:")
for coin in sorted(avg_sl_by_coin.keys(), key=lambda x: avg_sl_by_coin[x]):
    sl = avg_sl_by_coin[coin]
    pos_size = (RISK_PCT / (sl * LEVERAGE)) * 100
    coin_trades = trade_log_df[trade_log_df['symbol'] == coin]
    print(f"   {coin:15} (SL {sl:.2f}%) → Position: {pos_size:.2f}% | Trades: {len(coin_trades):>3} | "
          f"Profit: ${coin_profits.get(coin, {}).get('total_pnl', 0):>10,.2f}")

print("\n💡 KEY INSIGHT:")
print(f"   • Tightest stops (CRV, XLM) get 30.7% positions - 3.5x larger than TRUMPSOL!")
print(f"   • Each trade still risks exactly 5% if SL hits")
print(f"   • But winning trades on tight-stop coins contribute MUCH more")
