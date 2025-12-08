#!/usr/bin/env python3
"""
Compare market orders vs limit orders for BB3 strategy
"""
import pandas as pd
import numpy as np

# Load 1-minute ETH data
print("Loading data...")
eth_data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
eth_data['timestamp'] = pd.to_datetime(eth_data['timestamp'])
eth_data = eth_data.set_index('timestamp')

# Load trades
trades_df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_std_all_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

STARTING_BALANCE = 10000

def get_min_price(entry_time, exit_time, eth_data):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['low'].min()
    except:
        return None

# Calculate min price for each trade
trades_df['min_price'] = trades_df.apply(
    lambda r: get_min_price(r['entry_time'], r['exit_time'], eth_data), axis=1
)

# Fill missing with stop price for STOP trades, entry for TP
trades_df['min_price'] = trades_df.apply(
    lambda r: r['min_price'] if pd.notna(r['min_price']) else (r['stop'] if r['result']=='STOP' else r['entry']),
    axis=1
)

# Calculate dip below entry
trades_df['dip_pct'] = (trades_df['entry'] - trades_df['min_price']) / trades_df['entry'] * 100

def simulate_strategy(trades_df, entry_mode, maker_fee, taker_fee, limit_offset=0):
    """
    Simulate trading with given parameters

    entry_mode: 'market' or 'limit'
    maker_fee: fee when placing limit order (0.0007 = 0.07%)
    taker_fee: fee for market orders (0.001 = 0.10%)
    limit_offset: how far below signal to place limit (0.00035 = 0.035%)
    """
    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal_price = row['entry']
        stop = row['stop']
        target = row['target']
        result = row['result']
        min_price = row['min_price']

        if entry_mode == 'market':
            # Market order always fills at signal price
            entry_price = signal_price
            filled = True
            entry_fee = taker_fee  # Market = taker
        else:
            # Limit order fills only if price dips to limit
            limit_price = signal_price * (1 - limit_offset)
            filled = min_price <= limit_price
            entry_price = limit_price if filled else None
            entry_fee = maker_fee  # Limit = maker

        if not filled:
            results.append({
                'filled': False,
                'pnl_gross': 0,
                'fees': 0,
                'pnl_net': 0,
                'balance': balance
            })
            continue

        # Exit always at market (taker)
        exit_fee = taker_fee

        # Calculate exit price
        if result == 'TP':
            exit_price = target
        else:
            exit_price = stop

        # P/L calculation
        pnl_gross_pct = (exit_price - entry_price) / entry_price * 100
        total_fee_pct = (entry_fee + exit_fee) * 100
        pnl_net_pct = pnl_gross_pct - total_fee_pct

        # Dollar amounts
        pnl_dollar = balance * (pnl_net_pct / 100)
        balance += pnl_dollar

        results.append({
            'filled': True,
            'pnl_gross': pnl_gross_pct,
            'fees': total_fee_pct,
            'pnl_net': pnl_net_pct,
            'balance': balance
        })

    return results, balance

print("\n" + "=" * 70)
print("BB3 STRATEGY: MARKET vs LIMIT ORDERS COMPARISON")
print("=" * 70)

# Scenario 1: Market orders (taker/taker)
print("\n--- SCENARIO 1: MARKET ORDERS (0.10% entry + 0.10% exit) ---")
market_results, market_final = simulate_strategy(
    trades_df, 'market', maker_fee=0.001, taker_fee=0.001, limit_offset=0
)
market_df = pd.DataFrame(market_results)
filled = market_df['filled'].sum()
gross = market_df['pnl_gross'].sum()
fees = market_df['fees'].sum()
net = market_df['pnl_net'].sum()
print(f"Trades: {filled}/{len(trades_df)}")
print(f"Gross return: {gross:.2f}%")
print(f"Total fees: -{fees:.2f}%")
print(f"NET RETURN: {net:.2f}%")
print(f"Final balance: ${market_final:,.2f}")

# Scenario 2: Limit orders -0.035% (maker/taker)
print("\n--- SCENARIO 2: LIMIT ORDERS -0.035% (0.07% entry + 0.10% exit) ---")
limit_results, limit_final = simulate_strategy(
    trades_df, 'limit', maker_fee=0.0007, taker_fee=0.001, limit_offset=0.00035
)
limit_df = pd.DataFrame(limit_results)
filled = limit_df['filled'].sum()
winners = len(limit_df[(limit_df['filled']) & (limit_df['pnl_gross'] > 0)])
gross = limit_df['pnl_gross'].sum()
fees = limit_df['fees'].sum()
net = limit_df['pnl_net'].sum()
print(f"Trades filled: {filled}/{len(trades_df)} ({filled/len(trades_df)*100:.1f}%)")
print(f"Winners: {winners}, Win rate: {winners/filled*100:.1f}%")
print(f"Gross return: {gross:.2f}%")
print(f"Total fees: -{fees:.2f}%")
print(f"NET RETURN: {net:.2f}%")
print(f"Final balance: ${limit_final:,.2f}")

# Scenario 3: What if we could get maker fees on exit too? (limit exit)
print("\n--- SCENARIO 3: ALL LIMIT (0.07% entry + 0.07% exit) - THEORETICAL ---")
limit_results_best, limit_final_best = simulate_strategy(
    trades_df, 'limit', maker_fee=0.0007, taker_fee=0.0007, limit_offset=0.00035
)
limit_df_best = pd.DataFrame(limit_results_best)
filled = limit_df_best['filled'].sum()
gross = limit_df_best['pnl_gross'].sum()
fees = limit_df_best['fees'].sum()
net = limit_df_best['pnl_net'].sum()
print(f"Trades filled: {filled}/{len(trades_df)}")
print(f"Gross return: {gross:.2f}%")
print(f"Total fees: -{fees:.2f}%")
print(f"NET RETURN: {net:.2f}%")
print(f"Final balance: ${limit_final_best:,.2f}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n{'Method':<30} {'Trades':<10} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Final $':<12}")
print("-" * 70)

# Market
market_filled = market_df['filled'].sum()
print(f"{'Market (0.1%+0.1%)':<30} {market_filled:<10} {market_df['pnl_gross'].sum():>+.2f}%    {market_df['fees'].sum():>-.2f}%    {market_df['pnl_net'].sum():>+.2f}%   ${market_final:>,.2f}")

# Limit -0.035%
limit_filled = limit_df['filled'].sum()
print(f"{'Limit -0.035% (0.07%+0.1%)':<30} {limit_filled:<10} {limit_df['pnl_gross'].sum():>+.2f}%   {limit_df['fees'].sum():>-.2f}%   {limit_df['pnl_net'].sum():>+.2f}%   ${limit_final:>,.2f}")

# All maker
print(f"{'All Maker (0.07%+0.07%)':<30} {limit_filled:<10} {limit_df_best['pnl_gross'].sum():>+.2f}%   {limit_df_best['fees'].sum():>-.2f}%   {limit_df_best['pnl_net'].sum():>+.2f}%   ${limit_final_best:>,.2f}")

print("\n" + "=" * 70)
