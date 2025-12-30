#!/usr/bin/env python3
"""
Test Limit Order Offset Strategy on ETH

Instead of market orders at breakout, place limit orders at:
- LONG: signal_price - (offset * ATR)  -- get better entry on pullback
- SHORT: signal_price + (offset * ATR) -- get better entry on bounce

TP/SL remain calculated from SIGNAL price (not fill price)
24-hour timeout (24 bars on 1H) - cancel if not filled
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load ETH 1H data
data_file = Path(__file__).parent / 'eth_1h_2025.csv'
df = pd.read_csv(data_file)
df.columns = [c.lower() for c in df.columns]
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ETH params from COIN_PARAMS
TP_ATR = 1.5
SL_ATR = 4
PERIOD = 20
FEE_PCT = 0.07  # 0.035% per side

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

print("=" * 80)
print("LIMIT ORDER OFFSET TEST - ETH-USDT (1H Candles)")
print("=" * 80)
print(f"Data: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Base params: TP={TP_ATR} ATR, SL={SL_ATR} ATR, Period={PERIOD}")
print(f"Timeout: 24 hours (24 bars)")
print("=" * 80)

def run_backtest(offset_atr: float, max_wait_bars: int = 24):
    """
    Run backtest with limit order offset

    Args:
        offset_atr: ATR multiplier for limit offset (0 = market order)
        max_wait_bars: Max bars to wait for fill (24 = 24 hours)
    """
    trades = []
    pending_order = None

    for i in range(PERIOD + 14, len(df)):
        row = df.iloc[i]
        price = row['close']
        atr = row['atr']
        upper = row['donchian_upper']
        lower = row['donchian_lower']

        if pd.isna(atr) or pd.isna(upper) or atr <= 0:
            continue

        # Check pending order fill
        if pending_order:
            bars_waited = i - pending_order['signal_bar']

            # Check timeout
            if bars_waited >= max_wait_bars:
                pending_order = None  # Cancel order
                continue

            # Check if limit order would fill
            if pending_order['direction'] == 'LONG':
                # Long limit fills if low <= limit_price
                if row['low'] <= pending_order['limit_price']:
                    # Filled! Calculate result
                    fill_price = pending_order['limit_price']
                    signal_price = pending_order['signal_price']
                    signal_atr = pending_order['signal_atr']

                    # TP/SL from signal price
                    tp = signal_price + (TP_ATR * signal_atr)
                    sl = signal_price - (SL_ATR * signal_atr)

                    # Simulate trade outcome
                    result = simulate_trade(df, i, 'LONG', fill_price, tp, sl)
                    if result:
                        trades.append(result)
                    pending_order = None
                    continue

            elif pending_order['direction'] == 'SHORT':
                # Short limit fills if high >= limit_price
                if row['high'] >= pending_order['limit_price']:
                    fill_price = pending_order['limit_price']
                    signal_price = pending_order['signal_price']
                    signal_atr = pending_order['signal_atr']

                    tp = signal_price - (TP_ATR * signal_atr)
                    sl = signal_price + (SL_ATR * signal_atr)

                    result = simulate_trade(df, i, 'SHORT', fill_price, tp, sl)
                    if result:
                        trades.append(result)
                    pending_order = None
                    continue

        # Generate new signal (only if no pending order)
        if pending_order is None:
            if price > upper:  # LONG breakout
                signal_price = price
                limit_price = signal_price - (offset_atr * atr)

                if offset_atr == 0:
                    # Market order - immediate fill
                    tp = signal_price + (TP_ATR * atr)
                    sl = signal_price - (SL_ATR * atr)
                    result = simulate_trade(df, i, 'LONG', signal_price, tp, sl)
                    if result:
                        trades.append(result)
                else:
                    # Limit order - wait for fill
                    pending_order = {
                        'direction': 'LONG',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'signal_atr': atr,
                        'signal_bar': i
                    }

            elif price < lower:  # SHORT breakout
                signal_price = price
                limit_price = signal_price + (offset_atr * atr)

                if offset_atr == 0:
                    tp = signal_price - (TP_ATR * atr)
                    sl = signal_price + (SL_ATR * atr)
                    result = simulate_trade(df, i, 'SHORT', signal_price, tp, sl)
                    if result:
                        trades.append(result)
                else:
                    pending_order = {
                        'direction': 'SHORT',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'signal_atr': atr,
                        'signal_bar': i
                    }

    return trades


def simulate_trade(df, entry_bar, direction, entry_price, tp, sl):
    """Simulate trade from entry bar until TP/SL hit"""

    for j in range(entry_bar + 1, len(df)):
        row = df.iloc[j]

        if direction == 'LONG':
            # Check SL first (more conservative)
            if row['low'] <= sl:
                pnl_pct = ((sl - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            # Check TP
            if row['high'] >= tp:
                pnl_pct = ((tp - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

        elif direction == 'SHORT':
            # Check SL first
            if row['high'] >= sl:
                pnl_pct = ((entry_price - sl) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            # Check TP
            if row['low'] <= tp:
                pnl_pct = ((entry_price - tp) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

    return None  # Trade still open at end of data


def analyze_trades(trades, offset_atr):
    """Analyze trade results"""
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    wins = len(df_trades[df_trades['result'] == 'TP'])
    losses = len(df_trades[df_trades['result'] == 'SL'])
    total = len(df_trades)
    win_rate = wins / total * 100 if total > 0 else 0

    # Calculate equity curve with 3% risk
    equity = 100.0
    max_equity = equity
    max_dd = 0

    for _, trade in df_trades.iterrows():
        sl_dist = abs(trade['pnl_pct']) if trade['result'] == 'SL' else SL_ATR * 100 / trade['entry'] * df['atr'].mean()
        # Approximate leverage based on 3% risk
        leverage = min(3.0 / sl_dist, 5.0) if sl_dist > 0 else 1.0
        pnl = leverage * trade['pnl_pct']
        equity *= (1 + pnl / 100)
        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)

    total_return = (equity - 100)
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    return {
        'offset_atr': offset_atr,
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio
    }


# Test different offsets
print(f"\n{'Offset':<8} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'WinRate':<10} {'Return%':<12} {'MaxDD%':<10} {'R:R':<8}")
print("-" * 80)

results = []
offsets = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

for offset in offsets:
    trades = run_backtest(offset)
    stats = analyze_trades(trades, offset)

    if stats:
        results.append(stats)
        print(f"{offset:<8.1f} {stats['total_trades']:<8} {stats['wins']:<6} {stats['losses']:<8} "
              f"{stats['win_rate']:<10.1f} {stats['total_return']:<12.1f} {stats['max_dd']:<10.1f} "
              f"{stats['rr_ratio']:<8.2f}")

# Find best offset
print("\n" + "=" * 80)
if results:
    best = max(results, key=lambda x: x['rr_ratio'])
    baseline = results[0]  # offset=0 is market orders

    print(f"\nBASELINE (Market Orders): {baseline['total_trades']} trades, {baseline['rr_ratio']:.2f}x R:R")
    print(f"BEST OFFSET: {best['offset_atr']} ATR")
    print(f"  - Trades: {best['total_trades']} ({best['total_trades'] - baseline['total_trades']:+d} vs baseline)")
    print(f"  - Win Rate: {best['win_rate']:.1f}% ({best['win_rate'] - baseline['win_rate']:+.1f}% vs baseline)")
    print(f"  - Return: {best['total_return']:.1f}% ({best['total_return'] - baseline['total_return']:+.1f}% vs baseline)")
    print(f"  - Max DD: {best['max_dd']:.1f}% ({best['max_dd'] - baseline['max_dd']:+.1f}% vs baseline)")
    print(f"  - R:R Ratio: {best['rr_ratio']:.2f}x ({best['rr_ratio'] - baseline['rr_ratio']:+.2f}x vs baseline)")

    # Trade-off analysis
    print("\n" + "=" * 80)
    print("TRADE-OFF ANALYSIS:")
    print("=" * 80)
    for r in results:
        fill_rate = r['total_trades'] / baseline['total_trades'] * 100 if baseline['total_trades'] > 0 else 0
        print(f"  {r['offset_atr']:.1f} ATR: {fill_rate:5.1f}% fill rate, {r['rr_ratio']:6.2f}x R:R, {r['win_rate']:5.1f}% win rate")
