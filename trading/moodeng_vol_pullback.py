#!/usr/bin/env python3
"""
MOODENG - VOL EXPLOSION + PULLBACK ENTRY

Strategy:
1. Detect vol explosion (ATR spike + big move) - potwierdza że "coś się dzieje"
2. WAIT for pullback (dead cat bounce)
3. Entry na pullback = better price + mniejszy SL
4. Ride continuation of big move

Key insight: Vol explosion nie jest entry signal, jest CONFIRMATION signal.
Entry = pullback po vol explosion.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
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

df['return_1bar'] = df['close'].pct_change() * 100
df['return_4bar'] = df['close'].pct_change(4) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOODENG - VOL EXPLOSION + PULLBACK ENTRY")
print("="*140)
print()

# ============================================
# PART 1: FIND VOL EXPLOSIONS
# ============================================
print("="*140)
print("PART 1: DETECT VOL EXPLOSIONS + VERIFY PULLBACK PATTERN")
print("="*140)
print()

vol_explosions = []

for i in range(50, len(df) - 20):
    row = df.iloc[i]

    # Vol explosion criteria
    vol_spike = row['atr_pct'] > 1.5
    big_move = abs(row['return_4bar']) > 3.0

    if vol_spike and big_move:
        # Determine direction
        direction = 'UP' if row['return_4bar'] > 0 else 'DOWN'

        # Look for pullback in next 5-10 bars
        pullback_found = False
        pullback_bar = None
        pullback_size = 0

        for j in range(i + 1, min(i + 10, len(df))):
            pb_row = df.iloc[j]

            if direction == 'UP':
                # Look for down move (pullback in uptrend)
                if pb_row['return_4bar'] < -0.5:
                    pullback_found = True
                    pullback_bar = j
                    pullback_size = pb_row['return_4bar']
                    break
            else:
                # Look for up move (bounce in downtrend)
                if pb_row['return_4bar'] > 0.5:
                    pullback_found = True
                    pullback_bar = j
                    pullback_size = pb_row['return_4bar']
                    break

        if pullback_found:
            # Check what happens after pullback
            continuation_bars = min(pullback_bar + 16, len(df))
            future_high = df.iloc[pullback_bar:continuation_bars]['high'].max()
            future_low = df.iloc[pullback_bar:continuation_bars]['low'].min()

            entry_price = df.iloc[pullback_bar]['close']

            if direction == 'UP':
                continuation = ((future_high - entry_price) / entry_price) * 100
            else:
                continuation = ((entry_price - future_low) / entry_price) * 100

            vol_explosions.append({
                'bar': i,
                'pullback_bar': pullback_bar,
                'direction': direction,
                'initial_move': row['return_4bar'],
                'pullback_size': pullback_size,
                'continuation': continuation,
                'atr': row['atr_pct']
            })

print(f"Vol explosions with pullback pattern: {len(vol_explosions)}")

if len(vol_explosions) > 0:
    exp_df = pd.DataFrame(vol_explosions)

    print(f"\nCharacteristics:")
    print(f"  Avg initial move: {exp_df['initial_move'].abs().mean():.2f}%")
    print(f"  Avg pullback size: {exp_df['pullback_size'].abs().mean():.2f}%")
    print(f"  Avg continuation: {exp_df['continuation'].mean():.2f}%")
    print()

    # Success rate
    big_continuation = (exp_df['continuation'] > 5).sum()
    print(f"  Continuation > 5%: {big_continuation}/{len(exp_df)} ({big_continuation/len(exp_df)*100:.1f}%)")

    huge_continuation = (exp_df['continuation'] > 10).sum()
    print(f"  Continuation > 10%: {huge_continuation}/{len(exp_df)} ({huge_continuation/len(exp_df)*100:.1f}%)")

    print()

# ============================================
# PART 2: OPTIMIZE PARAMETERS
# ============================================
print("="*140)
print("PART 2: OPTIMIZE ENTRY PARAMETERS")
print("="*140)
print()

# Test different thresholds
param_grid = [
    {'vol_threshold': 1.3, 'move_threshold': 2.5, 'pullback_min': 0.5, 'tp': 8},
    {'vol_threshold': 1.3, 'move_threshold': 2.5, 'pullback_min': 0.5, 'tp': 10},
    {'vol_threshold': 1.5, 'move_threshold': 3.0, 'pullback_min': 0.5, 'tp': 8},
    {'vol_threshold': 1.5, 'move_threshold': 3.0, 'pullback_min': 0.5, 'tp': 10},
    {'vol_threshold': 1.5, 'move_threshold': 3.0, 'pullback_min': 1.0, 'tp': 10},
    {'vol_threshold': 1.8, 'move_threshold': 4.0, 'pullback_min': 1.0, 'tp': 12},
]

best_result = None
best_return_dd = -999

for params in param_grid:
    vol_thresh = params['vol_threshold']
    move_thresh = params['move_threshold']
    pb_min = params['pullback_min']
    tp_pct = params['tp']
    sl_pct = 3.0  # Fixed

    test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']
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

        i = 20
        while i < len(df_month) - 20:
            row = df_month.iloc[i]

            if pd.isna(row['atr_pct']):
                i += 1
                continue

            # STEP 1: Detect vol explosion (ARM)
            if not armed:
                vol_spike = row['atr_pct'] > vol_thresh
                big_move = abs(row['return_4bar']) > move_thresh

                if vol_spike and big_move:
                    armed = True
                    armed_direction = 'UP' if row['return_4bar'] > 0 else 'DOWN'
                    armed_bar = i
                    # print(f"  ARMED at bar {i}: {armed_direction} move {row['return_4bar']:.2f}%, ATR {row['atr_pct']:.2f}%")

            # STEP 2: Wait for pullback (ENTRY)
            elif armed and (i - armed_bar) <= 10:
                # Check for pullback
                pullback = False

                if armed_direction == 'UP' and row['return_4bar'] < -pb_min:
                    pullback = True
                elif armed_direction == 'DOWN' and row['return_4bar'] > pb_min:
                    pullback = True

                if pullback:
                    # ENTRY
                    entry_price = row['close']

                    if armed_direction == 'UP':
                        # LONG
                        sl_price = df_month.iloc[armed_bar:i+1]['low'].min()
                        tp_price = entry_price * (1 + tp_pct / 100)
                    else:
                        # SHORT
                        sl_price = df_month.iloc[armed_bar:i+1]['high'].max()
                        tp_price = entry_price * (1 - tp_pct / 100)

                    # Calculate SL distance
                    if armed_direction == 'UP':
                        sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100
                    else:
                        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                        position_size = (equity * 3.0) / sl_dist_pct

                        # Find exit
                        hit_sl = False
                        hit_tp = False

                        for j in range(i + 1, min(i + 30, len(df_month))):
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
                                pnl_pct = tp_pct if armed_direction == 'UP' else tp_pct
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
                                'result': 'TP' if hit_tp else 'SL',
                                'pnl': pnl_dollar
                            })

                            armed = False
                            i = j + 1
                            continue

                    armed = False

            # STEP 3: Timeout
            elif armed and (i - armed_bar) > 10:
                armed = False

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
                'trades': len(trades_df)
            })
        else:
            monthly_results.append({
                'month': month_str,
                'return': 0,
                'max_dd': 0,
                'win_rate': 0,
                'trades': 0
            })

    # Overall
    compounded = 100.0
    for m in monthly_results:
        compounded *= (1 + m['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([m['max_dd'] for m in monthly_results] + [0.01])
    return_dd = total_return / overall_max_dd
    total_trades = sum([m['trades'] for m in monthly_results])

    if return_dd > best_return_dd:
        best_return_dd = return_dd
        best_result = {
            'params': params,
            'return': total_return,
            'max_dd': overall_max_dd,
            'return_dd': return_dd,
            'trades': total_trades,
            'monthly': monthly_results
        }

    print(f"Vol={vol_thresh}, Move={move_thresh}, PB={pb_min}, TP={tp_pct}%: ", end="")
    print(f"Return {total_return:+.1f}%, R/DD {return_dd:.2f}x, {total_trades} trades")

print()

# ============================================
# PART 3: BEST RESULT
# ============================================
print("="*140)
print("PART 3: BEST CONFIGURATION")
print("="*140)
print()

if best_result:
    print(f"🏆 BEST PARAMS:")
    print(f"   Vol threshold: {best_result['params']['vol_threshold']}")
    print(f"   Move threshold: {best_result['params']['move_threshold']}%")
    print(f"   Pullback min: {best_result['params']['pullback_min']}%")
    print(f"   TP: {best_result['params']['tp']}%")
    print()

    print(f"📊 RESULTS:")
    print(f"   Total Return: {best_result['return']:+.1f}%")
    print(f"   Max Drawdown: {best_result['max_dd']:.1f}%")
    print(f"   Return/DD: {best_result['return_dd']:.2f}x")
    print(f"   Total Trades: {best_result['trades']} ({best_result['trades']/7:.1f}/month)")
    print()

    print(f"Monthly breakdown:")
    for m in best_result['monthly']:
        status = "✅" if m['return'] > 0 else "❌"
        print(f"  {m['month']}: {m['return']:>6.1f}% ({m['trades']} trades, {m['win_rate']:.0f}% WR) {status}")

    print()

    if best_result['return_dd'] > 5 and best_result['trades'] > 30:
        print(f"🔥 VOL EXPLOSION + PULLBACK STRATEGY DZIAŁA!")
        print(f"   Edge found: Wait for vol spike, enter on pullback")
    elif best_result['return_dd'] > 2:
        print(f"✅ Strategy ma positive edge, ale może potrzebuje refinement")
    else:
        print(f"⚠️  Edge wciąż słaby mimo pullback approach")

print("="*140)
