#!/usr/bin/env python3
"""
AUTHORITATIVE VERIFICATION - Individual Coin Metrics
Uses EXACT same logic as donchian_portfolio_backtest.py

This is the ONLY source of truth for individual coin R:R ratios.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# EXACT SAME CONFIG AS PORTFOLIO BACKTEST
FEE_PCT = 0.07
ATR_PERIOD = 14
MAX_LEVERAGE = 5.0
RISK_PCT = 3  # Using 3% for comparison with previous results
DATA_DIR = Path(__file__).parent

# EXACT SAME STRATEGIES AS PORTFOLIO BACKTEST
STRATEGIES = {
    'PENGU':    {'tp': 7.0,  'period': 25, 'sl': 5, 'file': 'pengu_1h_jun_dec_2025.csv'},
    'DOGE':     {'tp': 4.0,  'period': 15, 'sl': 4, 'file': 'doge_1h_jun_dec_2025.csv'},
    'FARTCOIN': {'tp': 7.5,  'period': 15, 'sl': 2, 'file': 'fartcoin_1h_jun_dec_2025.csv'},
    'ETH':      {'tp': 1.5,  'period': 20, 'sl': 4, 'file': 'eth_1h_2025.csv'},
    'UNI':      {'tp': 10.5, 'period': 30, 'sl': 2, 'file': 'uni_1h_jun_dec_2025.csv'},
    'PI':       {'tp': 3.0,  'period': 15, 'sl': 2, 'file': 'pi_1h_jun_dec_2025.csv'},
    'CRV':      {'tp': 9.0,  'period': 15, 'sl': 5, 'file': 'crv_1h_jun_dec_2025.csv'},
    'AIXBT':    {'tp': 12.0, 'period': 15, 'sl': 2, 'file': 'aixbt_1h_jun_dec_2025.csv'},
}


def get_all_trades(df, period, tp_atr, sl_atr):
    """EXACT COPY from donchian_portfolio_backtest.py - DO NOT MODIFY"""
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


def run_single_coin_backtest(trades, risk_pct):
    """Run backtest for single coin using SAME logic as portfolio"""
    if not trades:
        return {'equity': 100, 'return': 0, 'max_dd': 0, 'rr_ratio': 0, 'win_rate': 0, 'trades': 0, 'wins': 0}

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


if __name__ == '__main__':
    print("=" * 100)
    print("AUTHORITATIVE INDIVIDUAL COIN VERIFICATION")
    print("Using EXACT same logic as donchian_portfolio_backtest.py")
    print(f"Risk per trade: {RISK_PCT}%")
    print("=" * 100)

    print(f"\n{'Coin':<12} {'Params':<22} {'Trades':<8} {'Wins':<6} {'WinRate':<10} {'Return%':<14} {'MaxDD%':<10} {'R:R':<10}")
    print("-" * 100)

    all_results = []

    for coin, params in STRATEGIES.items():
        try:
            df = pd.read_csv(DATA_DIR / params['file'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df[df['timestamp'] >= '2025-06-01']

            trades = get_all_trades(df, params['period'], params['tp'], params['sl'])
            result = run_single_coin_backtest(trades, RISK_PCT)
            result['coin'] = coin
            result['params'] = f"TP={params['tp']}, SL={params['sl']}, P={params['period']}"
            all_results.append(result)

            print(f"{coin:<12} {result['params']:<22} {result['trades']:<8} {result['wins']:<6} "
                  f"{result['win_rate']:<10.1f} {result['return']:<14.1f} {result['max_dd']:<10.1f} "
                  f"{result['rr_ratio']:<10.2f}")
        except Exception as e:
            print(f"{coin:<12} ERROR: {e}")

    # Sort by R:R ratio
    all_results.sort(key=lambda x: x['rr_ratio'], reverse=True)

    print("\n" + "=" * 100)
    print("RANKING BY R:R RATIO (AUTHORITATIVE)")
    print("=" * 100)

    for i, r in enumerate(all_results, 1):
        print(f"{i}. {r['coin']:<12} {r['rr_ratio']:>8.2f}x R:R  ({r['trades']} trades, {r['win_rate']:.0f}% WR, {r['return']:+.0f}% return)")

    # Compare with claimed values
    CLAIMED = {
        'PENGU': 34.05,
        'DOGE': 17.97,
        'FARTCOIN': 12.57,
        'ETH': 10.12,
        'UNI': 9.95,
        'PI': 7.79,
        'CRV': 7.43,
        'AIXBT': 5.86,
    }

    print("\n" + "=" * 100)
    print("CLAIMED vs ACTUAL R:R COMPARISON")
    print("=" * 100)
    print(f"{'Coin':<12} {'Claimed':<12} {'Actual':<12} {'Difference':<12}")
    print("-" * 50)

    for r in all_results:
        claimed = CLAIMED.get(r['coin'], 0)
        actual = r['rr_ratio']
        diff = actual - claimed
        status = "CORRECT" if abs(diff) < 0.5 else ("HIGHER" if diff > 0 else "LOWER")
        print(f"{r['coin']:<12} {claimed:<12.2f} {actual:<12.2f} {diff:+.2f} ({status})")

    print("\n" + "=" * 100)
    print("CONCLUSION")
    print("=" * 100)
    print("These are the CORRECT R:R ratios using exact portfolio backtest logic.")
    print("All previous individual coin metrics should be replaced with these values.")
