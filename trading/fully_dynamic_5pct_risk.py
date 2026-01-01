#!/usr/bin/env python3
"""
FULLY DYNAMIC 5% risk per trade - each trade has its own SL distance
- Dec 8-15: Use actual stop_loss from data
- Sep-Dec 7: Infer SL from actual losses where available, else use coin average
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

print("=" * 100)
print("FULLY DYNAMIC 5% RISK - TRUE PER-TRADE POSITION SIZING")
print("=" * 100)

# Load Sep-Dec 7 data
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

# Load Dec 8-15 data with actual SL values
df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# For Sep-Dec 7: calculate SL distance per trade where possible
# For SL exits: the actual loss IS the SL distance
# For TP/Time exits: use coin average as fallback
sl_trades = df_sep_dec[df_sep_dec['exit_reason'] == 'SL']
coin_avg_sl = {}

for coin in df_sep_dec['coin'].unique():
    coin_sl = sl_trades[sl_trades['coin'] == coin]
    if len(coin_sl) > 0:
        coin_avg_sl[coin] = abs(coin_sl['pnl_pct'].mean())
    else:
        coin_avg_sl[coin] = 2.64

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
all_trades = []

# Sep-Dec 7 trades: infer SL distance
for _, trade in df_sep_dec.iterrows():
    if trade['exit_reason'] == 'SL':
        # For SL exits: actual loss is the SL distance
        sl_distance = abs(trade['pnl_pct'])
    else:
        # For TP/Time: use coin average
        sl_distance = coin_avg_sl.get(trade['coin'], 2.64)

    all_trades.append({
        'symbol': trade['coin'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance,
        'source': 'sep-dec7'
    })

# Dec 8-15 trades: use actual SL from data
for _, trade in df_dec_8_15.iterrows():
    coin_name = symbol_map.get(trade['symbol'], trade['symbol'])
    sl_distance = abs((trade['stop_loss'] - trade['entry_price']) / trade['entry_price'] * 100)

    all_trades.append({
        'symbol': coin_name,
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance,
        'source': 'dec8-15'
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

print(f"\nTotal trades: {len(trades_df)}")
print(f"  Sep-Dec 7: {len(trades_df[trades_df['source'] == 'sep-dec7'])} (SL inferred from actual losses)")
print(f"  Dec 8-15: {len(trades_df[trades_df['source'] == 'dec8-15'])} (SL from actual data)")

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
    # Use THIS trade's actual SL distance
    sl_distance_pct = trade['sl_distance']

    # Dynamic position sizing based on this specific trade
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
    coin = trade['symbol']
    if coin not in coin_profits:
        coin_profits[coin] = {'total_pnl': 0, 'trades': 0, 'winners': 0}

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
        'source': trade['source'],
    })

trade_log_df = pd.DataFrame(trade_log)

# Results
total_profit = capital - initial_capital

print(f"\n{'='*100}")
print("RESULTS - FULLY DYNAMIC POSITION SIZING")
print(f"{'='*100}")
print(f"\n💰 FINAL CAPITAL: ${capital:,.2f}")
print(f"   Total Profit: ${total_profit:,.2f} (+{(total_profit/initial_capital)*100:.2f}%)")
print(f"   Peak: ${peak_capital:,.2f}")
print(f"   Max Drawdown: {max_dd_pct:.2f}%")
print(f"   Return/DD: {abs(total_profit/initial_capital*100 / max_dd_pct):.2f}x")

print(f"\n📊 POSITION SIZE STATISTICS:")
print(f"   Min: {trade_log_df['position_size_pct'].min():.2f}%")
print(f"   Max: {trade_log_df['position_size_pct'].max():.2f}%")
print(f"   Mean: {trade_log_df['position_size_pct'].mean():.2f}%")
print(f"   Median: {trade_log_df['position_size_pct'].median():.2f}%")
print(f"   Std Dev: {trade_log_df['position_size_pct'].std():.2f}%")

print(f"\n📈 POSITION SIZE RANGE BY COIN:")
print(f"{'Coin':<15} {'Trades':>7} {'Min Pos':>10} {'Max Pos':>10} {'Avg Pos':>10} {'Profit':>15}")
print("-" * 80)

for coin in sorted(coin_profits.keys()):
    coin_trades = trade_log_df[trade_log_df['symbol'] == coin]
    print(f"{coin:<15} {len(coin_trades):>7} {coin_trades['position_size_pct'].min():>9.2f}% "
          f"{coin_trades['position_size_pct'].max():>9.2f}% {coin_trades['position_size_pct'].mean():>9.2f}% "
          f"${coin_profits[coin]['total_pnl']:>13,.2f}")

# Profit contribution
contribution_df = []
for symbol, stats in coin_profits.items():
    contribution_pct = (stats['total_pnl'] / total_profit) * 100 if total_profit > 0 else 0
    win_rate = (stats['winners'] / stats['trades']) * 100 if stats['trades'] > 0 else 0

    contribution_df.append({
        'symbol': symbol,
        'profit_usd': stats['total_pnl'],
        'contribution_pct': contribution_pct,
        'trades': stats['trades'],
        'win_rate': win_rate,
    })

contribution_df = pd.DataFrame(contribution_df).sort_values('profit_usd', ascending=False)

print(f"\n{'='*100}")
print("PROFIT CONTRIBUTION BY COIN")
print(f"{'='*100}")
print(f"{'Rank':<6} {'Coin':<15} {'Profit':>15} {'% of Total':>12} {'Trades':>8} {'Win%':>8}")
print("-" * 80)

for idx, row in contribution_df.iterrows():
    rank = contribution_df.index.get_loc(idx) + 1
    print(f"{rank:<6} {row['symbol']:<15} ${row['profit_usd']:>14,.2f} {row['contribution_pct']:>11.2f}% "
          f"{row['trades']:>8} {row['win_rate']:>7.1f}%")

print("-" * 80)
print(f"{'TOTAL':<6} {'ALL COINS':<15} ${total_profit:>14,.2f} {'100.00%':>12} {len(trade_log_df):>8}")

# Show examples of position size variation
print(f"\n{'='*100}")
print("EXAMPLES: POSITION SIZE VARIATION WITHIN SAME COIN")
print(f"{'='*100}")

for coin in ['MOODENG', 'AIXBT', 'DOGE'][:3]:
    coin_trades = trade_log_df[trade_log_df['symbol'] == coin].head(5)
    if len(coin_trades) > 0:
        print(f"\n{coin}:")
        for _, t in coin_trades.iterrows():
            print(f"  Trade #{t['trade_num']:>3}: SL {t['sl_distance']:>5.2f}% → Pos {t['position_size_pct']:>5.2f}% | "
                  f"P&L: {t['pnl_pct']:>+6.2f}% → ${t['pnl_usd']:>+10,.2f} | Exit: {t['exit_reason']}")

# Save files
trade_log_df.to_csv('trade_log_5pct_fully_dynamic.csv', index=False)
print(f"\n✅ Trade log saved to: trade_log_5pct_fully_dynamic.csv")

# Create equity curve
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])
fig.suptitle('5% Risk Per Trade - FULLY Dynamic Position Sizing (Sep 15 - Dec 15, 2025)',
             fontsize=16, fontweight='bold')

# Calculate drawdown
trade_log_df['peak'] = trade_log_df['capital_after'].cummax()
trade_log_df['drawdown_pct'] = ((trade_log_df['capital_after'] - trade_log_df['peak']) / trade_log_df['peak']) * 100

# Equity curve
ax1.plot(trade_log_df['date'], trade_log_df['capital_after'], linewidth=2, color='#2E86DE', label='Portfolio Equity')
ax1.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
ax1.fill_between(trade_log_df['date'], initial_capital, trade_log_df['capital_after'],
                  where=(trade_log_df['capital_after'] >= initial_capital),
                  color='green', alpha=0.1)

# Key points
peak_idx = trade_log_df['capital_after'].idxmax()
peak_date = trade_log_df.loc[peak_idx, 'date']
peak_value = trade_log_df.loc[peak_idx, 'capital_after']

worst_dd_idx = trade_log_df['drawdown_pct'].idxmin()
worst_dd_value = trade_log_df.loc[worst_dd_idx, 'capital_after']
worst_dd_date = trade_log_df.loc[worst_dd_idx, 'date']

final_value = trade_log_df['capital_after'].iloc[-1]
final_date = trade_log_df['date'].iloc[-1]

ax1.scatter([peak_date], [peak_value], color='gold', s=200, zorder=5, marker='*',
            edgecolors='black', linewidths=2)
ax1.scatter([worst_dd_date], [worst_dd_value], color='red', s=200, zorder=5, marker='v',
            edgecolors='black', linewidths=2)
ax1.scatter([final_date], [final_value], color='blue', s=200, zorder=5, marker='o',
            edgecolors='black', linewidths=2)

ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
ax1.set_title(f'5% Risk (Dynamic): \\${initial_capital:.0f} → \\${final_value:,.0f} (+{((final_value-initial_capital)/initial_capital*100):.1f}%)',
              fontsize=13, fontweight='bold', pad=10)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(trade_log_df['date'].min(), trade_log_df['date'].max())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Drawdown
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
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Stats box
stats_text = f"""FULLY DYNAMIC (5% Risk):
Starting: \\${initial_capital:.0f}
Peak: \\${peak_value:,.0f}
Final: \\${final_value:,.0f}
Max DD: {max_dd_pct:.2f}%
Return/DD: {abs((final_value-initial_capital)/initial_capital*100 / max_dd_pct):.1f}x
Win Rate: {(trade_log_df['pnl_usd'] > 0).sum() / len(trade_log_df) * 100:.1f}%
Position: {trade_log_df['position_size_pct'].min():.1f}%-{trade_log_df['position_size_pct'].max():.1f}%"""

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=9,
         verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()
plt.savefig('equity_curve_5pct_fully_dynamic.png', dpi=300, bbox_inches='tight')
print(f"✅ Equity curve saved to: equity_curve_5pct_fully_dynamic.png")

plt.close()
