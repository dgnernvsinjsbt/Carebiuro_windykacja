#!/usr/bin/env python3
"""
BTC - TREND + PULLBACK ENTRY

Problem: Direct momentum entry fails because we enter at extremes.
Solution: Wait for trend, then enter on PULLBACK.

Flow:
1. Detect strong trend (ARM)
2. Wait for pullback (better entry price)
3. Entry = continuation trade with smaller SL
4. Target: Ride the 2%+ continuation edge

Similar to MOODENG vol pullback, but using trend instead of vol explosion.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('btcusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Indicators
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()
df['ma_dist'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

df['return_1h'] = df['close'].pct_change(4) * 100
df['return_4h'] = df['close'].pct_change(16) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("BTC - TREND + PULLBACK ENTRY")
print("="*140)
print()

# ============================================
# OPTIMIZE PARAMETERS
# ============================================
param_grid = [
    # Conservative
    {'trend_thresh': 1.5, 'pullback_min': 0.3, 'tp_pct': 2.0, 'max_wait': 20},
    {'trend_thresh': 1.5, 'pullback_min': 0.5, 'tp_pct': 2.5, 'max_wait': 20},

    # Moderate
    {'trend_thresh': 1.0, 'pullback_min': 0.3, 'tp_pct': 2.0, 'max_wait': 20},
    {'trend_thresh': 1.0, 'pullback_min': 0.5, 'tp_pct': 2.0, 'max_wait': 20},
    {'trend_thresh': 1.0, 'pullback_min': 0.5, 'tp_pct': 2.5, 'max_wait': 20},

    # Aggressive
    {'trend_thresh': 0.8, 'pullback_min': 0.3, 'tp_pct': 2.5, 'max_wait': 20},
    {'trend_thresh': 0.8, 'pullback_min': 0.5, 'tp_pct': 3.0, 'max_wait': 20},

    # Longer wait
    {'trend_thresh': 1.0, 'pullback_min': 0.5, 'tp_pct': 2.0, 'max_wait': 30},
    {'trend_thresh': 0.8, 'pullback_min': 0.3, 'tp_pct': 2.0, 'max_wait': 30},
]

test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']

best_result = None
best_return_dd = -999

for params in param_grid:
    trend_thresh = params['trend_thresh']
    pb_min = params['pullback_min']
    tp_pct = params['tp_pct']
    max_wait = params['max_wait']

    monthly_results = []

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        armed = False
        armed_direction = None
        armed_bar = 0

        i = 50
        while i < len(df_month) - 20:
            row = df_month.iloc[i]

            if pd.isna(row['atr_pct']) or pd.isna(row['ma_dist']):
                i += 1
                continue

            # STEP 1: ARM on strong trend
            if not armed:
                # Uptrend
                if row['ma_dist'] > trend_thresh and row['ma_20'] > df_month.iloc[max(0, i-20)]['ma_20']:
                    armed = True
                    armed_direction = 'UP'
                    armed_bar = i

                # Downtrend
                elif row['ma_dist'] < -trend_thresh and row['ma_20'] < df_month.iloc[max(0, i-20)]['ma_20']:
                    armed = True
                    armed_direction = 'DOWN'
                    armed_bar = i

            # STEP 2: Wait for pullback
            elif armed and (i - armed_bar) <= max_wait:
                pullback = False

                if armed_direction == 'UP' and row['return_1h'] < -pb_min:
                    pullback = True
                elif armed_direction == 'DOWN' and row['return_1h'] > pb_min:
                    pullback = True

                if pullback:
                    entry_price = row['close']

                    if armed_direction == 'UP':
                        # LONG
                        sl_price = df_month.iloc[armed_bar:i+1]['low'].min()
                        tp_price = entry_price * (1 + tp_pct / 100)
                        sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100
                    else:
                        # SHORT
                        sl_price = df_month.iloc[armed_bar:i+1]['high'].max()
                        tp_price = entry_price * (1 - tp_pct / 100)
                        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 3.0:
                        position_size = (equity * 5.0) / sl_dist_pct

                        # Find exit
                        hit_sl = False
                        hit_tp = False

                        for j in range(i + 1, min(i + 40, len(df_month))):
                            exit_row = df_month.iloc[j]

                            if armed_direction == 'UP':
                                if exit_row['low'] <= sl_price:
                                    hit_sl = True
                                    break
                                elif exit_row['high'] >= tp_price:
                                    hit_tp = True
                                    break
                            else:
                                if exit_row['high'] >= sl_price:
                                    hit_sl = True
                                    break
                                elif exit_row['low'] <= tp_price:
                                    hit_tp = True
                                    break

                        if hit_sl or hit_tp:
                            if hit_tp:
                                pnl_pct = tp_pct
                            else:
                                pnl_pct = -sl_dist_pct

                            pnl_dollar = position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            if equity > peak_equity:
                                peak_equity = equity
                            dd = ((peak_equity - equity) / peak_equity) * 100
                            if dd > max_dd:
                                max_dd = dd

                            trades.append({
                                'direction': armed_direction,
                                'result': 'TP' if hit_tp else 'SL',
                                'pnl': pnl_dollar
                            })

                            armed = False
                            i = j + 1
                            continue

                    armed = False

            # STEP 3: Timeout
            elif armed and (i - armed_bar) > max_wait:
                armed = False

            i += 1

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100
            longs = (trades_df['direction'] == 'UP').sum()
            shorts = (trades_df['direction'] == 'DOWN').sum()

            monthly_results.append({
                'month': month_str,
                'return': total_return,
                'max_dd': max_dd,
                'win_rate': win_rate,
                'trades': len(trades_df),
                'longs': longs,
                'shorts': shorts
            })
        else:
            monthly_results.append({
                'month': month_str,
                'return': 0,
                'max_dd': 0,
                'win_rate': 0,
                'trades': 0,
                'longs': 0,
                'shorts': 0
            })

    # Overall
    compounded = 100.0
    for m in monthly_results:
        compounded *= (1 + m['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([m['max_dd'] for m in monthly_results] + [0.01])
    return_dd = total_return / overall_max_dd
    total_trades = sum([m['trades'] for m in monthly_results])
    total_longs = sum([m['longs'] for m in monthly_results])
    total_shorts = sum([m['shorts'] for m in monthly_results])

    if total_trades >= 15:
        if return_dd > best_return_dd:
            best_return_dd = return_dd
            best_result = {
                'params': params,
                'return': total_return,
                'max_dd': overall_max_dd,
                'return_dd': return_dd,
                'trades': total_trades,
                'longs': total_longs,
                'shorts': total_shorts,
                'monthly': monthly_results
            }

    print(f"Trend={trend_thresh}, PB={pb_min}, TP={tp_pct}%, Wait={max_wait}: ", end="")
    print(f"Return {total_return:+.1f}%, R/DD {return_dd:.2f}x, {total_trades} trades ({total_longs}L/{total_shorts}S)")

print()
print("="*140)
print("BEST CONFIGURATION")
print("="*140)
print()

if best_result:
    print(f"🏆 BEST PARAMS:")
    print(f"   Trend threshold: {best_result['params']['trend_thresh']}%")
    print(f"   Pullback min: {best_result['params']['pullback_min']}%")
    print(f"   TP: {best_result['params']['tp_pct']}%")
    print(f"   Max wait: {best_result['params']['max_wait']} bars")
    print()

    print(f"📊 RESULTS:")
    print(f"   Total Return: {best_result['return']:+.1f}%")
    print(f"   Max Drawdown: {best_result['max_dd']:.1f}%")
    print(f"   Return/DD: {best_result['return_dd']:.2f}x")
    print(f"   Total Trades: {best_result['trades']} ({best_result['trades']/7:.1f}/month)")
    print(f"   LONG: {best_result['longs']} ({best_result['longs']/best_result['trades']*100:.0f}%)")
    print(f"   SHORT: {best_result['shorts']} ({best_result['shorts']/best_result['trades']*100:.0f}%)")
    print()

    print(f"Monthly breakdown:")
    profitable = 0
    for m in best_result['monthly']:
        status = "✅" if m['return'] > 0 else "❌"
        if m['return'] > 0:
            profitable += 1
        print(f"  {m['month']}: {m['return']:>6.1f}% ({m['longs']}L/{m['shorts']}S, {m['win_rate']:.0f}% WR) {status}")

    print()
    print(f"Profitable months: {profitable}/7")
    print()

    if best_result['return_dd'] > 5 and best_result['trades'] >= 20:
        print(f"🔥 BTC PULLBACK STRATEGY DZIAŁA!")
        print(f"   Edge: {best_result['return'] / best_result['trades']:.2f}% per trade")
    elif best_result['return_dd'] > 2:
        print(f"✅ Strategy has positive edge")
    else:
        print(f"⚠️  Edge still weak")
else:
    print("❌ No profitable configuration found")

print("="*140)
