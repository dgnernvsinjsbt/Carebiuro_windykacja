#!/usr/bin/env python3
"""
BB3 strategy with CORRECT fee structure:
- Market orders: 0.05% + 0.05% = 0.10% RT (taker/taker)
- Limit below:   0.02% + 0.05% = 0.07% RT (maker/taker)
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

print("=" * 80)
print("BB3 STRATEGY - CORRECT FEE COMPARISON")
print("Market: 0.05%+0.05% = 0.10% RT | Limit below: 0.02%+0.05% = 0.07% RT")
print("=" * 80)

# ============================================
# SCENARIO 1: MARKET ORDERS (0.10% RT)
# ============================================
balance = STARTING_BALANCE
market_results = []

for _, row in trades_df.iterrows():
    entry = row['entry']
    exit_price = row['target'] if row['result'] == 'TP' else row['stop']

    gross_pnl_pct = (exit_price - entry) / entry * 100
    fee_pct = (TAKER_FEE + TAKER_FEE) * 100  # 0.10%
    net_pnl_pct = gross_pnl_pct - fee_pct

    pnl_dollar = balance * (net_pnl_pct / 100)
    balance += pnl_dollar

    market_results.append({
        'entry_time': row['entry_time'],
        'signal_price': entry,
        'exit_price': exit_price,
        'result': row['result'],
        'gross_pnl_pct': gross_pnl_pct,
        'entry_fee_pct': TAKER_FEE * 100,
        'exit_fee_pct': TAKER_FEE * 100,
        'total_fee_pct': fee_pct,
        'profit_after_fees_pct': net_pnl_pct,
        'profit_after_fees_dollar': pnl_dollar,
        'running_balance': balance
    })

market_df = pd.DataFrame(market_results)
market_final = balance

print(f"\n--- MARKET ORDERS (0.05% + 0.05% = 0.10% RT) ---")
print(f"Trades: {len(trades_df)}")
print(f"Gross return: {market_df['gross_pnl_pct'].sum():.2f}%")
print(f"Total fees: -{market_df['total_fee_pct'].sum():.2f}%")
print(f"NET RETURN: {market_df['profit_after_fees_pct'].sum():.2f}%")
print(f"Final: ${market_final:,.2f} (${market_final-STARTING_BALANCE:+,.2f})")

market_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_market_orders_correct.csv', index=False)

# ============================================
# SCENARIO 2: LIMIT BELOW -0.035% (0.07% RT)
# ============================================
LIMIT_OFFSET = 0.00035
balance = STARTING_BALANCE
limit_results = []

for _, row in trades_df.iterrows():
    signal = row['entry']
    limit_price = signal * (1 - LIMIT_OFFSET)
    min_price = row['min_price']

    filled = min_price <= limit_price

    if filled:
        entry = limit_price
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']

        gross_pnl_pct = (exit_price - entry) / entry * 100
        fee_pct = (MAKER_FEE + TAKER_FEE) * 100  # 0.07%
        net_pnl_pct = gross_pnl_pct - fee_pct

        pnl_dollar = balance * (net_pnl_pct / 100)
        balance += pnl_dollar
    else:
        entry = None
        exit_price = None
        gross_pnl_pct = 0
        fee_pct = 0
        net_pnl_pct = 0
        pnl_dollar = 0

    limit_results.append({
        'entry_time': row['entry_time'],
        'signal_price': signal,
        'limit_price': limit_price,
        'min_price_in_trade': min_price,
        'filled': 'YES' if filled else 'NO',
        'actual_entry': entry,
        'exit_price': exit_price,
        'result': row['result'] if filled else 'SKIPPED',
        'gross_pnl_pct': gross_pnl_pct,
        'entry_fee_pct': MAKER_FEE * 100 if filled else 0,
        'exit_fee_pct': TAKER_FEE * 100 if filled else 0,
        'total_fee_pct': fee_pct,
        'profit_after_fees_pct': net_pnl_pct,
        'profit_after_fees_dollar': pnl_dollar,
        'running_balance': balance
    })

limit_df = pd.DataFrame(limit_results)
limit_final = balance
filled_count = (limit_df['filled'] == 'YES').sum()

print(f"\n--- LIMIT BELOW -0.035% (0.02% + 0.05% = 0.07% RT) ---")
print(f"Filled: {filled_count}/{len(trades_df)} ({filled_count/len(trades_df)*100:.1f}%)")
filled_df = limit_df[limit_df['filled'] == 'YES']
print(f"W/L: {len(filled_df[filled_df['gross_pnl_pct'] > 0])}/{len(filled_df[filled_df['gross_pnl_pct'] <= 0])}")
print(f"Win rate: {len(filled_df[filled_df['gross_pnl_pct'] > 0])/filled_count*100:.1f}%")
print(f"Gross return: {limit_df['gross_pnl_pct'].sum():.2f}%")
print(f"Total fees: -{limit_df['total_fee_pct'].sum():.2f}%")
print(f"NET RETURN: {limit_df['profit_after_fees_pct'].sum():.2f}%")
print(f"Final: ${limit_final:,.2f} (${limit_final-STARTING_BALANCE:+,.2f})")

limit_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_limit_below_correct.csv', index=False)

# ============================================
# SUMMARY
# ============================================
print(f"\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\n{'Method':<30} {'Trades':<8} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Profit':<12}")
print("-" * 80)
print(f"{'Market (0.05%+0.05%=0.10%)':<30} {len(trades_df):<8} {market_df['gross_pnl_pct'].sum():>+.2f}%   -{market_df['total_fee_pct'].sum():.2f}%   {market_df['profit_after_fees_pct'].sum():>+.2f}%   ${market_final-STARTING_BALANCE:>+,.2f}")
print(f"{'Limit -0.035% (0.02%+0.05%)':<30} {filled_count:<8} {limit_df['gross_pnl_pct'].sum():>+.2f}%   -{limit_df['total_fee_pct'].sum():.2f}%   {limit_df['profit_after_fees_pct'].sum():>+.2f}%   ${limit_final-STARTING_BALANCE:>+,.2f}")

# Fee savings
fee_diff = market_df['total_fee_pct'].sum() - limit_df['total_fee_pct'].sum()
profit_diff = limit_final - market_final
print(f"\nLimit order advantage:")
print(f"  Fee savings: {fee_diff:.2f}%")
print(f"  Better/worse profit: ${profit_diff:+,.2f}")
print(f"  Better net return: {(limit_df['profit_after_fees_pct'].sum() - market_df['profit_after_fees_pct'].sum()):.2f}%")

print(f"\nCSVs saved:")
print(f"  - bb3_market_orders_correct.csv")
print(f"  - bb3_limit_below_correct.csv")
