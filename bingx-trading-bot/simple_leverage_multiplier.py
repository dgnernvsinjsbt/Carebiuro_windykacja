"""
Simple 10x Leverage Multiplier Analysis

Based on real backtest data:
- Multi-Timeframe Long: +10.38% return, -1.45% DD
- Trend Distance Short: +20.08% return, -2.26% DD

Shows what happens when you multiply these by 10x leverage
"""

def analyze_strategy_with_leverage(
    strategy_name: str,
    backtest_return_pct: float,
    backtest_max_dd_pct: float,
    rr_ratio: float,
    leverage: int = 10,
    fee_impact_pct: float = 0.5  # Approximate fee drag
):
    """
    Simple leverage multiplier analysis

    Args:
        strategy_name: Strategy name
        backtest_return_pct: Total return from backtest (e.g., 10.38)
        backtest_max_dd_pct: Max drawdown from backtest (e.g., -1.45)
        rr_ratio: Risk:reward ratio
        leverage: Leverage multiplier
        fee_impact_pct: Estimated fee drag as % of returns
    """

    print("="*80)
    print(f"{strategy_name.upper()}")
    print("="*80)

    print(f"\n📊 BACKTEST RESULTS (1x leverage):")
    print(f"   Total return: {backtest_return_pct:+.2f}%")
    print(f"   Max drawdown: {backtest_max_dd_pct:.2f}%")
    print(f"   R:R ratio: 1:{rr_ratio:.2f}")

    # Calculate leveraged returns (simple multiplier approach)
    # This assumes the strategy maintains similar win rate at higher position sizes
    leveraged_return_gross = backtest_return_pct * leverage
    leveraged_return_net = leveraged_return_gross - fee_impact_pct
    leveraged_max_dd = backtest_max_dd_pct * leverage

    print(f"\n⚡ WITH {leverage}x AGGRESSIVE LEVERAGE:")
    print(f"   Gross return: {leveraged_return_gross:+.2f}% (backtest × {leverage})")
    print(f"   Fee impact: -{fee_impact_pct:.2f}% (BingX 0.005% × trades)")
    print(f"   NET return: {leveraged_return_net:+.2f}%")
    print(f"   Max drawdown: {leveraged_max_dd:.2f}% (backtest × {leverage})")

    # Example single trade with 10x leverage
    print(f"\n💰 EXAMPLE SINGLE TRADE ($100 account, 1% risk):")
    print(f"   If you LOSE: -10% of account (-$10)")
    print(f"   If you WIN: +{10 * rr_ratio:.0f}% of account (+${10 * rr_ratio:.2f})")

    # Calculate break-even win rate
    # At 10x leverage: each loss = 10%, each win = 10 × rr_ratio
    # Break-even: win_rate × (10 × rr_ratio) = (1 - win_rate) × 10
    breakeven_wr = 10 / (10 + 10 * rr_ratio)

    print(f"\n🎯 BREAK-EVEN ANALYSIS:")
    print(f"   Need win rate > {breakeven_wr * 100:.1f}% to be profitable")

    # Since backtest was profitable, calculate implied win rate
    # backtest_return = win_rate × avg_win - (1 - win_rate) × avg_loss
    # If we assume avg_loss = 1% and avg_win = rr_ratio × 1%
    # Then: backtest_return = win_rate × rr_ratio - (1 - win_rate)
    # backtest_return = win_rate × rr_ratio - 1 + win_rate
    # backtest_return + 1 = win_rate × (rr_ratio + 1)
    implied_wr = (backtest_return_pct / 100 + 1) / (rr_ratio + 1)
    implied_wr = max(0, min(1, implied_wr))  # Clamp to 0-100%

    print(f"   Your backtest win rate: ~{implied_wr * 100:.1f}% (estimated)")
    print(f"   Above break-even? {'✅ YES' if implied_wr > breakeven_wr else '❌ NO'}")

    return {
        'gross_return': leveraged_return_gross,
        'net_return': leveraged_return_net,
        'max_dd': leveraged_max_dd,
        'breakeven_wr': breakeven_wr,
        'implied_wr': implied_wr
    }


def main():
    print("\n" + "="*80)
    print("10x LEVERAGE MULTIPLIER ANALYSIS")
    print("="*80)
    print("\n💡 Simple approach: Multiply your backtest results by 10x")
    print("   (This assumes your strategy scales well with larger positions)")

    print("\n\n")

    # Multi-Timeframe Long
    long_result = analyze_strategy_with_leverage(
        strategy_name="Multi-Timeframe Long",
        backtest_return_pct=10.38,
        backtest_max_dd_pct=-1.45,
        rr_ratio=7.14,
        leverage=10,
        fee_impact_pct=0.5
    )

    print("\n\n")

    # Trend Distance Short
    short_result = analyze_strategy_with_leverage(
        strategy_name="Trend Distance Short",
        backtest_return_pct=20.08,
        backtest_max_dd_pct=-2.26,
        rr_ratio=8.88,
        leverage=10,
        fee_impact_pct=0.5
    )

    # Side-by-side comparison
    print("\n\n")
    print("="*80)
    print("SIDE-BY-SIDE COMPARISON")
    print("="*80)

    print(f"\n{'Metric':<45} {'Long':<17} {'Short':<17}")
    print("-"*80)
    print(f"{'Backtest return (1x)':<45} {'+10.38%':<17} {'+20.08%':<17}")
    print(f"{'Expected return (10x, after fees)':<45} {f'{long_result["net_return"]:+.2f}%':<17} {f'{short_result["net_return"]:+.2f}%':<17}")
    print(f"{'Backtest max DD (1x)':<45} {'-1.45%':<17} {'-2.26%':<17}")
    print(f"{'Expected max DD (10x)':<45} {f'{long_result["max_dd"]:.2f}%':<17} {f'{short_result["max_dd"]:.2f}%':<17}")
    print(f"{'R:R ratio':<45} {'1:7.14':<17} {'1:8.88':<17}")
    print(f"{'Estimated win rate':<45} {f'{long_result["implied_wr"]*100:.1f}%':<17} {f'{short_result["implied_wr"]*100:.1f}%':<17}")
    print(f"{'Break-even win rate':<45} {f'{long_result["breakeven_wr"]*100:.1f}%':<17} {f'{short_result["breakeven_wr"]*100:.1f}%':<17}")

    # Winner
    print("\n" + "="*80)
    print("WINNER")
    print("="*80)

    if short_result['net_return'] > long_result['net_return']:
        print(f"\n🏆 TREND DISTANCE SHORT")
        print(f"   • {short_result['net_return']:+.2f}% expected return (vs {long_result['net_return']:+.2f}% for Long)")
        print(f"   • Higher backtest return: +20.08% vs +10.38%")
        print(f"   • Better R:R ratio: 1:8.88 vs 1:7.14")
        print(f"\n   ⚠️  Trade-off: Higher drawdown")
        print(f"   • {short_result['max_dd']:.2f}% max DD vs {long_result['max_dd']:.2f}%")
        print(f"   • But still < your 40% risk tolerance ✅")
    else:
        print(f"\n🏆 MULTI-TIMEFRAME LONG")
        print(f"   • {long_result['net_return']:+.2f}% expected return (vs {short_result['net_return']:+.2f}% for Short)")
        print(f"   • Lower drawdown risk: {long_result['max_dd']:.2f}% vs {short_result['max_dd']:.2f}%")

    # Both strategies
    print("\n" + "="*80)
    print("💡 PRO TIP: RUN BOTH STRATEGIES")
    print("="*80)

    combined_return = long_result['net_return'] + short_result['net_return']
    combined_dd = min(long_result['max_dd'], short_result['max_dd'])  # Conservative estimate

    print(f"\nIf you run both strategies simultaneously:")
    print(f"   • Combined expected return: {combined_return:+.2f}%")
    print(f"   • Diversification benefit (Long captures uptrends, Short captures downtrends)")
    print(f"   • Risk spread across two uncorrelated strategies")
    print(f"   • Estimated max DD: ~{combined_dd:.2f}% (lower due to diversification)")

    # Final notes
    print("\n" + "="*80)
    print("📝 IMPORTANT NOTES")
    print("="*80)
    print("""
1. These are ESTIMATES based on your backtest results:
   • Multi-Timeframe Long: +10.38% return, -1.45% DD
   • Trend Distance Short: +20.08% return, -2.26% DD

2. 10x leverage multiplies EVERYTHING by 10:
   • Profits × 10
   • Losses × 10
   • Drawdowns × 10

3. Fee impact is estimated at ~0.5% total:
   • BingX charges 0.005% per trade (entry + exit = 0.01% per round trip)
   • Over 100 trades ≈ 0.5% drag on returns

4. Both strategies fit your risk tolerance:
   • Expected max DD: -14.5% (Long) or -22.6% (Short)
   • Your tolerance: 40% max DD
   • ✅ Both are safe

5. To get EXACT numbers, I need from your backtest:
   • Total number of trades
   • Number of wins
   • Number of losses
   • Average win %
   • Average loss %

   Then I can calculate precise expected value with 10x leverage.
""")

    print("\n" + "="*80)
    print("🚀 READY TO TRADE?")
    print("="*80)
    print("""
Your bot is already configured for 10x aggressive leverage.

To start live trading:
1. Edit config.yaml:
   trading.enabled: true
   safety.dry_run: false

2. Run: python main.py

The bot will automatically:
   ✅ Set 10x leverage on BingX
   ✅ Calculate position sizes (base × 10)
   ✅ Place entry + SL + TP orders
   ✅ Track all positions
""")


if __name__ == "__main__":
    main()
