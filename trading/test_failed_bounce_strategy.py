#!/usr/bin/env python3
"""
STRATEGY 2: Failed Bounce in Downtrend
- Price bounces up (green candles)
- Fails to break above recent swing high
- SHORT on rejection
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
print("STRATEGY 2: FAILED BOUNCE IN DOWNTREND")
print("="*120)
print()

# Test on October first
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy().reset_index(drop=True)

lookback = 5  # Look back for swing high
bounce_threshold = 0.3  # Min % bounce to consider as "attempt"
rejection_distance = 0.5  # Max % distance from swing high to be considered "reached"
tp_pct = 5.0
max_sl_pct = 5.0

equity = 100.0
trades = []

i = lookback
while i < len(df_oct):
    row = df_oct.iloc[i]

    if pd.isna(row['atr']):
        i += 1
        continue

    # Find recent swing high (highest high in last N candles)
    recent_high = df_oct.iloc[max(0, i-lookback):i]['high'].max()

    # Check if current candle is bouncing UP
    if row['close'] > row['open']:  # Green candle
        # Check if it's near the recent swing high
        distance_to_high = ((recent_high - row['high']) / recent_high) * 100

        # If price got close to swing high but didn't break it
        if 0 < distance_to_high <= rejection_distance:
            # Check next candle for rejection (red candle)
            if i + 1 < len(df_oct):
                next_candle = df_oct.iloc[i + 1]

                # REJECTION: Next candle is red AND closes below current candle's low
                if next_candle['close'] < next_candle['open'] and next_candle['close'] < row['low']:
                    # SHORT signal
                    entry_price = next_candle['close']
                    sl_price = recent_high
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
                                'entry_time': next_candle['timestamp'],
                                'swing_high': recent_high,
                                'bounce_high': row['high'],
                                'distance_pct': distance_to_high,
                                'entry_price': entry_price,
                                'result': 'TP' if hit_tp else 'SL',
                                'pnl': pnl_dollar
                            })

                            # Skip to exit
                            i = k
                            continue

    i += 1

# Results
print(f"October 2025 - Failed Bounce Strategy:")
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
        print(f"  {t['entry_time'].strftime('%m-%d %H:%M')} | Swing High: ${t['swing_high']:.6f} | Bounced to: ${t['bounce_high']:.6f} ({t['distance_pct']:.2f}% away) | {t['result']} | ${t['pnl']:+.2f}")

print("="*120)
