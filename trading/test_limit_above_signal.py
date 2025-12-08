#!/usr/bin/env python3
"""
Test placing limit orders ABOVE signal price to filter out losing trades.

Hypothesis: If we require price to bounce X% above signal before entry,
we filter out "falling knife" losers while still catching winners.
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
ENTRY_FEE = 0.0002   # 0.02%
EXIT_FEE = 0.0005    # 0.05%
TOTAL_FEE = 0.0007   # 0.07%
STARTING_BALANCE = 10000

def get_max_price(entry_time, exit_time, eth_data):
    """Get max price during trade (to see if limit ABOVE would fill)"""
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['high'].max()
    except:
        return None

def get_min_price(entry_time, exit_time, eth_data):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['low'].min()
    except:
        return None

# Get max and min prices during each trade
trades_df['max_price'] = trades_df.apply(
    lambda r: get_max_price(r['entry_time'], r['exit_time'], eth_data), axis=1
)
trades_df['min_price'] = trades_df.apply(
    lambda r: get_min_price(r['entry_time'], r['exit_time'], eth_data), axis=1
)

# Fill missing
trades_df['max_price'] = trades_df.apply(
    lambda r: r['max_price'] if pd.notna(r['max_price']) else r['target'], axis=1
)
trades_df['min_price'] = trades_df.apply(
    lambda r: r['min_price'] if pd.notna(r['min_price']) else r['stop'], axis=1
)

# Calculate bounce above signal
trades_df['bounce_above_pct'] = (trades_df['max_price'] - trades_df['entry']) / trades_df['entry'] * 100

# Analyze bounce patterns
print("=" * 70)
print("BOUNCE ANALYSIS - How much does price rise above signal?")
print("=" * 70)

winners = trades_df[trades_df['result'] == 'TP']
losers = trades_df[trades_df['result'] == 'STOP']

print(f"\nWINNERS ({len(winners)} trades):")
print(f"  Min bounce:  {winners['bounce_above_pct'].min():.3f}%")
print(f"  Avg bounce:  {winners['bounce_above_pct'].mean():.3f}%")
print(f"  Max bounce:  {winners['bounce_above_pct'].max():.3f}%")

print(f"\nLOSERS ({len(losers)} trades):")
print(f"  Min bounce:  {losers['bounce_above_pct'].min():.3f}%")
print(f"  Avg bounce:  {losers['bounce_above_pct'].mean():.3f}%")
print(f"  Max bounce:  {losers['bounce_above_pct'].max():.3f}%")

# Distribution of bounces
print(f"\nBOUNCE DISTRIBUTION:")
thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
print(f"\n{'Threshold':<12} {'Winners':<15} {'Losers':<15} {'Net Filter':<15}")
print("-" * 60)
for thresh in thresholds:
    w_fill = (winners['bounce_above_pct'] >= thresh).sum()
    l_fill = (losers['bounce_above_pct'] >= thresh).sum()
    print(f"{thresh:.2f}%        {w_fill}/{len(winners)} ({w_fill/len(winners)*100:.0f}%)      {l_fill}/{len(losers)} ({l_fill/len(losers)*100:.0f}%)      W:{w_fill} L:{l_fill}")

# Test different "above" offsets
print(f"\n" + "=" * 70)
print("SIMULATION: Limit orders ABOVE signal price")
print("=" * 70)

results = []

for offset_pct in [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
    offset = offset_pct / 100
    balance = STARTING_BALANCE

    filled = 0
    wins = 0
    losses = 0
    gross_pnl = 0
    total_fees = 0

    for _, row in trades_df.iterrows():
        signal = row['entry']
        limit_price = signal * (1 + offset)  # ABOVE signal
        max_price = row['max_price']

        # Fills if price reaches our limit (goes UP to it)
        if max_price >= limit_price:
            filled += 1

            # Entry at limit price (above signal)
            entry = limit_price
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']

            # P/L
            pnl_pct = (exit_price - entry) / entry * 100
            fee_pct = TOTAL_FEE * 100

            if pnl_pct > 0:
                wins += 1
            else:
                losses += 1

            gross_pnl += pnl_pct
            total_fees += fee_pct

            net_pnl_pct = pnl_pct - fee_pct
            balance += balance * (net_pnl_pct / 100)

    net_return = ((balance / STARTING_BALANCE) - 1) * 100
    profit = balance - STARTING_BALANCE

    results.append({
        'offset_pct': offset_pct,
        'filled': filled,
        'wins': wins,
        'losses': losses,
        'win_rate': wins/filled*100 if filled > 0 else 0,
        'gross_pnl': gross_pnl,
        'total_fees': total_fees,
        'net_return': net_return,
        'profit': profit
    })

# Print results
print(f"\n{'Offset':<10} {'Filled':<10} {'W/L':<12} {'Win%':<8} {'Gross':<10} {'Fees':<10} {'NET':<10} {'Profit':<12}")
print("-" * 90)

for r in results:
    print(f"{r['offset_pct']:.2f}%      {r['filled']:<10} {r['wins']}/{r['losses']:<8} {r['win_rate']:.1f}%    {r['gross_pnl']:>+.2f}%   -{r['total_fees']:.2f}%   {r['net_return']:>+.2f}%   ${r['profit']:>+,.2f}")

# Find best offset
best = max(results, key=lambda x: x['net_return'])
print(f"\n" + "=" * 70)
print(f"BEST: {best['offset_pct']:.2f}% above signal → {best['net_return']:.2f}% net return")
print("=" * 70)

# Detailed trade-by-trade for best offset
print(f"\nGenerating CSV for best offset ({best['offset_pct']:.2f}%)...")

offset = best['offset_pct'] / 100
balance = STARTING_BALANCE
detailed = []

for idx, row in trades_df.iterrows():
    signal = row['entry']
    limit_price = signal * (1 + offset)
    max_price = row['max_price']
    min_price = row['min_price']

    filled = max_price >= limit_price

    trade = {
        'trade_num': idx + 1,
        'entry_time': row['entry_time'],
        'signal_price': signal,
        'limit_price_above': limit_price,
        'max_price_in_trade': max_price,
        'min_price_in_trade': min_price,
        'bounce_above_pct': row['bounce_above_pct'],
        'filled': 'YES' if filled else 'NO',
        'original_result': row['result'],
    }

    if filled:
        entry = limit_price
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']

        gross_pnl = (exit_price - entry) / entry * 100
        fee = TOTAL_FEE * 100
        net_pnl = gross_pnl - fee

        trade['actual_entry'] = entry
        trade['exit_price'] = exit_price
        trade['gross_pnl_pct'] = gross_pnl
        trade['entry_fee_pct'] = ENTRY_FEE * 100
        trade['exit_fee_pct'] = EXIT_FEE * 100
        trade['total_fee_pct'] = fee
        trade['profit_after_fees_pct'] = net_pnl

        pnl_dollar = balance * (net_pnl / 100)
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
    detailed.append(trade)

df_out = pd.DataFrame(detailed)
df_out.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_limit_above_best.csv', index=False)
print(f"Saved to: bb3_limit_above_best.csv")
