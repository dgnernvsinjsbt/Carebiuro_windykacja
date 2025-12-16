#!/usr/bin/env python3
"""
Test ETH RSI 30/68 with LIMIT orders instead of MARKET
LONG: Limit BELOW signal price (buy dip)
SHORT: Limit ABOVE signal price (sell rip)
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

def backtest_with_limit(df, limit_offset_pct, max_wait_bars=5):
    """
    Backtest RSI 30/68 with limit orders

    limit_offset_pct: e.g. 0.5 means:
        - LONG: place limit 0.5% BELOW signal price
        - SHORT: place limit 0.5% ABOVE signal price
    max_wait_bars: max bars to wait for limit fill (else cancel)
    """

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

        # LONG SIGNAL
        if prev['rsi'] <= 30 and row['rsi'] > 30:
            signals_total += 1
            signal_price = row['close']
            signal_time = row['timestamp']

            # Place limit BELOW market
            limit_price = signal_price * (1 - limit_offset_pct / 100)

            # Check if limit fills in next max_wait_bars
            filled = False
            for wait_idx in range(i+1, min(i+1+max_wait_bars, len(df))):
                check_row = df.iloc[wait_idx]

                # Limit fills if price touches/goes below limit
                if check_row['low'] <= limit_price:
                    entry_price = limit_price
                    entry_time = check_row['timestamp']
                    entry_idx = wait_idx
                    filled = True
                    signals_filled += 1
                    break

            if not filled:
                continue  # Signal didn't fill, skip

            # Now find exit from entry point
            atr_val = df.iloc[entry_idx]['atr']
            sl_price = entry_price - (2.0 * atr_val)

            exit_found = False
            for j in range(entry_idx+1, min(entry_idx+168, len(df))):
                exit_row = df.iloc[j]

                if exit_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                if exit_row['rsi'] >= 68:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(entry_idx+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            # Calculate PnL with 0.02% maker fee (limit order)
            pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.02  # maker fee
            equity *= (1 + pnl_pct / 100)

            trades.append({
                'direction': 'LONG',
                'signal_price': signal_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'equity': equity
            })

        # SHORT SIGNAL
        elif prev['rsi'] >= 68 and row['rsi'] < 68:
            signals_total += 1
            signal_price = row['close']
            signal_time = row['timestamp']

            # Place limit ABOVE market
            limit_price = signal_price * (1 + limit_offset_pct / 100)

            filled = False
            for wait_idx in range(i+1, min(i+1+max_wait_bars, len(df))):
                check_row = df.iloc[wait_idx]

                # Limit fills if price touches/goes above limit
                if check_row['high'] >= limit_price:
                    entry_price = limit_price
                    entry_time = check_row['timestamp']
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
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                if exit_row['rsi'] <= 30:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(entry_idx+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100 - 0.02  # maker fee
            equity *= (1 + pnl_pct / 100)

            trades.append({
                'direction': 'SHORT',
                'signal_price': signal_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'equity': equity
            })

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
        'signals_total': signals_total,
        'signals_filled': signals_filled,
        'fill_rate': fill_rate,
        'trades': len(df_t),
        'return': total_return,
        'dd': max_dd,
        'rdd': rdd,
        'wr': (df_t['pnl_pct'] > 0).mean() * 100,
        'avg_win': df_t[df_t['pnl_pct'] > 0]['pnl_pct'].mean() if len(df_t[df_t['pnl_pct'] > 0]) > 0 else 0,
        'avg_loss': df_t[df_t['pnl_pct'] <= 0]['pnl_pct'].mean() if len(df_t[df_t['pnl_pct'] <= 0]) > 0 else 0,
        'tp_rate': (df_t['exit_reason'] == 'TP').mean() * 100
    }

# Load ETH data
df = pd.read_csv('eth_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 90)
print("ETH RSI 30/68 - LIMIT ORDER OPTIMIZATION")
print("=" * 90)
print(f"\nData: {len(df):,} candles | {df['timestamp'].min()} to {df['timestamp'].max()}")
print("\nStrategy: LONG limit BELOW signal, SHORT limit ABOVE signal")
print("Fee: 0.02% maker (limit order) vs 0.05% taker (market)")
print("Max wait: 5 bars for limit fill")

# Test market order baseline first (0% offset = instant fill)
print(f"\n" + "-" * 90)
print("BASELINE: Market Orders (0% offset, instant fill, 0.05% taker fee)")
print("-" * 90)

# Calculate baseline with market orders (0.05% fee)
df_base = df.copy()
df_base['rsi'] = calculate_rsi(df_base['close'], 14)
df_base['atr'] = calculate_atr(df_base['high'], df_base['low'], df_base['close'], 14)

trades_base = []
equity_base = 100.0

for i in range(50, len(df_base)):
    row = df_base.iloc[i]
    prev = df_base.iloc[i-1]

    if prev['rsi'] <= 30 and row['rsi'] > 30:
        entry_price = row['close']
        atr_val = row['atr']
        sl_price = entry_price - (2.0 * atr_val)

        exit_found = False
        for j in range(i+1, min(i+168, len(df_base))):
            exit_row = df_base.iloc[j]
            if exit_row['low'] <= sl_price:
                exit_price = sl_price
                exit_reason = 'SL'
                exit_found = True
                break
            if exit_row['rsi'] >= 68:
                exit_price = exit_row['close']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df_base)-1)
            exit_price = df_base.iloc[j]['close']
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.05  # taker fee
        equity_base *= (1 + pnl_pct / 100)
        trades_base.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason, 'equity': equity_base})

    elif prev['rsi'] >= 68 and row['rsi'] < 68:
        entry_price = row['close']
        atr_val = row['atr']
        sl_price = entry_price + (2.0 * atr_val)

        exit_found = False
        for j in range(i+1, min(i+168, len(df_base))):
            exit_row = df_base.iloc[j]
            if exit_row['high'] >= sl_price:
                exit_price = sl_price
                exit_reason = 'SL'
                exit_found = True
                break
            if exit_row['rsi'] <= 30:
                exit_price = exit_row['close']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df_base)-1)
            exit_price = df_base.iloc[j]['close']
            exit_reason = 'TIME'

        pnl_pct = (entry_price - exit_price) / entry_price * 100 - 0.05  # taker fee
        equity_base *= (1 + pnl_pct / 100)
        trades_base.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason, 'equity': equity_base})

df_trades_base = pd.DataFrame(trades_base)
equity_series_base = pd.Series([t['equity'] for t in trades_base])
running_max_base = equity_series_base.cummax()
drawdown_base = (equity_series_base - running_max_base) / running_max_base * 100
total_return_base = equity_base - 100
max_dd_base = drawdown_base.min()
rdd_base = total_return_base / abs(max_dd_base)

print(f"\nMarket: {len(df_trades_base)} trades, {total_return_base:+.2f}% return, {max_dd_base:.2f}% DD, {rdd_base:.2f}x R/DD")
print(f"  Fill rate: 100% (all signals fill instantly)")
print(f"  WR: {(df_trades_base['pnl_pct'] > 0).mean() * 100:.1f}%")
print(f"  TP rate: {(df_trades_base['exit_reason'] == 'TP').mean() * 100:.1f}%")

# Test limit orders
print(f"\n" + "-" * 90)
print("LIMIT ORDER TESTS (0.1% - 2.0% offsets)")
print("-" * 90)

results = []

for offset in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]:
    result = backtest_with_limit(df, offset, max_wait_bars=5)
    if result:
        results.append(result)

# Sort by R/DD
results = sorted(results, key=lambda x: x['rdd'], reverse=True)

print(f"\n{'Rank':<6} {'Offset%':<10} {'Fill%':<10} {'Trades':<8} {'Return':<12} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'vs Base'}")
print("-" * 110)

for i, r in enumerate(results, 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
    vs_base = (r['rdd'] - rdd_base) / rdd_base * 100

    status = ""
    if r['rdd'] > rdd_base:
        status = f"✅ {vs_base:+.1f}%"
    elif r['rdd'] < rdd_base * 0.95:
        status = f"❌ {vs_base:+.1f}%"
    else:
        status = f"⚠️ {vs_base:+.1f}%"

    print(f"{marker} {i:<4} {r['offset']:<10.1f} {r['fill_rate']:<10.1f} {r['trades']:<8} {r['return']:+11.2f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['tp_rate']:7.1f}% {status}")

print(f"\n" + "=" * 90)
print("RECOMMENDATION")
print("=" * 90)

best = results[0]

print(f"\nBaseline (Market Orders):")
print(f"  {len(df_trades_base)} trades, {total_return_base:+.2f}% return, {max_dd_base:.2f}% DD, {rdd_base:.2f}x R/DD")
print(f"  Fee: 0.05% taker")

print(f"\nBest Limit Order ({best['offset']:.1f}% offset):")
print(f"  {best['trades']} trades, {best['return']:+.2f}% return, {best['dd']:.2f}% DD, {best['rdd']:.2f}x R/DD")
print(f"  Fill rate: {best['fill_rate']:.1f}%")
print(f"  Fee: 0.02% maker (0.03% saved per trade)")

improvement = (best['rdd'] - rdd_base) / rdd_base * 100

if best['rdd'] > rdd_base:
    print(f"\n✅ Limit orders BETTER: {improvement:+.1f}% R/DD improvement")
    print(f"   Use {best['offset']:.1f}% offset (LONG: -{best['offset']:.1f}%, SHORT: +{best['offset']:.1f}%)")
else:
    print(f"\n❌ Limit orders WORSE: {improvement:+.1f}% R/DD degradation")
    print(f"   Stick with market orders")

print("\n" + "=" * 90)
