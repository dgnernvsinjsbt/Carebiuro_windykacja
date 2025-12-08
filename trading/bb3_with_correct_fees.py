#!/usr/bin/env python3
"""
BB3 strategy with correct BingX fees: 0.02% entry + 0.05% exit = 0.07% round-trip
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

# CORRECT FEES
ENTRY_FEE = 0.0002   # 0.02%
EXIT_FEE = 0.0005    # 0.05%
TOTAL_FEE = 0.0007   # 0.07% round-trip

STARTING_BALANCE = 10000

def get_min_price(entry_time, exit_time, eth_data):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['low'].min()
    except:
        return None

# Get min prices
trades_df['min_price'] = trades_df.apply(
    lambda r: get_min_price(r['entry_time'], r['exit_time'], eth_data), axis=1
)
trades_df['min_price'] = trades_df.apply(
    lambda r: r['min_price'] if pd.notna(r['min_price']) else (r['stop'] if r['result']=='STOP' else r['entry']),
    axis=1
)
trades_df['dip_pct'] = (trades_df['entry'] - trades_df['min_price']) / trades_df['entry'] * 100

# Market orders simulation
print("=" * 70)
print("BB3 STRATEGY - CORRECT FEES (0.02% entry + 0.05% exit = 0.07% RT)")
print("=" * 70)

# MARKET ORDERS
balance = STARTING_BALANCE
results = []

for _, row in trades_df.iterrows():
    entry = row['entry']
    exit_price = row['target'] if row['result'] == 'TP' else row['stop']

    gross_pnl_pct = (exit_price - entry) / entry * 100
    fee_pct = TOTAL_FEE * 100  # 0.07%
    net_pnl_pct = gross_pnl_pct - fee_pct

    pnl_dollar = balance * (net_pnl_pct / 100)
    balance += pnl_dollar

    results.append({
        'entry_time': row['entry_time'],
        'signal_price': entry,
        'exit_price': exit_price,
        'result': row['result'],
        'gross_pnl_pct': gross_pnl_pct,
        'entry_fee_pct': ENTRY_FEE * 100,
        'exit_fee_pct': EXIT_FEE * 100,
        'total_fee_pct': fee_pct,
        'profit_after_fees_pct': net_pnl_pct,
        'profit_after_fees_dollar': pnl_dollar,
        'running_balance': balance
    })

market_df = pd.DataFrame(results)
market_final = balance

print(f"\n--- MARKET ORDERS ---")
print(f"Trades: {len(trades_df)}")
print(f"Gross return: {market_df['gross_pnl_pct'].sum():.2f}%")
print(f"Total fees: -{market_df['total_fee_pct'].sum():.2f}%")
print(f"NET RETURN: {market_df['profit_after_fees_pct'].sum():.2f}%")
print(f"Final balance: ${market_final:,.2f}")
print(f"Profit: ${market_final - STARTING_BALANCE:,.2f}")

# Save market orders CSV
market_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_market_orders_0.07pct_fees.csv', index=False)

# LIMIT ORDERS -0.035%
LIMIT_OFFSET = 0.00035
balance = STARTING_BALANCE
limit_results = []

for _, row in trades_df.iterrows():
    signal_price = row['entry']
    limit_price = signal_price * (1 - LIMIT_OFFSET)
    min_price = row['min_price']

    filled = min_price <= limit_price

    if filled:
        entry = limit_price
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']

        gross_pnl_pct = (exit_price - entry) / entry * 100
        fee_pct = TOTAL_FEE * 100
        net_pnl_pct = gross_pnl_pct - fee_pct

        pnl_dollar = balance * (net_pnl_pct / 100)
        balance += pnl_dollar
    else:
        gross_pnl_pct = 0
        fee_pct = 0
        net_pnl_pct = 0
        pnl_dollar = 0
        entry = None
        exit_price = None

    limit_results.append({
        'entry_time': row['entry_time'],
        'signal_price': signal_price,
        'limit_price': limit_price if filled else None,
        'min_price_in_trade': min_price,
        'dip_below_signal_pct': row['dip_pct'],
        'filled': 'YES' if filled else 'NO',
        'actual_entry': entry,
        'exit_price': exit_price,
        'result': row['result'] if filled else 'SKIPPED',
        'gross_pnl_pct': gross_pnl_pct,
        'entry_fee_pct': ENTRY_FEE * 100 if filled else 0,
        'exit_fee_pct': EXIT_FEE * 100 if filled else 0,
        'total_fee_pct': fee_pct,
        'profit_after_fees_pct': net_pnl_pct,
        'profit_after_fees_dollar': pnl_dollar,
        'running_balance': balance
    })

limit_df = pd.DataFrame(limit_results)
limit_final = balance
filled_count = (limit_df['filled'] == 'YES').sum()

print(f"\n--- LIMIT ORDERS -0.035% ---")
print(f"Trades filled: {filled_count}/{len(trades_df)} ({filled_count/len(trades_df)*100:.1f}%)")
filled_df = limit_df[limit_df['filled'] == 'YES']
print(f"Winners: {len(filled_df[filled_df['gross_pnl_pct'] > 0])}")
print(f"Losers: {len(filled_df[filled_df['gross_pnl_pct'] <= 0])}")
print(f"Win rate: {len(filled_df[filled_df['gross_pnl_pct'] > 0])/filled_count*100:.1f}%")
print(f"Gross return: {limit_df['gross_pnl_pct'].sum():.2f}%")
print(f"Total fees: -{limit_df['total_fee_pct'].sum():.2f}%")
print(f"NET RETURN: {limit_df['profit_after_fees_pct'].sum():.2f}%")
print(f"Final balance: ${limit_final:,.2f}")
print(f"Profit: ${limit_final - STARTING_BALANCE:,.2f}")

# Save limit orders CSV
limit_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_limit_orders_0.07pct_fees.csv', index=False)

print(f"\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n{'Method':<25} {'Trades':<8} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Profit $':<10}")
print("-" * 70)
print(f"{'Market orders':<25} {len(trades_df):<8} {market_df['gross_pnl_pct'].sum():>+.2f}%   -{market_df['total_fee_pct'].sum():.2f}%   {market_df['profit_after_fees_pct'].sum():>+.2f}%   ${market_final-STARTING_BALANCE:>+,.2f}")
print(f"{'Limit -0.035%':<25} {filled_count:<8} {limit_df['gross_pnl_pct'].sum():>+.2f}%   -{limit_df['total_fee_pct'].sum():.2f}%   {limit_df['profit_after_fees_pct'].sum():>+.2f}%   ${limit_final-STARTING_BALANCE:>+,.2f}")

print(f"\nCSV files saved:")
print(f"  - bb3_market_orders_0.07pct_fees.csv")
print(f"  - bb3_limit_orders_0.07pct_fees.csv")
