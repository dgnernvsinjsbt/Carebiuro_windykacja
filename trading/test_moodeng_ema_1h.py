#!/usr/bin/env python3
"""
EMA 8/21 Crossover - MOODENG 1h Broad Sweep
"""

import pandas as pd
import numpy as np

# Load 1h data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/moodeng_1h_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"MOODENG 1h: {len(df):,} candles ({df['timestamp'].min()} to {df['timestamp'].max()})")

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['ema8_prev'] = df['ema8'].shift(1)
df['ema21_prev'] = df['ema21'].shift(1)
df['long_signal'] = (df['ema8'] > df['ema21']) & (df['ema8_prev'] <= df['ema21_prev'])
df['short_signal'] = (df['ema8'] < df['ema21']) & (df['ema8_prev'] >= df['ema21_prev'])

MAX_WAIT_BARS = 20

def backtest(limit_offset, tp_atr, sl_atr):
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
                    'tp': signal_price + (tp_atr * atr),
                    'sl': signal_price - (sl_atr * atr),
                    'signal_bar': i
                }
            elif row['short_signal']:
                pending_order = {
                    'side': 'SHORT', 'signal_price': signal_price,
                    'limit_price': signal_price + (limit_offset * atr),
                    'tp': signal_price - (tp_atr * atr),
                    'sl': signal_price + (sl_atr * atr),
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
        'offset': limit_offset, 'tp': tp_atr, 'sl': sl_atr,
        'return': total_return, 'max_dd': max_dd,
        'rr': rr, 'trades': len(trades_df), 'win_rate': win_rate
    }

# Broad sweep
print("\n" + "=" * 80)
print("EMA 8/21 CROSSOVER - MOODENG 1H BROAD SWEEP")
print("=" * 80)
print(f"{'Offset':>8} {'TP':>6} {'SL':>6} {'Return':>12} {'Max DD':>10} {'R:R':>10} {'Trades':>8} {'Win%':>8}")
print("-" * 80)

results = []
test_configs = [
    # FARTCOIN optimal
    (0.7, 7, 5),
    # Variations
    (0.5, 5, 3),
    (0.5, 6, 4),
    (0.7, 5, 3),
    (0.7, 6, 4),
    (0.7, 8, 5),
    (0.7, 9, 5),
    (1.0, 7, 5),
    (1.0, 8, 6),
    (0.5, 7, 5),
    (0.7, 7, 4),
    (0.7, 7, 6),
]

for offset, tp, sl in test_configs:
    r = backtest(offset, tp, sl)
    if r:
        results.append(r)
        print(f"{r['offset']:>8} {r['tp']:>6} {r['sl']:>6} {r['return']:>+11.2f}% {r['max_dd']:>9.2f}% {r['rr']:>9.2f}x {r['trades']:>8} {r['win_rate']:>7.1f}%")

print("-" * 80)

if results:
    best = max(results, key=lambda x: x['rr'])
    print(f"\n🏆 BEST R:R: Offset {best['offset']} | TP {best['tp']} | SL {best['sl']} → {best['rr']:.2f}x ({best['return']:+.2f}%, {best['trades']} trades)")

    best_ret = max(results, key=lambda x: x['return'])
    print(f"💰 BEST Return: Offset {best_ret['offset']} | TP {best_ret['tp']} | SL {best_ret['sl']} → {best_ret['return']:+.2f}% ({best_ret['rr']:.2f}x R:R)")
