#!/usr/bin/env python3
"""
MOODENG FAST OPTIMIZER - Key parameters only
Focus on SL/TP ratios and critical filters
"""

import pandas as pd
import numpy as np

FEE_PER_TRADE = 0.10

def load_data():
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Calculate only essential indicators
    df['body'] = df['close'] - df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 0.0001)
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMA20
    df['sma_20'] = df['close'].rolling(20).mean()

    return df


def run_strategy(df, rsi_entry=55, body_thresh=0.5, sl_mult=1.0, tp_mult=4.0, max_bars=60):
    trades = []
    in_position = False

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            rsi_cross = prev['rsi'] < rsi_entry and row['rsi'] >= rsi_entry
            bullish_body = row['is_bullish'] and row['body_pct'] > body_thresh
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                entry_atr = row['atr']

                stop_loss = entry_price - (entry_atr * sl_mult)
                take_profit = entry_price + (entry_atr * tp_mult)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'pnl_pct': pnl, 'result': 'SL'})
                in_position = False
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'pnl_pct': pnl, 'result': 'TP'})
                in_position = False
            elif bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'pnl_pct': pnl, 'result': 'TIME'})
                in_position = False

    return trades


def analyze(trades, label=''):
    if not trades:
        return {'label': label, 'trades': 0, 'net': 0, 'wr': 0, 'dd': 0, 'rdd': 0}

    df = pd.DataFrame(trades)

    # Stats
    win_rate = (df['pnl_pct'] > 0).sum() / len(df) * 100

    # Equity
    equity = [100]
    for pnl in df['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    # Drawdown
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    gross = equity[-1] - 100
    fees = len(df) * FEE_PER_TRADE
    net = gross - fees

    rdd = abs(net / max_dd) if max_dd > 0 else 0

    return {
        'label': label,
        'trades': len(df),
        'net': net,
        'wr': win_rate,
        'dd': max_dd,
        'rdd': rdd
    }


def main():
    print("="*70)
    print("MOODENG FAST OPTIMIZER - BINGX DATA")
    print("="*70)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles\n")

    results = []

    # Baseline
    print("BASELINE:")
    trades = run_strategy(df, sl_mult=1.0, tp_mult=4.0)
    r = analyze(trades, 'Baseline SL1.0/TP4.0')
    results.append(r)
    print(f"  {r['trades']} trades, NET: {r['net']:+.2f}%, WR: {r['wr']:.0f}%, "
          f"DD: {r['dd']:.2f}%, R/DD: {r['rdd']:.2f}x\n")

    # SL/TP optimization
    print("SL/TP OPTIMIZATION:")
    configs = [
        (0.5, 3.0), (0.5, 4.0), (0.5, 5.0),
        (1.0, 3.0), (1.0, 4.0), (1.0, 5.0), (1.0, 6.0),
        (1.5, 4.0), (1.5, 5.0), (1.5, 6.0),
        (2.0, 5.0), (2.0, 6.0), (2.0, 8.0),
    ]

    for sl, tp in configs:
        trades = run_strategy(df, sl_mult=sl, tp_mult=tp)
        r = analyze(trades, f'SL{sl}/TP{tp}')
        results.append(r)
        print(f"  SL{sl}/TP{tp}: {r['trades']:>3} trades, NET: {r['net']:+7.2f}%, "
              f"WR: {r['wr']:>4.0f}%, R/DD: {r['rdd']:>5.2f}x")

    # RSI optimization
    print("\nRSI ENTRY THRESHOLD:")
    for rsi in [50, 52, 55, 57, 60]:
        trades = run_strategy(df, rsi_entry=rsi)
        r = analyze(trades, f'RSI{rsi}')
        results.append(r)
        print(f"  RSI{rsi}: {r['trades']:>3} trades, NET: {r['net']:+7.2f}%, "
              f"WR: {r['wr']:>4.0f}%, R/DD: {r['rdd']:>5.2f}x")

    # Body threshold
    print("\nBODY THRESHOLD:")
    for body in [0.3, 0.5, 0.7, 1.0]:
        trades = run_strategy(df, body_thresh=body)
        r = analyze(trades, f'Body{body}')
        results.append(r)
        print(f"  Body>{body}%: {r['trades']:>3} trades, NET: {r['net']:+7.2f}%, "
              f"WR: {r['wr']:>4.0f}%, R/DD: {r['rdd']:>5.2f}x")

    # Time exit
    print("\nTIME EXIT:")
    for max_bars in [30, 45, 60, 90, 120]:
        trades = run_strategy(df, max_bars=max_bars)
        r = analyze(trades, f'Time{max_bars}')
        results.append(r)
        print(f"  {max_bars} bars: {r['trades']:>3} trades, NET: {r['net']:+7.2f}%, "
              f"WR: {r['wr']:>4.0f}%, R/DD: {r['rdd']:>5.2f}x")

    # Best combinations
    print("\nBEST COMBOS:")
    combos = [
        {'sl_mult': 0.5, 'tp_mult': 4.0},
        {'sl_mult': 1.0, 'tp_mult': 5.0},
        {'sl_mult': 1.0, 'tp_mult': 6.0},
        {'rsi_entry': 60, 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'body_thresh': 0.7, 'sl_mult': 1.0, 'tp_mult': 5.0},
    ]

    for i, combo in enumerate(combos, 1):
        trades = run_strategy(df, **combo)
        r = analyze(trades, f'Combo{i}')
        results.append(r)
        desc = ', '.join([f"{k}={v}" for k,v in combo.items()])
        print(f"  Combo{i}: {r['trades']:>3} trades, NET: {r['net']:+7.2f}%, "
              f"R/DD: {r['rdd']:>5.2f}x | {desc}")

    # Top 10
    print("\n" + "="*70)
    print("TOP 10 BY RETURN/DD RATIO:")
    print("="*70)

    results.sort(key=lambda x: x['rdd'], reverse=True)

    print(f"\n{'Rank':<5} {'Config':<25} {'Trades':>7} {'NET':>9} {'WR':>6} {'DD':>7} {'R/DD':>8}")
    print("-"*70)

    for i, r in enumerate(results[:10], 1):
        print(f"{i:<5} {r['label']:<25} {r['trades']:>7} {r['net']:>+8.2f}% "
              f"{r['wr']:>5.0f}% {r['dd']:>6.2f}% {r['rdd']:>7.2f}x")

    # Save
    pd.DataFrame(results).to_csv(
        '/workspaces/Carebiuro_windykacja/trading/results/moodeng_fast_optimization.csv',
        index=False
    )
    print(f"\n✅ Results saved to: trading/results/moodeng_fast_optimization.csv")

    # Best
    best = results[0]
    baseline = [r for r in results if r['label'] == 'Baseline SL1.0/TP4.0'][0]

    print(f"\n\nBEST STRATEGY: {best['label']}")
    print(f"  NET Return: {best['net']:+.2f}%")
    print(f"  Max DD: {best['dd']:.2f}%")
    print(f"  Return/DD: {best['rdd']:.2f}x")
    print(f"  Improvement over baseline: {((best['rdd'] / baseline['rdd']) - 1) * 100:+.1f}%")


if __name__ == "__main__":
    main()
