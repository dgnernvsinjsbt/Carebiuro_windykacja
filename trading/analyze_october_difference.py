#!/usr/bin/env python3
"""Analyze why October is profitable on LBank but negative on BingX"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
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
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
df['ret_4h_abs'] = abs(df['ret_4h'])
df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

# OPTIMAL BINGX CONFIG
rsi_ob = 65
limit_offset_atr = 0.1
sl_atr = 2.0
tp_atr = 3.0
min_move = 0.8
min_momentum = 0

current_risk = 0.12
equity = 100.0
trades = []
position = None
pending_order = None

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
        continue

    # Check pending order
    if pending_order:
        bars_waiting = i - pending_order['signal_bar']
        if bars_waiting > 8:
            pending_order = None
            continue

        if row['high'] >= pending_order['limit_price']:
            position = {
                'entry': pending_order['limit_price'],
                'sl_price': pending_order['sl_price'],
                'tp_price': pending_order['tp_price'],
                'size': pending_order['size'],
                'entry_bar': i,
                'signal_bar': pending_order['signal_bar']
            }
            pending_order = None

    # Check exit
    if position:
        pnl_pct = None
        exit_reason = None

        if row['high'] >= position['sl_price']:
            pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            exit_reason = 'SL'
        elif row['low'] <= position['tp_price']:
            pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
            exit_reason = 'TP'

        if pnl_pct is not None:
            pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
            equity += pnl_dollar

            signal_row = df.iloc[position['signal_bar']]
            entry_row = df.iloc[position['entry_bar']]

            trades.append({
                'signal_time': signal_row['timestamp'],
                'entry_time': entry_row['timestamp'],
                'exit_time': row['timestamp'],
                'signal_price': signal_row['close'],
                'entry_price': position['entry'],
                'sl_price': position['sl_price'],
                'tp_price': position['tp_price'],
                'exit_price': row['close'],
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'signal_rsi': signal_row['rsi'],
                'signal_atr': signal_row['atr'],
                'signal_ret20': signal_row['ret_20'],
                'bars_held': i - position['entry_bar']
            })

            won = pnl_pct > 0
            current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
            position = None
            continue

    # Generate signals (SHORT only)
    if not position and not pending_order and i > 0:
        prev_row = df.iloc[i-1]

        if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
            continue

        if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
            if row['avg_move_size'] >= min_move:
                signal_price = row['close']
                atr = row['atr']

                limit_price = signal_price + (atr * limit_offset_atr)
                sl_price = limit_price + (atr * sl_atr)
                tp_price = limit_price - (atr * tp_atr)

                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

trades_df = pd.DataFrame(trades)
trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

# Filter October trades
oct_trades = trades_df[trades_df['month'] == '2025-10'].copy()

print("=" * 80)
print("OCTOBER 2025 ANALYSIS - BINGX OPTIMAL CONFIG")
print("=" * 80)

if len(oct_trades) == 0:
    print("\n❌ NO TRADES IN OCTOBER!")
    print("\nChecking for RSI signals in October that didn't fill...")

    # Count signals in October
    oct_df = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy()

    # Count RSI crossovers
    oct_df['prev_rsi'] = oct_df['rsi'].shift(1)
    rsi_crosses = ((oct_df['prev_rsi'] > 65) & (oct_df['rsi'] <= 65)).sum()

    print(f"\nRSI crossovers in October: {rsi_crosses}")
    print("\nPossible reasons:")
    print("1. Signals generated but limit orders didn't fill (price didn't reach limit)")
    print("2. avg_move_size filter rejected signals (volatility too low)")
    print("3. ret_20 momentum filter rejected signals")

else:
    print(f"\nTotal October Trades: {len(oct_trades)}")
    print(f"Winners: {len(oct_trades[oct_trades['pnl_dollar'] > 0])}")
    print(f"Losers: {len(oct_trades[oct_trades['pnl_dollar'] < 0])}")
    print(f"Total P&L: ${oct_trades['pnl_dollar'].sum():+.2f}")

    print("\n" + "=" * 80)
    print("DETAILED OCTOBER TRADES")
    print("=" * 80)

    for idx, trade in oct_trades.iterrows():
        won = "✅ WIN" if trade['pnl_dollar'] > 0 else "❌ LOSS"
        print(f"\n{won} | {trade['signal_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Signal → Entry → Exit: {trade['signal_price']:.6f} → {trade['entry_price']:.6f} → {trade['exit_price']:.6f}")
        print(f"  SL: {trade['sl_price']:.6f} | TP: {trade['tp_price']:.6f}")
        print(f"  Exit: {trade['exit_reason']} after {trade['bars_held']} bars")
        print(f"  P&L: ${trade['pnl_dollar']:+.2f} ({trade['pnl_pct']:+.2f}%)")
        print(f"  Signal RSI: {trade['signal_rsi']:.1f} | ATR: {trade['signal_atr']:.6f} | Ret20: {trade['signal_ret20']:+.1f}%")

# Now compare with ORIGINAL LBANK CONFIG (1.2 ATR SL, 3.0 ATR TP)
print("\n" + "=" * 80)
print("COMPARISON: BINGX OPTIMAL vs LBANK ORIGINAL")
print("=" * 80)

# Reset for LBank-style config
current_risk = 0.12
equity = 100.0
trades_lbank = []
position = None
pending_order = None

# LBANK CONFIG
sl_atr_lbank = 1.2
tp_atr_lbank = 3.0

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
        continue

    if pending_order:
        bars_waiting = i - pending_order['signal_bar']
        if bars_waiting > 8:
            pending_order = None
            continue

        if row['high'] >= pending_order['limit_price']:
            position = {
                'entry': pending_order['limit_price'],
                'sl_price': pending_order['sl_price'],
                'tp_price': pending_order['tp_price'],
                'size': pending_order['size'],
                'entry_bar': i,
                'signal_bar': pending_order['signal_bar']
            }
            pending_order = None

    if position:
        pnl_pct = None
        exit_reason = None

        if row['high'] >= position['sl_price']:
            pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            exit_reason = 'SL'
        elif row['low'] <= position['tp_price']:
            pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
            exit_reason = 'TP'

        if pnl_pct is not None:
            pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
            equity += pnl_dollar

            signal_row = df.iloc[position['signal_bar']]

            trades_lbank.append({
                'signal_time': signal_row['timestamp'],
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason
            })

            won = pnl_pct > 0
            current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
            position = None
            continue

    if not position and not pending_order and i > 0:
        prev_row = df.iloc[i-1]

        if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
            continue

        if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
            if row['avg_move_size'] >= min_move:
                signal_price = row['close']
                atr = row['atr']

                limit_price = signal_price + (atr * limit_offset_atr)
                sl_price = limit_price + (atr * sl_atr_lbank)  # LBANK SL
                tp_price = limit_price - (atr * tp_atr_lbank)  # LBANK TP

                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

trades_lbank_df = pd.DataFrame(trades_lbank)
trades_lbank_df['signal_time'] = pd.to_datetime(trades_lbank_df['signal_time'])
trades_lbank_df['month'] = trades_lbank_df['signal_time'].dt.to_period('M')

oct_trades_lbank = trades_lbank_df[trades_lbank_df['month'] == '2025-10']

print(f"\nLBank Config (SL 1.2, TP 3.0) on BingX data:")
print(f"  October trades: {len(oct_trades_lbank)}")
print(f"  October P&L: ${oct_trades_lbank['pnl_dollar'].sum():+.2f}")

print(f"\nOptimal Config (SL 2.0, TP 3.0) on BingX data:")
print(f"  October trades: {len(oct_trades)}")
print(f"  October P&L: ${oct_trades['pnl_dollar'].sum():+.2f}")

print("\n" + "=" * 80)
print("KEY INSIGHT")
print("=" * 80)

if len(oct_trades) == 0 and len(oct_trades_lbank) == 0:
    print("\nBoth configs have NO October trades on BingX data!")
    print("This means LBank October profitability came from DIFFERENT DATA")
    print("(LBank spot vs BingX futures have different price action)")
elif len(oct_trades_lbank) > 0 and len(oct_trades) == 0:
    print("\nLBank config (1.2 SL) had trades, optimal config (2.0 SL) didn't")
    print("Wider SL may have filtered out October signals")
elif len(oct_trades) > 0:
    if oct_trades['pnl_dollar'].sum() < 0:
        sl_losses = len(oct_trades[oct_trades['exit_reason'] == 'SL'])
        tp_wins = len(oct_trades[oct_trades['exit_reason'] == 'TP'])
        print(f"\nBingX October lost money: {sl_losses} SL vs {tp_wins} TP")
        print("Same signals as LBank but got stopped out more on BingX (choppier)")
    else:
        print("\nOctober is profitable with optimal config!")

print("\n" + "=" * 80)
