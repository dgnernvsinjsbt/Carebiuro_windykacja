#!/usr/bin/env python3
"""
DONCHIAN 1H PORTFOLIO BACKTEST
8 coins with monthly rebalancing

Created: 2025-12-30
Run: python3 trading/donchian_portfolio_backtest.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
FEE_PCT = 0.07  # Total round-trip fee
ATR_PERIOD = 14
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
    """Get all trades with timestamps for portfolio simulation"""
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
                trades.append({
                    'coin': coin,
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'side': position['side'],
                    'pnl_pct': pnl_pct,
                    'result': result
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


def run_portfolio_backtest(start_date='2025-06-01'):
    """Run full portfolio backtest with monthly rebalancing"""

    print("=" * 80)
    print("DONCHIAN 1H PORTFOLIO - 8 COINS WITH MONTHLY REBALANCING")
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

    # Portfolio simulation
    total_equity = 100.0
    coin_equity = {coin: total_equity / 8 for coin in STRATEGIES.keys()}
    max_equity = total_equity
    max_dd = 0

    current_month = None
    monthly_results = []

    for trade in all_trades:
        coin = trade['coin']
        exit_month = trade['exit_time'].strftime('%Y-%m')

        # Monthly rebalance
        if current_month is None:
            current_month = exit_month
        elif exit_month != current_month:
            month_equity = sum(coin_equity.values())
            monthly_results.append({'month': current_month, 'equity': month_equity})
            coin_equity = {c: month_equity / 8 for c in STRATEGIES.keys()}
            current_month = exit_month

        # Apply trade P&L
        coin_equity[coin] *= (1 + trade['pnl_pct'] / 100)

        # Track drawdown
        total_equity = sum(coin_equity.values())
        if total_equity > max_equity:
            max_equity = total_equity
        dd = (max_equity - total_equity) / max_equity * 100
        if dd > max_dd:
            max_dd = dd

    # Final month
    if current_month:
        monthly_results.append({'month': current_month, 'equity': sum(coin_equity.values())})

    # Results
    final_equity = sum(coin_equity.values())
    total_return = final_equity - 100
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    print("\n" + "=" * 80)
    print("PORTFOLIO RESULTS")
    print("=" * 80)
    print(f"  Starting Equity:  $100.00")
    print(f"  Final Equity:     ${final_equity:,.2f}")
    print(f"  Total Return:     +{total_return:,.1f}%")
    print(f"  Max Drawdown:     -{max_dd:.1f}%")
    print(f"  R:R Ratio:        {rr_ratio:.2f}x")

    print("\nMONTHLY PERFORMANCE:")
    print("-" * 50)
    prev_eq = 100
    for mr in monthly_results:
        month_ret = (mr['equity'] - prev_eq) / prev_eq * 100
        status = "+" if month_ret > 0 else "-"
        print(f"  {mr['month']}: ${mr['equity']:>10,.2f} ({month_ret:+.1f}%) {status}")
        prev_eq = mr['equity']

    return {
        'final_equity': final_equity,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'trades': len(all_trades),
        'monthly': monthly_results
    }


if __name__ == '__main__':
    run_portfolio_backtest()
