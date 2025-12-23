#!/usr/bin/env python3
"""
STRATEGY 1: Lower High Pattern
- Track swing highs in downtrend
- SHORT when new swing high < previous swing high
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

print("="*120)
print("STRATEGY 1: LOWER HIGH PATTERN")
print("="*120)
print()

# Test on October first
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy().reset_index(drop=True)

lookback = 3  # Swing high detection period
tp_pct = 5.0
max_sl_pct = 5.0

equity = 100.0
trades = []

# Track swing highs
swing_highs = []  # List of (bar_index, price)

i = lookback
while i < len(df_oct) - lookback:
    row = df_oct.iloc[i]

    if pd.isna(row['atr']):
        i += 1
        continue

    # Detect swing high (local peak)
    is_swing_high = True
    for j in range(1, lookback + 1):
        if df_oct.iloc[i]['high'] <= df_oct.iloc[i - j]['high']:
            is_swing_high = False
            break
        if df_oct.iloc[i]['high'] <= df_oct.iloc[i + j]['high']:
            is_swing_high = False
            break

    if is_swing_high:
        current_high = df_oct.iloc[i]['high']

        # If we have a previous swing high, compare
        if len(swing_highs) > 0:
            prev_high_price = swing_highs[-1][1]

            # LOWER HIGH detected!
            if current_high < prev_high_price:
                # SHORT signal
                entry_price = df_oct.iloc[i + 1]['open']  # Enter next candle open
                sl_price = current_high  # SL above the swing high that just formed
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                    position_size = (equity * 5.0) / sl_dist_pct

                    # Find exit
                    hit_sl = False
                    hit_tp = False

                    for k in range(i + 2, min(i + 100, len(df_oct))):
                        exit_row = df_oct.iloc[k]

                        if exit_row['high'] >= sl_price:
                            hit_sl = True
                            break
                        elif exit_row['low'] <= tp_price:
                            hit_tp = True
                            break

                    if hit_sl or hit_tp:
                        if hit_sl:
                            pnl_pct = -sl_dist_pct
                        else:
                            tp_dist_pct = ((entry_price - tp_price) / entry_price) * 100
                            pnl_pct = tp_dist_pct

                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        trades.append({
                            'entry_time': df_oct.iloc[i + 1]['timestamp'],
                            'prev_high': prev_high_price,
                            'current_high': current_high,
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'result': 'TP' if hit_tp else 'SL',
                            'pnl': pnl_dollar
                        })

        # Add to swing highs list
        swing_highs.append((i, current_high))

    i += 1

# Results
print(f"October 2025 - Lower High Pattern:")
print(f"Total Trades: {len(trades)}")
print(f"Final Equity: ${equity:.2f}")
print(f"Return: {((equity - 100) / 100) * 100:.1f}%")
print()

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['pnl'] > 0]
    print(f"Win Rate: {len(winners) / len(trades_df) * 100:.1f}%")
    print()

    print("Sample trades:")
    for idx, t in trades_df.head(10).iterrows():
        print(f"  {t['entry_time'].strftime('%m-%d %H:%M')} | Prev High: ${t['prev_high']:.6f} → Current: ${t['current_high']:.6f} | {t['result']} | ${t['pnl']:+.2f}")

print("="*120)
