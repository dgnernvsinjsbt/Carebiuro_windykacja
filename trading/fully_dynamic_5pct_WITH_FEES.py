#!/usr/bin/env python3
"""
FULLY DYNAMIC 5% risk with 0.07% FEES per round trip
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("FULLY DYNAMIC 5% RISK - WITH 0.07% FEES PER TRADE")
print("=" * 100)

# Load data
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Calculate SL distances
sl_trades = df_sep_dec[df_sep_dec['exit_reason'] == 'SL']
coin_avg_sl = {}

for coin in df_sep_dec['coin'].unique():
    coin_sl = sl_trades[sl_trades['coin'] == coin]
    if len(coin_sl) > 0:
        coin_avg_sl[coin] = abs(coin_sl['pnl_pct'].mean())
    else:
        coin_avg_sl[coin] = 2.64

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

# Sep-Dec 7
for _, trade in df_sep_dec.iterrows():
    if trade['exit_reason'] == 'SL':
        sl_distance = abs(trade['pnl_pct'])
    else:
        sl_distance = coin_avg_sl.get(trade['coin'], 2.64)

    all_trades.append({
        'symbol': trade['coin'],
        'date': trade['date'],
        'pnl_pct_gross': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance,
    })

# Dec 8-15
for _, trade in df_dec_8_15.iterrows():
    coin_name = symbol_map.get(trade['symbol'], trade['symbol'])
    sl_distance = abs((trade['stop_loss'] - trade['entry_price']) / trade['entry_price'] * 100)

    all_trades.append({
        'symbol': coin_name,
        'date': trade['entry_time'],
        'pnl_pct_gross': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance,
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Simulate WITHOUT fees first (for comparison)
print("\n" + "="*100)
print("SIMULATION 1: WITHOUT FEES (baseline)")
print("="*100)

RISK_PCT = 5.0
LEVERAGE = 10.0
FEE_PCT = 0.0  # No fees first

capital_no_fees = 100.0
peak_no_fees = 100.0
max_dd_no_fees = 0.0

for idx, trade in trades_df.iterrows():
    sl_distance_pct = trade['sl_distance']
    position_size_pct = (RISK_PCT / (sl_distance_pct * LEVERAGE)) * 100
    position_size = capital_no_fees * (position_size_pct / 100)

    # Gross P&L
    leveraged_pnl_pct = trade['pnl_pct_gross'] * LEVERAGE
    pnl_usd = position_size * (leveraged_pnl_pct / 100)

    capital_no_fees += pnl_usd

    if capital_no_fees > peak_no_fees:
        peak_no_fees = capital_no_fees

    dd_pct = ((capital_no_fees - peak_no_fees) / peak_no_fees) * 100
    if dd_pct < max_dd_no_fees:
        max_dd_no_fees = dd_pct

profit_no_fees = capital_no_fees - 100.0

print(f"\nWithout Fees:")
print(f"  Final: ${capital_no_fees:,.2f}")
print(f"  Profit: ${profit_no_fees:,.2f} (+{(profit_no_fees/100)*100:.2f}%)")
print(f"  Peak: ${peak_no_fees:,.2f}")
print(f"  Max DD: {max_dd_no_fees:.2f}%")
print(f"  Return/DD: {abs((profit_no_fees/100)*100 / max_dd_no_fees):.2f}x")

# Simulate WITH fees
print("\n" + "="*100)
print("SIMULATION 2: WITH 0.07% FEES PER TRADE")
print("="*100)

FEE_PCT = 0.07

capital = 100.0
initial_capital = 100.0
peak_capital = 100.0
max_dd_pct = 0.0

total_fees_paid = 0.0
trade_log = []
coin_profits = {}

for idx, trade in trades_df.iterrows():
    sl_distance_pct = trade['sl_distance']
    position_size_pct = (RISK_PCT / (sl_distance_pct * LEVERAGE)) * 100
    position_size = capital * (position_size_pct / 100)

    # Gross P&L
    pnl_pct_gross = trade['pnl_pct_gross']

    # Deduct fees (0.07% of position value, applied to the leveraged position)
    # Fees are charged on the full leveraged position value
    pnl_pct_net = pnl_pct_gross - FEE_PCT

    leveraged_pnl_pct_net = pnl_pct_net * LEVERAGE
    pnl_usd = position_size * (leveraged_pnl_pct_net / 100)

    # Calculate fees paid
    fees_this_trade = position_size * (FEE_PCT * LEVERAGE / 100)
    total_fees_paid += fees_this_trade

    # Update capital
    capital += pnl_usd

    if capital > peak_capital:
        peak_capital = capital

    dd_pct = ((capital - peak_capital) / peak_capital) * 100
    if dd_pct < max_dd_pct:
        max_dd_pct = dd_pct

    # Track by coin
    coin = trade['symbol']
    if coin not in coin_profits:
        coin_profits[coin] = {'total_pnl': 0, 'trades': 0, 'winners': 0, 'fees_paid': 0}

    coin_profits[coin]['total_pnl'] += pnl_usd
    coin_profits[coin]['fees_paid'] += fees_this_trade
    coin_profits[coin]['trades'] += 1
    if pnl_usd > 0:
        coin_profits[coin]['winners'] += 1

    trade_log.append({
        'trade_num': idx + 1,
        'date': trade['date'],
        'symbol': coin,
        'position_size_pct': position_size_pct,
        'pnl_pct_gross': pnl_pct_gross,
        'pnl_pct_net': pnl_pct_net,
        'leveraged_pnl_net': leveraged_pnl_pct_net,
        'pnl_usd': pnl_usd,
        'fees_paid': fees_this_trade,
        'capital_after': capital,
        'exit_reason': trade['exit_reason'],
        'sl_distance': sl_distance_pct,
    })

trade_log_df = pd.DataFrame(trade_log)
total_profit = capital - initial_capital

print(f"\nWith 0.07% Fees:")
print(f"  Final: ${capital:,.2f}")
print(f"  Profit: ${total_profit:,.2f} (+{(total_profit/initial_capital)*100:.2f}%)")
print(f"  Peak: ${peak_capital:,.2f}")
print(f"  Max DD: {max_dd_pct:.2f}%")
print(f"  Return/DD: {abs((total_profit/initial_capital)*100 / max_dd_pct):.2f}x")
print(f"  Total Fees Paid: ${total_fees_paid:,.2f}")

# Impact comparison
print("\n" + "="*100)
print("FEE IMPACT ANALYSIS")
print("="*100)

profit_lost = profit_no_fees - total_profit
pct_lost = (profit_lost / profit_no_fees) * 100

print(f"\n💸 COST OF FEES:")
print(f"   Gross Profit: ${profit_no_fees:,.2f}")
print(f"   Fees Paid: ${total_fees_paid:,.2f}")
print(f"   Net Profit: ${total_profit:,.2f}")
print(f"   Profit Lost to Fees: ${profit_lost:,.2f} ({pct_lost:.2f}% of gross profit)")

print(f"\n📊 RETURN COMPARISON:")
print(f"   Without Fees: +{(profit_no_fees/100)*100:.2f}%")
print(f"   With Fees: +{(total_profit/100)*100:.2f}%")
print(f"   Difference: -{((profit_no_fees - total_profit)/100)*100:.2f}%")

print(f"\n📉 DRAWDOWN COMPARISON:")
print(f"   Without Fees: {max_dd_no_fees:.2f}%")
print(f"   With Fees: {max_dd_pct:.2f}%")
print(f"   Difference: {max_dd_pct - max_dd_no_fees:.2f}pp")

print(f"\n🎯 RETURN/DD RATIO:")
print(f"   Without Fees: {abs((profit_no_fees/100)*100 / max_dd_no_fees):.2f}x")
print(f"   With Fees: {abs((total_profit/100)*100 / max_dd_pct):.2f}x")

# Profit by coin
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
        'fees_paid': stats['fees_paid'],
    })

contribution_df = pd.DataFrame(contribution_df).sort_values('profit_usd', ascending=False)

print(f"\n{'='*100}")
print("PROFIT CONTRIBUTION BY COIN (After Fees)")
print(f"{'='*100}")
print(f"{'Rank':<6} {'Coin':<15} {'Profit':>15} {'% of Total':>12} {'Trades':>8} {'Win%':>8} {'Fees Paid':>12}")
print("-" * 90)

for idx, row in contribution_df.iterrows():
    rank = contribution_df.index.get_loc(idx) + 1
    print(f"{rank:<6} {row['symbol']:<15} ${row['profit_usd']:>14,.2f} {row['contribution_pct']:>11.2f}% "
          f"{row['trades']:>8} {row['win_rate']:>7.1f}% ${row['fees_paid']:>11,.2f}")

print("-" * 90)
print(f"{'TOTAL':<6} {'ALL COINS':<15} ${total_profit:>14,.2f} {'100.00%':>12} "
      f"{len(trade_log_df):>8} {'':<8} ${total_fees_paid:>11,.2f}")

# Fee efficiency
print(f"\n💡 FEE EFFICIENCY BY COIN:")
for idx, row in contribution_df.iterrows():
    if row['fees_paid'] > 0:
        roi_on_fees = (row['profit_usd'] / row['fees_paid']) if row['fees_paid'] > 0 else 0
        print(f"   {row['symbol']:15} Profit: ${row['profit_usd']:>10,.2f} | Fees: ${row['fees_paid']:>8,.2f} | "
              f"ROI: {roi_on_fees:>6.1f}x")

# Save
trade_log_df.to_csv('trade_log_5pct_WITH_FEES.csv', index=False)
print(f"\n✅ Trade log saved to: trade_log_5pct_WITH_FEES.csv")
