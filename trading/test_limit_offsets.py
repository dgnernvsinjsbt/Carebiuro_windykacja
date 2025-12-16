#!/usr/bin/env python3
"""Test different limit offset types: ATR vs flat %"""
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

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

def test(offset_type, offset_value):
    """
    offset_type: 'atr' or 'flat'
    offset_value: if atr, it's ATR multiplier; if flat, it's %
    """
    rsi_trigger = 72
    lookback = 5
    tp_pct = 10.0
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

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                # Calculate limit price based on type
                if offset_type == 'atr':
                    atr = row['atr']
                    limit_price = swing_low + (atr * offset_value)
                else:  # flat
                    limit_price = swing_low * (1 + offset_value / 100)

                swing_high_for_sl = find_swing_high(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

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
                    'pnl_dollar': pnl_dollar,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                })

                limit_pending = False

    if len(trades) < 5:
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
    tp_rate = len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df) * 100

    profitable_months = sum([1 for x in [jun, jul, aug, sep, oct, nov, dec] if x > 0])

    return {
        'offset_type': offset_type,
        'offset_value': offset_value,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'jun': jun,
        'jul': jul,
        'aug': aug,
        'sep': sep,
        'oct': oct,
        'nov': nov,
        'dec': dec,
        'profitable_months': profitable_months
    }

print("=" * 110)
print("LIMIT OFFSET OPTIMIZATION (TP 10% fixed)")
print("=" * 110)
print()

# Test ATR-based offsets
print("=" * 110)
print("ATR-BASED OFFSETS (0.1 to 1.0 ATR)")
print("=" * 110)

atr_results = []
for offset in [round(x * 0.1, 1) for x in range(1, 11)]:  # 0.1 to 1.0
    r = test('atr', offset)
    if r:
        atr_results.append(r)
        status = "✅" if r['profitable_months'] == 7 else f"({r['profitable_months']}/7)"
        print(f"\nOffset = {offset:.1f} ATR {status}")
        print(f"  R/DD: {r['return_dd']:6.2f}x | Ret: {r['return']:+8.1f}% | DD: {r['max_dd']:7.2f}%")
        print(f"  Trades: {r['trades']:2d} | Win: {r['win_rate']:5.1f}% | TP Rate: {r['tp_rate']:5.1f}%")
        print(f"  Jun: ${r['jun']:+6.2f} | Jul: ${r['jul']:+6.2f} | Aug: ${r['aug']:+6.2f} | Sep: ${r['sep']:+6.2f}")
        print(f"  Oct: ${r['oct']:+6.2f} | Nov: ${r['nov']:+6.2f} | Dec: ${r['dec']:+7.2f}")

# Test flat % offsets
print("\n" + "=" * 110)
print("FLAT % OFFSETS (0.2% to 1.0%)")
print("=" * 110)

flat_results = []
for offset in [0.2, 0.4, 0.6, 0.8, 1.0]:
    r = test('flat', offset)
    if r:
        flat_results.append(r)
        status = "✅" if r['profitable_months'] == 7 else f"({r['profitable_months']}/7)"
        print(f"\nOffset = {offset:.1f}% {status}")
        print(f"  R/DD: {r['return_dd']:6.2f}x | Ret: {r['return']:+8.1f}% | DD: {r['max_dd']:7.2f}%")
        print(f"  Trades: {r['trades']:2d} | Win: {r['win_rate']:5.1f}% | TP Rate: {r['tp_rate']:5.1f}%")
        print(f"  Jun: ${r['jun']:+6.2f} | Jul: ${r['jul']:+6.2f} | Aug: ${r['aug']:+6.2f} | Sep: ${r['sep']:+6.2f}")
        print(f"  Oct: ${r['oct']:+6.2f} | Nov: ${r['nov']:+6.2f} | Dec: ${r['dec']:+7.2f}")

# Compare best from each
print("\n" + "=" * 110)
print("COMPARISON: BEST FROM EACH METHOD")
print("=" * 110)

if atr_results:
    atr_results.sort(key=lambda x: x['return_dd'], reverse=True)
    best_atr = atr_results[0]
    print(f"\n🏆 BEST ATR: {best_atr['offset_value']:.1f} ATR")
    print(f"   R/DD: {best_atr['return_dd']:.2f}x | Return: {best_atr['return']:+.1f}% | Win: {best_atr['win_rate']:.1f}%")
    print(f"   Profitable months: {best_atr['profitable_months']}/7")

if flat_results:
    flat_results.sort(key=lambda x: x['return_dd'], reverse=True)
    best_flat = flat_results[0]
    print(f"\n🏆 BEST FLAT %: {best_flat['offset_value']:.1f}%")
    print(f"   R/DD: {best_flat['return_dd']:.2f}x | Return: {best_flat['return']:+.1f}% | Win: {best_flat['win_rate']:.1f}%")
    print(f"   Profitable months: {best_flat['profitable_months']}/7")

# Overall winner
all_results = atr_results + flat_results
all_results.sort(key=lambda x: x['return_dd'], reverse=True)
winner = all_results[0]

print("\n" + "=" * 110)
print("🎯 OVERALL WINNER")
print("=" * 110)
if winner['offset_type'] == 'atr':
    offset_label = f"{winner['offset_value']:.1f} ATR"
else:
    offset_label = f"{winner['offset_value']:.1f}%"
print(f"Offset = {offset_label} ({winner['offset_type']})")
print(f"R/DD: {winner['return_dd']:.2f}x | Return: {winner['return']:+.1f}% | Max DD: {winner['max_dd']:.2f}%")
print(f"Trades: {winner['trades']} | Win Rate: {winner['win_rate']:.1f}% | TP Rate: {winner['tp_rate']:.1f}%")
print(f"Profitable months: {winner['profitable_months']}/7")
print()
print("Monthly breakdown:")
print(f"  Jun: ${winner['jun']:+.2f} | Jul: ${winner['jul']:+.2f} | Aug: ${winner['aug']:+.2f} | Sep: ${winner['sep']:+.2f}")
print(f"  Oct: ${winner['oct']:+.2f} | Nov: ${winner['nov']:+.2f} | Dec: ${winner['dec']:+.2f}")
