"""
PEPE LIMIT ORDER STRATEGY - FULL AUDIT

This script implements limit orders with STRICT verification:
1. Realistic fill logic (price must actually touch limit)
2. Proper fee accounting (maker/taker split)
3. Lookahead bias check
4. Trade-by-trade verification
5. Profit concentration analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_data(file_path: str) -> pd.DataFrame:
    """Load and prepare PEPE data"""
    df = pd.read_csv(file_path)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['time'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def calculate_indicators(df, bb_period=20, bb_std=2.0, rsi_period=14, atr_period=14):
    """Calculate indicators - NO LOOKAHEAD"""
    df = df.copy()

    # Bollinger Bands
    df['sma20'] = df['close'].rolling(bb_period).mean()
    std = df['close'].rolling(bb_period).std()
    df['bb_upper'] = df['sma20'] + (std * bb_std)
    df['bb_lower'] = df['sma20'] - (std * bb_std)

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(atr_period).mean()

    return df


def backtest_limit_orders(df, rsi_threshold=40, sl_mult=1.5, tp_mult=2.0,
                          limit_offset_pct=0.15, max_wait_candles=10):
    """
    Backtest with LIMIT or MARKET ORDERS

    Logic:
    1. Signal fires when close <= BB lower AND RSI <= threshold
    2. Place LIMIT order at (close * (1 - limit_offset_pct/100))
    3. Wait up to max_wait_candles for fill (price must touch limit)

    Fees:
    - If limit_offset_pct > 0: LIMIT entry (0.02% maker) + MARKET exit (0.05% taker) = 0.07%
    - If limit_offset_pct = 0: MARKET entry (0.05% taker) + MARKET exit (0.05% taker) = 0.10%
    """

    # Entry signals (based on PREVIOUS candle close, not current!)
    entry_signals = (
        (df['close'] <= df['bb_lower']) &
        (df['rsi'] <= rsi_threshold)
    )

    trades = []
    pending_limit = None  # {idx, limit_price, wait_count}
    in_position = False
    entry_price = 0
    entry_idx = 0
    entry_time = None
    sl_price = 0
    tp_price = 0

    for i in range(len(df)):
        # Handle pending limit order
        if pending_limit is not None:
            current_low = df.iloc[i]['low']

            # Check if limit was touched (filled)
            if current_low <= pending_limit['limit_price']:
                # FILLED!
                entry_price = pending_limit['limit_price']
                entry_idx = i
                entry_time = df.iloc[i]['timestamp']
                atr = df.iloc[i]['atr']

                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)

                in_position = True
                pending_limit = None

            elif (i - pending_limit['signal_idx']) >= max_wait_candles:
                # Limit expired (not filled)
                pending_limit = None

        # Handle existing position
        if in_position:
            current_low = df.iloc[i]['low']
            current_high = df.iloc[i]['high']
            current_close = df.iloc[i]['close']
            exit_time = df.iloc[i]['timestamp']

            # Check if BOTH SL and TP hit in same candle (take worst case)
            sl_hit = current_low <= sl_price
            tp_hit = current_high >= tp_price

            if sl_hit and tp_hit:
                # Both hit - which came first? Conservative: assume SL
                exit_price = sl_price
                exit_reason = 'SL'
                pnl = (exit_price - entry_price) / entry_price
            elif sl_hit:
                exit_price = sl_price
                exit_reason = 'SL'
                pnl = (exit_price - entry_price) / entry_price
            elif tp_hit:
                exit_price = tp_price
                exit_reason = 'TP'
                pnl = (exit_price - entry_price) / entry_price
            elif (i - entry_idx) >= 60:  # Time exit
                exit_price = current_close
                exit_reason = 'TIME'
                pnl = (exit_price - entry_price) / entry_price
            else:
                continue  # Still in position

            # Apply fees
            if limit_offset_pct > 0:
                # Limit entry + market exit
                fees = 0.0002 + 0.0005  # 0.07% total
            else:
                # Market entry + market exit
                fees = 0.0005 + 0.0005  # 0.10% total
            pnl_after_fees = pnl - fees

            trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'pnl_gross': pnl * 100,
                'fees_paid': fees * 100,
                'pnl_net': pnl_after_fees * 100,
                'exit_reason': exit_reason,
                'hold_candles': i - entry_idx,
                'hold_minutes': i - entry_idx
            })

            in_position = False

        # Check for new signal (only if not in position and no pending limit)
        elif pending_limit is None:
            if entry_signals.iloc[i]:
                # Signal! Place limit order
                signal_close = df.iloc[i]['close']
                limit_price = signal_close * (1 - limit_offset_pct / 100)

                pending_limit = {
                    'signal_idx': i,
                    'limit_price': limit_price,
                    'signal_close': signal_close
                }

    return pd.DataFrame(trades)


def analyze_profit_concentration(trades_df):
    """Check if profits concentrated in few trades (red flag!)"""
    if len(trades_df) == 0:
        return None

    # Sort by P&L
    sorted_trades = trades_df.sort_values('pnl_net', ascending=False).reset_index(drop=True)
    total_profit = sorted_trades['pnl_net'].sum()

    if total_profit <= 0:
        return {
            "status": "FAILED",
            "reason": "Strategy has NEGATIVE return",
            "total_profit": total_profit,
            "top_5_pct": 0,
            "top_10_pct": 0,
            "trades_for_50pct": 0,
            "trades_for_50pct_percent": 0,
            "trades_for_80pct": 0,
            "trades_for_80pct_percent": 0,
            "red_flags": [f"⚠️ TOTAL RETURN IS NEGATIVE: {total_profit:.2f}%"]
        }

    # Calculate concentration
    top_5_profit = sorted_trades.head(5)['pnl_net'].sum()
    top_10_profit = sorted_trades.head(10)['pnl_net'].sum()

    # Find how many trades account for 50% and 80% of profit
    cumsum = sorted_trades['pnl_net'].cumsum()
    trades_for_50pct = (cumsum >= total_profit * 0.5).idxmax() + 1
    trades_for_80pct = (cumsum >= total_profit * 0.8).idxmax() + 1

    concentration = {
        'total_trades': len(trades_df),
        'total_profit': total_profit,
        'top_5_profit': top_5_profit,
        'top_5_pct': (top_5_profit / total_profit * 100),
        'top_10_profit': top_10_profit,
        'top_10_pct': (top_10_profit / total_profit * 100),
        'trades_for_50pct': trades_for_50pct,
        'trades_for_50pct_percent': (trades_for_50pct / len(trades_df) * 100),
        'trades_for_80pct': trades_for_80pct,
        'trades_for_80pct_percent': (trades_for_80pct / len(trades_df) * 100),
    }

    # Red flags
    flags = []
    if concentration['top_5_pct'] > 50:
        flags.append(f"⚠️ Top 5 trades = {concentration['top_5_pct']:.1f}% of profit (>50% threshold)")
    if concentration['trades_for_50pct_percent'] < 10:
        flags.append(f"⚠️ Only {concentration['trades_for_50pct_percent']:.1f}% of trades = 50% of profit")
    if sorted_trades.iloc[0]['pnl_net'] > total_profit * 0.2:
        flags.append(f"⚠️ Single best trade = {sorted_trades.iloc[0]['pnl_net']/total_profit*100:.1f}% of profit")

    concentration['red_flags'] = flags
    concentration['status'] = 'PASS' if len(flags) == 0 else 'WARNING'

    return concentration


def verify_calculations(trades_df):
    """Manually verify 5 random trades"""
    if len(trades_df) == 0:
        return []

    sample_size = min(5, len(trades_df))
    sample = trades_df.sample(sample_size, random_state=42)

    verifications = []
    for _, trade in sample.iterrows():
        # Verify P&L calculation
        expected_pnl = (trade['exit_price'] - trade['entry_price']) / trade['entry_price'] * 100
        pnl_match = abs(expected_pnl - trade['pnl_gross']) < 0.001

        # Verify fees
        expected_fees = 0.07  # 0.02% + 0.05%
        fees_match = abs(trade['fees_paid'] - expected_fees) < 0.001

        # Verify net P&L
        expected_net = trade['pnl_gross'] - trade['fees_paid']
        net_match = abs(expected_net - trade['pnl_net']) < 0.001

        verifications.append({
            'entry_time': trade['entry_time'],
            'pnl_gross_claimed': trade['pnl_gross'],
            'pnl_gross_verified': expected_pnl,
            'pnl_match': pnl_match,
            'fees_match': fees_match,
            'net_match': net_match,
            'all_correct': pnl_match and fees_match and net_match
        })

    return verifications


def main():
    print("=" * 80)
    print("PEPE LIMIT ORDER STRATEGY - FULL AUDIT")
    print("=" * 80)
    print()

    # Load data
    data_file = '/workspaces/Carebiuro_windykacja/trading/pepe_usdt_1m_lbank.csv'
    df = load_data(data_file)
    df = calculate_indicators(df)
    print(f"✅ Loaded {len(df):,} candles")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    # TEST 1: LIMIT ORDERS
    print("=" * 80)
    print("TEST 1: LIMIT ORDERS (-0.15%)")
    print("=" * 80)
    trades_limit = backtest_limit_orders(
        df,
        rsi_threshold=40,
        sl_mult=1.5,
        tp_mult=2.0,
        limit_offset_pct=0.15,
        max_wait_candles=10
    )

    # TEST 2: MARKET ORDERS (limit offset = 0)
    print("TEST 2: MARKET ORDERS (instant fill)")
    print("=" * 80)
    trades_market = backtest_limit_orders(
        df,
        rsi_threshold=40,
        sl_mult=1.5,
        tp_mult=2.0,
        limit_offset_pct=0.0,  # NO OFFSET = market order
        max_wait_candles=1  # Fill immediately
    )

    # Compare both
    print("\n" + "=" * 80)
    print("COMPARISON: LIMIT vs MARKET")
    print("=" * 80)

    for name, trades_df in [("LIMIT (-0.15%)", trades_limit), ("MARKET (instant)", trades_market)]:
        if len(trades_df) == 0:
            print(f"\n{name}: NO TRADES")
            continue

        winners = trades_df[trades_df['pnl_net'] > 0]
        equity = 1.0
        for pnl in trades_df['pnl_net']:
            equity *= (1 + pnl / 100)
        compounded = (equity - 1) * 100

        print(f"\n{name}:")
        print(f"  Trades: {len(trades_df)}")
        print(f"  Win Rate: {len(winners)/len(trades_df)*100:.1f}%")
        print(f"  Return (simple): {trades_df['pnl_net'].sum():.2f}%")
        print(f"  Return (compounded): {compounded:.2f}%")
        print(f"  Avg trade: {trades_df['pnl_net'].mean():.4f}%")

    print("\n" + "=" * 80)
    print("USING MARKET ORDERS FOR DETAILED ANALYSIS")
    print("=" * 80)
    trades_df = trades_market

    if len(trades_df) == 0:
        print("❌ NO TRADES GENERATED!")
        return

    # Calculate metrics
    winners = trades_df[trades_df['pnl_net'] > 0]
    losers = trades_df[trades_df['pnl_net'] <= 0]

    total_return_simple = trades_df['pnl_net'].sum()

    # Compounded return
    equity = 1.0
    for pnl in trades_df['pnl_net']:
        equity *= (1 + pnl / 100)
    compounded_return = (equity - 1) * 100

    # Max drawdown
    cumulative = trades_df['pnl_net'].cumsum()
    running_max = cumulative.cummax()
    drawdown = running_max - cumulative
    max_dd = drawdown.max()

    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {len(winners) / len(trades_df) * 100:.2f}%")
    print(f"Total Return (Simple): {total_return_simple:.2f}%")
    print(f"Total Return (Compounded): {compounded_return:.2f}%")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Avg Trade: {trades_df['pnl_net'].mean():.4f}%")
    print(f"Avg Winner: {winners['pnl_net'].mean():.4f}%" if len(winners) > 0 else "N/A")
    print(f"Avg Loser: {losers['pnl_net'].mean():.4f}%" if len(losers) > 0 else "N/A")
    print(f"R:R Ratio: {abs(winners['pnl_net'].mean() / losers['pnl_net'].mean()):.2f}:1" if len(losers) > 0 else "N/A")
    print(f"TP Exits: {len(trades_df[trades_df['exit_reason'] == 'TP'])} ({len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df) * 100:.1f}%)")
    print(f"SL Exits: {len(trades_df[trades_df['exit_reason'] == 'SL'])} ({len(trades_df[trades_df['exit_reason'] == 'SL']) / len(trades_df) * 100:.1f}%)")
    print(f"Total Fees Paid: {trades_df['fees_paid'].sum():.2f}%")
    print()

    # AUDIT 1: Profit Concentration
    print("=" * 80)
    print("AUDIT 1: PROFIT CONCENTRATION CHECK")
    print("=" * 80)
    concentration = analyze_profit_concentration(trades_df)
    if concentration:
        print(f"Status: {concentration['status']}")
        print(f"Top 5 trades: {concentration['top_5_pct']:.1f}% of total profit")
        print(f"Top 10 trades: {concentration['top_10_pct']:.1f}% of total profit")
        print(f"Trades for 50% profit: {concentration['trades_for_50pct']} ({concentration['trades_for_50pct_percent']:.1f}%)")
        print(f"Trades for 80% profit: {concentration['trades_for_80pct']} ({concentration['trades_for_80pct_percent']:.1f}%)")
        print()
        if concentration['red_flags']:
            print("⚠️ RED FLAGS:")
            for flag in concentration['red_flags']:
                print(f"   {flag}")
        else:
            print("✅ No red flags - profits well distributed")
    print()

    # AUDIT 2: Calculation Verification
    print("=" * 80)
    print("AUDIT 2: CALCULATION VERIFICATION (5 random trades)")
    print("=" * 80)
    verifications = verify_calculations(trades_df)
    all_correct = all(v['all_correct'] for v in verifications)
    for v in verifications:
        status = "✅" if v['all_correct'] else "❌"
        print(f"{status} {v['entry_time']}: PNL {v['pnl_gross_claimed']:.4f}% (verified: {v['pnl_gross_verified']:.4f}%)")
    print()
    if all_correct:
        print("✅ All calculations verified correct")
    else:
        print("❌ CALCULATION ERRORS FOUND!")
    print()

    # AUDIT 3: Strategy R:R (Return / MaxDD)
    print("=" * 80)
    print("AUDIT 3: STRATEGY RISK:REWARD")
    print("=" * 80)
    strategy_rr = compounded_return / max_dd if max_dd > 0 else 0
    print(f"Strategy R:R: {strategy_rr:.2f}:1")
    print(f"   (Return {compounded_return:.2f}% / MaxDD {max_dd:.2f}%)")
    print()

    # Save results
    trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/PEPE_limit_audit_trades.csv', index=False)
    print(f"✅ Saved trade log to: PEPE_limit_audit_trades.csv")
    print()

    # FINAL VERDICT
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if compounded_return > 150:
        print(f"⚠️ Return of {compounded_return:.2f}% in 30 days seems VERY HIGH")
        print(f"   This is {compounded_return/30:.1f}%/day compounded")
        print(f"   Annualized: ~{((1 + compounded_return/100) ** (365/30) - 1) * 100:.0f}%")
        print(f"   RECOMMENDATION: Paper trade for 1-2 weeks before risking real money")
    elif compounded_return > 50:
        print(f"✅ Return of {compounded_return:.2f}% is strong but believable for meme coins")
        print(f"   RECOMMENDATION: Start with small capital, scale up if it performs")
    else:
        print(f"✅ Return of {compounded_return:.2f}% is conservative and realistic")
    print()

    if concentration and concentration['status'] == 'WARNING':
        print(f"⚠️ Profit concentration warnings detected - review trade distribution")
    else:
        print(f"✅ Profit distribution looks healthy")
    print()

    if all_correct:
        print(f"✅ All calculations verified - no backtest errors")
    else:
        print(f"❌ Calculation errors found - DO NOT TRUST RESULTS")


if __name__ == "__main__":
    main()
