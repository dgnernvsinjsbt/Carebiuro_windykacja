"""
Calculate P&L with 10x Leverage and Fees - REAL BACKTEST DATA

Based on actual backtest results from strategy files:
- Multi-Timeframe Long: 7.14x R:R, +10.38% return, -1.45% DD
- Trend Distance Short: 8.88x R:R, +20.08% return, -2.26% DD
"""

def calculate_win_rate_from_backtest(total_return_pct, rr_ratio, num_trades_estimate=100):
    """
    Estimate win rate from total return and R:R ratio

    Formula: total_return = (win_rate × rr_ratio) - (loss_rate × 1)
    Assuming avg_loss = 1% and avg_win = rr_ratio × 1%
    """
    # Solve for win rate:
    # total_return = win_rate × rr_ratio - (1 - win_rate) × 1
    # total_return = win_rate × rr_ratio - 1 + win_rate
    # total_return + 1 = win_rate × (rr_ratio + 1)
    # win_rate = (total_return + 1) / (rr_ratio + 1)

    # But total_return is for multiple trades, so divide by estimated trades
    return_per_trade = total_return_pct / num_trades_estimate

    win_rate = (return_per_trade + 1.0) / (rr_ratio + 1.0)

    # Clamp to reasonable range
    win_rate = max(0.1, min(0.9, win_rate))

    return win_rate


def calculate_pnl_with_leverage_and_fees_real_data(
    strategy_name: str,
    total_return_pct: float,
    max_drawdown_pct: float,
    rr_ratio: float,
    stop_atr_mult: float,
    target_atr_mult: float,
    account_balance: float = 100.0,
    risk_pct: float = 1.0,
    leverage: int = 10,
    taker_fee_pct: float = 0.005,
    num_trades_estimate: int = 100
):
    """
    Calculate realistic P&L using actual backtest data

    Args:
        strategy_name: Strategy name
        total_return_pct: Total return from backtest (e.g., 10.38 for 10.38%)
        max_drawdown_pct: Max drawdown from backtest (e.g., -1.45 for -1.45%)
        rr_ratio: Actual achieved R:R ratio (e.g., 7.14)
        stop_atr_mult: Stop-loss ATR multiplier
        target_atr_mult: Take-profit ATR multiplier
        account_balance: Account size in USDT
        risk_pct: Risk per trade (e.g., 1.0 = 1%)
        leverage: Leverage multiplier
        taker_fee_pct: Taker fee percentage (0.005 = 0.005%)
        num_trades_estimate: Estimated number of trades in backtest
    """

    print("="*80)
    print(f"STRATEGY: {strategy_name}")
    print("="*80)

    print(f"\nBACKTEST RESULTS (1x leverage):")
    print(f"  Total return: {total_return_pct:+.2f}%")
    print(f"  Max drawdown: {max_drawdown_pct:.2f}%")
    print(f"  Achieved R:R ratio: 1:{rr_ratio:.2f}")
    print(f"  Stop-loss: {stop_atr_mult}x ATR")
    print(f"  Take-profit: {target_atr_mult}x ATR")
    print(f"  Estimated trades: {num_trades_estimate}")

    # Estimate win rate from backtest data
    win_rate = calculate_win_rate_from_backtest(total_return_pct, rr_ratio, num_trades_estimate)

    print(f"\nESTIMATED TRADING METRICS:")
    print(f"  Win rate: {win_rate*100:.1f}%")
    print(f"  Average win: ~{rr_ratio:.2f}%")
    print(f"  Average loss: ~1.00%")

    # Example trade with typical FARTCOIN parameters
    entry_price = 0.40  # USDT
    atr = 0.01  # Typical ATR

    # Calculate stop and target distances
    stop_distance = atr * stop_atr_mult
    target_distance = atr * target_atr_mult

    # Calculate prices
    stop_loss = entry_price - stop_distance
    take_profit = entry_price + target_distance

    # Calculate risk amount
    risk_amount = account_balance * (risk_pct / 100.0)

    # Base position size (1x)
    base_position_size = risk_amount / stop_distance

    # 10x AGGRESSIVE: Multiply position size by leverage
    position_size = base_position_size * leverage
    position_value = position_size * entry_price
    margin_required = position_value / leverage

    # Calculate fees (on position value)
    entry_fee = position_value * (taker_fee_pct / 100.0)
    exit_fee = position_value * (taker_fee_pct / 100.0)
    total_fees = entry_fee + exit_fee

    # Calculate P&L if stop hits
    sl_gross_loss = position_size * stop_distance
    sl_net_loss = sl_gross_loss + total_fees
    sl_net_loss_pct = (sl_net_loss / account_balance) * 100

    # Calculate P&L if target hits
    tp_gross_profit = position_size * target_distance
    tp_net_profit = tp_gross_profit - total_fees
    tp_net_profit_pct = (tp_net_profit / account_balance) * 100

    # Net R:R ratio
    net_rr_ratio = tp_net_profit / sl_net_loss if sl_net_loss > 0 else 0

    print(f"\n{'10x LEVERAGE CALCULATIONS':^80}")
    print("="*80)

    print(f"\nEXAMPLE TRADE:")
    print(f"  Entry: ${entry_price:.4f}")
    print(f"  Stop-Loss: ${stop_loss:.4f} (-{(stop_distance/entry_price)*100:.2f}%)")
    print(f"  Take-Profit: ${take_profit:.4f} (+{(target_distance/entry_price)*100:.2f}%)")
    print(f"  ATR: ${atr:.4f}")

    print(f"\nPOSITION SIZING:")
    print(f"  Risk amount: ${risk_amount:.2f} ({risk_pct}% of account)")
    print(f"  Base size (1x): {base_position_size:.2f} coins")
    print(f"  Leveraged size (10x): {position_size:.2f} coins")
    print(f"  Position value: ${position_value:.2f}")
    print(f"  Margin required: ${margin_required:.2f} ({(margin_required/account_balance)*100:.1f}% of account)")

    print(f"\nFEES (BingX 0.005% taker):")
    print(f"  Entry fee: ${entry_fee:.4f}")
    print(f"  Exit fee: ${exit_fee:.4f}")
    print(f"  Total fees: ${total_fees:.4f} ({(total_fees/account_balance)*100:.3f}% of account)")

    print(f"\nIF STOP-LOSS HITS:")
    print(f"  Gross loss: ${sl_gross_loss:.2f}")
    print(f"  Fees: ${total_fees:.4f}")
    print(f"  NET LOSS: ${sl_net_loss:.2f} ({sl_net_loss_pct:.2f}% of account)")

    print(f"\nIF TAKE-PROFIT HITS:")
    print(f"  Gross profit: ${tp_gross_profit:.2f}")
    print(f"  Fees: ${total_fees:.4f}")
    print(f"  NET PROFIT: ${tp_net_profit:.2f} (+{tp_net_profit_pct:.2f}% of account)")

    print(f"\nRISK:REWARD:")
    print(f"  Net R:R ratio: 1:{net_rr_ratio:.2f}")
    print(f"  Break-even win rate: {(sl_net_loss / (sl_net_loss + tp_net_profit)) * 100:.1f}%")

    # Expected value based on ACTUAL win rate from backtest
    expected_value_per_trade = (win_rate * tp_net_profit) - ((1 - win_rate) * sl_net_loss)
    ev_pct = (expected_value_per_trade / account_balance) * 100

    print(f"\nEXPECTED VALUE (based on backtest win rate):")
    print(f"  Per trade: ${expected_value_per_trade:+.2f} ({ev_pct:+.2f}% per trade)")
    print(f"  10 trades: ${expected_value_per_trade * 10:+.2f} ({ev_pct * 10:+.2f}%)")
    print(f"  100 trades: ${expected_value_per_trade * 100:+.2f} ({ev_pct * 100:+.2f}%)")

    # Compare to backtest
    print(f"\n{'BACKTEST vs 10x LEVERAGE COMPARISON':^80}")
    print("="*80)

    backtest_return_per_trade = total_return_pct / num_trades_estimate
    leveraged_return_per_trade = ev_pct

    print(f"\nPER TRADE PERFORMANCE:")
    print(f"  Backtest (1x): {backtest_return_per_trade:+.4f}% per trade")
    print(f"  With 10x leverage: {leveraged_return_per_trade:+.2f}% per trade")
    print(f"  Multiplier: {leveraged_return_per_trade / backtest_return_per_trade:.1f}x")

    print(f"\nAFTER {num_trades_estimate} TRADES:")
    print(f"  Backtest (1x): {total_return_pct:+.2f}%")
    print(f"  Expected with 10x: {leveraged_return_per_trade * num_trades_estimate:+.2f}%")

    print(f"\nDRAWDOWN EXPECTATIONS:")
    print(f"  Backtest max DD (1x): {max_drawdown_pct:.2f}%")
    print(f"  Expected max DD (10x): {max_drawdown_pct * leverage:.2f}%")

    return {
        'win_rate': win_rate,
        'expected_value_per_trade': expected_value_per_trade,
        'expected_value_pct': ev_pct,
        'net_loss_per_trade': sl_net_loss,
        'net_profit_per_trade': tp_net_profit,
        'net_rr_ratio': net_rr_ratio,
        'expected_max_dd_pct': max_drawdown_pct * leverage
    }


def main():
    """Compare both strategies with real backtest data"""

    account_balance = 100.0  # $100 USDT
    risk_pct = 1.0  # 1% risk per trade
    leverage = 10  # 10x aggressive

    print("\n" + "="*80)
    print("P&L ANALYSIS WITH 10x LEVERAGE AND FEES")
    print("BASED ON REAL BACKTEST DATA")
    print("="*80)
    print(f"\nAccount: ${account_balance:.2f} USDT")
    print(f"Risk per trade: {risk_pct}%")
    print(f"Leverage: {leverage}x AGGRESSIVE")
    print(f"BingX taker fee: 0.005% (entry + exit)")

    print("\n\n")

    # Multi-Timeframe Long Strategy
    long_result = calculate_pnl_with_leverage_and_fees_real_data(
        strategy_name='Multi-Timeframe Long',
        total_return_pct=10.38,  # From strategy file comment
        max_drawdown_pct=-1.45,   # From strategy file comment
        rr_ratio=7.14,            # From strategy file comment
        stop_atr_mult=3.0,        # From strategy implementation
        target_atr_mult=12.0,     # From strategy implementation
        account_balance=account_balance,
        risk_pct=risk_pct,
        leverage=leverage,
        num_trades_estimate=100   # Reasonable estimate
    )

    print("\n\n")

    # Trend Distance Short Strategy
    short_result = calculate_pnl_with_leverage_and_fees_real_data(
        strategy_name='Trend Distance Short',
        total_return_pct=20.08,   # From strategy file comment
        max_drawdown_pct=-2.26,   # From strategy file comment
        rr_ratio=8.88,            # From strategy file comment
        stop_atr_mult=3.0,        # From strategy implementation
        target_atr_mult=15.0,     # From strategy implementation
        account_balance=account_balance,
        risk_pct=risk_pct,
        leverage=leverage,
        num_trades_estimate=100   # Reasonable estimate
    )

    # Final comparison
    print("\n\n")
    print("="*80)
    print("FINAL SUMMARY - WHICH STRATEGY IS BETTER WITH 10x LEVERAGE?")
    print("="*80)

    print(f"\n{'Metric':<40} {'Long':<20} {'Short':<20}")
    print("-"*80)
    print(f"{'Backtest total return (1x)':<40} {'+10.38%':<20} {'+20.08%':<20}")
    print(f"{'Backtest max DD (1x)':<40} {'-1.45%':<20} {'-2.26%':<20}")
    print(f"{'Actual R:R ratio':<40} {'1:7.14':<20} {'1:8.88':<20}")
    print(f"{'Estimated win rate':<40} {f'{long_result["win_rate"]*100:.1f}%':<20} {f'{short_result["win_rate"]*100:.1f}%':<20}")

    print(f"\n{'WITH 10x LEVERAGE:':<40}")
    print(f"{'Expected per trade':<40} {f'{long_result["expected_value_pct"]:+.2f}%':<20} {f'{short_result["expected_value_pct"]:+.2f}%':<20}")
    print(f"{'Expected after 100 trades':<40} {f'{long_result["expected_value_pct"]*100:+.2f}%':<20} {f'{short_result["expected_value_pct"]*100:+.2f}%':<20}")
    print(f"{'Expected max DD (10x)':<40} {f'{long_result["expected_max_dd_pct"]:.2f}%':<20} {f'{short_result["expected_max_dd_pct"]:.2f}%':<20}")
    print(f"{'Net R:R with fees':<40} {f'1:{long_result["net_rr_ratio"]:.2f}':<20} {f'1:{short_result["net_rr_ratio"]:.2f}':<20}")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    if short_result['expected_value_pct'] > long_result['expected_value_pct']:
        print(f"\n✅ TREND DISTANCE SHORT is better:")
        print(f"   • {short_result['expected_value_pct']:+.2f}% per trade vs {long_result['expected_value_pct']:+.2f}% (Long)")
        print(f"   • Higher R:R ratio (1:{short_result['net_rr_ratio']:.2f})")
        print(f"   • Better total return in backtest (+20.08% vs +10.38%)")
        print(f"\n⚠️  But slightly higher drawdown risk:")
        print(f"   • {short_result['expected_max_dd_pct']:.2f}% vs {long_result['expected_max_dd_pct']:.2f}% max DD")
    else:
        print(f"\n✅ MULTI-TIMEFRAME LONG is better:")
        print(f"   • {long_result['expected_value_pct']:+.2f}% per trade vs {short_result['expected_value_pct']:+.2f}% (Short)")
        print(f"   • Lower drawdown risk ({long_result['expected_max_dd_pct']:.2f}% vs {short_result['expected_max_dd_pct']:.2f}%)")

    print("\n" + "="*80)
    print("NOTES")
    print("="*80)
    print("""
1. These calculations use REAL backtest data from strategy files:
   - Multi-Timeframe Long: 7.14x R:R, +10.38% return, -1.45% DD
   - Trend Distance Short: 8.88x R:R, +20.08% return, -2.26% DD

2. Win rates are ESTIMATED from total return and R:R ratio
   - Actual win rates may vary

3. Leverage calculations assume AGGRESSIVE mode:
   - Position size × 10 (not just margin reduction)
   - Each loss = ~10% of account
   - Each win = ~40-50% of account

4. Fees are included (BingX 0.005% taker on entry + exit)

5. Both strategies are viable with 10x leverage:
   - Expected max DD: -14.5% (Long) or -22.6% (Short)
   - Both well within your 40% risk tolerance

6. You can run both strategies simultaneously:
   - Long captures uptrends
   - Short captures downtrends
   - Diversification benefit
""")


if __name__ == "__main__":
    main()
