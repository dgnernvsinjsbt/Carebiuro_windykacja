#!/usr/bin/env python3
"""
Verify AIXBT results using EXACT same logic as portfolio backtest
"""

import pandas as pd
import numpy as np
from pathlib import Path

FEE_PCT = 0.07
ATR_PERIOD = 14
MAX_LEVERAGE = 5.0
DATA_DIR = Path(__file__).parent

def get_all_trades(df, period, tp_atr, sl_atr):
    """Exact same logic as portfolio backtest"""
    df = df.copy()
    df['atr'] = (df['high'] - df['low']).rolling(ATR_PERIOD).mean()
    df['high_n'] = df['high'].rolling(period).max().shift(1)
    df['low_n'] = df['low'].rolling(period).min().shift(1)

    trades = []
    position = None
    entry_time = None

    for i in range(max(period, ATR_PERIOD) + 1, len(df)):
        curr = df.iloc[i]

        if position:
            exit_time = None
            pnl_pct = None
            result = None

            if position['side'] == 'LONG':
                if curr['low'] <= position['sl']:
                    pnl_pct = (position['sl'] - position['entry']) / position['entry'] * 100 - FEE_PCT
                    result = 'SL'
                    exit_time = curr['timestamp']
                elif curr['high'] >= position['tp']:
                    pnl_pct = (position['tp'] - position['entry']) / position['entry'] * 100 - FEE_PCT
                    result = 'TP'
                    exit_time = curr['timestamp']
            else:  # SHORT
                if curr['high'] >= position['sl']:
                    pnl_pct = (position['entry'] - position['sl']) / position['entry'] * 100 - FEE_PCT
                    result = 'SL'
                    exit_time = curr['timestamp']
                elif curr['low'] <= position['tp']:
                    pnl_pct = (position['entry'] - position['tp']) / position['entry'] * 100 - FEE_PCT
                    result = 'TP'
                    exit_time = curr['timestamp']

            if exit_time:
                sl_dist_pct = abs(position['sl'] - position['entry']) / position['entry'] * 100
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'pnl_pct': pnl_pct,
                    'sl_dist_pct': sl_dist_pct,
                    'result': result,
                })
                position = None

        if not position:
            if pd.notna(curr['high_n']) and pd.notna(curr['atr']) and curr['atr'] > 0:
                if curr['close'] > curr['high_n']:
                    entry = curr['close']
                    position = {'side': 'LONG', 'entry': entry,
                               'sl': entry - sl_atr * curr['atr'],
                               'tp': entry + tp_atr * curr['atr']}
                    entry_time = curr['timestamp']
                elif curr['close'] < curr['low_n']:
                    entry = curr['close']
                    position = {'side': 'SHORT', 'entry': entry,
                               'sl': entry + sl_atr * curr['atr'],
                               'tp': entry - tp_atr * curr['atr']}
                    entry_time = curr['timestamp']

    return trades


def run_single_coin_backtest(trades, risk_pct=3):
    """Run backtest with risk-based sizing"""
    equity = 100.0
    max_equity = 100.0
    max_dd = 0
    wins = 0

    for trade in trades:
        if trade['sl_dist_pct'] > 0:
            leverage = min(risk_pct / trade['sl_dist_pct'], MAX_LEVERAGE)
            equity *= (1 + leverage * trade['pnl_pct'] / 100)

        if trade['result'] == 'TP':
            wins += 1

        if equity > max_equity:
            max_equity = equity
        dd = (max_equity - equity) / max_equity * 100
        if dd > max_dd:
            max_dd = dd

    total_return = equity - 100
    # SAME R:R FORMULA AS PORTFOLIO BACKTEST
    rr_ratio = total_return / max_dd if max_dd > 0 and total_return > 0 else 0
    win_rate = 100 * wins / len(trades) if trades else 0

    return {
        'equity': equity,
        'return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'win_rate': win_rate,
        'trades': len(trades),
        'wins': wins
    }


# Load AIXBT data
df = pd.read_csv(DATA_DIR / 'aixbt_1h_jun_dec_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 80)
print("AIXBT VERIFICATION - Using EXACT portfolio backtest logic")
print("=" * 80)

# Test current params
print("\n--- CURRENT PARAMS (TP=12, SL=2, Period=15) ---")
trades = get_all_trades(df, 15, 12.0, 2)
result = run_single_coin_backtest(trades, risk_pct=3)
print(f"Trades: {result['trades']}, Wins: {result['wins']}, Win Rate: {result['win_rate']:.1f}%")
print(f"Return: {result['return']:.1f}%, Max DD: {result['max_dd']:.1f}%, R:R: {result['rr_ratio']:.2f}x")

# Test SL=4
print("\n--- NEW PARAMS (TP=12, SL=4, Period=15) ---")
trades = get_all_trades(df, 15, 12.0, 4)
result = run_single_coin_backtest(trades, risk_pct=3)
print(f"Trades: {result['trades']}, Wins: {result['wins']}, Win Rate: {result['win_rate']:.1f}%")
print(f"Return: {result['return']:.1f}%, Max DD: {result['max_dd']:.1f}%, R:R: {result['rr_ratio']:.2f}x")

# Test TP=18, SL=4
print("\n--- OPTIMIZED PARAMS (TP=18, SL=4, Period=15) ---")
trades = get_all_trades(df, 15, 18.0, 4)
result = run_single_coin_backtest(trades, risk_pct=3)
print(f"Trades: {result['trades']}, Wins: {result['wins']}, Win Rate: {result['win_rate']:.1f}%")
print(f"Return: {result['return']:.1f}%, Max DD: {result['max_dd']:.1f}%, R:R: {result['rr_ratio']:.2f}x")

# Compare all SL levels with consistent methodology
print("\n" + "=" * 80)
print("SL LEVEL COMPARISON (TP=12 fixed, 3% risk)")
print("=" * 80)
print(f"{'SL':<6} {'Trades':<8} {'Wins':<6} {'WinRate':<10} {'Return%':<12} {'MaxDD%':<10} {'R:R':<8}")
print("-" * 70)

for sl in [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8]:
    trades = get_all_trades(df, 15, 12.0, sl)
    r = run_single_coin_backtest(trades, risk_pct=3)
    marker = " <-- CURRENT" if sl == 2 else ""
    print(f"{sl:<6.1f} {r['trades']:<8} {r['wins']:<6} {r['win_rate']:<10.1f} {r['return']:<12.1f} {r['max_dd']:<10.1f} {r['rr_ratio']:<8.2f}{marker}")
