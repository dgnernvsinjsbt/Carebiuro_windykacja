#!/usr/bin/env python3
"""
Create enhanced CSV with fee breakdown for BB3 strategy with limit orders.
Uses actual 1-minute data to calculate real minimum prices during trades.
"""
import pandas as pd
import numpy as np
from datetime import datetime

# Load 1-minute ETH data
print("Loading 1-minute ETH data...")
eth_data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
eth_data['timestamp'] = pd.to_datetime(eth_data['timestamp'])
eth_data = eth_data.set_index('timestamp')

# Load trades
trades_df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_std_all_trades.csv')
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])

# Strategy parameters
LIMIT_OFFSET = 0.00035  # 0.035% below signal
MAKER_FEE = 0.0007      # 0.07%
TAKER_FEE = 0.001       # 0.10%
STARTING_BALANCE = 10000

def get_min_price_during_trade(entry_time, exit_time, eth_data):
    """Get the actual minimum price during a trade from 1-minute data"""
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        trade_data = eth_data.loc[mask]
        if len(trade_data) > 0:
            return trade_data['low'].min()
        return None
    except:
        return None

print("Calculating minimum prices during each trade...")
results = []
balance = STARTING_BALANCE

for idx, row in trades_df.iterrows():
    # Get actual minimum price during trade
    min_price = get_min_price_during_trade(row['entry_time'], row['exit_time'], eth_data)

    if min_price is None:
        min_price = row['stop'] if row['result'] == 'STOP' else row['entry']

    signal_price = row['entry']
    limit_price = signal_price * (1 - LIMIT_OFFSET)

    # Calculate dip
    dip_pct = (signal_price - min_price) / signal_price * 100

    # Check if limit would fill
    limit_filled = min_price <= limit_price

    trade = {
        'trade_num': idx + 1,
        'entry_time': row['entry_time'],
        'exit_time': row['exit_time'],
        'signal_price': signal_price,
        'stop': row['stop'],
        'target': row['target'],
        'result': row['result'],
        'min_price_during_trade': min_price,
        'dip_below_signal_pct': dip_pct,
        'limit_price': limit_price,
        'filled': 'YES' if limit_filled else 'NO',
    }

    if limit_filled:
        # Calculate P/L from limit entry to stop/target
        actual_entry = limit_price

        if row['result'] == 'TP':
            exit_price = row['target']
        else:
            exit_price = row['stop']

        gross_pnl_pct = (exit_price - actual_entry) / actual_entry * 100

        trade['actual_entry'] = actual_entry
        trade['exit_price'] = exit_price
        trade['entry_improvement_pct'] = LIMIT_OFFSET * 100
        trade['gross_pnl_pct'] = gross_pnl_pct
        trade['entry_fee_type'] = 'MAKER'
        trade['entry_fee_pct'] = MAKER_FEE * 100
        trade['exit_fee_type'] = 'TAKER'
        trade['exit_fee_pct'] = TAKER_FEE * 100
        trade['total_fees_pct'] = (MAKER_FEE + TAKER_FEE) * 100
        trade['profit_after_fees_pct'] = gross_pnl_pct - trade['total_fees_pct']

        pnl_dollar = balance * (trade['profit_after_fees_pct'] / 100)
        balance += pnl_dollar
        trade['profit_after_fees_dollar'] = pnl_dollar
    else:
        trade['actual_entry'] = None
        trade['exit_price'] = None
        trade['entry_improvement_pct'] = 0
        trade['gross_pnl_pct'] = 0
        trade['entry_fee_type'] = 'N/A'
        trade['entry_fee_pct'] = 0
        trade['exit_fee_type'] = 'N/A'
        trade['exit_fee_pct'] = 0
        trade['total_fees_pct'] = 0
        trade['profit_after_fees_pct'] = 0
        trade['profit_after_fees_dollar'] = 0

    trade['running_balance'] = balance
    results.append(trade)

# Create DataFrame
results_df = pd.DataFrame(results)

# Save to CSV
output_path = '/workspaces/Carebiuro_windykacja/trading/results/bb3_limit_orders_with_fees.csv'
results_df.to_csv(output_path, index=False)

# Print summary
print("\n" + "=" * 70)
print("BB3 STRATEGY WITH LIMIT ORDERS (-0.035%) - FEE BREAKDOWN")
print("=" * 70)

total_trades = len(trades_df)
filled_trades = (results_df['filled'] == 'YES').sum()
skipped_trades = total_trades - filled_trades

filled_df = results_df[results_df['filled'] == 'YES']
winners = filled_df[filled_df['gross_pnl_pct'] > 0]
losers = filled_df[filled_df['gross_pnl_pct'] <= 0]

print(f"\nTRADE STATISTICS:")
print(f"  Total signals:     {total_trades}")
print(f"  Filled (limit):    {filled_trades} ({filled_trades/total_trades*100:.1f}%)")
print(f"  Skipped (no fill): {skipped_trades} ({skipped_trades/total_trades*100:.1f}%)")
print(f"  Winners:           {len(winners)}")
print(f"  Losers:            {len(losers)}")
if filled_trades > 0:
    print(f"  Win rate:          {len(winners)/filled_trades*100:.1f}%")

print(f"\nDIP ANALYSIS (all trades):")
print(f"  Winners avg dip:   {results_df[results_df['result']=='TP']['dip_below_signal_pct'].mean():.3f}%")
print(f"  Losers avg dip:    {results_df[results_df['result']=='STOP']['dip_below_signal_pct'].mean():.3f}%")

print(f"\nFEE BREAKDOWN (filled trades only):")
total_maker_fees = filled_df['entry_fee_pct'].sum()
total_taker_fees = filled_df['exit_fee_pct'].sum()
print(f"  Total maker fees:  {total_maker_fees:.2f}% ({filled_trades} trades × 0.07%)")
print(f"  Total taker fees:  {total_taker_fees:.2f}% ({filled_trades} trades × 0.10%)")
print(f"  Total fees paid:   {total_maker_fees + total_taker_fees:.2f}%")

print(f"\nRETURNS:")
gross_return = filled_df['gross_pnl_pct'].sum()
total_fees = filled_df['total_fees_pct'].sum()
net_return = filled_df['profit_after_fees_pct'].sum()
print(f"  Gross return:      {gross_return:.2f}%")
print(f"  Total fees:        -{total_fees:.2f}%")
print(f"  NET RETURN:        {net_return:.2f}%")
print(f"\n  Starting balance:  ${STARTING_BALANCE:,.2f}")
print(f"  Final balance:     ${balance:,.2f}")
print(f"  Profit:            ${balance - STARTING_BALANCE:,.2f}")

# Show first 10 trades
print(f"\n" + "=" * 70)
print("FIRST 10 TRADES SAMPLE:")
print("=" * 70)
cols_to_show = ['trade_num', 'signal_price', 'dip_below_signal_pct', 'filled',
                'result', 'gross_pnl_pct', 'total_fees_pct', 'profit_after_fees_pct']
print(results_df[cols_to_show].head(10).to_string(index=False))

print(f"\nCSV saved to: {output_path}")
