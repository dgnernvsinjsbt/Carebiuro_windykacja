"""
Calculate P&L for Strategies with 10x Leverage and Fees
Shows realistic profit/loss expectations including BingX trading fees
"""

def calculate_pnl_with_leverage_and_fees(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_atr_mult: float,
    target_atr_mult: float,
    atr: float,
    leverage: int = 10,
    taker_fee_pct: float = 0.005
):
    """
    Calculate P&L with leverage and fees

    Args:
        account_balance: Account size in USDT
        risk_pct: Risk per trade (e.g., 1.0 = 1%)
        entry_price: Entry price
        stop_atr_mult: Stop-loss ATR multiplier
        target_atr_mult: Take-profit ATR multiplier
        atr: Average True Range value
        leverage: Leverage multiplier
        taker_fee_pct: Taker fee percentage (0.005 = 0.005%)

    Returns:
        Dict with P&L calculations
    """
    # Calculate stop loss and take profit distances
    stop_distance = atr * stop_atr_mult
    target_distance = atr * target_atr_mult

    # Calculate prices
    stop_loss = entry_price - stop_distance
    take_profit = entry_price + target_distance

    # Calculate risk amount
    risk_amount = account_balance * (risk_pct / 100.0)

    # Base position size (1x)
    base_position_size = risk_amount / stop_distance

    # Leveraged position size (10x aggressive)
    position_size = base_position_size * leverage

    # Position value
    position_value = position_size * entry_price

    # Margin required
    margin_required = position_value / leverage

    # Calculate fees (on position value, not margin)
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

    # Risk:Reward ratio (net)
    risk_reward_ratio = tp_net_profit / sl_net_loss if sl_net_loss > 0 else 0

    return {
        'position_size': position_size,
        'position_value': position_value,
        'margin_required': margin_required,
        'margin_pct': (margin_required / account_balance) * 100,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'stop_distance': stop_distance,
        'target_distance': target_distance,
        'entry_fee': entry_fee,
        'exit_fee': exit_fee,
        'total_fees': total_fees,
        'fees_pct_of_account': (total_fees / account_balance) * 100,
        'sl_gross_loss': sl_gross_loss,
        'sl_net_loss': sl_net_loss,
        'sl_net_loss_pct': sl_net_loss_pct,
        'tp_gross_profit': tp_gross_profit,
        'tp_net_profit': tp_net_profit,
        'tp_net_profit_pct': tp_net_profit_pct,
        'risk_reward_ratio': risk_reward_ratio
    }


def print_strategy_analysis(strategy_name: str, config: dict):
    """Print detailed P&L analysis for a strategy"""

    print("="*80)
    print(f"STRATEGY: {strategy_name}")
    print("="*80)

    result = calculate_pnl_with_leverage_and_fees(
        account_balance=config['account_balance'],
        risk_pct=config['risk_pct'],
        entry_price=config['entry_price'],
        stop_atr_mult=config['stop_atr_mult'],
        target_atr_mult=config['target_atr_mult'],
        atr=config['atr'],
        leverage=config['leverage']
    )

    print(f"\nAccount: ${config['account_balance']:.2f} USDT")
    print(f"Risk per trade: {config['risk_pct']}%")
    print(f"Leverage: {config['leverage']}x AGGRESSIVE")
    print(f"Entry price: ${result['entry_price']:.4f}")
    print(f"ATR: ${config['atr']:.4f}")

    print(f"\n{'POSITION SIZING':^80}")
    print("-"*80)
    print(f"Position size: {result['position_size']:.2f} coins")
    print(f"Position value: ${result['position_value']:.2f}")
    print(f"Margin required: ${result['margin_required']:.2f} ({result['margin_pct']:.1f}% of account)")

    print(f"\n{'FEES (0.005% taker fee on entry + exit)':^80}")
    print("-"*80)
    print(f"Entry fee: ${result['entry_fee']:.4f}")
    print(f"Exit fee: ${result['exit_fee']:.4f}")
    print(f"Total fees: ${result['total_fees']:.4f} ({result['fees_pct_of_account']:.3f}% of account)")

    print(f"\n{'STOP LOSS SCENARIO':^80}")
    print("-"*80)
    print(f"Stop-Loss price: ${result['stop_loss']:.4f}")
    print(f"Stop distance: ${result['stop_distance']:.4f} ({config['stop_atr_mult']}x ATR)")
    print(f"Gross loss: ${result['sl_gross_loss']:.2f}")
    print(f"Fees: ${result['total_fees']:.4f}")
    print(f"NET LOSS: ${result['sl_net_loss']:.2f} ({result['sl_net_loss_pct']:.2f}% of account)")

    print(f"\n{'TAKE PROFIT SCENARIO':^80}")
    print("-"*80)
    print(f"Take-Profit price: ${result['take_profit']:.4f}")
    print(f"Target distance: ${result['target_distance']:.4f} ({config['target_atr_mult']}x ATR)")
    print(f"Gross profit: ${result['tp_gross_profit']:.2f}")
    print(f"Fees: ${result['total_fees']:.4f}")
    print(f"NET PROFIT: ${result['tp_net_profit']:.2f} (+{result['tp_net_profit_pct']:.2f}% of account)")

    print(f"\n{'RISK:REWARD ANALYSIS':^80}")
    print("-"*80)
    print(f"Net Risk:Reward Ratio: 1:{result['risk_reward_ratio']:.2f}")

    # Calculate break-even win rate
    win_rate_breakeven = (result['sl_net_loss'] / (result['sl_net_loss'] + result['tp_net_profit'])) * 100
    print(f"Break-even win rate: {win_rate_breakeven:.1f}%")

    # Expected value with different win rates
    print(f"\n{'EXPECTED VALUE BY WIN RATE':^80}")
    print("-"*80)

    for win_rate in [50, 60, 70, 80, 90]:
        loss_rate = 100 - win_rate
        expected_value = (
            (win_rate / 100) * result['tp_net_profit'] -
            (loss_rate / 100) * result['sl_net_loss']
        )
        ev_pct = (expected_value / config['account_balance']) * 100
        print(f"  {win_rate}% win rate: ${expected_value:+.2f} per trade ({ev_pct:+.2f}% of account)")

    return result


def compare_strategies():
    """Compare both strategies side-by-side"""

    # Common parameters
    account_balance = 100.0  # $100 USDT account
    risk_pct = 1.0  # 1% risk per trade
    leverage = 10  # 10x aggressive

    # Typical FARTCOIN parameters (from recent data)
    entry_price = 0.38  # Current FARTCOIN price
    atr = 0.01  # Typical ATR (adjust based on market)

    print("\n" + "="*80)
    print("LEVERAGE P&L CALCULATOR - WITH FEES")
    print("="*80)
    print(f"\nBingX Taker Fee: 0.005% (both entry and exit)")
    print(f"Leverage: 10x AGGRESSIVE (position size × 10)")
    print(f"Account: ${account_balance:.2f} USDT")
    print(f"Risk per trade: {risk_pct}%")
    print(f"\n")

    # Strategy 1: Multi-Timeframe Long
    long_config = {
        'account_balance': account_balance,
        'risk_pct': risk_pct,
        'entry_price': entry_price,
        'stop_atr_mult': 3.0,  # From config
        'target_atr_mult': 12.0,  # From config
        'atr': atr,
        'leverage': leverage
    }

    long_result = print_strategy_analysis('Multi-Timeframe Long', long_config)

    print("\n\n")

    # Strategy 2: Trend Distance Short
    short_config = {
        'account_balance': account_balance,
        'risk_pct': risk_pct,
        'entry_price': entry_price,
        'stop_atr_mult': 3.0,  # From config
        'target_atr_mult': 15.0,  # From config (higher target)
        'atr': atr,
        'leverage': leverage
    }

    short_result = print_strategy_analysis('Trend Distance Short', short_config)

    # Side-by-side comparison
    print("\n\n")
    print("="*80)
    print("SIDE-BY-SIDE COMPARISON")
    print("="*80)

    print(f"\n{'Metric':<40} {'Long Strategy':<20} {'Short Strategy':<20}")
    print("-"*80)
    print(f"{'Stop-loss (ATR mult)':<40} {long_config['stop_atr_mult']:<20} {short_config['stop_atr_mult']:<20}")
    print(f"{'Take-profit (ATR mult)':<40} {long_config['target_atr_mult']:<20} {short_config['target_atr_mult']:<20}")
    print(f"{'Position size (coins)':<40} {long_result['position_size']:<20.2f} {short_result['position_size']:<20.2f}")
    print(f"{'Margin required ($)':<40} ${long_result['margin_required']:<19.2f} ${short_result['margin_required']:<19.2f}")
    print(f"{'Total fees ($)':<40} ${long_result['total_fees']:<19.4f} ${short_result['total_fees']:<19.4f}")
    print(f"{'Net loss if SL hits ($)':<40} ${long_result['sl_net_loss']:<19.2f} ${short_result['sl_net_loss']:<19.2f}")
    print(f"{'Net loss if SL hits (%)':<40} {long_result['sl_net_loss_pct']:<19.2f}% {short_result['sl_net_loss_pct']:<19.2f}%")
    print(f"{'Net profit if TP hits ($)':<40} ${long_result['tp_net_profit']:<19.2f} ${short_result['tp_net_profit']:<19.2f}")
    print(f"{'Net profit if TP hits (%)':<40} {long_result['tp_net_profit_pct']:<19.2f}% {short_result['tp_net_profit_pct']:<19.2f}%")
    print(f"{'Risk:Reward ratio':<40} 1:{long_result['risk_reward_ratio']:<18.2f} 1:{short_result['risk_reward_ratio']:<18.2f}")

    # Calculate how fees impact the risk
    print("\n")
    print("="*80)
    print("FEES IMPACT ANALYSIS")
    print("="*80)

    # Without fees (theoretical)
    long_sl_without_fees = long_result['sl_gross_loss']
    long_tp_without_fees = long_result['tp_gross_profit']
    long_rr_without_fees = long_tp_without_fees / long_sl_without_fees

    short_sl_without_fees = short_result['sl_gross_loss']
    short_tp_without_fees = short_result['tp_gross_profit']
    short_rr_without_fees = short_tp_without_fees / short_sl_without_fees

    print(f"\nMulti-Timeframe Long:")
    print(f"  Without fees - R:R = 1:{long_rr_without_fees:.2f}")
    print(f"  With fees    - R:R = 1:{long_result['risk_reward_ratio']:.2f}")
    print(f"  Fee impact: {((long_rr_without_fees - long_result['risk_reward_ratio']) / long_rr_without_fees * 100):.2f}% reduction")

    print(f"\nTrend Distance Short:")
    print(f"  Without fees - R:R = 1:{short_rr_without_fees:.2f}")
    print(f"  With fees    - R:R = 1:{short_result['risk_reward_ratio']:.2f}")
    print(f"  Fee impact: {((short_rr_without_fees - short_result['risk_reward_ratio']) / short_rr_without_fees * 100):.2f}% reduction")

    print("\n")
    print("="*80)
    print("KEY INSIGHTS")
    print("="*80)

    print(f"\n1. With 10x leverage and 1% base risk:")
    print(f"   • Each loss = ~{long_result['sl_net_loss_pct']:.1f}% of account (including fees)")
    print(f"   • Each win (long) = +{long_result['tp_net_profit_pct']:.1f}% of account (after fees)")
    print(f"   • Each win (short) = +{short_result['tp_net_profit_pct']:.1f}% of account (after fees)")

    print(f"\n2. Fees eat into your profits:")
    print(f"   • ${long_result['total_fees']:.4f} per trade ({long_result['fees_pct_of_account']:.3f}% of account)")
    print(f"   • On a $100 account, that's meaningful!")

    print(f"\n3. Your backtest showed 2.5% max drawdown at 1x:")
    print(f"   • With 10x leverage: expect ~{2.5 * 10:.1f}% max drawdown")
    print(f"   • After 3 consecutive losses: ~{long_result['sl_net_loss_pct'] * 3:.1f}%")

    print(f"\n4. To be profitable, you need:")
    print(f"   • Long strategy: >{(long_result['sl_net_loss'] / (long_result['sl_net_loss'] + long_result['tp_net_profit']) * 100):.1f}% win rate")
    print(f"   • Short strategy: >{(short_result['sl_net_loss'] / (short_result['sl_net_loss'] + short_result['tp_net_profit']) * 100):.1f}% win rate")

    print(f"\n5. If your backtest win rate is 80%:")
    long_80_ev = (0.8 * long_result['tp_net_profit'] - 0.2 * long_result['sl_net_loss'])
    short_80_ev = (0.8 * short_result['tp_net_profit'] - 0.2 * short_result['sl_net_loss'])
    print(f"   • Long: ${long_80_ev:+.2f} per trade ({(long_80_ev/account_balance*100):+.2f}% per trade)")
    print(f"   • Short: ${short_80_ev:+.2f} per trade ({(short_80_ev/account_balance*100):+.2f}% per trade)")
    print(f"   • 10 trades at 80% win rate: ${long_80_ev * 10:+.2f} ({(long_80_ev*10/account_balance*100):+.2f}%)")


if __name__ == "__main__":
    compare_strategies()

    print("\n\n")
    print("="*80)
    print("NOTES")
    print("="*80)
    print("""
1. These calculations assume:
   • 10x AGGRESSIVE leverage (position size × 10)
   • BingX taker fee: 0.005% on entry + 0.005% on exit
   • Market orders (instant fill)
   • No slippage

2. Actual results will vary based on:
   • Real ATR values (adjust 'atr' parameter in script)
   • Market volatility
   • Execution timing
   • Slippage on large orders

3. To recalculate with different parameters:
   • Edit line 175-177 (account_balance, risk_pct, leverage)
   • Edit line 180-181 (entry_price, atr)
   • Run: python calculate_leverage_pnl.py
    """)
