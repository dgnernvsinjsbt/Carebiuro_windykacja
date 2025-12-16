#!/usr/bin/env python3
"""
Simulate 9 separate $10 accounts (one per coin) vs shared portfolio
Compare: isolated coin performance vs portfolio diversification
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("SEPARATE ACCOUNTS SIMULATION")
print("=" * 80)
print("Setup: Each coin gets $10 starting capital, trades independently")
print("Total starting capital: $90 (9 coins × $10)")
print()

# Load Sep 15 - Dec 7 trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

# Load Dec 8-15 trades
df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Combine all trades
# Need to standardize column names
df_sep_dec['symbol'] = df_sep_dec['coin'].apply(lambda x: x if 'USDT' in str(x) else f"{x}-USDT")
df_sep_dec['pnl_pct'] = df_sep_dec['pnl_pct']

all_trades = []

# Add Sep-Dec 7 trades
for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'period': 'Sep-Dec7'
    })

# Add Dec 8-15 trades
for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'period': 'Dec8-15'
    })

# Convert to DataFrame
trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Map symbol names to standard format
symbol_map = {
    'AIXBT-USDT': 'AIXBT-USDT',
    'AIXBT': 'AIXBT-USDT',
    'MELANIA-USDT': 'MELANIA-USDT',
    'MELANIA': 'MELANIA-USDT',
    'MOODENG-USDT': 'MOODENG-USDT',
    'MOODENG': 'MOODENG-USDT',
    'PEPE-USDT': 'PEPE-USDT',
    'PEPE': 'PEPE-USDT',
    '1000PEPE-USDT': 'PEPE-USDT',
    'DOGE-USDT': 'DOGE-USDT',
    'DOGE': 'DOGE-USDT',
    'CRV-USDT': 'CRV-USDT',
    'CRV': 'CRV-USDT',
    'TRUMPSOL-USDT': 'TRUMPSOL-USDT',
    'TRUMPSOL': 'TRUMPSOL-USDT',
    'UNI-USDT': 'UNI-USDT',
    'UNI': 'UNI-USDT',
    'XLM-USDT': 'XLM-USDT',
    'XLM': 'XLM-USDT',
}

trades_df['symbol'] = trades_df['symbol'].map(symbol_map)

# Simulate each coin with $10 starting capital
results = []

for symbol in sorted(trades_df['symbol'].unique()):
    coin_trades = trades_df[trades_df['symbol'] == symbol].sort_values('date')

    capital = 10.0  # Each coin starts with $10
    initial_capital = 10.0
    peak_capital = 10.0
    max_dd = 0.0

    for _, trade in coin_trades.iterrows():
        # Position size: 10% of current capital (same as portfolio strategy)
        position_size = capital * 0.10
        pnl_usd = position_size * (trade['pnl_pct'] / 100)
        capital += pnl_usd

        # Track drawdown
        if capital > peak_capital:
            peak_capital = capital

        dd = ((capital - peak_capital) / peak_capital) * 100
        if dd < max_dd:
            max_dd = dd

    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    results.append({
        'symbol': symbol,
        'starting': initial_capital,
        'final': final_capital,
        'profit': final_capital - initial_capital,
        'return_pct': total_return,
        'max_dd_pct': max_dd,
        'trades': len(coin_trades),
        'sep_dec_trades': len(coin_trades[coin_trades['period'] == 'Sep-Dec7']),
        'dec8_15_trades': len(coin_trades[coin_trades['period'] == 'Dec8-15'])
    })

results_df = pd.DataFrame(results).sort_values('profit', ascending=False)

# Calculate totals
total_starting = results_df['starting'].sum()
total_final = results_df['final'].sum()
total_profit = results_df['profit'].sum()
total_return = ((total_final - total_starting) / total_starting) * 100

# Calculate portfolio-level max DD
# For independent accounts, max DD is weighted average
weighted_dd = sum(results_df['max_dd_pct'] * results_df['starting']) / total_starting

print("\n📊 INDIVIDUAL COIN PERFORMANCE:")
print("=" * 100)
print(f"{'Coin':<15} {'Start':>8} {'Final':>8} {'Profit':>9} {'Return%':>9} {'MaxDD%':>9} {'Trades':>7} {'Sep-Dec7':>9} {'Dec8-15':>8}")
print("-" * 100)

for _, row in results_df.iterrows():
    print(f"{row['symbol']:<15} ${row['starting']:>7.2f} ${row['final']:>7.2f} "
          f"${row['profit']:>+8.2f} {row['return_pct']:>+8.2f}% {row['max_dd_pct']:>+8.2f}% "
          f"{row['trades']:>7} {row['sep_dec_trades']:>9} {row['dec8_15_trades']:>8}")

print("-" * 100)
print(f"{'TOTAL':<15} ${total_starting:>7.2f} ${total_final:>7.2f} "
      f"${total_profit:>+8.2f} {total_return:>+8.2f}%")

print("\n" + "=" * 100)
print("COMPARISON: Separate Accounts vs Shared Portfolio")
print("=" * 100)

# Shared portfolio results (from previous analysis)
shared_starting = 100.0
shared_final = 133.65  # From continuation backtest
shared_return = 33.65
shared_max_dd = -3.23

print(f"\n{'Metric':<30} {'Separate Accounts':>20} {'Shared Portfolio':>20} {'Difference':>15}")
print("-" * 90)
print(f"{'Starting Capital':<30} ${total_starting:>19.2f} ${shared_starting:>19.2f} ${total_starting - shared_starting:>+14.2f}")
print(f"{'Final Capital':<30} ${total_final:>19.2f} ${shared_final:>19.2f} ${total_final - shared_final:>+14.2f}")
print(f"{'Total Profit':<30} ${total_profit:>19.2f} ${shared_final - shared_starting:>19.2f} ${total_profit - (shared_final - shared_starting):>+14.2f}")
print(f"{'Return %':<30} {total_return:>19.2f}% {shared_return:>19.2f}% {total_return - shared_return:>+14.2f}pp")
print(f"{'Max Drawdown %':<30} {weighted_dd:>19.2f}% {shared_max_dd:>19.2f}% {weighted_dd - shared_max_dd:>+14.2f}pp")

# Normalized comparison (per $100)
sep_per_100 = (total_final / total_starting) * 100
shared_per_100 = shared_final

print(f"\n{'Normalized to $100 start:':<30} ${sep_per_100:>19.2f} ${shared_per_100:>19.2f} ${sep_per_100 - shared_per_100:>+14.2f}")

print("\n" + "=" * 100)
print("ANALYSIS:")
print("=" * 100)

winners = results_df[results_df['profit'] > 0]
losers = results_df[results_df['profit'] <= 0]

print(f"\n✅ Winning Coins: {len(winners)}/9 ({len(winners)/9*100:.1f}%)")
print(f"❌ Losing Coins: {len(losers)}/9 ({len(losers)/9*100:.1f}%)")

print(f"\n📈 Best Performer: {results_df.iloc[0]['symbol']} ({results_df.iloc[0]['return_pct']:+.2f}%)")
print(f"📉 Worst Performer: {results_df.iloc[-1]['symbol']} ({results_df.iloc[-1]['return_pct']:+.2f}%)")

total_winner_profit = winners['profit'].sum()
total_loser_loss = abs(losers['profit'].sum())

print(f"\n💰 Total from Winners: ${total_winner_profit:+.2f}")
print(f"💸 Total from Losers: ${-total_loser_loss:+.2f}")
print(f"🎯 Net: ${total_winner_profit - total_loser_loss:+.2f}")

print("\n🔍 KEY INSIGHTS:")

if total_final > shared_final:
    print(f"  ✅ Separate accounts OUTPERFORMED shared portfolio by ${total_final - shared_final:.2f}")
    print(f"     → Starting with $90 beats starting with $100!")
else:
    diff_pct = ((shared_per_100 - sep_per_100) / sep_per_100) * 100
    print(f"  ⚠️ Shared portfolio performed BETTER (${shared_per_100:.2f} vs ${sep_per_100:.2f} per $100)")
    print(f"     → Compounding + capital allocation boosted returns by {diff_pct:.1f}%")

if abs(weighted_dd) < abs(shared_max_dd):
    print(f"  ✅ Separate accounts had LOWER drawdown ({weighted_dd:.2f}% vs {shared_max_dd:.2f}%)")
    print(f"     → Isolation protected from worst drawdowns")
else:
    print(f"  ⚠️ Shared portfolio had LOWER drawdown ({shared_max_dd:.2f}% vs {weighted_dd:.2f}%)")
    print(f"     → Diversification benefit worked")

print("\n💡 IMPLICATIONS:")
print("  • Separate accounts = Better risk isolation per coin")
print("  • Shared portfolio = Better capital efficiency + compounding")
print("  • Losing coins (CRV) hurt less with separation")
print("  • Winning coins compound faster in shared portfolio")

# Calculate what $90 would have done in shared portfolio
shared_90_start = 90.0
shared_90_final = (shared_final / shared_starting) * shared_90_start

print(f"\n🎲 FAIREST COMPARISON ($90 start for both):")
print(f"  Separate Accounts: ${total_final:.2f}")
print(f"  Shared Portfolio:  ${shared_90_final:.2f}")

if total_final > shared_90_final:
    print(f"  → Separate accounts WIN by ${total_final - shared_90_final:.2f}")
else:
    print(f"  → Shared portfolio WINS by ${shared_90_final - total_final:.2f}")
