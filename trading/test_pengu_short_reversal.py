#!/usr/bin/env python3
"""
Test PENGU-USDT with SHORT Reversal Strategy (MELANIA parameters)
PENGU ATR: 0.993% vs MELANIA ATR: 0.943% (very similar!)
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU-USDT SHORT REVERSAL - MELANIA PARAMETERS")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data Loaded:")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Avg Price: ${df['close'].mean():.6f}")
print(f"   Price Range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")

# Calculate RSI (Wilder's EMA method)
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
df['atr_pct'] = (df['atr'] / df['close']) * 100

print(f"   Avg ATR%: {df['atr_pct'].mean():.3f}%")

# MELANIA Parameters
rsi_trigger = 72
lookback = 5
limit_atr_offset = 0.8
tp_pct = 10.0
max_wait_bars = 20
max_sl_pct = 10.0
risk_pct = 5.0

print(f"\n🦊 MELANIA Parameters Applied to PENGU:")
print(f"   RSI Trigger: {rsi_trigger}")
print(f"   Lookback: {lookback}")
print(f"   Limit Offset: {limit_atr_offset} ATR")
print(f"   Take Profit: {tp_pct}%")
print(f"   Max Wait: {max_wait_bars} bars (5 hours)")
print(f"   Max SL: {max_sl_pct}%")
print(f"   Risk per Trade: {risk_pct}%")

# Backtest
equity = 100.0
trades = []

armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_placed_idx = None
swing_high_for_sl = None
limit_price = None

for i in range(lookback + 14, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # STEP 1: ARM on RSI > trigger
    if row['rsi'] > rsi_trigger and not armed and not limit_pending:
        armed = True
        signal_idx = i
        swing_low = df.iloc[i-lookback:i+1]['low'].min()
        limit_pending = False

    # STEP 2: Wait for break below swing low
    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            # Swing low broken - place limit order
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()

            sl_dist_pct = ((swing_high_for_sl - limit_price) / limit_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                armed = False
                continue

            limit_pending = True
            limit_placed_idx = i
            armed = False

    # STEP 3: Check limit fill
    if limit_pending:
        bars_waiting = i - limit_placed_idx

        # Timeout
        if bars_waiting > max_wait_bars:
            limit_pending = False
            swing_low = None
            swing_high_for_sl = None
            continue

        # Check fill
        if row['low'] <= limit_price:
            # FILLED - now find exit
            entry_price = limit_price
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - tp_pct / 100)  # SHORT: TP below entry

            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            # Position sizing
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False
            exit_idx = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]

                # SHORT: SL hit if price goes UP above SL
                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_idx = j
                    break
                # SHORT: TP hit if price goes DOWN below TP
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
                continue

            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'signal_time': df.iloc[signal_idx]['timestamp'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'] if exit_idx else None,
                'rsi': df.iloc[signal_idx]['rsi'],
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

            limit_pending = False
            swing_low = None
            swing_high_for_sl = None

if len(trades) == 0:
    print("\n❌ No trades generated!")
    exit(1)

# Calculate metrics
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

tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
sl_count = len(trades_df[trades_df['exit_reason'] == 'SL'])

# Monthly breakdown
trades_df['month'] = pd.to_datetime(trades_df['signal_time']).dt.to_period('M')
monthly = trades_df.groupby('month')['pnl_dollar'].sum()

print(f"\n" + "="*90)
print("🏆 PENGU BACKTEST RESULTS (MELANIA PARAMETERS)")
print("="*90)
print()

print(f"📊 Performance:")
print(f"   Total Return:     {total_return:+.1f}%")
print(f"   Max Drawdown:     {max_dd:.2f}%")
print(f"   Return/DD Ratio:  {return_dd:.2f}x")
print(f"   Final Equity:     ${equity:.2f}")
print()

print(f"📈 Trade Statistics:")
print(f"   Total Trades:     {len(trades_df)}")
print(f"   Winners:          {len(winners)} ({win_rate:.1f}%)")
print(f"   Losers:           {len(losers)} ({100-win_rate:.1f}%)")
print(f"   TP Hits:          {tp_count}")
print(f"   SL Hits:          {sl_count}")
print(f"   Trades/Day:       {len(trades_df)/199:.2f}")
print()

print(f"💰 P&L Analysis:")
print(f"   Avg Winner:       {winners['pnl_pct'].mean():.2f}%")
print(f"   Avg Loser:        {losers['pnl_pct'].mean():.2f}%")
print(f"   Largest Winner:   ${winners['pnl_dollar'].max():.2f} ({winners['pnl_pct'].max():.2f}%)")
print(f"   Largest Loser:    ${losers['pnl_dollar'].min():.2f} ({losers['pnl_pct'].min():.2f}%)")
print(f"   Avg SL Distance:  {trades_df['sl_dist_pct'].mean():.2f}%")

# Compare to MELANIA
print(f"\n" + "="*90)
print("📊 PENGU vs MELANIA COMPARISON")
print("="*90)
print()

melania_stats = {
    'trades': 45,
    'return': 1330.4,
    'max_dd': -24.66,
    'return_dd': 53.96,
    'win_rate': 42.2,
    'months': '6/7 profitable',
    'best_month': 708.74
}

print(f"{'Metric':<25} | {'MELANIA (6mo)':<20} | {'PENGU (6mo)':<20}")
print("-" * 70)
print(f"{'Total Trades':<25} | {melania_stats['trades']:<20} | {len(trades_df):<20}")

melania_wr = f"{melania_stats['win_rate']:.1f}%"
pengu_wr = f"{win_rate:.1f}%"
print(f"{'Win Rate':<25} | {melania_wr:<20} | {pengu_wr:<20}")

melania_rdd = f"{melania_stats['return_dd']:.2f}x"
pengu_rdd = f"{return_dd:.2f}x"
print(f"{'Return/DD':<25} | {melania_rdd:<20} | {pengu_rdd:<20}")

melania_ret = f"{melania_stats['return']:+.1f}%"
pengu_ret = f"{total_return:+.1f}%"
print(f"{'Total Return':<25} | {melania_ret:<20} | {pengu_ret:<20}")

melania_dd = f"{melania_stats['max_dd']:.2f}%"
pengu_dd = f"{max_dd:.2f}%"
print(f"{'Max Drawdown':<25} | {melania_dd:<20} | {pengu_dd:<20}")

# Monthly performance
print(f"\n📅 Monthly Performance:")
print()
print(f"{'Month':<15} | {'P&L ($)':<10}")
print("-" * 30)

for month, pnl in monthly.items():
    status = "✅" if pnl > 0 else "❌"
    print(f"{str(month):<15} | {pnl:>9.2f} {status}")

profitable_months = (monthly > 0).sum()
total_months = len(monthly)
print()
print(f"Profitable Months: {profitable_months}/{total_months}")

# Find best/worst months
best_month = monthly.idxmax()
worst_month = monthly.idxmin()
print(f"Best Month:  {best_month} (${monthly[best_month]:.2f})")
print(f"Worst Month: {worst_month} (${monthly[worst_month]:.2f})")

# Save trades
trades_df.to_csv('pengu_melania_params_trades.csv', index=False)
print(f"\n💾 Trades saved to: pengu_melania_params_trades.csv")
print("="*90)
