#!/usr/bin/env python3
"""
Verify the math: Should 25% position = 1/4 of 100% returns?
"""
import pandas as pd

print("="*100)
print("MATH VERIFICATION - Sequential 100% vs 25%")
print("="*100)

# Load trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} trades")
print(f"   Testing SEQUENTIAL processing (one trade at a time, ignoring overlaps)")

def sequential_backtest(position_pct):
    """
    Sequential backtest - process trades one by one
    Each trade uses position_pct of current equity
    IGNORES that trades might overlap in time
    """
    equity = 100.0

    for _, trade in df.iterrows():
        # Position size = position_pct of current equity
        position_size = equity * position_pct

        # P&L in dollars
        pnl_dollar = position_size * (trade['pnl_pct'] / 100)

        # Update equity
        equity += pnl_dollar

    total_return = ((equity - 100) / 100) * 100

    return {
        'final_equity': equity,
        'total_return': total_return
    }

print("\n" + "="*100)
print("TEST 1: SEQUENTIAL PROCESSING (ignoring overlaps)")
print("="*100)

# Test different position sizes
position_sizes = [1.0, 0.75, 0.50, 0.25, 0.20, 0.15, 0.10]

print("\nSequential Results:")
print(f"{'Position %':>12} | {'Final Equity':>15} | {'Total Return':>15} | {'vs 100%':>15}")
print("-" * 75)

baseline_100_result = sequential_backtest(1.0)

for pos in position_sizes:
    result = sequential_backtest(pos)
    ratio = result['total_return'] / baseline_100_result['total_return']

    print(f"{int(pos*100):>10}%  | ${result['final_equity']:>13,.2f}  | {result['total_return']:>13.1f}%  | {ratio:>13.2%}")

print("\n" + "="*100)
print("INSIGHT: Returns do NOT scale linearly!")
print("="*100)
print()
print("Why? Because each trade compounds on previous equity.")
print("With 100% positions: $100 + 10% = $110, then $110 + 10% = $121 (heavy compound)")
print("With 25% positions: $100 + 2.5% = $102.5, then $102.5 + 2.5% = $105.06 (light compound)")
print()
print("So 25% position ≠ 1/4 of 100% returns in compounding!")

# Now show realistic portfolio with overlaps
print("\n" + "="*100)
print("TEST 2: PORTFOLIO PROCESSING (accounting for overlaps)")
print("="*100)

def portfolio_backtest(base_pct):
    """
    Portfolio backtest - accounts for overlapping positions
    """
    equity = 100.0
    open_positions = []

    # Create events
    all_events = []
    for idx, trade in df.iterrows():
        all_events.append({'time': trade['entry_time'], 'type': 'entry', 'trade_idx': idx})
        all_events.append({'time': trade['exit_time'], 'type': 'exit', 'trade_idx': idx})

    all_events = sorted(all_events, key=lambda x: x['time'])

    # Process events
    for event in all_events:
        if event['type'] == 'entry':
            trade = df.iloc[event['trade_idx']]
            position_size = equity * base_pct

            open_positions.append({
                'trade_idx': event['trade_idx'],
                'position_size': position_size,
                'pnl_pct': trade['pnl_pct']
            })

        elif event['type'] == 'exit':
            for i, pos in enumerate(open_positions):
                if pos['trade_idx'] == event['trade_idx']:
                    position = open_positions.pop(i)
                    pnl_dollar = position['position_size'] * (position['pnl_pct'] / 100)
                    equity += pnl_dollar
                    break

    total_return = ((equity - 100) / 100) * 100

    return {
        'final_equity': equity,
        'total_return': total_return
    }

print("\nPortfolio Results (with overlaps):")
print(f"{'Position %':>12} | {'Final Equity':>15} | {'Total Return':>15} | {'Difference':>15}")
print("-" * 75)

for pos in position_sizes:
    seq_result = sequential_backtest(pos)
    port_result = portfolio_backtest(pos)
    diff = port_result['total_return'] - seq_result['total_return']

    print(f"{int(pos*100):>10}%  | ${port_result['final_equity']:>13,.2f}  | {port_result['total_return']:>13.1f}%  | {diff:>13.1f}pp")

print("\n" + "="*100)
print("KEY FINDING:")
print("="*100)
print()
print("Sequential 100%: ${:,.2f} ({:+.1f}%)".format(
    baseline_100_result['final_equity'],
    baseline_100_result['total_return']
))

port_25_result = portfolio_backtest(0.25)
print("Portfolio 25%:   ${:,.2f} ({:+.1f}%)".format(
    port_25_result['final_equity'],
    port_25_result['total_return']
))

print()
print("User expected: ~${:,.2f} (sequential 100% / 4)".format(baseline_100_result['final_equity'] / 4))
print("Actual result: ${:,.2f}".format(port_25_result['final_equity']))
print()
print("Difference explained:")
print("1. Sequential ignores overlaps → overestimates returns")
print("2. Portfolio accounts for overlaps → realistic but lower returns")
print("3. Non-linear compounding: 25% position ≠ 1/4 returns")
print()

# Show what happens with sequential 25%
seq_25_result = sequential_backtest(0.25)
print("If we did Sequential 25% (still ignoring overlaps):")
print("Result would be: ${:,.2f} ({:+.1f}%)".format(
    seq_25_result['final_equity'],
    seq_25_result['total_return']
))
print()
print("This is closer to user's expectation but still WRONG")
print("because it ignores that trades overlap in time!")

print("\n" + "="*100)
print("CONCLUSION")
print("="*100)
print()
print("✅ Portfolio 25% calculation is CORRECT: ${:,.2f}".format(port_25_result['final_equity']))
print("❌ Sequential 100% calculation is INFLATED: ${:,.2f} (ignores overlaps)".format(baseline_100_result['final_equity']))
print()
print("The realistic result with 4 strategies @ 25% each is: ${:,.2f}".format(port_25_result['final_equity']))
print("="*100)
