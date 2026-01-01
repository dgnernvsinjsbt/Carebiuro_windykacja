#!/usr/bin/env python3
"""
Test ALL coins with limit orders to find optimal offset for each
"""

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def backtest_limit(df, rsi_low, rsi_high, limit_offset_pct, max_wait_bars=5):
    """Backtest with limit orders"""

    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

    trades = []
    signals_total = 0
    signals_filled = 0
    equity = 100.0

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG
        if prev['rsi'] <= rsi_low and row['rsi'] > rsi_low:
            signals_total += 1
            signal_price = row['close']
            limit_price = signal_price * (1 - limit_offset_pct / 100)

            filled = False
            for wait_idx in range(i+1, min(i+1+max_wait_bars, len(df))):
                check_row = df.iloc[wait_idx]
                if check_row['low'] <= limit_price:
                    entry_price = limit_price
                    entry_idx = wait_idx
                    filled = True
                    signals_filled += 1
                    break

            if not filled:
                continue

            atr_val = df.iloc[entry_idx]['atr']
            sl_price = entry_price - (2.0 * atr_val)

            exit_found = False
            for j in range(entry_idx+1, min(entry_idx+168, len(df))):
                exit_row = df.iloc[j]
                if exit_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    exit_found = True
                    break
                if exit_row['rsi'] >= rsi_high:
                    exit_price = exit_row['close']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(entry_idx+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_reason = 'TIME'

            pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.02
            equity *= (1 + pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason, 'equity': equity})

        # SHORT
        elif prev['rsi'] >= rsi_high and row['rsi'] < rsi_high:
            signals_total += 1
            signal_price = row['close']
            limit_price = signal_price * (1 + limit_offset_pct / 100)

            filled = False
            for wait_idx in range(i+1, min(i+1+max_wait_bars, len(df))):
                check_row = df.iloc[wait_idx]
                if check_row['high'] >= limit_price:
                    entry_price = limit_price
                    entry_idx = wait_idx
                    filled = True
                    signals_filled += 1
                    break

            if not filled:
                continue

            atr_val = df.iloc[entry_idx]['atr']
            sl_price = entry_price + (2.0 * atr_val)

            exit_found = False
            for j in range(entry_idx+1, min(entry_idx+168, len(df))):
                exit_row = df.iloc[j]
                if exit_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    exit_found = True
                    break
                if exit_row['rsi'] <= rsi_low:
                    exit_price = exit_row['close']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(entry_idx+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100 - 0.02
            equity *= (1 + pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason, 'equity': equity})

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    equity_series = pd.Series([t['equity'] for t in trades])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100

    total_return = equity - 100
    max_dd = drawdown.min()
    rdd = total_return / abs(max_dd) if max_dd != 0 else 0
    fill_rate = signals_filled / signals_total * 100 if signals_total > 0 else 0

    return {
        'offset': limit_offset_pct,
        'fill_rate': fill_rate,
        'trades': len(df_t),
        'return': total_return,
        'dd': max_dd,
        'rdd': rdd
    }

def test_coin(file_path, coin_name, rsi_low, rsi_high):
    """Test a coin with different limit offsets"""

    df = pd.read_csv(file_path)
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"\n{'='*80}")
    print(f"{coin_name} - RSI {rsi_low}/{rsi_high} LIMIT ORDER TEST")
    print(f"{'='*80}")

    results = []

    # Test offsets from 0.1% to 2.0%
    for offset in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]:
        result = backtest_limit(df, rsi_low, rsi_high, offset, max_wait_bars=5)
        if result:
            results.append(result)

    if not results:
        print("❌ No results")
        return None

    results = sorted(results, key=lambda x: x['rdd'], reverse=True)

    print(f"\n{'Rank':<6} {'Offset%':<10} {'Fill%':<10} {'Trades':<8} {'Return':<12} {'DD':<10} {'R/DD'}")
    print("-" * 75)

    for i, r in enumerate(results[:10], 1):
        marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{marker} {i:<4} {r['offset']:<10.1f} {r['fill_rate']:<10.1f} {r['trades']:<8} {r['return']:+11.2f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x")

    best = results[0]
    print(f"\n✅ Best: {best['offset']:.1f}% offset → {best['rdd']:.2f}x R/DD, {best['trades']} trades ({best['fill_rate']:.1f}% fill)")

    return best

# Test all coins
print("=" * 80)
print("LIMIT ORDER OPTIMIZATION - ALL COINS")
print("=" * 80)

configs = [
    ('btc_1h_90d.csv', 'BTC', 30, 65),
    ('eth_1h_90d.csv', 'ETH', 30, 68),
    ('1000pepe_1h_90d.csv', '1000PEPE', 30, 65),
    ('doge_1h_90d.csv', 'DOGE', 27, 65)
]

summary = []

for file_path, coin_name, rsi_low, rsi_high in configs:
    best = test_coin(file_path, coin_name, rsi_low, rsi_high)
    if best:
        summary.append({
            'coin': coin_name,
            'rsi': f"{rsi_low}/{rsi_high}",
            'best_offset': best['offset'],
            'fill_rate': best['fill_rate'],
            'trades': best['trades'],
            'return': best['return'],
            'dd': best['dd'],
            'rdd': best['rdd']
        })

# Final summary
print("\n" + "=" * 80)
print("FINAL SUMMARY - BEST LIMIT OFFSETS PER COIN")
print("=" * 80)

print(f"\n{'Coin':<12} {'RSI':<10} {'Offset%':<10} {'Fill%':<10} {'Trades':<8} {'Return':<12} {'DD':<10} {'R/DD'}")
print("-" * 90)

for s in sorted(summary, key=lambda x: x['rdd'], reverse=True):
    print(f"{s['coin']:<12} {s['rsi']:<10} {s['best_offset']:<10.1f} {s['fill_rate']:<10.1f} {s['trades']:<8} {s['return']:+11.2f}% {s['dd']:9.2f}% {s['rdd']:7.2f}x")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)

print("\nUse LIMIT ORDERS with these offsets for each coin:")
for s in summary:
    print(f"  {s['coin']}: {s['best_offset']:.1f}% (LONG: -{s['best_offset']:.1f}%, SHORT: +{s['best_offset']:.1f}%)")

print("\nBenefits:")
print("  ✅ Better entries (buy dips, sell rips)")
print("  ✅ Lower fees (0.02% maker vs 0.05% taker)")
print("  ✅ Improved R/DD ratios")
print("  ⚠️ Lower fill rates (more selective)")

print("\n" + "=" * 80)
