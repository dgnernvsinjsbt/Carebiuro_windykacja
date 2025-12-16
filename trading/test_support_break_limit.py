#!/usr/bin/env python3
"""Support break + limit order retest entry"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

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

# Test full 6-month dataset (Jun-Dec 2025)
# df = df[df['timestamp'] >= '2025-10-01'].copy().reset_index(drop=True)

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

def test(limit_atr_offset):
    rsi_trigger = 72
    lookback = 5
    tp_pct = 5
    max_wait_bars = 20  # Wait max 20 bars for limit fill

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

        # Check if RSI triggered
        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False  # Reset any pending limit

        # If armed, wait for break below swing low
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                # BREAK! Place limit order above break line
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)

                # SL = swing high between signal and now
                swing_high_for_sl = find_swing_high(df, signal_idx, i)

                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Check if limit order fills
        if limit_pending:
            # Timeout check
            if i - limit_placed_idx > max_wait_bars:
                limit_pending = False
                continue

            # Check if price reached limit
            if row['high'] >= limit_price:
                # FILLED!
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:
                    limit_pending = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)

                # Find exit
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

                trades.append({
                    'signal_time': df.iloc[signal_idx]['timestamp'],
                    'entry_time': row['timestamp'],
                    'pnl_dollar': pnl_dollar,
                    'pnl_pct': pnl_pct,
                    'sl_dist_pct': sl_dist_pct,
                    'exit_reason': exit_reason
                })

                limit_pending = False

    if len(trades) < 3:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()

    jun = monthly_pnl.get('2025-06', 0)
    jul = monthly_pnl.get('2025-07', 0)
    aug = monthly_pnl.get('2025-08', 0)
    sep = monthly_pnl.get('2025-09', 0)
    oct = monthly_pnl.get('2025-10', 0)
    nov = monthly_pnl.get('2025-11', 0)
    dec = monthly_pnl.get('2025-12', 0)

    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0]
    running_equity = 100.0
    for pnl in trades_df['pnl_dollar']:
        running_equity += pnl
        equity_curve.append(running_equity)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = len(winners) / len(trades_df) * 100
    avg_sl = trades_df['sl_dist_pct'].mean()
    tp_rate = len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df) * 100

    return {
        'limit_atr': limit_atr_offset,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'avg_sl': avg_sl,
        'jun': jun,
        'jul': jul,
        'aug': aug,
        'sep': sep,
        'oct': oct,
        'nov': nov,
        'dec': dec,
        'all_profitable': all([jun > 0, jul > 0, aug > 0, sep > 0, oct > 0, nov > 0, dec > 0]) if len(trades_df) > 10 else False
    }

print("=" * 80)
print("SUPPORT BREAK + LIMIT ORDER RETEST (Jun-Dec 2025)")
print("Break → Limit at support + X*ATR → Short retest")
print("=" * 80)

offsets = [round(x * 0.1, 1) for x in range(1, 11)]  # 0.1 to 1.0

results = []
for offset in offsets:
    r = test(offset)
    if r:
        results.append(r)
        status = "✅" if r['all_profitable'] else "❌"
        print(f"\nLimit at support + {offset:.1f} ATR {status}")
        print(f"  R/DD: {r['return_dd']:5.2f}x | Ret: {r['return']:+6.1f}% | DD: {r['max_dd']:6.2f}%")
        print(f"  Trades: {r['trades']:2d} | Win: {r['win_rate']:5.1f}% | TP: {r['tp_rate']:5.1f}%")
        print(f"  Jun: ${r['jun']:+5.2f} | Jul: ${r['jul']:+5.2f} | Aug: ${r['aug']:+5.2f} | Sep: ${r['sep']:+5.2f}")
        print(f"  Oct: ${r['oct']:+5.2f} | Nov: ${r['nov']:+5.2f} | Dec: ${r['dec']:+6.2f}")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "=" * 80)
    print("TOP CONFIGS")
    print("=" * 80)

    for i, r in enumerate(results[:5], 1):
        status = "✅" if r['all_profitable'] else "❌"
        print(f"#{i} {status} Limit +{r['limit_atr']:.1f} ATR | R/DD: {r['return_dd']:.2f}x | Ret: {r['return']:+.1f}% | Trades: {r['trades']}")
        print(f"     Jun: ${r['jun']:+.2f} | Jul: ${r['jul']:+.2f} | Aug: ${r['aug']:+.2f} | Sep: ${r['sep']:+.2f}")
        print(f"     Oct: ${r['oct']:+.2f} | Nov: ${r['nov']:+.2f} | Dec: ${r['dec']:+.2f}")

    valid = [r for r in results if r['all_profitable']]
    if valid:
        best = valid[0]
        print("\n" + "=" * 80)
        print("BEST WITH ALL MONTHS PROFITABLE")
        print("=" * 80)
        print(f"Limit at support + {best['limit_atr']:.1f} ATR")
        print(f"R/DD: {best['return_dd']:.2f}x | Return: {best['return']:+.1f}%")
        print(f"Win: {best['win_rate']:.1f}% | TP: {best['tp_rate']:.1f}% | Avg SL: {best['avg_sl']:.2f}%")
        print(f"Jun: ${best['jun']:+.2f} | Jul: ${best['jul']:+.2f} | Aug: ${best['aug']:+.2f} | Sep: ${best['sep']:+.2f}")
        print(f"Oct: ${best['oct']:+.2f} | Nov: ${best['nov']:+.2f} | Dec: ${best['dec']:+.2f}")
