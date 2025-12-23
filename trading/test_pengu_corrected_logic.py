#!/usr/bin/env python3
"""
PENGU with CORRECTED arming logic
RSI >72 = armed ALWAYS (checked every candle)
Not a one-time flag that persists
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - CORRECTED ARMING LOGIC")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Parameters
rsi_trigger = 72
lookback = 5
limit_atr_offset = 0.8
tp_pct = 10.0
max_wait_bars = 20
max_sl_pct = 10.0
risk_pct = 5.0

print(f"\n📊 Corrected Strategy Logic:")
print(f"   RSI >72 = ARMED (checked EVERY candle)")
print(f"   While armed → track swing low from last {lookback} bars")
print(f"   If break → place limit order")
print(f"   If new high → update swing low, stay armed")
print()

# Diagnostic counters
stats = {
    'armed_candles': 0,
    'swing_low_breaks': 0,
    'limits_placed': 0,
    'limits_filled': 0,
    'limits_timeout': 0,
    'rejected_sl_too_wide': 0,
    'rejected_sl_negative': 0
}

# Backtest
equity = 100.0
trades = []

# Track pending limit orders
pending_limits = []  # List of pending limit orders

# Track armed state
was_armed_last_bar = False
current_swing_low = None
signal_candle_idx = None

for i in range(lookback + 14, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # STEP 1: Check if ARMED (every candle)
    armed = row['rsi'] > rsi_trigger

    if armed:
        stats['armed_candles'] += 1

        # If NEWLY armed (wasn't armed last bar), capture swing low
        if not was_armed_last_bar:
            current_swing_low = df.iloc[i-lookback:i+1]['low'].min()
            signal_candle_idx = i
    else:
        # Not armed - clear swing low
        if was_armed_last_bar:
            current_swing_low = None
            signal_candle_idx = None

    # Update armed state for next iteration
    was_armed_last_bar = armed

    # STEP 2: Update pending limit orders
    filled_limits = []
    for limit in pending_limits[:]:
        bars_waiting = i - limit['placed_idx']

        # Check timeout
        if bars_waiting > max_wait_bars:
            pending_limits.remove(limit)
            stats['limits_timeout'] += 1
            continue

        # Check fill
        if row['low'] <= limit['limit_price']:
            # FILLED
            entry_price = limit['limit_price']
            sl_price = limit['sl_price']
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_dist_pct = limit['sl_dist_pct']
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False
            exit_idx = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]
                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_idx = j
                    break
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    exit_idx = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_reason = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_reason = 'TP'
            else:
                pending_limits.remove(limit)
                continue

            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'signal_time': limit['signal_time'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'] if exit_idx else None,
                'rsi': limit['rsi'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'position_size': position_size,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'equity_before': equity - pnl_dollar,
                'equity_after': equity
            })

            pending_limits.remove(limit)
            stats['limits_filled'] += 1

    # STEP 3: If armed, check for swing low break
    if armed and current_swing_low is not None:
        # Check if price made new high (reset swing low if so)
        if signal_candle_idx is not None:
            swing_high_at_signal = df.iloc[signal_candle_idx-lookback:signal_candle_idx+1]['high'].max()
            if row['high'] > swing_high_at_signal:
                # New high - recalculate swing low
                current_swing_low = df.iloc[i-lookback:i+1]['low'].min()
                signal_candle_idx = i

        # Check if current bar breaks below swing low
        if row['low'] < current_swing_low:
            stats['swing_low_breaks'] += 1

            # Calculate limit order details
            atr = row['atr']
            limit_price = current_swing_low + (atr * limit_atr_offset)

            # Calculate swing high from signal to current bar
            swing_high = df.iloc[signal_candle_idx:i+1]['high'].max()

            sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

            # Validate SL distance
            if sl_dist_pct <= 0:
                stats['rejected_sl_negative'] += 1
                continue

            if sl_dist_pct > max_sl_pct:
                stats['rejected_sl_too_wide'] += 1
                continue

            # Valid - add to pending limits
            pending_limits.append({
                'placed_idx': i,
                'signal_time': row['timestamp'],
                'limit_price': limit_price,
                'sl_price': swing_high,
                'sl_dist_pct': sl_dist_pct,
                'rsi': row['rsi']
            })
            stats['limits_placed'] += 1

# Results
print(f"\n" + "="*90)
print("📊 CORRECTED SIGNAL FLOW")
print("="*90)
print()

total_candles = len(df) - (lookback + 14)
print(f"Total candles analyzed:      {total_candles}")
print(f"Armed candles (RSI >72):     {stats['armed_candles']} ({stats['armed_candles']/total_candles*100:.1f}%)")
print(f"Swing low breaks:            {stats['swing_low_breaks']} ({stats['swing_low_breaks']/stats['armed_candles']*100 if stats['armed_candles'] > 0 else 0:.1f}% of armed)")
print()
print(f"Limit orders placed:         {stats['limits_placed']}")
print(f"  ❌ Rejected (SL >10%):      {stats['rejected_sl_too_wide']}")
print(f"  ❌ Rejected (SL ≤0%):       {stats['rejected_sl_negative']}")
print()
print(f"Limit fills:                 {stats['limits_filled']} ({stats['limits_filled']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}% fill rate)")
print(f"Limit timeouts:              {stats['limits_timeout']} ({stats['limits_timeout']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}%)")

# Backtest results
if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max DD
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    losers = trades_df[trades_df['pnl_dollar'] < 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    print(f"\n" + "="*90)
    print("🏆 BACKTEST RESULTS")
    print("="*90)
    print()
    print(f"Total Trades:     {len(trades_df)}")
    print(f"Win Rate:         {win_rate:.1f}%")
    print(f"Total Return:     {total_return:+.1f}%")
    print(f"Max Drawdown:     {max_dd:.2f}%")
    print(f"Return/DD:        {return_dd:.2f}x")
    print(f"Final Equity:     ${equity:.2f}")
    print(f"Trades/Day:       {len(trades_df)/199:.2f}")

    print(f"\n📊 Comparison:")
    print(f"   OLD logic: 10 trades, +46.1%, 3.23x R/DD")
    print(f"   NEW logic: {len(trades_df)} trades, {total_return:+.1f}%, {return_dd:.2f}x R/DD")

    trades_df.to_csv('pengu_corrected_logic_trades.csv', index=False)
    print(f"\n💾 Trades saved to: pengu_corrected_logic_trades.csv")
else:
    print("\n❌ No trades generated!")

print("="*90)
