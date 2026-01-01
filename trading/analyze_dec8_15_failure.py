#!/usr/bin/env python3
"""
Deep dive analysis: Why did Dec 8-15 have 3x worse drawdown than Sep-Dec 7?
"""

import pandas as pd
import numpy as np

# Load trades
df = pd.read_csv('dec8_15_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])

# Load Sep-Dec 7 trades for comparison
df_original = pd.read_csv('portfolio_trade_log_chronological.csv')
df_original['date'] = pd.to_datetime(df_original['date'])

print("=" * 80)
print("FORENSIC ANALYSIS: Why Did Dec 8-15 Fail?")
print("=" * 80)

# 1. Exit Reason Analysis
print("\n1. EXIT REASON BREAKDOWN:")
print("-" * 40)

exit_counts = df['exit_reason'].value_counts()
for reason, count in exit_counts.items():
    pct = (count / len(df)) * 100
    reason_trades = df[df['exit_reason'] == reason]
    avg_pnl = reason_trades['pnl_pct'].mean()
    print(f"  {reason:12} {count:3} trades ({pct:5.1f}%)  Avg P&L: {avg_pnl:+6.2f}%")

# Compare to original period
print("\n  COMPARISON TO SEP-DEC 7:")
original_sl_rate = (df_original['exit_reason'] == 'SL').sum() / len(df_original) * 100
dec_sl_rate = (df['exit_reason'] == 'SL').sum() / len(df) * 100
print(f"    Sep-Dec 7 SL Rate: {original_sl_rate:.1f}%")
print(f"    Dec 8-15 SL Rate:  {dec_sl_rate:.1f}%")
print(f"    **INCREASE: {dec_sl_rate - original_sl_rate:+.1f} percentage points**")

# 2. Worst Offenders
print("\n2. WORST LOSING TRADES (caused drawdown):")
print("-" * 40)

worst_trades = df[df['pnl_pct'] < 0].sort_values('pnl_pct').head(10)
for idx, trade in worst_trades.iterrows():
    print(f"  {trade['symbol']:15} {trade['direction']:5} {trade['entry_time'].strftime('%m-%d %H:%M')}  "
          f"{trade['pnl_pct']:+7.2f}%  {trade['exit_reason']:12} → DD: {trade['drawdown_pct']:.2f}%")

# 3. Performance by Coin
print("\n3. COIN-BY-COIN ANALYSIS (Dec 8-15):")
print("-" * 80)
print(f"{'Coin':<15} {'Trades':>7} {'Win%':>7} {'SL%':>7} {'Avg SL':>9} {'Avg TP':>9} {'Net P&L':>10}")
print("-" * 80)

for symbol in sorted(df['symbol'].unique()):
    coin_trades = df[df['symbol'] == symbol]

    winners = coin_trades[coin_trades['pnl_pct'] > 0]
    losers = coin_trades[coin_trades['pnl_pct'] <= 0]
    sl_trades = coin_trades[coin_trades['exit_reason'] == 'SL']

    win_rate = (len(winners) / len(coin_trades)) * 100
    sl_rate = (len(sl_trades) / len(coin_trades)) * 100

    avg_sl = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    avg_tp = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    net_pnl = coin_trades['pnl_usd'].sum()

    print(f"{symbol:<15} {len(coin_trades):>7} {win_rate:>6.1f}% {sl_rate:>6.1f}% "
          f"{avg_sl:>+8.2f}% {avg_tp:>+8.2f}% {net_pnl:>+9.2f}$")

# 4. The Drawdown Journey
print("\n4. THE DRAWDOWN SEQUENCE (Capital Peak → Trough):")
print("-" * 80)

# Find peak and worst DD
peak_capital = df['peak'].max()
worst_dd_idx = df['drawdown_pct'].idxmin()
worst_dd_capital = df.loc[worst_dd_idx, 'capital_after']
worst_dd_pct = df.loc[worst_dd_idx, 'drawdown_pct']

print(f"  Peak Capital: ${peak_capital:.2f} (after Dec 9 winning streak)")
print(f"  Worst Point:  ${worst_dd_capital:.2f} (Dec 13, trade #{worst_dd_idx})")
print(f"  Max Drawdown: {worst_dd_pct:.2f}%")
print(f"  Amount Lost:  ${peak_capital - worst_dd_capital:.2f}")

print("\n  Trades that created the drawdown:")
dd_trades = df[(df['capital_after'] <= peak_capital) &
               (df['capital_after'] <= worst_dd_capital * 1.01)].sort_values('entry_time')

for idx, trade in dd_trades.head(15).iterrows():
    loss = trade['capital_before'] - trade['capital_after']
    print(f"    {trade['entry_time'].strftime('%m-%d %H:%M')} {trade['symbol']:15} {trade['direction']:5} "
          f"{trade['pnl_pct']:+7.2f}% ({trade['exit_reason']:3})  Cap: ${trade['capital_after']:6.2f}  DD: {trade['drawdown_pct']:.2f}%")

# 5. What was different?
print("\n5. KEY DIFFERENCES FROM SEP-DEC 7:")
print("-" * 80)

# Compare metrics
orig_win_rate = (df_original['pnl_pct'] > 0).sum() / len(df_original) * 100
dec_win_rate = (df['pnl_pct'] > 0).sum() / len(df) * 100

orig_avg_winner = df_original[df_original['pnl_pct'] > 0]['pnl_pct'].mean()
dec_avg_winner = df[df['pnl_pct'] > 0]['pnl_pct'].mean()

orig_avg_loser = df_original[df_original['pnl_pct'] <= 0]['pnl_pct'].mean()
dec_avg_loser = df[df['pnl_pct'] <= 0]['pnl_pct'].mean()

print(f"  Win Rate:")
print(f"    Sep-Dec 7: {orig_win_rate:.1f}%")
print(f"    Dec 8-15:  {dec_win_rate:.1f}%")
print(f"    **CHANGE: {dec_win_rate - orig_win_rate:+.1f}pp**")

print(f"\n  Average Winner:")
print(f"    Sep-Dec 7: +{orig_avg_winner:.2f}%")
print(f"    Dec 8-15:  +{dec_avg_winner:.2f}%")
print(f"    **CHANGE: {dec_avg_winner - orig_avg_winner:+.2f}%**")

print(f"\n  Average Loser:")
print(f"    Sep-Dec 7: {orig_avg_loser:.2f}%")
print(f"    Dec 8-15:  {dec_avg_loser:.2f}%")
print(f"    **CHANGE: {dec_avg_loser - orig_avg_loser:+.2f}%**")

# 6. Coin-specific failures
print("\n6. COINS THAT FAILED IN DEC 8-15 (But worked in Sep-Dec 7):")
print("-" * 80)

# Get Sep-Dec 7 performance by coin
orig_by_coin = df_original.groupby('coin').agg({
    'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
}).round(2)
orig_by_coin.columns = ['trades', 'avg_pnl', 'win_rate']

print(f"{'Coin':<15} {'Sep-Dec7 Win%':>15} {'Dec8-15 Win%':>15} {'Degradation':>15}")
print("-" * 80)

for symbol in df['symbol'].unique():
    # Map symbol format
    coin_name = symbol.replace('-USDT', '').replace('1000PEPE', 'PEPE')

    if coin_name in orig_by_coin.index:
        orig_wr = orig_by_coin.loc[coin_name, 'win_rate']
    else:
        orig_wr = 0

    dec_trades = df[df['symbol'] == symbol]
    dec_wr = (dec_trades['pnl_pct'] > 0).sum() / len(dec_trades) * 100

    degradation = dec_wr - orig_wr

    if len(dec_trades) >= 4:  # Only show coins with significant sample
        status = "❌ WORSE" if degradation < -20 else "⚠️ MIXED" if degradation < 0 else "✅ BETTER"
        print(f"{symbol:<15} {orig_wr:>14.1f}% {dec_wr:>14.1f}% {degradation:>+13.1f}pp {status}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)

# Calculate key failure factors
sl_increase = dec_sl_rate - original_sl_rate
win_rate_drop = dec_win_rate - orig_win_rate
loser_size_increase = dec_avg_loser - orig_avg_loser

print(f"\n🔴 PRIMARY FAILURE FACTORS:")
print(f"  1. Stop Loss Rate INCREASED by {sl_increase:+.1f}pp ({original_sl_rate:.1f}% → {dec_sl_rate:.1f}%)")
print(f"  2. Win Rate DROPPED by {win_rate_drop:+.1f}pp ({orig_win_rate:.1f}% → {dec_win_rate:.1f}%)")
print(f"  3. Average Loss SIZE increased by {abs(loser_size_increase):.2f}% ({orig_avg_loser:.2f}% → {dec_avg_loser:.2f}%)")

print(f"\n🎯 WORST PERFORMERS:")
worst_coin = df.groupby('symbol')['pnl_usd'].sum().sort_values().head(3)
for symbol, pnl in worst_coin.items():
    coin_trades = df[df['symbol'] == symbol]
    sl_rate = (coin_trades['exit_reason'] == 'SL').sum() / len(coin_trades) * 100
    print(f"  - {symbol}: {pnl:+.2f}$ ({len(coin_trades)} trades, {sl_rate:.0f}% SL rate)")

print(f"\n⚠️ IMPLICATIONS FOR LEVERAGE:")
print(f"  - With 5x leverage: -3.23% DD → -16.15% account loss")
print(f"  - With 10x leverage: -3.23% DD → -32.30% account loss (liquidation risk)")
print(f"  - Current strategies are NOT safe for >3x leverage")
