#!/usr/bin/env python3
"""
EMA Crossover - EMA Period Optimization
Fixed: TP 7 ATR, SL 5 ATR, Offset 0.7 ATR
Testing EMA combinations
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/fartcoin_1h_jun_dec_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Pre-calculate ATR
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# Fixed params
LIMIT_ATR_OFFSET = 0.7
TP_ATR = 7.0
SL_ATR = 5.0
MAX_WAIT_BARS = 20

def backtest(fast_ema, slow_ema):
    # Calculate EMAs
    ema_fast = df['close'].ewm(span=fast_ema, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_ema, adjust=False).mean()
    ema_fast_prev = ema_fast.shift(1)
    ema_slow_prev = ema_slow.shift(1)

    long_signal = (ema_fast > ema_slow) & (ema_fast_prev <= ema_slow_prev)
    short_signal = (ema_fast < ema_slow) & (ema_fast_prev >= ema_slow_prev)

    trades = []
    equity = 100.0
    position = None
    pending_order = None
    start_bar = max(slow_ema + 5, 21)

    for i in range(start_bar, len(df)):
        row = df.iloc[i]
        atr = df['atr'].iloc[i]

        if pending_order is not None:
            order = pending_order
            bars_waiting = i - order['signal_bar']
            filled = False

            if order['side'] == 'LONG' and row['low'] <= order['limit_price']:
                filled = True
                entry_price = order['limit_price']
            elif order['side'] == 'SHORT' and row['high'] >= order['limit_price']:
                filled = True
                entry_price = order['limit_price']

            if filled:
                position = {
                    'side': order['side'], 'entry_price': entry_price,
                    'tp': order['tp'], 'sl': order['sl'], 'entry_bar': i
                }
                pending_order = None
            elif bars_waiting >= MAX_WAIT_BARS:
                pending_order = None

        if position is not None:
            exit_price = None
            if position['side'] == 'LONG':
                if row['high'] >= position['tp']:
                    exit_price = position['tp']
                elif row['low'] <= position['sl']:
                    exit_price = position['sl']
            else:
                if row['low'] <= position['tp']:
                    exit_price = position['tp']
                elif row['high'] >= position['sl']:
                    exit_price = position['sl']

            if exit_price is not None:
                if position['side'] == 'LONG':
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
                else:
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * 100
                equity *= (1 + pnl_pct / 100)
                trades.append({'pnl_pct': pnl_pct, 'equity': equity})
                position = None

        if position is None and pending_order is None:
            signal_price = row['close']

            if long_signal.iloc[i]:
                pending_order = {
                    'side': 'LONG', 'signal_price': signal_price,
                    'limit_price': signal_price - (LIMIT_ATR_OFFSET * atr),
                    'tp': signal_price + (TP_ATR * atr),
                    'sl': signal_price - (SL_ATR * atr),
                    'signal_bar': i
                }
            elif short_signal.iloc[i]:
                pending_order = {
                    'side': 'SHORT', 'signal_price': signal_price,
                    'limit_price': signal_price + (LIMIT_ATR_OFFSET * atr),
                    'tp': signal_price - (TP_ATR * atr),
                    'sl': signal_price + (SL_ATR * atr),
                    'signal_bar': i
                }

    if not trades or len(trades) < 5:
        return None

    trades_df = pd.DataFrame(trades)
    total_return = equity - 100
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['dd'] = (trades_df['equity'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = trades_df['dd'].min()
    rr = abs(total_return / max_dd) if max_dd != 0 else 0
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = wins / len(trades_df) * 100

    return {
        'fast': fast_ema, 'slow': slow_ema,
        'return': total_return, 'max_dd': max_dd,
        'rr': rr, 'trades': len(trades_df), 'win_rate': win_rate
    }

# Test EMA combinations
print("=" * 80)
print("EMA CROSSOVER - PERIOD OPTIMIZATION")
print("=" * 80)
print(f"Fixed: Limit 0.7 ATR | TP 7 ATR | SL 5 ATR")
print("-" * 80)
print(f"{'Fast':>6} {'Slow':>6} {'Return':>12} {'Max DD':>10} {'R:R':>10} {'Trades':>8} {'Win %':>8}")
print("-" * 80)

results = []
fast_periods = [5, 8, 10, 12, 15]
slow_periods = [13, 21, 26, 34, 50, 55, 89]

for fast in fast_periods:
    for slow in slow_periods:
        if fast >= slow:
            continue
        r = backtest(fast, slow)
        if r:
            results.append(r)
            print(f"{r['fast']:>6} {r['slow']:>6} {r['return']:>+11.2f}% {r['max_dd']:>9.2f}% {r['rr']:>9.2f}x {r['trades']:>8} {r['win_rate']:>7.1f}%")

print("-" * 80)

if results:
    # Best by R:R
    best = max(results, key=lambda x: x['rr'])
    print(f"\n🏆 BEST R:R: EMA {best['fast']}/{best['slow']} → {best['rr']:.2f}x ({best['return']:+.2f}%, {best['trades']} trades)")

    # Best by return
    best_ret = max(results, key=lambda x: x['return'])
    print(f"💰 BEST Return: EMA {best_ret['fast']}/{best_ret['slow']} → {best_ret['return']:+.2f}% ({best_ret['rr']:.2f}x R:R)")

    # Top 5 by R:R
    print(f"\nTop 5 by R:R:")
    sorted_results = sorted(results, key=lambda x: x['rr'], reverse=True)[:5]
    for i, r in enumerate(sorted_results, 1):
        print(f"  {i}. EMA {r['fast']}/{r['slow']}: {r['rr']:.2f}x R:R, {r['return']:+.2f}%, {r['trades']} trades, {r['win_rate']:.1f}% win")
