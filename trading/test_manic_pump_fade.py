#!/usr/bin/env python3
"""
PENGU: Fade MANIC_PUMP strategy

Entry: RSI > 75 + ATR > 0.6% (high vol overbought)
TP: 2-3%
SL: Above recent swing high
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Indicators
period = 14
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("PENGU: MANIC PUMP FADE STRATEGY")
print("="*140)
print()

test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']

# Test different parameters
param_grid = [
    {'rsi_trigger': 75, 'tp_pct': 2.0},
    {'rsi_trigger': 75, 'tp_pct': 3.0},
    {'rsi_trigger': 75, 'tp_pct': 4.0},
    {'rsi_trigger': 70, 'tp_pct': 2.0},
    {'rsi_trigger': 70, 'tp_pct': 3.0},
    {'rsi_trigger': 80, 'tp_pct': 2.0},
    {'rsi_trigger': 80, 'tp_pct': 3.0},
]

all_results = []

for params in param_grid:
    rsi_trigger = params['rsi_trigger']
    tp_pct = params['tp_pct']

    monthly_results = []

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        i = 0
        while i < len(df_month) - 20:
            row = df_month.iloc[i]

            # MANIC PUMP: RSI > trigger + High vol
            if row['rsi'] > rsi_trigger and row['atr_pct'] > 0.6:
                # Entry: SHORT at close
                entry_price = row['close']

                # SL: Find swing high in last 10 candles
                lookback_start = max(0, i - 10)
                sl_price = df_month.iloc[lookback_start:i+1]['high'].max()

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                    position_size = (equity * 5.0) / sl_dist_pct

                    # TP: entry - tp_pct
                    tp_price = entry_price * (1 - tp_pct / 100)

                    # Find exit
                    hit_sl = False
                    hit_tp = False

                    for j in range(i + 1, min(i + 40, len(df_month))):
                        exit_row = df_month.iloc[j]

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
                            pnl_pct = tp_pct

                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        if equity > peak_equity:
                            peak_equity = equity
                        dd = ((peak_equity - equity) / peak_equity) * 100
                        if dd > max_dd:
                            max_dd = dd

                        trades.append({'result': 'TP' if hit_tp else 'SL', 'pnl': pnl_dollar})

                        # Skip ahead to avoid overlapping trades
                        i = j + 1
                        continue

            i += 1

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            sl_hits = len(trades_df[trades_df['result'] == 'SL'])
            tp_hits = len(trades_df[trades_df['result'] == 'TP'])
            win_rate = (tp_hits / len(trades_df)) * 100

            monthly_results.append({
                'month': month_str,
                'return': total_return,
                'max_dd': max_dd,
                'trades': len(trades_df),
                'win_rate': win_rate
            })
        else:
            monthly_results.append({
                'month': month_str,
                'return': 0,
                'max_dd': 0,
                'trades': 0,
                'win_rate': 0
            })

    # Overall
    compounded = 100.0
    for m in monthly_results:
        compounded *= (1 + m['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([m['max_dd'] for m in monthly_results] + [0.01])
    return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
    total_trades = sum([m['trades'] for m in monthly_results])
    wins = len([m for m in monthly_results if m['return'] > 0])

    all_results.append({
        'rsi_trigger': rsi_trigger,
        'tp_pct': tp_pct,
        'total_return': total_return,
        'max_dd': overall_max_dd,
        'return_dd': return_dd,
        'total_trades': total_trades,
        'wins': wins,
        'trades_per_month': total_trades / len(test_months)
    })

# Display
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('return_dd', ascending=False)

print(f"{'RSI':<5} | {'TP%':<5} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Trades':<7} | {'Wins':<6} | {'T/Month':<8}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['return_dd'] > 5 and row['trades_per_month'] > 10 else "❌"
    print(f"{row['rsi_trigger']:<5} | {row['tp_pct']:<5.1f} | {row['total_return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['total_trades']:<7} | {row['wins']}/7 {status} | {row['trades_per_month']:<8.1f}")

print()
print("="*140)
print("VERDICT:")
print("="*140)

best = results_df.iloc[0]

if best['return_dd'] > 5 and best['trades_per_month'] > 10:
    print(f"✅ MANIC PUMP FADE DZIAŁA!")
    print(f"   Best: RSI > {best['rsi_trigger']}, TP {best['tp_pct']}%")
    print(f"   Return: {best['total_return']:+.1f}%")
    print(f"   R/DD: {best['return_dd']:.2f}x")
    print(f"   Trades: {best['total_trades']} ({best['trades_per_month']:.1f}/month)")
else:
    print(f"❌ MANIC PUMP FADE ma słaby edge:")
    print(f"   Best R/DD: {best['return_dd']:.2f}x (target: >5x)")
    print(f"   Trades/month: {best['trades_per_month']:.1f} (target: >10)")
    print()
    print("PENGU prawdopodobnie NIE MA wyraźnego edge do tradowania.")
    print("Wniosek: Szukaj innego coina z lepszymi wzorcami.")

print("="*140)
