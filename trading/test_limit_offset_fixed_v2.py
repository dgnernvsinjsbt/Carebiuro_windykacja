#!/usr/bin/env python3
"""
FIXED V2: Correct fill detection + only ONE position at a time
"""
import pandas as pd

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

# December only for testing
df_dec = df[(df['timestamp'] >= '2025-12-01') & (df['timestamp'] < '2026-01-01')].copy().reset_index(drop=True)

print("="*120)
print("FIXED V2: Correct HIGH check for limit fills + only ONE position at a time")
print("="*120)
print()

offset_pct = 0.8
equity = 100.0
trades = []

# STATE: Only one thing happening at a time
is_busy = False  # True if pending limit OR in active position
pending_limit_price = None
pending_signal_bar = None
pending_sl_price = None
pending_tp_price = None

i = 32
while i < len(df_dec):
    row = df_dec.iloc[i]

    if pd.isna(row['atr']):
        i += 1
        continue

    # If busy with pending limit order
    if is_busy and pending_limit_price is not None:
        bars_waiting = i - pending_signal_bar

        # Check if limit FILLED (price bounced UP to reach limit)
        if row['high'] >= pending_limit_price:
            entry_price = pending_limit_price
            sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                position_size = (equity * 5.0) / sl_dist_pct

                # Now we're SHORT - find exit
                for k in range(i + 1, min(i + 100, len(df_dec))):
                    exit_row = df_dec.iloc[k]

                    if exit_row['high'] >= pending_sl_price:
                        # Hit SL (price went up)
                        pnl_pct = -sl_dist_pct
                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        trades.append({
                            'entry_time': row['timestamp'],
                            'entry_bar': i,
                            'exit_time': exit_row['timestamp'],
                            'exit_bar': k,
                            'result': 'SL',
                            'pnl': pnl_dollar
                        })

                        # Jump to exit bar
                        i = k
                        break

                    elif exit_row['low'] <= pending_tp_price:
                        # Hit TP (price went down)
                        tp_dist_pct = ((entry_price - pending_tp_price) / entry_price) * 100
                        pnl_pct = tp_dist_pct
                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        trades.append({
                            'entry_time': row['timestamp'],
                            'entry_bar': i,
                            'exit_time': exit_row['timestamp'],
                            'exit_bar': k,
                            'result': 'TP',
                            'pnl': pnl_dollar
                        })

                        # Jump to exit bar
                        i = k
                        break

            # Clear pending
            is_busy = False
            pending_limit_price = None

        # Check if limit INVALIDATED (SL hit before fill)
        elif row['high'] >= pending_sl_price:
            is_busy = False
            pending_limit_price = None

        # Check if limit TIMEOUT (waited too long)
        elif bars_waiting >= 16:
            is_busy = False
            pending_limit_price = None

        i += 1
        continue

    # If NOT busy - check for new signal
    if not is_busy:
        high_8h = df_dec.iloc[max(0, i-32):i]['high'].max()
        dist_pct = ((row['close'] - high_8h) / high_8h) * 100

        if dist_pct <= -2.5:
            signal_price = row['close']
            sl_price = high_8h
            tp_price = signal_price * (1 - 0.05)
            limit_price = signal_price * (1 + offset_pct / 100)

            if limit_price < sl_price:
                # Place pending limit order
                is_busy = True
                pending_limit_price = limit_price
                pending_signal_bar = i
                pending_sl_price = sl_price
                pending_tp_price = tp_price

    i += 1

# Results
print(f"December 2025:")
print(f"Total Trades: {len(trades)}")
print(f"Final Equity: ${equity:.2f}")
print(f"Return: {((equity - 100) / 100) * 100:.1f}%")
print()

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['pnl'] > 0]
    print(f"Win Rate: {len(winners) / len(trades_df) * 100:.1f}%")
    print()

    # Show last 5 trades
    print("LAST 5 TRADES:")
    print("-" * 120)
    for idx, t in enumerate(trades[-5:], 1):
        entry_time = (t['entry_time'] + pd.Timedelta(hours=1)).strftime('%m-%d %H:%M')
        exit_time = (t['exit_time'] + pd.Timedelta(hours=1)).strftime('%m-%d %H:%M')
        hold_bars = t['exit_bar'] - t['entry_bar']
        print(f"{idx}. {entry_time} → {exit_time} | {t['result']} | {hold_bars} bars | ${t['pnl']:+.2f}")

print("="*120)
