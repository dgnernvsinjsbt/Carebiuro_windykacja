#!/usr/bin/env python3
"""
BTC - MOMENTUM STRATEGY (Optimized for 2% edge)

Based on deep analysis findings:
1. Downtrend continuation: -2.229% (SHORT edge)
2. Uptrend continuation: +2.142% (LONG edge)
3. Only 6.3% time trending, but STRONG edge when it happens
4. 79.6% ranging (skip this!)

Strategy:
- Detect STRONG trends (>1% from MA20)
- Enter on momentum continuation
- Ride 2%+ moves
- Skip ranging markets
- Selective: 10-15 trades/month
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
print("BTC - MOMENTUM STRATEGY OPTIMIZATION")
print("="*140)
print()

# ============================================
# PART 1: PARAMETER GRID SEARCH
# ============================================
print("="*140)
print("PART 1: OPTIMIZE PARAMETERS")
print("="*140)
print()

param_grid = [
    # Conservative (tight filters)
    {'trend_thresh': 1.5, 'momentum_thresh': 0.3, 'tp_pct': 2.0, 'sl_atr': 2.0},
    {'trend_thresh': 1.5, 'momentum_thresh': 0.3, 'tp_pct': 2.5, 'sl_atr': 2.0},
    {'trend_thresh': 1.5, 'momentum_thresh': 0.5, 'tp_pct': 2.0, 'sl_atr': 2.0},

    # Moderate
    {'trend_thresh': 1.0, 'momentum_thresh': 0.3, 'tp_pct': 2.0, 'sl_atr': 2.5},
    {'trend_thresh': 1.0, 'momentum_thresh': 0.3, 'tp_pct': 2.5, 'sl_atr': 2.5},
    {'trend_thresh': 1.0, 'momentum_thresh': 0.5, 'tp_pct': 2.0, 'sl_atr': 2.0},
    {'trend_thresh': 1.0, 'momentum_thresh': 0.5, 'tp_pct': 3.0, 'sl_atr': 2.5},

    # Aggressive (wider targets)
    {'trend_thresh': 0.8, 'momentum_thresh': 0.3, 'tp_pct': 3.0, 'sl_atr': 2.5},
    {'trend_thresh': 0.8, 'momentum_thresh': 0.3, 'tp_pct': 3.5, 'sl_atr': 3.0},
    {'trend_thresh': 0.8, 'momentum_thresh': 0.5, 'tp_pct': 2.5, 'sl_atr': 2.0},
]

test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']

best_result = None
best_return_dd = -999

for params in param_grid:
    trend_thresh = params['trend_thresh']
    momentum_thresh = params['momentum_thresh']
    tp_pct = params['tp_pct']
    sl_atr_mult = params['sl_atr']

    monthly_results = []

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        i = 50
        while i < len(df_month) - 20:
            row = df_month.iloc[i]

            if pd.isna(row['atr_pct']) or pd.isna(row['ma_dist']):
                i += 1
                continue

            # Detect STRONG trend
            strong_uptrend = row['ma_dist'] > trend_thresh and row['ma_20'] > df_month.iloc[i-20]['ma_20']
            strong_downtrend = row['ma_dist'] < -trend_thresh and row['ma_20'] < df_month.iloc[i-20]['ma_20']

            # Momentum confirmation
            momentum_up = row['return_1h'] > momentum_thresh
            momentum_down = row['return_1h'] < -momentum_thresh

            # LONG setup
            if strong_uptrend and momentum_up:
                entry_price = row['close']
                sl_price = entry_price - (row['atr'] * sl_atr_mult)
                tp_price = entry_price * (1 + tp_pct / 100)
                sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= 3.0:
                    position_size = (equity * 5.0) / sl_dist_pct

                    # Find exit
                    hit_sl = False
                    hit_tp = False

                    for j in range(i + 1, min(i + 40, len(df_month))):
                        exit_row = df_month.iloc[j]

                        if exit_row['low'] <= sl_price:
                            hit_sl = True
                            break
                        elif exit_row['high'] >= tp_price:
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
                            'direction': 'LONG',
                            'result': 'TP' if hit_tp else 'SL',
                            'pnl': pnl_dollar
                        })

                        i = j + 2
                        continue

            # SHORT setup
            elif strong_downtrend and momentum_down:
                entry_price = row['close']
                sl_price = entry_price + (row['atr'] * sl_atr_mult)
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= 3.0:
                    position_size = (equity * 5.0) / sl_dist_pct

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
                            'direction': 'SHORT',
                            'result': 'TP' if hit_tp else 'SL',
                            'pnl': pnl_dollar
                        })

                        i = j + 2
                        continue

            i += 1

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100

            monthly_results.append({
                'month': month_str,
                'return': total_return,
                'max_dd': max_dd,
                'win_rate': win_rate,
                'trades': len(trades_df),
                'longs': (trades_df['direction'] == 'LONG').sum(),
                'shorts': (trades_df['direction'] == 'SHORT').sum()
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

    if return_dd > best_return_dd and total_trades >= 20:
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

    print(f"Trend={trend_thresh}, Mom={momentum_thresh}, TP={tp_pct}%, SL={sl_atr_mult}x: ", end="")
    print(f"Return {total_return:+.1f}%, R/DD {return_dd:.2f}x, {total_trades} trades ({total_longs}L/{total_shorts}S)")

print()

# ============================================
# PART 2: BEST RESULT
# ============================================
print("="*140)
print("PART 2: BEST CONFIGURATION")
print("="*140)
print()

if best_result:
    print(f"🏆 BEST PARAMS:")
    print(f"   Trend threshold: {best_result['params']['trend_thresh']}%")
    print(f"   Momentum threshold: {best_result['params']['momentum_thresh']}%")
    print(f"   TP: {best_result['params']['tp_pct']}%")
    print(f"   SL: {best_result['params']['sl_atr']}x ATR")
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
    for m in best_result['monthly']:
        status = "✅" if m['return'] > 0 else "❌"
        print(f"  {m['month']}: {m['return']:>6.1f}% ({m['longs']}L/{m['shorts']}S, {m['win_rate']:.0f}% WR) {status}")

    print()

    if best_result['return_dd'] > 5 and best_result['trades'] > 20:
        print(f"🔥 BTC MOMENTUM STRATEGY DZIAŁA!")
        print(f"   Edge: {best_result['return'] / best_result['trades']:.2f}% per trade")
        print(f"   10x better than MOODENG's best (0.22%)")
    elif best_result['return_dd'] > 2:
        print(f"✅ Strategy has positive edge")
        print(f"   Może potrzeba refinement")
    else:
        print(f"⚠️  Edge wciąż słaby")
else:
    print("❌ No profitable configuration found")

print("="*140)
