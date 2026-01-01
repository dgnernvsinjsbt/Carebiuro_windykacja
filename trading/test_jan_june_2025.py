"""
Test original strategy on Jan-Jun 2025 (month by month)

Strategy: RSI 35/65 + ret_20 > 0%, 2x SL, 3x TP, 12% risk

Find which months work, which don't, and what distinguishes them
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("MONTHLY ANALYSIS: JAN-JUN 2025")
print("Test strategy on each month to find good vs bad periods")
print("=" * 80)

exchange = ccxt.bingx({'enableRateLimit': True})

# Define all months
months = [
    {'name': 'Jan 2025', 'start': datetime(2025, 1, 1, tzinfo=timezone.utc), 'end': datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)},
    {'name': 'Feb 2025', 'start': datetime(2025, 2, 1, tzinfo=timezone.utc), 'end': datetime(2025, 2, 28, 23, 59, 59, tzinfo=timezone.utc)},
    {'name': 'Mar 2025', 'start': datetime(2025, 3, 1, tzinfo=timezone.utc), 'end': datetime(2025, 3, 31, 23, 59, 59, tzinfo=timezone.utc)},
    {'name': 'Apr 2025', 'start': datetime(2025, 4, 1, tzinfo=timezone.utc), 'end': datetime(2025, 4, 30, 23, 59, 59, tzinfo=timezone.utc)},
    {'name': 'May 2025', 'start': datetime(2025, 5, 1, tzinfo=timezone.utc), 'end': datetime(2025, 5, 31, 23, 59, 59, tzinfo=timezone.utc)},
    {'name': 'Jun 2025', 'start': datetime(2025, 6, 1, tzinfo=timezone.utc), 'end': datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)},
]

def backtest_month(df, month_name):
    """Backtest strategy on a single month"""
    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
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
                    trades.append({'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Filter: ret_20 > 0%
            if row['ret_20'] <= 0:
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

                    position = {'direction': 'LONG', 'entry': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'size': size}

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry_price = row['close']
                    sl_price = entry_price + (row['atr'] * 2.0)
                    tp_price = entry_price - (row['atr'] * 3.0)

                    sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
                    risk_dollars = equity * 0.12
                    size = risk_dollars / (sl_distance_pct / 100)

                    position = {'direction': 'SHORT', 'entry': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'size': size}

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100

    return {
        'month': month_name,
        'trades': len(df_t),
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

# Download and test each month
results = []

for month in months:
    print(f"\nDownloading {month['name']}...")

    start_ts = int(month['start'].timestamp() * 1000)
    end_ts = int(month['end'].timestamp() * 1000)

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

    if len(all_candles) == 0:
        print(f"  No data for {month['name']}")
        continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= month['start'].replace(tzinfo=None)) & (df['timestamp'] <= month['end'].replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
    df['volatility_96'] = df['close'].rolling(96).std() / df['close'].rolling(96).mean() * 100
    df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100

    print(f"  {len(df)} bars loaded")

    result = backtest_month(df, month['name'])

    if result:
        result['avg_range_96'] = df['range_96'].mean()
        result['avg_volatility_96'] = df['volatility_96'].mean()
        result['avg_ret_288'] = df['ret_288'].mean()
        result['price_change'] = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100

        results.append(result)
        print(f"  {result['trades']} trades, {result['win_rate']:.1f}% win, {result['return']:+.0f}%, {result['return_dd']:.2f}x R/DD")

results.append({'month': 'Jul-Aug 2025', 'trades': 57, 'win_rate': 45.6, 'return': 4.18, 'max_dd': -79.70, 'return_dd': 0.05, 'final_equity': 104.18, 'avg_range_96': 9.46, 'avg_volatility_96': 1.97, 'avg_ret_288': 0.28, 'price_change': -5.0})
results.append({'month': 'Sep-Dec 2025', 'trades': 53, 'win_rate': 64.2, 'return': 1685.86, 'max_dd': -41.32, 'return_dd': 40.80, 'final_equity': 1785.86, 'avg_range_96': 15.52, 'avg_volatility_96': 2.35, 'avg_ret_288': -1.13, 'price_change': -44.62})

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("ALL MONTHS RANKED BY R/DD:")
print("=" * 80)

print(f"\n| # | Month | Trades | Win% | Return | DD | R/DD | Range96 | Vol96 | ret288 | Price% | Status |")
print("|---|-------|--------|------|--------|--------|------|---------|-------|--------|--------|--------|")

for i, (idx, row) in enumerate(results_df.iterrows(), 1):
    status = "✅ GOOD" if row['return_dd'] >= 5 else ("⚠️  OK" if row['return_dd'] >= 1 else "❌ BAD")
    highlight = "🏆" if i == 1 else ""

    print(f"| {i:2d} | {row['month']:<14s} | {row['trades']:3.0f} | {row['win_rate']:4.1f}% | {row['return']:+6.0f}% | {row['max_dd']:6.1f}% | {row['return_dd']:4.2f} | {row['avg_range_96']:7.1f} | {row['avg_volatility_96']:5.2f} | {row['avg_ret_288']:+6.2f}% | {row['price_change']:+6.1f}% | {status:8s} | {highlight}")

good_months = results_df[results_df['return_dd'] >= 3]
bad_months = results_df[results_df['return_dd'] < 1]

if len(good_months) > 0 and len(bad_months) > 0:
    print("\n" + "=" * 80)
    print("GOOD vs BAD MONTHS:")
    print("=" * 80)
    
    print(f"\n{'Metric':<20} | {'GOOD':<12} | {'BAD':<12} | {'Diff %':<10}")
    print("-" * 60)
    
    for metric in ['avg_range_96', 'avg_volatility_96', 'avg_ret_288', 'price_change']:
        good_avg = good_months[metric].mean()
        bad_avg = bad_months[metric].mean()
        diff_pct = ((good_avg - bad_avg) / abs(bad_avg) * 100) if bad_avg != 0 else 0
        marker = " ⭐⭐⭐" if abs(diff_pct) > 50 else (" ⭐⭐" if abs(diff_pct) > 30 else (" ⭐" if abs(diff_pct) > 15 else ""))
        print(f"{metric:<20} | {good_avg:>11.2f} | {bad_avg:>11.2f} | {diff_pct:>+9.1f}%{marker}")

results_df.to_csv('monthly_results_jan_dec_2025.csv', index=False)
print(f"\n💾 Saved: monthly_results_jan_dec_2025.csv")
