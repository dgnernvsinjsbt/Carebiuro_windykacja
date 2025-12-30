#!/usr/bin/env python3
"""
Test different SL levels on AIXBT

Current params: TP=12.0 ATR, SL=2 ATR, Period=15, R:R=5.86x
Test SL from 1-10 ATR to find optimal
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load AIXBT 1H data
data_file = Path(__file__).parent / 'aixbt_1h_jun_dec_2025.csv'
df = pd.read_csv(data_file)
df.columns = [c.lower() for c in df.columns]
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Fixed params
TP_ATR = 12.0
PERIOD = 15
FEE_PCT = 0.07

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

print("=" * 80)
print("AIXBT SL OPTIMIZATION TEST (1H Candles)")
print("=" * 80)
print(f"Data: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Fixed: TP={TP_ATR} ATR, Period={PERIOD}")
print("=" * 80)


def run_backtest(sl_atr: float):
    """Run backtest with specific SL"""
    trades = []

    for i in range(PERIOD + 14, len(df)):
        row = df.iloc[i]
        price = row['close']
        atr = row['atr']
        upper = row['donchian_upper']
        lower = row['donchian_lower']

        if pd.isna(atr) or pd.isna(upper) or atr <= 0:
            continue

        signal = None
        if price > upper:
            signal = 'LONG'
            entry = price
            tp = entry + (TP_ATR * atr)
            sl = entry - (sl_atr * atr)
        elif price < lower:
            signal = 'SHORT'
            entry = price
            tp = entry - (TP_ATR * atr)
            sl = entry + (sl_atr * atr)

        if signal:
            result = simulate_trade(df, i, signal, entry, tp, sl)
            if result:
                result['sl_atr'] = sl_atr
                trades.append(result)

    return trades


def simulate_trade(df, entry_bar, direction, entry_price, tp, sl):
    """Simulate trade from entry bar until TP/SL hit"""
    for j in range(entry_bar + 1, len(df)):
        row = df.iloc[j]

        if direction == 'LONG':
            if row['low'] <= sl:
                pnl_pct = ((sl - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            if row['high'] >= tp:
                pnl_pct = ((tp - entry_price) / entry_price * 100) - FEE_PCT
                return {'direction': 'LONG', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

        elif direction == 'SHORT':
            if row['high'] >= sl:
                pnl_pct = ((entry_price - sl) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': sl,
                        'pnl_pct': pnl_pct, 'result': 'SL'}
            if row['low'] <= tp:
                pnl_pct = ((entry_price - tp) / entry_price * 100) - FEE_PCT
                return {'direction': 'SHORT', 'entry': entry_price, 'exit': tp,
                        'pnl_pct': pnl_pct, 'result': 'TP'}

    return None


def analyze_trades(trades, sl_atr):
    """Analyze trade results with 3% risk sizing"""
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    wins = len(df_trades[df_trades['result'] == 'TP'])
    losses = len(df_trades[df_trades['result'] == 'SL'])
    total = len(df_trades)
    win_rate = wins / total * 100 if total > 0 else 0

    # Calculate equity curve with 3% risk
    equity = 100.0
    max_equity = equity
    max_dd = 0

    for _, trade in df_trades.iterrows():
        # SL distance in %
        sl_dist_pct = sl_atr * df['atr'].mean() / trade['entry'] * 100
        # Leverage = 3% risk / SL distance, capped at 5x
        leverage = min(3.0 / sl_dist_pct, 5.0) if sl_dist_pct > 0 else 1.0
        pnl = leverage * trade['pnl_pct']
        equity *= (1 + pnl / 100)
        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)

    total_return = (equity - 100)
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    return {
        'sl_atr': sl_atr,
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio
    }


# Test different SL levels
print(f"\n{'SL_ATR':<8} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'WinRate':<10} {'Return%':<12} {'MaxDD%':<10} {'R:R':<8}")
print("-" * 80)

results = []
sl_levels = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 9, 10]

for sl in sl_levels:
    trades = run_backtest(sl)
    stats = analyze_trades(trades, sl)

    if stats:
        results.append(stats)
        marker = " <-- CURRENT" if sl == 2 else ""
        print(f"{sl:<8.1f} {stats['total_trades']:<8} {stats['wins']:<6} {stats['losses']:<8} "
              f"{stats['win_rate']:<10.1f} {stats['total_return']:<12.1f} {stats['max_dd']:<10.1f} "
              f"{stats['rr_ratio']:<8.2f}{marker}")

# Find best
print("\n" + "=" * 80)
if results:
    best = max(results, key=lambda x: x['rr_ratio'])
    current = next((r for r in results if r['sl_atr'] == 2), None)

    print(f"\nCURRENT (SL=2 ATR): {current['rr_ratio']:.2f}x R:R, {current['win_rate']:.1f}% WR, {current['total_return']:.1f}% return")
    print(f"BEST (SL={best['sl_atr']} ATR): {best['rr_ratio']:.2f}x R:R, {best['win_rate']:.1f}% WR, {best['total_return']:.1f}% return")

    if best['sl_atr'] != 2:
        print(f"\nIMPROVEMENT:")
        print(f"  - R:R: {best['rr_ratio']:.2f}x vs {current['rr_ratio']:.2f}x ({best['rr_ratio'] - current['rr_ratio']:+.2f}x)")
        print(f"  - Return: {best['total_return']:.1f}% vs {current['total_return']:.1f}% ({best['total_return'] - current['total_return']:+.1f}%)")
        print(f"  - Win Rate: {best['win_rate']:.1f}% vs {current['win_rate']:.1f}% ({best['win_rate'] - current['win_rate']:+.1f}%)")
        print(f"  - Max DD: {best['max_dd']:.1f}% vs {current['max_dd']:.1f}% ({best['max_dd'] - current['max_dd']:+.1f}%)")

# Also test with different TP levels for best SL
print("\n" + "=" * 80)
print("TESTING TP LEVELS WITH BEST SL")
print("=" * 80)

best_sl = best['sl_atr']

def run_backtest_custom(tp_atr: float, sl_atr: float):
    """Run backtest with custom TP/SL"""
    trades = []

    for i in range(PERIOD + 14, len(df)):
        row = df.iloc[i]
        price = row['close']
        atr = row['atr']
        upper = row['donchian_upper']
        lower = row['donchian_lower']

        if pd.isna(atr) or pd.isna(upper) or atr <= 0:
            continue

        signal = None
        if price > upper:
            signal = 'LONG'
            entry = price
            tp = entry + (tp_atr * atr)
            sl = entry - (sl_atr * atr)
        elif price < lower:
            signal = 'SHORT'
            entry = price
            tp = entry - (tp_atr * atr)
            sl = entry + (sl_atr * atr)

        if signal:
            result = simulate_trade(df, i, signal, entry, tp, sl)
            if result:
                trades.append(result)

    return trades


print(f"\nTesting TP levels with SL={best_sl} ATR:")
print(f"{'TP_ATR':<8} {'Trades':<8} {'Wins':<6} {'WinRate':<10} {'Return%':<12} {'MaxDD%':<10} {'R:R':<8}")
print("-" * 70)

tp_results = []
tp_levels = [4, 6, 8, 10, 12, 14, 16, 18, 20]

for tp in tp_levels:
    trades = run_backtest_custom(tp, best_sl)
    stats = analyze_trades(trades, best_sl)
    if stats:
        stats['tp_atr'] = tp
        tp_results.append(stats)
        marker = " <-- CURRENT TP" if tp == 12 else ""
        print(f"{tp:<8.1f} {stats['total_trades']:<8} {stats['wins']:<6} "
              f"{stats['win_rate']:<10.1f} {stats['total_return']:<12.1f} {stats['max_dd']:<10.1f} "
              f"{stats['rr_ratio']:<8.2f}{marker}")

if tp_results:
    best_tp = max(tp_results, key=lambda x: x['rr_ratio'])
    print(f"\nBEST COMBO: TP={best_tp['tp_atr']} ATR, SL={best_sl} ATR -> {best_tp['rr_ratio']:.2f}x R:R")
