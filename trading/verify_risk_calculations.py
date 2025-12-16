"""
Verify risk-based calculations step-by-step
"""
import pandas as pd

df = pd.read_csv('portfolio_RISK_BASED.csv')

print('='*100)
print('🔍 VERIFICATION: Risk-Based Position Sizing Calculations')
print('='*100)
print()

# Show first 10 trades step-by-step
print('FIRST 10 TRADES - STEP BY STEP:')
print('='*100)

equity = 1000.0
for i in range(10):
    trade = df.iloc[i]

    print(f"\nTrade {i+1}: {trade['coin']} {trade['side']} @ {trade['exit_time']}")
    print('-'*100)

    # Calculate risk amount (1% of current equity)
    risk_amount = equity * 0.01
    print(f"  Current Equity: ${equity:,.2f}")
    print(f"  Risk Amount (1%): ${risk_amount:.2f}")

    # Calculate position size based on stop loss
    stop_loss_pct = trade['stop_loss_pct']
    position_size_raw = risk_amount / (stop_loss_pct / 100)
    print(f"  Stop Loss: {stop_loss_pct:.2f}%")
    print(f"  Position Size (uncapped): ${position_size_raw:,.2f} ({position_size_raw/equity*100:.2f}% of equity)")

    # Apply 50% cap
    max_position = equity * 0.50
    position_size = min(position_size_raw, max_position)
    if position_size_raw > max_position:
        print(f"  ⚠️  CAPPED at 50%: ${position_size:,.2f}")
    else:
        print(f"  Final Position Size: ${position_size:,.2f}")

    # Calculate P&L
    pnl_pct = trade['pnl_pct']
    dollar_pnl = position_size * (pnl_pct / 100)
    print(f"  Trade P&L: {pnl_pct:+.2f}%")
    print(f"  Dollar P&L: ${dollar_pnl:+.2f}")

    # Update equity
    new_equity = equity + dollar_pnl
    portfolio_impact = (dollar_pnl / equity) * 100
    print(f"  Portfolio Impact: {portfolio_impact:+.2f}%")
    print(f"  New Equity: ${new_equity:,.2f}")

    # Verify against saved data
    saved_position = trade['position_size']
    saved_pnl = trade['dollar_pnl']
    saved_equity = trade['equity']

    # Check if calculations match
    position_match = abs(position_size - saved_position) < 0.01
    pnl_match = abs(dollar_pnl - saved_pnl) < 0.01
    equity_match = abs(new_equity - saved_equity) < 0.01

    if position_match and pnl_match and equity_match:
        print(f"  ✅ VERIFIED - All calculations match saved data")
    else:
        print(f"  ❌ MISMATCH!")
        print(f"     Position: Calc=${position_size:.2f} vs Saved=${saved_position:.2f}")
        print(f"     P&L: Calc=${dollar_pnl:.2f} vs Saved=${saved_pnl:.2f}")
        print(f"     Equity: Calc=${new_equity:.2f} vs Saved=${saved_equity:.2f}")

    equity = new_equity

print()
print('='*100)
print('📊 FINAL VERIFICATION')
print('='*100)
print()

# Verify final equity
final_equity = df['equity'].iloc[-1]
print(f"Final Equity from CSV: ${final_equity:,.2f}")

# Recalculate from scratch
equity = 1000.0
for idx, trade in df.iterrows():
    risk_amount = equity * 0.01
    position_size = risk_amount / (trade['stop_loss_pct'] / 100)
    position_size = min(position_size, equity * 0.50)
    dollar_pnl = position_size * (trade['pnl_pct'] / 100)
    equity += dollar_pnl

print(f"Final Equity (recalculated): ${equity:,.2f}")
print()

if abs(equity - final_equity) < 0.01:
    print("✅ VERIFIED - All calculations are CORRECT!")
else:
    print("❌ ERROR - Calculations don't match!")

print()

# Calculate and verify stats
total_return = ((final_equity - 1000) / 1000) * 100
max_dd = df['drawdown_pct'].min()
rr_ratio = abs(total_return / max_dd)

print(f"Total Return: +{total_return:.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"R/R Ratio: {rr_ratio:.2f}x")
print()

# Find max DD trade
max_dd_idx = df['drawdown_pct'].idxmin()
max_dd_trade = df.loc[max_dd_idx]
print(f"Max DD occurred: {max_dd_trade['exit_time']}")
print(f"  Coin: {max_dd_trade['coin']}")
print(f"  Exit: {max_dd_trade['exit_reason']}")
print(f"  Equity at point: ${max_dd_trade['equity']:,.2f}")
print(f"  Peak before: ${max_dd_trade['equity'] - max_dd_trade['equity'] * (max_dd_trade['drawdown_pct']/100):,.2f}")
