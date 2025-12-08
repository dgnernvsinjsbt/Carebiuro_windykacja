#!/usr/bin/env python3
"""
Create enhanced CSV with fee breakdown for BB3 strategy with limit orders
"""
import pandas as pd
import numpy as np

# Load trades
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_std_all_trades.csv')

# Strategy parameters
LIMIT_OFFSET = 0.00035  # 0.035% below signal
MAKER_FEE = 0.0007      # 0.07%
TAKER_FEE = 0.001       # 0.10%
STARTING_BALANCE = 10000

# Calculate limit entry price
df['limit_entry'] = df['entry'] * (1 - LIMIT_OFFSET)

# Calculate how much price dipped below entry (to determine if limit would fill)
# For this we need to check if the trade would have filled
# Using the pnl_pct to reverse-engineer min price during trade

# For TP trades: price went up to target, min was somewhere between entry and stop
# For STOP trades: price went down to stop

# Estimate minimum price during trade based on outcome
def estimate_min_price(row):
    if row['result'] == 'STOP':
        # Hit stop loss - min was at or below stop
        return row['stop']
    else:
        # Hit TP - min could be entry or slightly below
        # Use a conservative estimate: min was at entry (no dip)
        return row['entry']

df['est_min_price'] = df.apply(estimate_min_price, axis=1)

# Calculate dip below entry
df['dip_below_entry_pct'] = (df['entry'] - df['est_min_price']) / df['entry'] * 100

# Determine if limit order would fill (limit price >= min price)
df['limit_filled'] = df['limit_entry'] >= df['est_min_price']

# For filled limit orders:
# - Entry is at limit_entry (better price)
# - Entry fee is MAKER (0.07%)
# - Exit fee is TAKER (0.10%) - we use market order to exit
# - Entry improvement = LIMIT_OFFSET %

results = []
balance = STARTING_BALANCE

for idx, row in df.iterrows():
    trade = {
        'trade_num': idx + 1,
        'entry_time': row['entry_time'],
        'exit_time': row['exit_time'],
        'signal_price': row['entry'],
        'result': row['result'],
        'original_pnl_pct': row['pnl_pct'],
    }

    if row['limit_filled']:
        # Limit order filled
        trade['filled'] = 'YES'
        trade['actual_entry'] = row['limit_entry']
        trade['entry_improvement_pct'] = LIMIT_OFFSET * 100  # 0.035%

        # Recalculate P/L with limit entry
        # Stop and target are based on SIGNAL price (as per user request)
        stop = row['stop']
        target = row['target']
        exit_price = row['exit']
        entry = row['limit_entry']

        # P/L calculation
        if row['result'] == 'TP':
            # Exit at target
            pnl_pct = (target - entry) / entry * 100
        else:
            # Exit at stop
            pnl_pct = (stop - entry) / entry * 100

        trade['limit_pnl_pct'] = pnl_pct
        trade['entry_fee_type'] = 'MAKER'
        trade['entry_fee_pct'] = MAKER_FEE * 100
        trade['exit_fee_type'] = 'TAKER'
        trade['exit_fee_pct'] = TAKER_FEE * 100
        trade['total_fee_pct'] = (MAKER_FEE + TAKER_FEE) * 100

    else:
        # Limit order NOT filled - trade skipped
        trade['filled'] = 'NO'
        trade['actual_entry'] = None
        trade['entry_improvement_pct'] = 0
        trade['limit_pnl_pct'] = 0
        trade['entry_fee_type'] = 'N/A'
        trade['entry_fee_pct'] = 0
        trade['exit_fee_type'] = 'N/A'
        trade['exit_fee_pct'] = 0
        trade['total_fee_pct'] = 0

    # Calculate profit after fees
    if row['limit_filled']:
        trade['profit_after_fees_pct'] = trade['limit_pnl_pct'] - trade['total_fee_pct']
        pnl_dollar = balance * (trade['profit_after_fees_pct'] / 100)
        balance += pnl_dollar
        trade['profit_after_fees_dollar'] = pnl_dollar
    else:
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
print("=" * 70)
print("BB3 STRATEGY WITH LIMIT ORDERS (-0.035%) - FEE BREAKDOWN")
print("=" * 70)

total_trades = len(df)
filled_trades = results_df['filled'].value_counts().get('YES', 0)
skipped_trades = total_trades - filled_trades

filled_df = results_df[results_df['filled'] == 'YES']
winners = filled_df[filled_df['limit_pnl_pct'] > 0]
losers = filled_df[filled_df['limit_pnl_pct'] <= 0]

print(f"\nTRADE STATISTICS:")
print(f"  Total signals:     {total_trades}")
print(f"  Filled (limit):    {filled_trades} ({filled_trades/total_trades*100:.1f}%)")
print(f"  Skipped (no fill): {skipped_trades} ({skipped_trades/total_trades*100:.1f}%)")
print(f"  Winners:           {len(winners)}")
print(f"  Losers:            {len(losers)}")
print(f"  Win rate:          {len(winners)/filled_trades*100:.1f}%")

print(f"\nFEE BREAKDOWN:")
total_maker_fees = filled_df['entry_fee_pct'].sum()
total_taker_fees = filled_df['exit_fee_pct'].sum()
print(f"  Total maker fees:  {total_maker_fees:.2f}% ({filled_trades} trades × 0.07%)")
print(f"  Total taker fees:  {total_taker_fees:.2f}% ({filled_trades} trades × 0.10%)")
print(f"  Total fees paid:   {total_maker_fees + total_taker_fees:.2f}%")

print(f"\nRETURNS:")
gross_return = filled_df['limit_pnl_pct'].sum()
total_fees = filled_df['total_fee_pct'].sum()
net_return = filled_df['profit_after_fees_pct'].sum()
print(f"  Gross return:      {gross_return:.2f}%")
print(f"  Total fees:        -{total_fees:.2f}%")
print(f"  NET RETURN:        {net_return:.2f}%")
print(f"\n  Starting balance:  ${STARTING_BALANCE:,.2f}")
print(f"  Final balance:     ${balance:,.2f}")
print(f"  Profit:            ${balance - STARTING_BALANCE:,.2f}")

print(f"\nCSV saved to: {output_path}")
print("=" * 70)
