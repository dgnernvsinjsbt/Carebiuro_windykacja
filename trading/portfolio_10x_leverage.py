#!/usr/bin/env python3
"""
Shared portfolio with 10x leverage (chronological, compounding)
- Start with $100
- Each trade uses 10% of current capital
- P&L is multiplied by 10x (leverage)
- Trades executed chronologically across all coins
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("SHARED PORTFOLIO WITH 10X LEVERAGE")
print("=" * 100)
print("Setup: $100 starting capital, 10% position sizing, 10x leverage on each trade\n")

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
    })

for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

# Convert to DataFrame and sort chronologically
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

print(f"Total trades to process: {len(trades_df)}")
print(f"Date range: {trades_df['date'].min()} to {trades_df['date'].max()}\n")

# Simulate portfolio with 10x leverage
capital = 100.0
initial_capital = 100.0
peak_capital = 100.0
max_dd_pct = 0.0

liquidated = False
liquidation_trade_num = None

equity_curve = [capital]
trade_log = []

for idx, trade in trades_df.iterrows():
    if liquidated:
        break

    # Position size: 10% of current capital
    position_size = capital * 0.10

    # Apply 10x leverage to P&L
    leveraged_pnl_pct = trade['pnl_pct'] * 10

    # Calculate P&L in USD
    pnl_usd = position_size * (leveraged_pnl_pct / 100)

    # Update capital
    new_capital = capital + pnl_usd

    # Check for liquidation
    if new_capital <= 0:
        liquidated = True
        liquidation_trade_num = idx + 1
        capital = 0

        trade_log.append({
            'trade_num': idx + 1,
            'date': trade['date'],
            'symbol': trade['symbol'],
            'capital_before': capital,
            'position_size': position_size,
            'pnl_pct': trade['pnl_pct'],
            'leveraged_pnl_pct': leveraged_pnl_pct,
            'pnl_usd': pnl_usd,
            'capital_after': 0,
            'exit_reason': trade['exit_reason'],
            'liquidated': True
        })

        break

    capital = new_capital
    equity_curve.append(capital)

    # Track peak and drawdown
    if capital > peak_capital:
        peak_capital = capital

    dd_pct = ((capital - peak_capital) / peak_capital) * 100
    if dd_pct < max_dd_pct:
        max_dd_pct = dd_pct

    # Log trade
    trade_log.append({
        'trade_num': idx + 1,
        'date': trade['date'],
        'symbol': trade['symbol'],
        'capital_before': capital - pnl_usd,
        'position_size': position_size,
        'pnl_pct': trade['pnl_pct'],
        'leveraged_pnl_pct': leveraged_pnl_pct,
        'pnl_usd': pnl_usd,
        'capital_after': capital,
        'exit_reason': trade['exit_reason'],
        'liquidated': False
    })

# Convert to DataFrame
trade_log_df = pd.DataFrame(trade_log)

# Display results
print("=" * 100)
print("RESULTS:")
print("=" * 100)

if liquidated:
    print(f"\n💀 PORTFOLIO LIQUIDATED on trade #{liquidation_trade_num}/{len(trades_df)}")

    # Show the death trade
    death_trade = trade_log_df[trade_log_df['liquidated'] == True].iloc[0]
    print(f"\n🪦 DEATH TRADE:")
    print(f"   Trade #: {death_trade['trade_num']}")
    print(f"   Date: {death_trade['date'].strftime('%Y-%m-%d %H:%M')}")
    print(f"   Coin: {death_trade['symbol']}")
    print(f"   Capital Before: ${death_trade['capital_before']:.2f}")
    print(f"   Position Size: ${death_trade['position_size']:.2f} (10% of capital)")
    print(f"   Trade P&L: {death_trade['pnl_pct']:.2f}%")
    print(f"   With 10x Leverage: {death_trade['leveraged_pnl_pct']:.2f}%")
    print(f"   USD Loss: ${death_trade['pnl_usd']:.2f}")
    print(f"   Capital After: $0.00 (LIQUIDATED)")

    # Show last 10 trades before death
    print(f"\n📊 LAST 10 TRADES BEFORE LIQUIDATION:")
    print(f"{'#':<5} {'Date':<12} {'Coin':<15} {'P&L%':>8} {'10xP&L%':>9} {'USD P&L':>10} {'Capital':>10}")
    print("-" * 90)

    for _, t in trade_log_df.tail(11).iterrows():
        status = "💀" if t['liquidated'] else ""
        print(f"{t['trade_num']:<5} {t['date'].strftime('%Y-%m-%d'):<12} {t['symbol']:<15} "
              f"{t['pnl_pct']:>+7.2f}% {t['leveraged_pnl_pct']:>+8.2f}% ${t['pnl_usd']:>+9.2f} "
              f"${t['capital_after']:>9.2f} {status}")

    # Calculate how far we got
    trades_completed = liquidation_trade_num - 1
    pct_complete = (trades_completed / len(trades_df)) * 100

    print(f"\n⚠️ STATISTICS:")
    print(f"   Trades completed: {trades_completed}/{len(trades_df)} ({pct_complete:.1f}%)")
    print(f"   Peak capital: ${peak_capital:.2f}")
    print(f"   Max drawdown before death: {max_dd_pct:.2f}%")

else:
    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    print(f"\n✅ PORTFOLIO SURVIVED!")
    print(f"\n💰 FINAL RESULTS:")
    print(f"   Starting Capital: ${initial_capital:.2f}")
    print(f"   Final Capital:    ${final_capital:.2f}")
    print(f"   Total Profit:     ${final_capital - initial_capital:+.2f}")
    print(f"   Total Return:     {total_return:+.2f}%")
    print(f"   Peak Capital:     ${peak_capital:.2f}")
    print(f"   Max Drawdown:     {max_dd_pct:.2f}%")
    print(f"   Return/DD Ratio:  {abs(total_return / max_dd_pct):.2f}x")

    # Win/loss stats
    winners = trade_log_df[trade_log_df['pnl_usd'] > 0]
    losers = trade_log_df[trade_log_df['pnl_usd'] <= 0]
    win_rate = (len(winners) / len(trade_log_df)) * 100

    print(f"\n📊 TRADE STATISTICS:")
    print(f"   Total Trades:     {len(trade_log_df)}")
    print(f"   Winners:          {len(winners)} ({win_rate:.1f}%)")
    print(f"   Losers:           {len(losers)} ({100-win_rate:.1f}%)")
    print(f"   Avg Winner:       ${winners['pnl_usd'].mean():.2f} ({winners['leveraged_pnl_pct'].mean():.2f}%)")
    print(f"   Avg Loser:        ${losers['pnl_usd'].mean():.2f} ({losers['leveraged_pnl_pct'].mean():.2f}%)")
    print(f"   Best Trade:       ${trade_log_df['pnl_usd'].max():.2f}")
    print(f"   Worst Trade:      ${trade_log_df['pnl_usd'].min():.2f}")

    # Show top 10 trades
    print(f"\n🏆 TOP 10 MOST PROFITABLE TRADES:")
    print(f"{'#':<5} {'Date':<12} {'Coin':<15} {'P&L%':>8} {'10xP&L%':>9} {'USD P&L':>10} {'Capital':>12}")
    print("-" * 95)

    top_trades = trade_log_df.nlargest(10, 'pnl_usd')
    for _, t in top_trades.iterrows():
        print(f"{t['trade_num']:<5} {t['date'].strftime('%Y-%m-%d'):<12} {t['symbol']:<15} "
              f"{t['pnl_pct']:>+7.2f}% {t['leveraged_pnl_pct']:>+8.2f}% ${t['pnl_usd']:>+9.2f} "
              f"${t['capital_after']:>11.2f}")

    # Show worst 10 trades
    print(f"\n💀 WORST 10 LOSING TRADES:")
    print(f"{'#':<5} {'Date':<12} {'Coin':<15} {'P&L%':>8} {'10xP&L%':>9} {'USD P&L':>10} {'Capital':>12}")
    print("-" * 95)

    worst_trades = trade_log_df.nsmallest(10, 'pnl_usd')
    for _, t in worst_trades.iterrows():
        print(f"{t['trade_num']:<5} {t['date'].strftime('%Y-%m-%d'):<12} {t['symbol']:<15} "
              f"{t['pnl_pct']:>+7.2f}% {t['leveraged_pnl_pct']:>+8.2f}% ${t['pnl_usd']:>+9.2f} "
              f"${t['capital_after']:>11.2f}")

print("\n" + "=" * 100)
print("COMPARISON:")
print("=" * 100)

print(f"\n{'Method':<30} {'Start':>10} {'Final':>12} {'Profit':>12} {'Return%':>10} {'Max DD%':>10}")
print("-" * 85)
print(f"{'1x Leverage (10% sizing)':<30} ${'100.00':>9} ${'133.65':>11} ${'+33.65':>11} {'+33.65%':>9} {'-3.23%':>9}")

if liquidated:
    print(f"{'10x Leverage (10% sizing)':<30} ${'100.00':>9} ${'0.00':>11} ${'-100.00':>11} {'-100.00%':>9} {'N/A':>9}")
    print(f"\n💀 WITH 10X LEVERAGE, YOUR PORTFOLIO WAS LIQUIDATED")
else:
    print(f"{'10x Leverage (10% sizing)':<30} ${'100.00':>9} ${final_capital:>11.2f} ${final_capital - 100:>+11.2f} {total_return:>+9.2f}% {max_dd_pct:>+9.2f}%")

    if final_capital > 133.65:
        improvement = ((final_capital - 133.65) / 133.65) * 100
        print(f"\n🚀 10X LEVERAGE INCREASED PROFITS BY ${final_capital - 133.65:.2f} ({improvement:+.1f}%)")
    else:
        decline = ((133.65 - final_capital) / 133.65) * 100
        print(f"\n⚠️ 10X LEVERAGE REDUCED PROFITS BY ${133.65 - final_capital:.2f} ({decline:.1f}%)")

# Save results
trade_log_df.to_csv('portfolio_10x_leverage_log.csv', index=False)
print(f"\n✅ Trade log saved to: portfolio_10x_leverage_log.csv")
