#!/usr/bin/env python3
"""Export MELANIA SHORT REVERSAL trades to CSV"""
import pandas as pd
import numpy as np

df = pd.read_csv('trading/melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

# Strategy parameters
rsi_trigger = 72
limit_atr_offset = 0.8
tp_pct = 10.0
lookback = 5
max_wait_bars = 20

equity = 100.0
trades = []
trade_num = 0

armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_price = None
limit_placed_idx = None
swing_high_for_sl = None

consecutive_wins = 0
consecutive_losses = 0

for i in range(lookback, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    if row['rsi'] > rsi_trigger:
        armed = True
        signal_idx = i
        swing_low = find_swing_low(df, i, lookback)
        limit_pending = False

    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = find_swing_high(df, signal_idx, i)
            limit_pending = True
            limit_placed_idx = i
            armed = False

    if limit_pending:
        if i - limit_placed_idx > max_wait_bars:
            limit_pending = False
            continue

        if row['high'] >= limit_price:
            entry_price = limit_price
            atr = row['atr']
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > 10:
                limit_pending = False
                continue

            size = (equity * 0.05) / (sl_dist_pct / 100)

            hit_sl = False
            hit_tp = False
            exit_bar = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]

                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_bar = j
                    break
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    exit_bar = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_reason = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_reason = 'TP'
            else:
                continue

            pnl_dollar = size * (pnl_pct / 100) - size * 0.001
            equity += pnl_dollar
            trade_num += 1

            # Track consecutive wins/losses
            if pnl_dollar > 0:
                consecutive_wins += 1
                consecutive_losses = 0
            else:
                consecutive_losses += 1
                consecutive_wins = 0

            trades.append({
                'trade_num': trade_num,
                'signal_time': df.iloc[signal_idx]['timestamp'],
                'signal_bar': signal_idx,
                'break_time': df.iloc[limit_placed_idx]['timestamp'],
                'break_bar': limit_placed_idx,
                'entry_time': row['timestamp'],
                'entry_bar': i,
                'exit_time': df.iloc[exit_bar]['timestamp'],
                'exit_bar': exit_bar,
                'rsi_at_signal': df.iloc[signal_idx]['rsi'],
                'swing_low': swing_low,
                'swing_high_sl': swing_high_for_sl,
                'limit_price': limit_price,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'position_size': size,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'equity_before': equity - pnl_dollar,
                'equity_after': equity,
                'consecutive_wins_before': consecutive_wins - 1 if pnl_dollar > 0 else 0,
                'consecutive_losses_before': consecutive_losses - 1 if pnl_dollar <= 0 else 0
            })

            limit_pending = False

# Save to CSV
trades_df = pd.DataFrame(trades)
trades_df.to_csv('melania_short_reversal_trades.csv', index=False)

print(f"✅ Exported {len(trades_df)} MELANIA SHORT REVERSAL trades to: melania_short_reversal_trades.csv")
print(f"   Final Equity: ${equity:.2f}")
print(f"   Total Return: {((equity - 100) / 100) * 100:+.1f}%")
