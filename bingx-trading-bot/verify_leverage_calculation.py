"""
Verify Leverage Position Sizing Calculations
Shows exactly how the bot will calculate positions with 10x leverage
"""

def calculate_position_conservative(account_balance, risk_pct, entry_price, stop_loss, leverage):
    """Conservative mode - same position size, less margin"""
    risk_amount = account_balance * (risk_pct / 100.0)
    stop_distance = abs(entry_price - stop_loss)

    # Position size stays the same as 1x
    position_size = risk_amount / stop_distance

    position_value = position_size * entry_price
    margin_required = position_value / leverage
    margin_saved = position_value - margin_required

    # Calculate P&L at SL and TP
    sl_loss = position_size * stop_distance
    tp_distance = abs(entry_price * 1.05 - entry_price)  # Assume 5% TP
    tp_profit = position_size * tp_distance

    return {
        'position_size': position_size,
        'position_value': position_value,
        'margin_required': margin_required,
        'margin_saved': margin_saved,
        'sl_loss': sl_loss,
        'sl_loss_pct': (sl_loss / account_balance) * 100,
        'tp_profit': tp_profit,
        'tp_profit_pct': (tp_profit / account_balance) * 100
    }

def calculate_position_aggressive(account_balance, risk_pct, entry_price, stop_loss, leverage):
    """Aggressive mode - position size multiplied by leverage"""
    risk_amount = account_balance * (risk_pct / 100.0)
    stop_distance = abs(entry_price - stop_loss)

    # Base position size
    base_position_size = risk_amount / stop_distance

    # Multiply by leverage
    position_size = base_position_size * leverage

    position_value = position_size * entry_price
    margin_required = position_value / leverage

    # Calculate P&L at SL and TP
    sl_loss = position_size * stop_distance
    tp_distance = abs(entry_price * 1.05 - entry_price)  # Assume 5% TP
    tp_profit = position_size * tp_distance

    return {
        'position_size': position_size,
        'position_value': position_value,
        'margin_required': margin_required,
        'sl_loss': sl_loss,
        'sl_loss_pct': (sl_loss / account_balance) * 100,
        'tp_profit': tp_profit,
        'tp_profit_pct': (tp_profit / account_balance) * 100
    }

def print_comparison():
    """Print side-by-side comparison of both modes"""

    # Example scenario
    account_balance = 100  # USDT
    risk_pct = 1.0  # 1% risk per trade
    entry_price = 0.40  # FARTCOIN entry price
    stop_loss = 0.39  # Stop-loss price
    leverage = 10  # 10x leverage

    print("="*80)
    print("LEVERAGE POSITION SIZING COMPARISON")
    print("="*80)
    print(f"\nAccount Balance: ${account_balance:.2f} USDT")
    print(f"Risk Per Trade: {risk_pct}%")
    print(f"Entry Price: ${entry_price}")
    print(f"Stop-Loss: ${stop_loss}")
    print(f"Stop Distance: ${entry_price - stop_loss} ({((entry_price - stop_loss)/entry_price)*100:.1f}%)")
    print(f"Leverage: {leverage}x")
    print(f"Take-Profit (assumed): ${entry_price * 1.05} (+5%)")

    print("\n" + "="*80)
    print("1️⃣  NO LEVERAGE (1x) - Baseline")
    print("="*80)

    baseline = calculate_position_conservative(account_balance, risk_pct, entry_price, stop_loss, 1)
    print(f"Position Size: {baseline['position_size']:.2f} FARTCOIN")
    print(f"Position Value: ${baseline['position_value']:.2f}")
    print(f"Margin Required: ${baseline['margin_required']:.2f}")
    print(f"\nIF STOP-LOSS HITS:")
    print(f"  Loss: ${baseline['sl_loss']:.2f} ({baseline['sl_loss_pct']:.1f}% of account) ✓")
    print(f"\nIF TAKE-PROFIT HITS:")
    print(f"  Profit: ${baseline['tp_profit']:.2f} (+{baseline['tp_profit_pct']:.1f}% of account) ✓")

    print("\n" + "="*80)
    print("2️⃣  CONSERVATIVE MODE (10x leverage)")
    print("="*80)
    print("→ Same position size, less margin required")

    conservative = calculate_position_conservative(account_balance, risk_pct, entry_price, stop_loss, leverage)
    print(f"Position Size: {conservative['position_size']:.2f} FARTCOIN (unchanged)")
    print(f"Position Value: ${conservative['position_value']:.2f}")
    print(f"Margin Required: ${conservative['margin_required']:.2f} (90% saved!)")
    print(f"Margin Saved: ${conservative['margin_saved']:.2f} (available for other positions)")
    print(f"\nIF STOP-LOSS HITS:")
    print(f"  Loss: ${conservative['sl_loss']:.2f} ({conservative['sl_loss_pct']:.1f}% of account) ✓")
    print(f"\nIF TAKE-PROFIT HITS:")
    print(f"  Profit: ${conservative['tp_profit']:.2f} (+{conservative['tp_profit_pct']:.1f}% of account) ✓")
    print(f"\n💡 Result: Same risk/reward as 1x, but can run {leverage}x more positions!")

    print("\n" + "="*80)
    print("3️⃣  AGGRESSIVE MODE (10x leverage) ⚡")
    print("="*80)
    print("→ Position size multiplied by 10x")

    aggressive = calculate_position_aggressive(account_balance, risk_pct, entry_price, stop_loss, leverage)
    print(f"Position Size: {aggressive['position_size']:.2f} FARTCOIN (10x larger!) 🚀")
    print(f"Position Value: ${aggressive['position_value']:.2f}")
    print(f"Margin Required: ${aggressive['margin_required']:.2f}")
    print(f"\nIF STOP-LOSS HITS:")
    print(f"  Loss: ${aggressive['sl_loss']:.2f} ({aggressive['sl_loss_pct']:.1f}% of account) ⚠️")
    print(f"\nIF TAKE-PROFIT HITS:")
    print(f"  Profit: ${aggressive['tp_profit']:.2f} (+{aggressive['tp_profit_pct']:.1f}% of account) 🚀")
    print(f"\n⚡ Result: {leverage}x faster profits AND losses!")

    print("\n" + "="*80)
    print("DRAWDOWN COMPARISON")
    print("="*80)

    print("\nYour backtest showed 1-2% max drawdown...")
    print(f"\nWith CONSERVATIVE mode:")
    print(f"  Expected drawdown: 1-2% (same as backtest) ✓")
    print(f"  After 3 losses: {conservative['sl_loss_pct'] * 3:.1f}% ✓")

    print(f"\nWith AGGRESSIVE mode:")
    print(f"  Expected drawdown: {baseline['sl_loss_pct'] * leverage:.0f}% (10x backtest) ⚠️")
    print(f"  After 3 losses: {aggressive['sl_loss_pct'] * 3:.1f}% 💥")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    print(f"\n✅ For ${account_balance} account:")
    print("  → Start with CONSERVATIVE mode")
    print("  → Verify execution works correctly")
    print("  → Then switch to AGGRESSIVE if you want faster gains")

    print(f"\n✅ For $1000+ account:")
    print("  → AGGRESSIVE mode is more manageable")
    print("  → 10% loss = $100 (less psychologically difficult)")

    print("\n" + "="*80)
    print("CURRENT BOT CONFIGURATION")
    print("="*80)
    print("\nconfig.yaml:")
    print("  default_leverage: 10")
    print("  leverage_mode: 'aggressive'  ← Currently set to AGGRESSIVE")
    print("\nTo change to conservative:")
    print("  leverage_mode: 'conservative'")

    print("\n" + "="*80)

if __name__ == "__main__":
    print_comparison()

    print("\n\n💡 Want to test with different values?")
    print("Edit this script and change:")
    print("  - account_balance (line 65)")
    print("  - risk_pct (line 66)")
    print("  - entry_price (line 67)")
    print("  - stop_loss (line 68)")
    print("  - leverage (line 69)")
    print("\nThen run: python verify_leverage_calculation.py")
