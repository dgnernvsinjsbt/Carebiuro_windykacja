#!/usr/bin/env python3
"""
Simulate each coin with 10x leverage applied to EACH TRADE
Track when accounts get liquidated (capital <= 0)
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("10X LEVERAGE SIMULATION - REAL TRADE-BY-TRADE CALCULATION")
print("=" * 100)
print("Each trade P&L is multiplied by 10x")
print("Liquidation occurs when capital drops to $0 or below\n")

# Load Sep 15 - Dec 7 trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

# Load Dec 8-15 trades
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
        'period': 'Sep-Dec7'
    })

for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'period': 'Dec8-15'
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Map symbol names
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

# Simulate each coin with 10x leverage
results = []

for symbol in sorted(trades_df['symbol'].unique()):
    coin_trades = trades_df[trades_df['symbol'] == symbol].sort_values('date').reset_index(drop=True)

    capital = 10.0
    initial_capital = 10.0
    peak_capital = 10.0
    max_dd_pct = 0.0

    liquidated = False
    liquidation_trade = None
    trades_before_liquidation = 0

    # Track equity curve
    equity_curve = [capital]

    for idx, trade in coin_trades.iterrows():
        if liquidated:
            break

        # Apply 10x leverage to the P&L
        leveraged_pnl_pct = trade['pnl_pct'] * 10

        # Calculate new capital
        pnl_multiplier = 1 + (leveraged_pnl_pct / 100)
        new_capital = capital * pnl_multiplier

        # Check for liquidation
        if new_capital <= 0:
            liquidated = True
            liquidation_trade = idx + 1
            trades_before_liquidation = idx + 1
            capital = 0
            equity_curve.append(0)
            break

        capital = new_capital
        equity_curve.append(capital)
        trades_before_liquidation = idx + 1

        # Track peak and drawdown
        if capital > peak_capital:
            peak_capital = capital

        dd_pct = ((capital - peak_capital) / peak_capital) * 100
        if dd_pct < max_dd_pct:
            max_dd_pct = dd_pct

    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    # Find worst losing streak
    losing_streak = 0
    max_losing_streak = 0
    for _, trade in coin_trades.head(trades_before_liquidation).iterrows():
        if trade['pnl_pct'] < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0

    results.append({
        'symbol': symbol,
        'starting': initial_capital,
        'final': final_capital,
        'profit': final_capital - initial_capital,
        'return_pct': total_return,
        'max_dd_pct': max_dd_pct,
        'trades_completed': trades_before_liquidation,
        'total_trades': len(coin_trades),
        'liquidated': liquidated,
        'liquidation_trade': liquidation_trade,
        'max_losing_streak': max_losing_streak,
        'peak_capital': peak_capital
    })

results_df = pd.DataFrame(results).sort_values('profit', ascending=False)

# Display results
print("\n" + "=" * 100)
print("RESULTS BY COIN:")
print("=" * 100)
print(f"{'Coin':<15} {'Start':>8} {'Final':>8} {'Profit':>10} {'Return%':>10} {'MaxDD%':>10} "
      f"{'Trades':>8} {'Status':>20}")
print("-" * 100)

for _, row in results_df.iterrows():
    if row['liquidated']:
        status = f"💀 LIQUIDATED (trade #{row['liquidation_trade']})"
        status_color = "❌"
    elif row['profit'] > 0:
        status = f"✅ Survived"
        status_color = "✅"
    else:
        status = f"⚠️ Lost money"
        status_color = "⚠️"

    print(f"{row['symbol']:<15} ${row['starting']:>7.2f} ${row['final']:>7.2f} "
          f"${row['profit']:>+9.2f} {row['return_pct']:>+9.2f}% {row['max_dd_pct']:>+9.2f}% "
          f"{row['trades_completed']:>3}/{row['total_trades']:<3} {status:>20}")

# Portfolio totals
survivors = results_df[~results_df['liquidated']]
liquidated = results_df[results_df['liquidated']]

total_starting = results_df['starting'].sum()
total_final = results_df['final'].sum()
total_profit = results_df['profit'].sum()
total_return = ((total_final - total_starting) / total_starting) * 100

print("-" * 100)
print(f"{'PORTFOLIO':<15} ${total_starting:>7.2f} ${total_final:>7.2f} "
      f"${total_profit:>+9.2f} {total_return:>+9.2f}%")

print("\n" + "=" * 100)
print("SUMMARY:")
print("=" * 100)

print(f"\n📊 SURVIVAL RATE:")
print(f"   Survivors:     {len(survivors)}/9 ({len(survivors)/9*100:.1f}%)")
print(f"   Liquidated:    {len(liquidated)}/9 ({len(liquidated)/9*100:.1f}%)")

if len(liquidated) > 0:
    print(f"\n💀 LIQUIDATED ACCOUNTS:")
    for _, row in liquidated.iterrows():
        print(f"   • {row['symbol']:15} - Liquidated on trade #{row['liquidation_trade']}/{row['total_trades']} "
              f"(survived {row['trades_completed']} trades)")

        # Find the trade that caused liquidation
        coin_trades = trades_df[trades_df['symbol'] == row['symbol']].sort_values('date')
        if row['liquidation_trade'] <= len(coin_trades):
            death_trade = coin_trades.iloc[row['liquidation_trade']-1]
            print(f"     → Death trade: {death_trade['pnl_pct']:.2f}% loss × 10x leverage = {death_trade['pnl_pct']*10:.2f}% account loss")
            print(f"     → Date: {death_trade['date'].strftime('%Y-%m-%d')}")

if len(survivors) > 0:
    print(f"\n✅ SURVIVORS:")
    for _, row in survivors.iterrows():
        roi = ((row['final'] - row['starting']) / row['starting']) * 100
        print(f"   • {row['symbol']:15} ${row['starting']:.2f} → ${row['final']:.2f} ({roi:+.1f}%) | "
              f"Max DD: {row['max_dd_pct']:.2f}% | Peak: ${row['peak_capital']:.2f}")

print(f"\n💰 PORTFOLIO PERFORMANCE:")
print(f"   Total Starting Capital: ${total_starting:.2f}")
print(f"   Total Final Capital:    ${total_final:.2f}")
print(f"   Total Profit/Loss:      ${total_profit:+.2f}")
print(f"   Portfolio Return:       {total_return:+.2f}%")

print(f"\n🔍 KEY INSIGHTS:")

if len(liquidated) > 0:
    avg_liquidation_trade = liquidated['liquidation_trade'].mean()
    print(f"   • Liquidated accounts survived an average of {avg_liquidation_trade:.0f} trades")
    print(f"   • Earliest liquidation: Trade #{liquidated['liquidation_trade'].min()}")
    print(f"   • Latest liquidation: Trade #{liquidated['liquidation_trade'].max()}")

if len(survivors) > 0:
    best_survivor = survivors.iloc[0]
    print(f"   • Best performer: {best_survivor['symbol']} (${best_survivor['final']:.2f}, {best_survivor['return_pct']:+.1f}%)")

    worst_survivor = survivors.iloc[-1]
    print(f"   • Worst survivor: {worst_survivor['symbol']} (${worst_survivor['final']:.2f}, {worst_survivor['return_pct']:+.1f}%)")

print(f"\n⚠️ COMPARISON TO 1X LEVERAGE:")
print(f"   1x leverage: $90 → $124.42 (+38.25%)")
print(f"   10x leverage: $90 → ${total_final:.2f} ({total_return:+.2f}%)")
print(f"   Difference: ${total_final - 124.42:+.2f}")

if total_final < 90:
    print(f"\n   💀 WITH 10X LEVERAGE, YOU WOULD LOSE ${90 - total_final:.2f} (your entire portfolio would be down {(total_final - 90)/90*100:.1f}%)")
elif total_final < 124.42:
    print(f"\n   ⚠️ 10x leverage REDUCED profits by ${124.42 - total_final:.2f} due to liquidations")
else:
    print(f"\n   🚀 10x leverage INCREASED profits by ${total_final - 124.42:.2f}")
