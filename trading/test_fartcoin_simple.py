#!/usr/bin/env python3
"""Simple FARTCOIN SHORT reversal test - pure Python implementation"""
import pandas as pd
import sys

print("Loading data...", flush=True)
df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# RSI calculation
print("Calculating RSI...", flush=True)
for i in range(14, len(df)):
    if i == 14:
        gains = []
        losses = []
        for j in range(1, 15):
            delta = df.iloc[j]['close'] - df.iloc[j-1]['close']
            if delta > 0:
                gains.append(delta)
            else:
                losses.append(-delta)
        avg_g = sum(gains) / 14
        avg_l = sum(losses) / 14
    else:
        delta = df.iloc[i]['close'] - df.iloc[i-1]['close']
        if delta > 0:
            gain = delta
            loss = 0
        else:
            gain = 0
            loss = -delta
        avg_g = (avg_g * 13 + gain) / 14
        avg_l = (avg_l * 13 + loss) / 14

    rs = avg_g / avg_l if avg_l != 0 else 0
    df.loc[i, 'rsi'] = 100 - (100 / (1 + rs)) if rs else 0

# ATR calculation
print("Calculating ATR...", flush=True)
df['tr'] = 0.0
for i in range(1, len(df)):
    high_low = df.iloc[i]['high'] - df.iloc[i]['low']
    high_close = abs(df.iloc[i]['high'] - df.iloc[i-1]['close'])
    low_close = abs(df.iloc[i]['low'] - df.iloc[i-1]['close'])
    df.loc[i, 'tr'] = max(high_low, high_close, low_close)

df['atr'] = 0.0
for i in range(14, len(df)):
    df.loc[i, 'atr'] = df.iloc[i-13:i+1]['tr'].mean()

def test(rsi_trigger, limit_atr_offset, tp_pct):
    lookback = 5
    max_wait_bars = 20
    equity = 100.0
    trades = []
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_price = None
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
            swing_low = min(df.iloc[max(0, i-lookback):i+1]['low'])
            limit_pending = False

        # Place limit order when price breaks swing low
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = max(df.iloc[signal_idx:i+1]['high'])
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
                    if df.iloc[j]['high'] >= sl_price:
                        hit_sl = True
                        break
                    elif df.iloc[j]['low'] <= tp_price:
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
                trades.append({'signal_time': df.iloc[signal_idx]['timestamp'], 'pnl_dollar': pnl_dollar})
                limit_pending = False

    if len(trades) < 5:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = float(trades_df[trades_df['month'] == month]['pnl_dollar'].sum())

    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    running_max = max(equity_curve)
    max_dd = 0
    for val in equity_curve:
        if val < running_max:
            dd = (val - running_max) / running_max * 100
            if dd < max_dd:
                max_dd = dd
        if val > running_max:
            running_max = val

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = len([p for p in trades_df['pnl_dollar'] if p > 0])
    win_rate = (winners / len(trades_df) * 100) if len(trades_df) > 0 else 0
    profitable_months = sum(1 for v in monthly_pnl.values() if v > 0)

    return {
        'rsi': rsi_trigger, 'offset': limit_atr_offset, 'tp': tp_pct,
        'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd,
        'trades': len(trades_df), 'win_rate': win_rate, 'profitable_months': profitable_months,
        'monthly': monthly_pnl
    }

print("Testing 120 configurations...", flush=True)
results = []
for idx, rsi in enumerate([68, 70, 72, 74, 76]):
    for oidx, offset in enumerate([0.4, 0.6, 0.8, 1.0]):
        for tidx, tp in enumerate([5, 6, 7, 8, 9, 10]):
            config_num = idx*24 + oidx*6 + tidx + 1
            r = test(rsi, offset, tp)
            if r:
                results.append(r)
            if config_num % 20 == 0:
                print(f"  {config_num}/120 configs done", flush=True)

print(f"\nFound {len(results)}/120 valid configs", flush=True)

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "="*100)
    print("FARTCOIN SHORT REVERSAL - TOP 5 CONFIGURATIONS")
    print("="*100)

    for i, r in enumerate(results[:5], 1):
        print(f"\n#{i} - RSI>{r['rsi']} | {r['offset']:.1f}ATR Offset | {r['tp']}% TP")
        print(f"    Return/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.2f}% | Max DD: {r['max_dd']:.2f}%")
        print(f"    Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}% | Profitable Months: {r['profitable_months']}/7")

    print("\n" + "="*100)
    w = results[0]
    print(f"BEST CONFIG: RSI>{w['rsi']} | {w['offset']:.1f}ATR Offset | {w['tp']}% TP")
    print("="*100)
    print(f"Return/DD Ratio: {w['return_dd']:.2f}x")
    print(f"Total Return: {w['return']:+.2f}%")
    print(f"Max Drawdown: {w['max_dd']:.2f}%")
    print(f"Total Trades: {w['trades']}")
    print(f"Win Rate: {w['win_rate']:.1f}%")
    print(f"Profitable Months: {w['profitable_months']}/7")
    print("\nMonthly Breakdown:")
    for m, p in sorted(w['monthly'].items()):
        print(f"  {m}: ${p:+.2f}")

    print("\n" + "="*100)
