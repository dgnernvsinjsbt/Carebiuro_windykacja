"""
Verify the ETH backtest results - check for calculation errors
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("VERIFICATION OF ETH BACKTEST RESULTS")
print("=" * 80)

# Load trades
trades = pd.read_csv('./results/eth_session_best_trades.csv')
print(f"\nLoaded {len(trades)} trades from best strategy")

# Check first trade manually
print("\n" + "=" * 80)
print("MANUAL VERIFICATION OF FIRST TRADE")
print("=" * 80)

trade1 = trades.iloc[0]
print(f"\nTrade 1: {trade1['side'].upper()}")
print(f"  Entry: ${trade1['entry']:.2f}")
print(f"  Exit:  ${trade1['exit']:.2f}")
print(f"  Reported PnL: ${trade1['pnl']:.2f}")

# Calculate what it SHOULD be
# From the code: pnl = (exit - entry) / entry * 100 * leverage * position['size']
# Where position['size'] = balance * 0.05 = 10000 * 0.05 = 500

# But this is WRONG! Let me show why:
entry = trade1['entry']
exit_price = trade1['exit']
leverage = 8
position_size_dollars = 10000 * 0.05  # $500

# What the code calculates:
code_pnl = (exit_price - entry) / entry * 100 * leverage * position_size_dollars
print(f"\n  Code calculates: {code_pnl:.2f}")

# PROBLEM: The formula multiplies by position_size in DOLLARS
# This doesn't make sense! PnL should be:
#   - Price change % * leverage * position_size_in_base_currency
#   OR
#   - Price change in dollars * leverage * position_quantity

# Correct calculation for a SHORT trade with $500 position at 8x leverage:
position_value = position_size_dollars * leverage  # $4000 total position
quantity = position_value / entry  # How many ETH we're shorting

# For SHORT: profit when price goes DOWN
price_change_pct = (entry - exit_price) / entry * 100
correct_pnl_pct = price_change_pct * leverage  # Percentage return on margin
correct_pnl_dollars = (entry - exit_price) * quantity  # Dollar PnL

print(f"\n  CORRECT Calculations:")
print(f"  Position value: ${position_value:.2f} (${position_size_dollars} margin * {leverage}x)")
print(f"  Quantity: {quantity:.4f} ETH")
print(f"  Price change: {price_change_pct:.4f}%")
print(f"  Return on margin: {correct_pnl_pct:.4f}%")
print(f"  Dollar PnL: ${correct_pnl_dollars:.2f}")

print("\n" + "=" * 80)
print("BUG #1: PnL FORMULA IS WRONG")
print("=" * 80)
print("""
The code uses:
  pnl = (exit - entry) / entry * 100 * leverage * position_size_dollars

This multiplies percentage change by dollar amount, creating nonsensical units!
For a 0.1% move with $500 position and 8x leverage:
  Code: 0.1 * 8 * 500 = 400 (treating as $400 gain)

CORRECT formula should be:
  pnl = (exit - entry) / entry * leverage * position_size_dollars
  = 0.001 * 8 * 500 = $4 actual gain

The current formula is 100x INFLATED!
""")

# Recalculate all trades correctly
print("\n" + "=" * 80)
print("RECALCULATED RESULTS (CORRECT FORMULA)")
print("=" * 80)

balance = 10000
correct_pnls = []

for i, trade in trades.iterrows():
    entry = trade['entry']
    exit_price = trade['exit']
    side = trade['side']
    position_size = balance * 0.05  # 5% of current balance

    # Correct PnL calculation
    if side == 'long':
        pnl = (exit_price - entry) / entry * leverage * position_size
    else:  # short
        pnl = (entry - exit_price) / entry * leverage * position_size

    # Subtract fees: 0.005% each side = 0.01% round trip
    fee_cost = position_size * leverage * 0.0001  # 0.01% of position value
    pnl -= fee_cost

    correct_pnls.append(pnl)
    balance += pnl

print(f"\nStarting balance: $10,000")
print(f"Final balance: ${balance:.2f}")
print(f"Total return: {(balance - 10000) / 10000 * 100:.2f}%")

# Calculate drawdown
equity = [10000]
running_balance = 10000
for pnl in correct_pnls:
    running_balance += pnl
    equity.append(running_balance)

equity_series = pd.Series(equity)
running_max = equity_series.expanding().max()
drawdown = (equity_series - running_max) / running_max * 100
max_drawdown = drawdown.min()

print(f"Max drawdown: {max_drawdown:.2f}%")

if max_drawdown != 0:
    profit_dd = abs((balance - 10000) / 10000 * 100 / max_drawdown)
    print(f"Profit/DD ratio: {profit_dd:.2f}:1")
else:
    print("No drawdown")

# Win/loss stats
wins = [p for p in correct_pnls if p > 0]
losses = [p for p in correct_pnls if p <= 0]
win_rate = len(wins) / len(correct_pnls) * 100

print(f"\nWin rate: {win_rate:.1f}%")
print(f"Avg win: ${np.mean(wins):.2f}" if wins else "No wins")
print(f"Avg loss: ${np.mean(losses):.2f}" if losses else "No losses")

print("\n" + "=" * 80)
print("SUMMARY OF BUGS FOUND")
print("=" * 80)
print("""
1. PnL formula multiplies by 100 incorrectly, inflating all returns by 100x
2. Fees are NOT subtracted (0.005% per side = 0.01% per trade)
3. Position sizing compounds incorrectly (using current balance * 0.05)

ORIGINAL CLAIMED RESULTS:
- Return: 1,503.95%
- Max DD: 50.42%
- Profit/DD: 29.83:1

These are WRONG by approximately 100x!
""")
