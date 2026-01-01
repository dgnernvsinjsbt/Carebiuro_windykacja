#!/usr/bin/env python3
"""
EMA 8/21 Crossover - Limit Offset Optimization
Fixed: TP 7 ATR, SL 5 ATR
Testing offset ATR levels: 0.3, 0.5, 0.7, 1.0, 1.2, 1.5, 2.0
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/fartcoin_1h_jun_dec_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['ema8_prev'] = df['ema8'].shift(1)
df['ema21_prev'] = df['ema21'].shift(1)
df['long_signal'] = (df['ema8'] > df['ema21']) & (df['ema8_prev'] <= df['ema21_prev'])
df['short_signal'] = (df['ema8'] < df['ema21']) & (df['ema8_prev'] >= df['ema21_prev'])

# Fixed params (from optimization)
TP_ATR = 7.0
SL_ATR = 5.0
MAX_WAIT_BARS = 20

def backtest(limit_offset):
    trades = []
    equity = 100.0
    position = None
    pending_order = None

    for i in range(21, len(df)):
        row = df.iloc[i]

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
            atr = row['atr']
            signal_price = row['close']

            if row['long_signal']:
                pending_order = {
                    'side': 'LONG', 'signal_price': signal_price,
                    'limit_price': signal_price - (limit_offset * atr),
                    'tp': signal_price + (TP_ATR * atr),
                    'sl': signal_price - (SL_ATR * atr),
                    'signal_bar': i
                }
            elif row['short_signal']:
                pending_order = {
                    'side': 'SHORT', 'signal_price': signal_price,
                    'limit_price': signal_price + (limit_offset * atr),
                    'tp': signal_price - (TP_ATR * atr),
                    'sl': signal_price + (SL_ATR * atr),
                    'signal_bar': i
                }

    if not trades:
        return {'offset': limit_offset, 'return': 0, 'max_dd': 0, 'rr': 0, 'trades': 0, 'win_rate': 0}

    trades_df = pd.DataFrame(trades)
    total_return = equity - 100
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['dd'] = (trades_df['equity'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = trades_df['dd'].min()
    rr = abs(total_return / max_dd) if max_dd != 0 else 0
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = wins / len(trades_df) * 100

    return {
        'offset': limit_offset, 'return': total_return, 'max_dd': max_dd,
        'rr': rr, 'trades': len(trades_df), 'win_rate': win_rate
    }

# Test offset levels
print("=" * 70)
print("EMA 8/21 CROSSOVER - LIMIT OFFSET OPTIMIZATION")
print("=" * 70)
print(f"Fixed: TP 7 ATR | SL 5 ATR | Max wait 20 bars")
print("-" * 70)
print(f"{'Offset':>8} {'Return':>12} {'Max DD':>10} {'R:R':>10} {'Trades':>8} {'Win %':>8}")
print("-" * 70)

results = []
for offset in [0.0, 0.3, 0.5, 0.7, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]:
    r = backtest(offset)
    results.append(r)
    print(f"{r['offset']:>8} {r['return']:>+11.2f}% {r['max_dd']:>9.2f}% {r['rr']:>9.2f}x {r['trades']:>8} {r['win_rate']:>7.1f}%")

print("-" * 70)

# Best by R:R
best = max(results, key=lambda x: x['rr'])
print(f"\n🏆 BEST R:R: Offset {best['offset']} ATR → {best['rr']:.2f}x ({best['return']:+.2f}% return, {best['max_dd']:.2f}% DD)")

# Best by return
best_ret = max(results, key=lambda x: x['return'])
print(f"💰 BEST Return: Offset {best_ret['offset']} ATR → {best_ret['return']:+.2f}% ({best_ret['rr']:.2f}x R:R)")
