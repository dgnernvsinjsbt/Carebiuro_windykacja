"""
Test Range20 filter on BOTH Jul-Aug and Sep-Dec

Find Range20 threshold that improves performance on BOTH periods
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("RANGE20 FILTER TESTING - BOTH PERIODS")
print("Find threshold that works on Jul-Aug AND Sep-Dec")
print("=" * 80)

exchange = ccxt.bingx({'enableRateLimit': True})

periods = [
    {
        'name': 'Jul-Aug',
        'start': datetime(2025, 7, 1, tzinfo=timezone.utc),
        'end': datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
    },
    {
        'name': 'Sep-Dec',
        'start': datetime(2025, 9, 16, tzinfo=timezone.utc),
        'end': datetime(2025, 12, 15, tzinfo=timezone.utc)
    }
]

def backtest_with_range20_filter(df, min_range20):
    """Backtest RSI 35/65 + ret_20 > 0% + Range20 > min_range20"""
    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['range_20']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Filters: ret_20 > 0% AND range_20 > min_range20
            if row['ret_20'] <= 0 or row['range_20'] < min_range20:
                i += 1
                continue

            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry_price = row['close']
                    sl_price = entry_price - (row['atr'] * 2.0)
                    tp_price = entry_price + (row['atr'] * 3.0)

                    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
                    risk_dollars = equity * 0.12
                    size = risk_dollars / (sl_distance_pct / 100)

                    position = {
                        'direction': 'LONG',
                        'entry': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size
                    }

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry_price = row['close']
                    sl_price = entry_price + (row['atr'] * 2.0)
                    tp_price = entry_price - (row['atr'] * 3.0)

                    sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
                    risk_dollars = equity * 0.12
                    size = risk_dollars / (sl_distance_pct / 100)

                    position = {
                        'direction': 'SHORT',
                        'entry': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size
                    }

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl'] > 0).sum() / len(df_t) * 100

    return {
        'trades': len(df_t),
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

# Download and prepare data for both periods
period_data = []

for period in periods:
    print(f"\nDownloading {period['name']}...")

    start_ts = int(period['start'].timestamp() * 1000)
    end_ts = int(period['end'].timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)
        except Exception as e:
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= period['start'].replace(tzinfo=None)) &
            (df['timestamp'] <= period['end'].replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Calculate indicators
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
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
    df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) /
                      df['low'].rolling(20).min()) * 100

    period_data.append({
        'name': period['name'],
        'df': df
    })

    print(f"  {len(df)} bars loaded")

# Test different Range20 thresholds
print("\n" + "=" * 80)
print("TESTING RANGE20 THRESHOLDS:")
print("=" * 80)

range20_thresholds = [0, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15]

results = []

for threshold in range20_thresholds:
    jul_aug_result = backtest_with_range20_filter(period_data[0]['df'], threshold)
    sep_dec_result = backtest_with_range20_filter(period_data[1]['df'], threshold)

    if jul_aug_result and sep_dec_result:
        # Calculate combined score
        combined_score = (jul_aug_result['return_dd'] + sep_dec_result['return_dd']) / 2

        results.append({
            'threshold': threshold,
            'jul_aug_trades': jul_aug_result['trades'],
            'jul_aug_win_rate': jul_aug_result['win_rate'],
            'jul_aug_return': jul_aug_result['return'],
            'jul_aug_dd': jul_aug_result['max_dd'],
            'jul_aug_r_dd': jul_aug_result['return_dd'],
            'sep_dec_trades': sep_dec_result['trades'],
            'sep_dec_win_rate': sep_dec_result['win_rate'],
            'sep_dec_return': sep_dec_result['return'],
            'sep_dec_dd': sep_dec_result['max_dd'],
            'sep_dec_r_dd': sep_dec_result['return_dd'],
            'combined_score': combined_score,
            'both_profitable': jul_aug_result['return'] > 0 and sep_dec_result['return'] > 0
        })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('combined_score', ascending=False)

print(f"\n| R20  | Jul-Aug |       |       | Sep-Dec |       |       | Combined | Both+ |")
print(f"| Min  | Trades  | Win%  | R/DD  | Trades  | Win%  | R/DD  | Score    | Prof? |")
print("|------|---------|-------|-------|---------|-------|-------|----------|-------|")

for idx, row in results_df.iterrows():
    both_mark = "✅" if row['both_profitable'] else "❌"
    best_mark = "🏆" if idx == results_df.index[0] else ""

    print(f"| {row['threshold']:4.0f} | {row['jul_aug_trades']:3.0f} | "
          f"{row['jul_aug_win_rate']:4.1f}% | {row['jul_aug_r_dd']:5.2f} | "
          f"{row['sep_dec_trades']:3.0f} | {row['sep_dec_win_rate']:4.1f}% | "
          f"{row['sep_dec_r_dd']:5.2f} | {row['combined_score']:6.2f}x | "
          f"{both_mark:5s} | {best_mark}")

# Best config
best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST RANGE20 THRESHOLD:")
print("=" * 80)

print(f"\nThreshold: Range20 > {best['threshold']:.0f}%")

print(f"\n📊 JUL-AUG PERFORMANCE:")
print(f"  Trades:     {best['jul_aug_trades']:.0f}")
print(f"  Win Rate:   {best['jul_aug_win_rate']:.1f}%")
print(f"  Return:     {best['jul_aug_return']:+.0f}%")
print(f"  Max DD:     {best['jul_aug_dd']:.1f}%")
print(f"  R/DD:       {best['jul_aug_r_dd']:.2f}x")

print(f"\n📊 SEP-DEC PERFORMANCE:")
print(f"  Trades:     {best['sep_dec_trades']:.0f}")
print(f"  Win Rate:   {best['sep_dec_win_rate']:.1f}%")
print(f"  Return:     {best['sep_dec_return']:+.0f}%")
print(f"  Max DD:     {best['sep_dec_dd']:.1f}%")
print(f"  R/DD:       {best['sep_dec_r_dd']:.2f}x")

print(f"\n⚖️  COMBINED:")
print(f"  Avg R/DD:   {best['combined_score']:.2f}x")
print(f"  Both Profitable: {'✅ YES' if best['both_profitable'] else '❌ NO'}")

if best['both_profitable'] and best['jul_aug_win_rate'] >= 50 and best['sep_dec_win_rate'] >= 50:
    print(f"\n✅ SUCCESS!")
    print(f"   Range20 > {best['threshold']:.0f}% improves strategy on BOTH periods")
    print(f"   Both periods profitable with 50%+ win rates")
elif best['both_profitable']:
    print(f"\n⚠️  PARTIAL SUCCESS")
    print(f"   Both periods profitable but win rates may need improvement")
else:
    print(f"\n❌ STILL FAILS")
    print(f"   One or both periods remain unprofitable")
    print(f"   May need additional filters or different approach")

results_df.to_csv('range20_filter_test_results.csv', index=False)
print(f"\n💾 Saved results to: range20_filter_test_results.csv")

print("\n" + "=" * 80)
