#!/usr/bin/env python3
"""
Complete comparison of all order types for BB3:
1. Market orders (0.10% RT) - baseline
2. Limit BELOW signal (0.07% RT) - maker entry
3. Limit ABOVE signal (0.10% RT) - taker (confirmation filter)
"""
import pandas as pd
import numpy as np

# Load data
eth_data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
eth_data['timestamp'] = pd.to_datetime(eth_data['timestamp'])
eth_data = eth_data.set_index('timestamp')

trades_df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_std_all_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

# FEES
MAKER_FEE = 0.0002   # 0.02%
TAKER_FEE = 0.0005   # 0.05%
STARTING_BALANCE = 10000

def get_min_price(entry_time, exit_time, eth_data):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['low'].min()
    except:
        return None

def get_max_price(entry_time, exit_time, eth_data):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['high'].max()
    except:
        return None

# Get price extremes
trades_df['min_price'] = trades_df.apply(lambda r: get_min_price(r['entry_time'], r['exit_time'], eth_data), axis=1)
trades_df['max_price'] = trades_df.apply(lambda r: get_max_price(r['entry_time'], r['exit_time'], eth_data), axis=1)
trades_df['min_price'] = trades_df.apply(lambda r: r['min_price'] if pd.notna(r['min_price']) else r['stop'], axis=1)
trades_df['max_price'] = trades_df.apply(lambda r: r['max_price'] if pd.notna(r['max_price']) else r['target'], axis=1)

print("=" * 85)
print("BB3 STRATEGY - COMPLETE COMPARISON")
print("=" * 85)

# ============================================
# SCENARIO 1: MARKET ORDERS (0.10% RT)
# ============================================
def simulate_market(trades_df):
    balance = STARTING_BALANCE
    results = []
    rt_fee = (TAKER_FEE + TAKER_FEE) * 100  # 0.10%

    for _, row in trades_df.iterrows():
        entry = row['entry']
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']
        gross = (exit_price - entry) / entry * 100
        net = gross - rt_fee
        balance += balance * (net / 100)
        results.append({'gross': gross, 'fee': rt_fee, 'net': net, 'balance': balance, 'filled': True, 'win': gross > 0})
    return pd.DataFrame(results), balance

# ============================================
# SCENARIO 2: LIMIT BELOW (0.07% RT)
# ============================================
def simulate_limit_below(trades_df, offset_pct):
    balance = STARTING_BALANCE
    results = []
    offset = offset_pct / 100
    rt_fee = (MAKER_FEE + TAKER_FEE) * 100  # 0.07%

    for _, row in trades_df.iterrows():
        signal = row['entry']
        limit_price = signal * (1 - offset)
        min_price = row['min_price']
        filled = min_price <= limit_price

        if filled:
            entry = limit_price
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']
            gross = (exit_price - entry) / entry * 100
            net = gross - rt_fee
            balance += balance * (net / 100)
            results.append({'gross': gross, 'fee': rt_fee, 'net': net, 'balance': balance, 'filled': True, 'win': gross > 0})
        else:
            results.append({'gross': 0, 'fee': 0, 'net': 0, 'balance': balance, 'filled': False, 'win': False})

    return pd.DataFrame(results), balance

# ============================================
# SCENARIO 3: LIMIT ABOVE (0.10% RT - taker!)
# ============================================
def simulate_limit_above(trades_df, offset_pct):
    balance = STARTING_BALANCE
    results = []
    offset = offset_pct / 100
    rt_fee = (TAKER_FEE + TAKER_FEE) * 100  # 0.10% - still taker fees!

    for _, row in trades_df.iterrows():
        signal = row['entry']
        limit_price = signal * (1 + offset)
        max_price = row['max_price']
        filled = max_price >= limit_price

        if filled:
            entry = limit_price
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']
            gross = (exit_price - entry) / entry * 100
            net = gross - rt_fee
            balance += balance * (net / 100)
            results.append({'gross': gross, 'fee': rt_fee, 'net': net, 'balance': balance, 'filled': True, 'win': gross > 0})
        else:
            results.append({'gross': 0, 'fee': 0, 'net': 0, 'balance': balance, 'filled': False, 'win': False})

    return pd.DataFrame(results), balance

# Run all scenarios
market_df, market_bal = simulate_market(trades_df)
limit_below_df, limit_below_bal = simulate_limit_below(trades_df, 0.035)

print("\n" + "-" * 85)
print("BASELINE COMPARISON")
print("-" * 85)

print(f"\n{'Method':<35} {'Trades':<8} {'W/L':<10} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Profit':<10}")
print("-" * 85)

# Market
mf = market_df[market_df['filled']]
print(f"{'1. Market (0.05%+0.05%=0.10%)':<35} {len(mf):<8} {mf['win'].sum()}/{len(mf)-mf['win'].sum():<6} {mf['gross'].sum():>+.2f}%   -{mf['fee'].sum():.2f}%   {mf['net'].sum():>+.2f}%   ${market_bal-STARTING_BALANCE:>+,.0f}")

# Limit below
lbf = limit_below_df[limit_below_df['filled']]
print(f"{'2. Limit -0.035% (0.02%+0.05%)':<35} {len(lbf):<8} {lbf['win'].sum()}/{len(lbf)-lbf['win'].sum():<6} {lbf['gross'].sum():>+.2f}%   -{lbf['fee'].sum():.2f}%   {lbf['net'].sum():>+.2f}%   ${limit_below_bal-STARTING_BALANCE:>+,.0f}")

# Test various "above" offsets
print("\n" + "-" * 85)
print("LIMIT ABOVE SIGNAL (confirmation filter) - STILL TAKER FEES 0.10%!")
print("-" * 85)

print(f"\n{'Offset':<10} {'Trades':<8} {'W/L':<12} {'Win%':<8} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Profit':<10}")
print("-" * 85)

for offset in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70]:
    df, bal = simulate_limit_above(trades_df, offset)
    filled = df[df['filled']]
    if len(filled) == 0:
        continue
    wins = filled['win'].sum()
    losses = len(filled) - wins
    print(f"{offset:.2f}%      {len(filled):<8} {wins}/{losses:<8} {wins/len(filled)*100:.1f}%    {filled['gross'].sum():>+.2f}%   -{filled['fee'].sum():.2f}%   {filled['net'].sum():>+.2f}%   ${bal-STARTING_BALANCE:>+,.0f}")

# Find breakeven point for "above" strategy
print("\n" + "-" * 85)
print("KEY INSIGHT")
print("-" * 85)
print("""
Limit ABOVE signal doesn't work because:

1. You still pay TAKER fees (0.10%) - no fee advantage
2. You enter at HIGHER price - less profit per trade
3. Yes, you filter losers, but you also reduce profit on winners
4. The math: filtering 1 loser saves ~0.3%, but entering 0.3% higher costs 0.3% on ALL trades

For "above" to work, you'd need to filter WAY more losers than winners.
But the data shows losers bounce almost as much as winners before dying.
""")

# Export the best strategy CSV
print("Generating final CSV for limit -0.035% strategy...")

balance = STARTING_BALANCE
final_results = []

for _, row in trades_df.iterrows():
    signal = row['entry']
    limit_price = signal * (1 - 0.00035)
    min_price = row['min_price']
    filled = min_price <= limit_price

    trade = {
        'trade_num': len(final_results) + 1,
        'entry_time': row['entry_time'],
        'exit_time': row['exit_time'],
        'signal_price': signal,
        'limit_price': limit_price,
        'min_price': min_price,
        'stop': row['stop'],
        'target': row['target'],
        'filled': 'YES' if filled else 'NO',
        'result': row['result'] if filled else 'SKIPPED',
    }

    if filled:
        entry = limit_price
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']
        gross = (exit_price - entry) / entry * 100
        fee = (MAKER_FEE + TAKER_FEE) * 100

        trade['actual_entry'] = entry
        trade['exit_price'] = exit_price
        trade['gross_pnl_pct'] = gross
        trade['entry_fee_pct'] = MAKER_FEE * 100
        trade['exit_fee_pct'] = TAKER_FEE * 100
        trade['total_fee_pct'] = fee
        trade['profit_after_fees_pct'] = gross - fee

        pnl_dollar = balance * ((gross - fee) / 100)
        balance += pnl_dollar
        trade['profit_after_fees_dollar'] = pnl_dollar
    else:
        trade['actual_entry'] = None
        trade['exit_price'] = None
        trade['gross_pnl_pct'] = 0
        trade['entry_fee_pct'] = 0
        trade['exit_fee_pct'] = 0
        trade['total_fee_pct'] = 0
        trade['profit_after_fees_pct'] = 0
        trade['profit_after_fees_dollar'] = 0

    trade['running_balance'] = balance
    final_results.append(trade)

final_df = pd.DataFrame(final_results)
final_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_limit_below_FINAL.csv', index=False)

print(f"\nFinal CSV saved: bb3_limit_below_FINAL.csv")
print(f"Final balance: ${balance:,.2f} (+{(balance/STARTING_BALANCE-1)*100:.2f}%)")
