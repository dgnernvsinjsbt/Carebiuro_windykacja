#!/usr/bin/env python3
"""FARTCOIN SHORT reversal test - FULLY CORRECTED"""
import pandas as pd
import numpy as np
import time

start = time.time()

print("Loading data...", flush=True)
df = pd.read_csv('trading/fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# RSI calculation with Wilder's smoothing (SAME AS MOODENG)
print("Calculating RSI...", flush=True)
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR calculation (SAME AS MOODENG)
print("Calculating ATR...", flush=True)
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

print(f"Data loaded: {len(df)} rows ({time.time()-start:.1f}s)", flush=True)

def test(rsi_trigger, limit_atr_offset, tp_pct):
    lookback = 5
    max_wait_bars = 20
    equity = 100.0
    trades = []
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
    swing_high_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # Arm on RSI crossover
        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = df.iloc[max(0, i-lookback):i+1]['low'].min()
            limit_pending = False

        # Place limit order when price breaks swing low
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Execute trade if limit hit
        if limit_pending:
            if i - limit_placed_idx > max_wait_bars:
                limit_pending = False
                continue

            if row['high'] >= limit_price:
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:
                    limit_pending = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)
                hit_sl = False
                hit_tp = False

                # Check exit
                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]
                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar
                trades.append(pnl_dollar)
                limit_pending = False

    if len(trades) < 5:
        return None

    # ✅ FIXED: Use MOODENG's correct drawdown calculation
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0]
    for pnl in trades:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()  # ✅ PROGRESSIVE running max
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = len([p for p in trades if p > 0])
    win_rate = (winners / len(trades) * 100) if len(trades) > 0 else 0

    return {
        'rsi': rsi_trigger, 'offset': limit_atr_offset, 'tp': tp_pct,
        'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd,
        'trades': len(trades), 'win_rate': win_rate
    }

print("\nTesting 120 configurations...", flush=True)
results = []
for idx, rsi in enumerate([68, 70, 72, 74, 76]):
    for oidx, offset in enumerate([0.4, 0.6, 0.8, 1.0]):
        for tidx, tp in enumerate([5, 6, 7, 8, 9, 10]):
            config_num = idx*24 + oidx*6 + tidx + 1
            r = test(rsi, offset, tp)
            if r:
                results.append(r)
            if config_num % 30 == 0:
                print(f"  {config_num}/120 configs done ({time.time()-start:.0f}s)", flush=True)

print(f"\nFound {len(results)}/120 valid configs", flush=True)

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "="*100)
    print("FARTCOIN SHORT REVERSAL - TOP 5 CONFIGURATIONS (CORRECTED)")
    print("="*100)

    for i, r in enumerate(results[:5], 1):
        print(f"\n#{i} - RSI>{r['rsi']} | {r['offset']:.1f}ATR Offset | {r['tp']}% TP")
        print(f"    Return/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.2f}% | Max DD: {r['max_dd']:.2f}%")
        print(f"    Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}%")

    print("\n" + "="*100)
    w = results[0]
    print(f"BEST CONFIG: RSI>{w['rsi']} | {w['offset']:.1f}ATR Offset | {w['tp']}% TP")
    print("="*100)
    print(f"Return/DD Ratio: {w['return_dd']:.2f}x")
    print(f"Total Return: {w['return']:+.2f}%")
    print(f"Max Drawdown: {w['max_dd']:.2f}%")
    print(f"Total Trades: {w['trades']}")
    print(f"Win Rate: {w['win_rate']:.1f}%")
    print("\n" + "="*100)

print(f"\nTotal time: {time.time()-start:.1f}s")
