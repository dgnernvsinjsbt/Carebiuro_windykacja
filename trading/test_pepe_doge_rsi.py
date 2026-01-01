#!/usr/bin/env python3
"""Test RSI 30/65 strategy on 1000PEPE and DOGE"""

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

def backtest_rsi(df, coin_name, rsi_low=30, rsi_high=65, atr_mult=2.0):
    """Backtest RSI strategy with 100% compounding"""

    # Calculate indicators
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

    trades = []
    equity = 100.0  # Start with $100

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG signal
        if prev['rsi'] <= rsi_low and row['rsi'] > rsi_low:
            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']
            sl_price = entry_price - (atr_mult * atr_val)

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]

                # Stop loss
                if exit_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                # RSI target
                if exit_row['rsi'] >= rsi_high:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            equity_before = equity
            equity = equity * (1 + pnl_pct / 100)

            trades.append({
                'direction': 'LONG',
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'equity_before': equity_before,
                'equity_after': equity
            })

        # SHORT signal
        elif prev['rsi'] >= rsi_high and row['rsi'] < rsi_high:
            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']
            sl_price = entry_price + (atr_mult * atr_val)

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]

                if exit_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                if exit_row['rsi'] <= rsi_low:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100
            equity_before = equity
            equity = equity * (1 + pnl_pct / 100)

            trades.append({
                'direction': 'SHORT',
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'equity_before': equity_before,
                'equity_after': equity
            })

    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    # Calculate metrics
    df_trades['cum_pnl'] = df_trades['pnl_pct'].cumsum()
    equity_series = pd.Series([t['equity_after'] for t in trades])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100

    total_return = (equity - 100)
    max_dd = drawdown.min()
    rdd = total_return / abs(max_dd) if max_dd != 0 else 0

    df_trades['hold_hours'] = (df_trades['exit_time'] - df_trades['entry_time']).dt.total_seconds() / 3600

    return {
        'coin': coin_name,
        'trades': len(df_trades),
        'return': total_return,
        'dd': max_dd,
        'rdd': rdd,
        'wr': (df_trades['pnl_pct'] > 0).mean() * 100,
        'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if len(df_trades[df_trades['pnl_pct'] > 0]) > 0 else 0,
        'avg_loss': df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if len(df_trades[df_trades['pnl_pct'] <= 0]) > 0 else 0,
        'avg_hold': df_trades['hold_hours'].mean(),
        'tp_rate': (df_trades['exit_reason'] == 'TP').mean() * 100,
        'sl_rate': (df_trades['exit_reason'] == 'SL').mean() * 100
    }

# Load data
print("=" * 80)
print("RSI 30/65 SWING STRATEGY - 1000PEPE & DOGE TEST")
print("=" * 80)

df_pepe = pd.read_csv('1000pepe_1h_90d.csv')
df_pepe.columns = df_pepe.columns.str.lower()
df_pepe['timestamp'] = pd.to_datetime(df_pepe['timestamp'])
df_pepe = df_pepe.sort_values('timestamp').reset_index(drop=True)

df_doge = pd.read_csv('doge_1h_90d.csv')
df_doge.columns = df_doge.columns.str.lower()
df_doge['timestamp'] = pd.to_datetime(df_doge['timestamp'])
df_doge = df_doge.sort_values('timestamp').reset_index(drop=True)

print(f"\n1000PEPE: {len(df_pepe):,} candles | Range: {df_pepe['timestamp'].min()} to {df_pepe['timestamp'].max()}")
print(f"DOGE:     {len(df_doge):,} candles | Range: {df_doge['timestamp'].min()} to {df_doge['timestamp'].max()}")

# Test baseline RSI 30/65
print(f"\n" + "=" * 80)
print("BASELINE: RSI 30/65 + 2x ATR STOP")
print("=" * 80)

pepe_result = backtest_rsi(df_pepe.copy(), "1000PEPE", rsi_low=30, rsi_high=65, atr_mult=2.0)
doge_result = backtest_rsi(df_doge.copy(), "DOGE", rsi_low=30, rsi_high=65, atr_mult=2.0)

results = [pepe_result, doge_result]

print(f"\n{'Coin':<12} {'Trades':<8} {'Return':<12} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'AvgWin':<8} {'AvgLoss':<9} {'HoldH':<8} {'TP%':<6} {'SL%'}")
print("-" * 110)

for r in results:
    if r:
        status = "✅" if r['rdd'] >= 5 else "⚠️" if r['rdd'] >= 3 else "❌"
        print(f"{r['coin']:<12} {r['trades']:<8} {r['return']:+11.2f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['avg_win']:7.2f}% {r['avg_loss']:8.2f}% {r['avg_hold']:7.1f}h {r['tp_rate']:5.1f}% {r['sl_rate']:5.1f}% {status}")

print("\n" + "=" * 80)

# Compare to BTC/ETH benchmarks
print("BENCHMARKS FOR COMPARISON:")
print("-" * 80)
print(f"{'BTC':<12} {'171':<8} {'+62.69%':<12} {'-9.60%':<10} {'6.53x':<8} {'61.4%':<8} {'3.70%':<8} {'-3.02%':<9} {'12.1h':<8} {'57.9%':<6} {'31.6%'}")
print(f"{'ETH':<12} {'143':<8} {'+141.35%':<12} {'-14.22%':<10} {'9.94x':<8} {'62.9%':<8} {'5.31%':<8} {'-3.63%':<9} {'12.3h':<8} {'65.7%':<6} {'26.6%'}")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)

for r in results:
    if r:
        print(f"\n{r['coin']}:")
        if r['rdd'] >= 5:
            print(f"  ✅ EXCELLENT: {r['rdd']:.2f}x R/DD meets target (5x+)")
        elif r['rdd'] >= 3:
            print(f"  ⚠️ GOOD: {r['rdd']:.2f}x R/DD but below target. Consider optimization.")
        else:
            print(f"  ❌ WEAK: {r['rdd']:.2f}x R/DD - needs significant optimization")

        print(f"  Hold time: {r['avg_hold']:.1f}h ({r['avg_hold']/24:.1f} days)")
        print(f"  Best exit: {'TP' if r['tp_rate'] > r['sl_rate'] else 'SL'} ({max(r['tp_rate'], r['sl_rate']):.1f}%)")

print("\n" + "=" * 80)
