"""
Test RSI mean reversion on 5m and 15m timeframes (last 3 months)
Goal: Faster compounding with more trade opportunities
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("LOWER TIMEFRAME TESTING - 5m & 15m")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)  # 3 months

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

def download_data(timeframe, name):
    print(f"\nDownloading MELANIA {timeframe} data ({name})...")

    all_candles = []
    current_ts = start_ts

    # Determine interval in ms
    if timeframe == '5m':
        interval_ms = 5 * 60 * 1000
    elif timeframe == '15m':
        interval_ms = 15 * 60 * 1000
    elif timeframe == '1h':
        interval_ms = 60 * 60 * 1000

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe=timeframe, since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + interval_ms
            time.sleep(0.5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"Downloaded {len(df)} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")
    return df

# Download both timeframes
df_5m = download_data('5m', '5-minute')
df_15m = download_data('15m', '15-minute')

def calculate_indicators(df):
    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()

    # 24h range (288 bars for 5m, 96 bars for 15m)
    if len(df) > 0:
        # Detect timeframe from first few bars
        time_diff = (df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds() / 60
        if time_diff <= 5:
            bars_24h = 288  # 5m
        elif time_diff <= 15:
            bars_24h = 96   # 15m
        else:
            bars_24h = 24   # 1h

        df['high_24h'] = df['high'].rolling(bars_24h).max()
        df['low_24h'] = df['low'].rolling(bars_24h).min()
        df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

    return df

print("\nCalculating indicators...")
df_5m = calculate_indicators(df_5m)
df_15m = calculate_indicators(df_15m)

def backtest(df, timeframe, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, risk_pct, min_range_24h):
    trades = []
    equity = 100.0

    # Start after warmup
    i = 300
    while i < len(df):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
            i += 1
            continue

        has_signal = False
        direction = None

        if prev_row['rsi'] < rsi_low and row['rsi'] >= rsi_low:
            has_signal = True
            direction = 'LONG'
        elif prev_row['rsi'] > rsi_high and row['rsi'] <= rsi_high:
            has_signal = True
            direction = 'SHORT'

        if not has_signal:
            i += 1
            continue

        # 24h range filter
        if pd.notna(row['range_24h']) and row['range_24h'] < min_range_24h:
            i += 1
            continue

        signal_price = row['close']
        if direction == 'LONG':
            entry_price = signal_price * (1 + limit_pct / 100)
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)
        else:
            entry_price = signal_price * (1 - limit_pct / 100)
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

        risk_dollars = equity * (risk_pct / 100)
        sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100 if direction == 'LONG' else abs((sl_price - entry_price) / entry_price) * 100
        position_size_dollars = risk_dollars / (sl_distance_pct / 100)

        # Fill check (wait max 3 bars)
        filled = False
        fill_idx = None
        for j in range(i + 1, min(i + 4, len(df))):
            if direction == 'LONG' and df.iloc[j]['low'] <= entry_price:
                filled = True
                fill_idx = j
                break
            elif direction == 'SHORT' and df.iloc[j]['high'] >= entry_price:
                filled = True
                fill_idx = j
                break

        if not filled:
            i += 1
            continue

        # Exit logic
        exit_idx = None
        exit_price = None
        exit_type = None

        for k in range(fill_idx + 1, len(df)):
            bar = df.iloc[k]
            prev_bar = df.iloc[k-1]

            if direction == 'LONG':
                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] > rsi_high and bar['rsi'] <= rsi_high:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break
            else:
                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] < rsi_low and bar['rsi'] >= rsi_low:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

        if exit_idx is None:
            i += 1
            continue

        if direction == 'LONG':
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_before_fees = position_size_dollars * (price_change_pct / 100)
        fees = position_size_dollars * 0.001
        pnl_dollars = pnl_before_fees - fees
        equity += pnl_dollars

        trades.append({'pnl_dollars': pnl_dollars, 'equity': equity})
        i = exit_idx + 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100

    return {
        'timeframe': timeframe,
        'rsi': f"{rsi_low}/{rsi_high}",
        'offset': limit_pct,
        'sl': sl_mult,
        'tp': tp_mult,
        'risk': risk_pct,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity
    }

# Test configs
configs = [
    # Winner from 1h
    {'rsi_low': 25, 'rsi_high': 70, 'limit_pct': 0.3, 'sl_mult': 1.5, 'tp_mult': 2.5, 'risk_pct': 20, 'min_range_24h': 15.0},
    # Tighter RSI
    {'rsi_low': 30, 'rsi_high': 65, 'limit_pct': 0.3, 'sl_mult': 1.5, 'tp_mult': 2.5, 'risk_pct': 20, 'min_range_24h': 15.0},
    # Wider offset
    {'rsi_low': 25, 'rsi_high': 70, 'limit_pct': 0.5, 'sl_mult': 1.5, 'tp_mult': 2.5, 'risk_pct': 20, 'min_range_24h': 15.0},
    # Lower risk
    {'rsi_low': 25, 'rsi_high': 70, 'limit_pct': 0.3, 'sl_mult': 1.5, 'tp_mult': 2.5, 'risk_pct': 15, 'min_range_24h': 15.0},
    # Tighter SL/TP
    {'rsi_low': 25, 'rsi_high': 70, 'limit_pct': 0.3, 'sl_mult': 1.0, 'tp_mult': 2.0, 'risk_pct': 20, 'min_range_24h': 15.0},
]

print("\nRunning backtests...")
results = []

for config in configs:
    print(f"  Testing RSI {config['rsi_low']}/{config['rsi_high']}, {config['limit_pct']}% offset, {config['sl_mult']}x SL, {config['tp_mult']}x TP, {config['risk_pct']}% risk...")

    # 5m
    res_5m = backtest(df_5m, '5m', **config)
    if res_5m:
        results.append(res_5m)

    # 15m
    res_15m = backtest(df_15m, '15m', **config)
    if res_15m:
        results.append(res_15m)

print(f"\nDone! {len(results)} results")

# Sort by R/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display
print("\n" + "=" * 80)
print("RESULTS (by R/DD):")
print("=" * 80)

print("\n| # | TF  | RSI    | Off% | SL  | TP  | Risk | Return  | DD     | R/DD   | Trades | Win%  | Final $ |")
print("|---|-----|--------|------|-----|-----|------|---------|--------|--------|--------|-------|---------|")

for i, (idx, row) in enumerate(results_df.head(10).iterrows(), 1):
    highlight = "🏆" if i == 1 else ""
    print(f"| {i:2d} | {row['timeframe']:3s} | {row['rsi']:6s} | {row['offset']:4.1f} | {row['sl']:3.1f} | {row['tp']:3.1f} | "
          f"{row['risk']:4.0f}% | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
          f"{row['trades']:3.0f} | {row['win_rate']:4.1f}% | ${row['final_equity']:6.0f} | {highlight}")

# Best per timeframe
print("\n" + "=" * 80)
print("BEST BY TIMEFRAME:")
print("=" * 80)

for tf in ['5m', '15m']:
    tf_results = results_df[results_df['timeframe'] == tf]
    if len(tf_results) > 0:
        best = tf_results.iloc[0]
        print(f"\n🏆 {tf}:")
        print(f"  Config: RSI {best['rsi']}, {best['offset']}% offset, {best['sl']}x SL, {best['tp']}x TP, {best['risk']}% risk")
        print(f"  Return: {best['return']:+.2f}%")
        print(f"  Max DD: {best['max_dd']:.2f}%")
        print(f"  R/DD: {best['return_dd']:.2f}x")
        print(f"  Trades: {best['trades']:.0f} ({best['trades'] / 3:.1f}/month avg)")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Final Equity: ${best['final_equity']:,.2f}")

print("\n" + "=" * 80)
