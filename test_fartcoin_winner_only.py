#!/usr/bin/env python3
"""Test FARTCOIN winning config only - RSI>70, 1.0 ATR offset, 10% TP"""
import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('trading/fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# RSI calculation
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR calculation
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

# Test winning config: RSI>70, 1.0 ATR offset, 10% TP
rsi_trigger = 70
limit_atr_offset = 1.0
tp_pct = 10
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

    if row['rsi'] > rsi_trigger:
        armed = True
        signal_idx = i
        swing_low = df.iloc[max(0, i-lookback):i+1]['low'].min()
        limit_pending = False

    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
            limit_pending = True
            limit_placed_idx = i
            armed = False

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

# ✅ CORRECT drawdown calculation
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

print("\n" + "="*80)
print("FARTCOIN RSI>70, 1.0 ATR offset, 10% TP - CORRECTED RESULTS")
print("="*80)
print(f"Total Return: {total_return:+.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%  ← REAL VALUE (not -97%!)")
print(f"Return/DD Ratio: {return_dd:.2f}x")
print(f"Total Trades: {len(trades)}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Final Equity: ${equity:.2f}")
print("="*80)
