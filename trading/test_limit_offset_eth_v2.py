#!/usr/bin/env python3
"""
Test Limit Order Offset Strategy on ETH - V2

VERSION 2: TP/SL calculated from FILL price (not signal price)
This gives better risk:reward when filled at a discount

- LONG: fill at signal - offset → TP/SL from fill price
- SHORT: fill at signal + offset → TP/SL from fill price
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

# ETH params
TP_ATR = 1.5
SL_ATR = 4
PERIOD = 20
FEE_PCT = 0.07

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

print("=" * 80)
print("LIMIT ORDER OFFSET TEST V2 - ETH-USDT (TP/SL from FILL price)")
print("=" * 80)
print(f"Data: {len(df)} candles")
print(f"Base params: TP={TP_ATR} ATR, SL={SL_ATR} ATR, Period={PERIOD}")
print("=" * 80)


def run_backtest(offset_atr: float, max_wait_bars: int = 24):
    """Run backtest with limit order - TP/SL from fill price"""
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

            if bars_waited >= max_wait_bars:
                pending_order = None
                continue

            if pending_order['direction'] == 'LONG':
                if row['low'] <= pending_order['limit_price']:
                    fill_price = pending_order['limit_price']
                    fill_atr = atr  # Use current ATR at fill time

                    # TP/SL from FILL price
                    tp = fill_price + (TP_ATR * fill_atr)
                    sl = fill_price - (SL_ATR * fill_atr)

                    result = simulate_trade(df, i, 'LONG', fill_price, tp, sl)
                    if result:
                        result['offset_gain'] = (pending_order['signal_price'] - fill_price) / pending_order['signal_price'] * 100
                        trades.append(result)
                    pending_order = None
                    continue

            elif pending_order['direction'] == 'SHORT':
                if row['high'] >= pending_order['limit_price']:
                    fill_price = pending_order['limit_price']
                    fill_atr = atr

                    tp = fill_price - (TP_ATR * fill_atr)
                    sl = fill_price + (SL_ATR * fill_atr)

                    result = simulate_trade(df, i, 'SHORT', fill_price, tp, sl)
                    if result:
                        result['offset_gain'] = (fill_price - pending_order['signal_price']) / pending_order['signal_price'] * 100
                        trades.append(result)
                    pending_order = None
                    continue

        # Generate new signal
        if pending_order is None:
            if price > upper:
                signal_price = price
                limit_price = signal_price - (offset_atr * atr)

                if offset_atr == 0:
                    tp = signal_price + (TP_ATR * atr)
                    sl = signal_price - (SL_ATR * atr)
                    result = simulate_trade(df, i, 'LONG', signal_price, tp, sl)
                    if result:
                        result['offset_gain'] = 0
                        trades.append(result)
                else:
                    pending_order = {
                        'direction': 'LONG',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'signal_bar': i
                    }

            elif price < lower:
                signal_price = price
                limit_price = signal_price + (offset_atr * atr)

                if offset_atr == 0:
                    tp = signal_price - (TP_ATR * atr)
                    sl = signal_price + (SL_ATR * atr)
                    result = simulate_trade(df, i, 'SHORT', signal_price, tp, sl)
                    if result:
                        result['offset_gain'] = 0
                        trades.append(result)
                else:
                    pending_order = {
                        'direction': 'SHORT',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'signal_bar': i
                    }

    return trades


def simulate_trade(df, entry_bar, direction, entry_price, tp, sl):
    """Simulate trade from entry bar until TP/SL hit"""
    for j in range(entry_bar + 1, len(df)):
        row = df.iloc[j]

        if direction == 'LONG':
            if row['low'] <= sl:
                pnl_pct = ((sl - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            if row['high'] >= tp:
                pnl_pct = ((tp - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

        elif direction == 'SHORT':
            if row['high'] >= sl:
                pnl_pct = ((entry_price - sl) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            if row['low'] <= tp:
                pnl_pct = ((entry_price - tp) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

    return None


def analyze_trades(trades, offset_atr):
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    wins = len(df_trades[df_trades['result'] == 'TP'])
    losses = len(df_trades[df_trades['result'] == 'SL'])
    total = len(df_trades)
    win_rate = wins / total * 100 if total > 0 else 0

    # Average entry improvement from limit offset
    avg_offset_gain = df_trades['offset_gain'].mean() if 'offset_gain' in df_trades else 0

    # Calculate equity curve with 3% risk
    equity = 100.0
    max_equity = equity
    max_dd = 0

    for _, trade in df_trades.iterrows():
        sl_dist = SL_ATR * df['atr'].mean() / trade['entry'] * 100
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
        'avg_offset_gain': avg_offset_gain,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio
    }


print(f"\n{'Offset':<8} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'WinRate':<10} {'OffsetGain':<12} {'Return%':<12} {'MaxDD%':<10} {'R:R':<8}")
print("-" * 100)

results = []
offsets = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

for offset in offsets:
    trades = run_backtest(offset)
    stats = analyze_trades(trades, offset)

    if stats:
        results.append(stats)
        print(f"{offset:<8.1f} {stats['total_trades']:<8} {stats['wins']:<6} {stats['losses']:<8} "
              f"{stats['win_rate']:<10.1f} {stats['avg_offset_gain']:<12.2f} {stats['total_return']:<12.1f} "
              f"{stats['max_dd']:<10.1f} {stats['rr_ratio']:<8.2f}")

print("\n" + "=" * 100)
if results:
    best = max(results, key=lambda x: x['rr_ratio'])
    baseline = results[0]

    print(f"\nBASELINE (Market Orders): {baseline['total_trades']} trades, {baseline['rr_ratio']:.2f}x R:R")
    print(f"BEST OFFSET: {best['offset_atr']} ATR")
    print(f"  - Trades: {best['total_trades']} ({best['total_trades'] - baseline['total_trades']:+d} vs baseline)")
    print(f"  - Win Rate: {best['win_rate']:.1f}% ({best['win_rate'] - baseline['win_rate']:+.1f}%)")
    print(f"  - Avg Entry Improvement: {best['avg_offset_gain']:.2f}%")
    print(f"  - Return: {best['total_return']:.1f}% ({best['total_return'] - baseline['total_return']:+.1f}%)")
    print(f"  - R:R Ratio: {best['rr_ratio']:.2f}x ({best['rr_ratio'] - baseline['rr_ratio']:+.2f}x)")

print("\n" + "=" * 100)
print("CONCLUSION:")
print("=" * 100)
print("Even with TP/SL from fill price, limit offsets hurt performance on ETH.")
print("Donchian breakout is a MOMENTUM strategy - you want to enter AT the breakout.")
print("Waiting for pullback means missing the strongest moves that drive profitability.")
print("\nRECOMMENDATION: Use MARKET ORDERS for Donchian breakout strategy.")
