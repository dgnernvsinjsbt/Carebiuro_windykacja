#!/usr/bin/env python3
"""Test SHORT reversal strategy on DOGE (same as MELANIA)"""
import pandas as pd
import numpy as np

df = pd.read_csv('doge_6months_bingx_15m.csv')
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

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
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
    for pnl in trades_df['pnl_dollar']:
        equity_curve[-1] += pnl
        equity_curve.append(equity_curve[-1])

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
        'rsi': rsi_trigger,
        'offset': limit_atr_offset,
        'tp': tp_pct,
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
print("DOGE SHORT REVERSAL STRATEGY TEST")
print("Logic: RSI >X → swing low break → limit above → SHORT retest")
print("=" * 110)
print()

# Test grid: RSI 68-76 × Offset 0.4-1.0 × TP 5-10
results = []
total_configs = 0

for rsi in [68, 70, 72, 74, 76]:
    for offset in [0.4, 0.6, 0.8, 1.0]:
        for tp in [5, 6, 7, 8, 9, 10]:
            total_configs += 1
            r = test(rsi, offset, tp)
            if r:
                results.append(r)

print(f"Tested {total_configs} configs ({len(results)} had enough trades)")
print()

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("=" * 110)
    print("TOP 10 CONFIGS BY R/DD")
    print("=" * 110)
    print(f"{'#':<3} {'RSI':<5} {'Offset':<8} {'TP':<5} {'R/DD':<8} {'Return':<9} {'Trades':<7} {'Win%':<6} {'Months':<8}")
    print("-" * 110)

    for i, r in enumerate(results[:10], 1):
        status = "✅" if r['profitable_months'] == 7 else f"{r['profitable_months']}/7"
        print(f"{i:<3} >{r['rsi']:<4} {r['offset']:.1f}ATR{'':<3} {r['tp']:<4}% "
              f"{r['return_dd']:7.2f}x {r['return']:+8.1f}% {r['trades']:<7} "
              f"{r['win_rate']:5.1f}% {status:<8}")

    winner = results[0]
    print("\n" + "=" * 110)
    print("🎯 BEST DOGE CONFIG")
    print("=" * 110)
    print(f"RSI > {winner['rsi']} | Offset: {winner['offset']:.1f} ATR | TP: {winner['tp']}%")
    print(f"R/DD: {winner['return_dd']:.2f}x | Return: {winner['return']:+.1f}% | Max DD: {winner['max_dd']:.2f}%")
    print(f"Trades: {winner['trades']} | Win Rate: {winner['win_rate']:.1f}% | TP Rate: {winner['tp_rate']:.1f}%")
    print(f"Profitable months: {winner['profitable_months']}/7")
    print()
    print("Monthly:")
    print(f"  Jun: ${winner['jun']:+.2f} | Jul: ${winner['jul']:+.2f} | Aug: ${winner['aug']:+.2f} | Sep: ${winner['sep']:+.2f}")
    print(f"  Oct: ${winner['oct']:+.2f} | Nov: ${winner['nov']:+.2f} | Dec: ${winner['dec']:+.2f}")

    print("\n" + "=" * 110)
    print("📊 DOGE vs MELANIA COMPARISON")
    print("=" * 110)
    print(f"DOGE    (>{winner['rsi']} {winner['offset']:.1f}ATR {winner['tp']}%): R/DD {winner['return_dd']:6.2f}x | Ret {winner['return']:+7.1f}% | {winner['trades']} trades")
    print(f"MELANIA (>72 0.8ATR 10%): R/DD  53.96x | Ret +1330.4% | 45 trades")
    print()

    if winner['return_dd'] > 20:
        print("✅ DOGE strategy is STRONG!")
    elif winner['return_dd'] > 10:
        print("⚠️  DOGE strategy is viable but weaker than MELANIA")
    else:
        print("❌ DOGE strategy underperforms MELANIA significantly")

    all_green = [r for r in results if r['profitable_months'] == 7]
    if all_green:
        print(f"\n✅ Found {len(all_green)} configs with ALL 7 months profitable!")
    else:
        print("\n❌ No configs have all 7 months profitable")
