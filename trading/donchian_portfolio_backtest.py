#!/usr/bin/env python3
"""
DONCHIAN 1H PORTFOLIO BACKTEST
8 coins with risk-based position sizing

Created: 2025-12-30
Run: python3 trading/donchian_portfolio_backtest.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
FEE_PCT = 0.07       # Total round-trip fee
ATR_PERIOD = 14
MAX_LEVERAGE = 5.0   # Cap leverage to prevent extreme positions
DATA_DIR = Path(__file__).parent

# TOP 8 COINS WITH OPTIMAL PARAMETERS
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


def get_all_trades(df, coin, period, tp_atr, sl_atr):
    """Get all trades with entry/exit details and SL distance"""
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
                    'coin': coin,
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


def run_portfolio_backtest(risk_pct=2, start_date='2025-06-01'):
    """
    Run portfolio backtest with risk-based position sizing.

    Position size = (Equity × Risk%) / SL_distance%
    If SL hit → lose exactly Risk% of equity
    """
    print("=" * 80)
    print(f"DONCHIAN 1H PORTFOLIO - {risk_pct}% RISK PER TRADE")
    print("=" * 80)

    # Collect all trades from all coins
    print("\nCollecting trades...")
    all_trades = []

    for coin, params in STRATEGIES.items():
        df = pd.read_csv(DATA_DIR / params['file'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= start_date]

        trades = get_all_trades(df, coin, params['period'], params['tp'], params['sl'])
        all_trades.extend(trades)
        print(f"  {coin:12s}: {len(trades):3d} trades")

    # Sort by exit time
    all_trades.sort(key=lambda x: x['exit_time'])
    print(f"\nTotal trades: {len(all_trades)}")

    avg_sl = np.mean([t['sl_dist_pct'] for t in all_trades])
    print(f"Avg SL distance: {avg_sl:.2f}%")

    # Portfolio simulation with risk-based sizing
    equity = 100.0
    max_equity = 100.0
    max_dd = 0
    wins = 0
    monthly_equity = {}

    for trade in all_trades:
        month = trade['exit_time'].strftime('%Y-%m')

        if trade['sl_dist_pct'] > 0:
            # Position size to risk exactly risk_pct of equity
            leverage = min(risk_pct / trade['sl_dist_pct'], MAX_LEVERAGE)
            equity_pnl_pct = leverage * trade['pnl_pct']
            equity *= (1 + equity_pnl_pct / 100)

        if trade['result'] == 'TP':
            wins += 1

        if equity > max_equity:
            max_equity = equity
        dd = (max_equity - equity) / max_equity * 100
        if dd > max_dd:
            max_dd = dd

        monthly_equity[month] = equity

    # Results
    total_return = equity - 100
    rr_ratio = total_return / max_dd if max_dd > 0 and total_return > 0 else 0
    win_rate = 100 * wins / len(all_trades)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"  Starting Equity:  $100.00")
    print(f"  Final Equity:     ${equity:,.2f}")
    print(f"  Total Return:     +{total_return:,.1f}%")
    print(f"  Max Drawdown:     -{max_dd:.1f}%")
    print(f"  R:R Ratio:        {rr_ratio:.2f}x")
    print(f"  Win Rate:         {win_rate:.1f}%")

    print("\nMONTHLY PERFORMANCE:")
    print("-" * 50)
    prev_eq = 100
    for m, eq in sorted(monthly_equity.items()):
        month_ret = (eq - prev_eq) / prev_eq * 100
        status = "+" if month_ret > 0 else "-"
        print(f"  {m}: ${eq:>12,.2f} ({month_ret:+.0f}%) {status}")
        prev_eq = eq

    return {
        'final_equity': equity,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'trades': len(all_trades),
        'win_rate': win_rate,
        'monthly': monthly_equity
    }


def compare_risk_levels():
    """Compare different risk levels side by side"""
    print("\n" + "=" * 100)
    print("RISK LEVEL COMPARISON")
    print("=" * 100)
    print(f"{'Risk':>6} | {'Final Equity':>16} | {'Return':>14} | {'Max DD':>8} | {'R:R':>12}")
    print("-" * 100)

    # Collect trades once
    all_trades = []
    for coin, params in STRATEGIES.items():
        df = pd.read_csv(DATA_DIR / params['file'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= '2025-06-01']
        trades = get_all_trades(df, coin, params['period'], params['tp'], params['sl'])
        all_trades.extend(trades)
    all_trades.sort(key=lambda x: x['exit_time'])

    for risk_pct in [1, 2, 3, 4, 5]:
        equity = 100.0
        max_equity = 100.0
        max_dd = 0

        for trade in all_trades:
            if trade['sl_dist_pct'] > 0:
                leverage = min(risk_pct / trade['sl_dist_pct'], MAX_LEVERAGE)
                equity *= (1 + leverage * trade['pnl_pct'] / 100)
            if equity > max_equity:
                max_equity = equity
            dd = (max_equity - equity) / max_equity * 100
            if dd > max_dd:
                max_dd = dd

        ret = equity - 100
        rr = ret / max_dd if max_dd > 0 and ret > 0 else 0
        print(f"{risk_pct:>5}% | ${equity:>15,.2f} | {ret:>+13,.0f}% | {max_dd:>7.1f}% | {rr:>11,.0f}x")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        risk = int(sys.argv[1])
        run_portfolio_backtest(risk_pct=risk)
    else:
        run_portfolio_backtest(risk_pct=2)
        compare_risk_levels()
