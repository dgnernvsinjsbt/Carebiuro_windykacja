#!/usr/bin/env python3
"""
OPTIMIZE: Find best parameters for Gradual Short Strategy
Target: Max R:R with DD < 40%
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot'))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from execution.bingx_client import BingXClient
from config import load_config
import pickle

CACHE_FILE = 'trading/cache/listings_2025_data.pkl'

async def download_all_data(bingx, listings):
    """Download and cache all data"""
    os.makedirs('trading/cache', exist_ok=True)

    data = {}
    semaphore = asyncio.Semaphore(5)

    async def download_coin(row):
        async with semaphore:
            symbol = row['symbol']
            listing_date = row['listing_date'].to_pydatetime().replace(tzinfo=timezone.utc)

            try:
                start = listing_date + timedelta(hours=1)
                end = start + timedelta(days=30)

                all_candles = []
                current = start

                while current < end:
                    chunk_end = min(current + timedelta(days=7), end)
                    candles = await bingx.get_klines(
                        symbol=symbol,
                        interval='1h',
                        start_time=int(current.timestamp() * 1000),
                        end_time=int(chunk_end.timestamp() * 1000),
                        limit=1000
                    )
                    if candles:
                        all_candles.extend(candles)
                    current = chunk_end
                    await asyncio.sleep(0.05)

                if all_candles:
                    df = pd.DataFrame(all_candles)
                    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                    df = df.sort_values('timestamp').drop_duplicates(subset=['time']).reset_index(drop=True)
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    return symbol, df, row['first_price']
            except:
                pass
            return symbol, None, None

    print("Downloading data for all coins...")
    tasks = [download_coin(row) for _, row in listings.iterrows()]
    results = await asyncio.gather(*tasks)

    for symbol, df, listing_price in results:
        if df is not None and len(df) >= 24:
            data[symbol] = {'df': df, 'listing_price': listing_price}

    print(f"Downloaded {len(data)} coins")

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(data, f)

    return data

def backtest_params(data, wait_hours, pump_threshold, max_entries, entry_step, sl_pct, tp_pct, risk_per_entry):
    """Backtest with specific parameters"""
    all_trades = []

    for symbol, coin_data in data.items():
        df = coin_data['df']
        listing_price = coin_data['listing_price']

        if len(df) < wait_hours + 10:
            continue

        position = None
        entries = []

        for i in range(wait_hours, len(df)):
            row = df.iloc[i]
            price = row['close']
            high = row['high']
            low = row['low']

            if position:
                # Check SL
                if high >= position['sl_price']:
                    pnl_pct = -sl_pct
                    all_trades.append({
                        'symbol': symbol,
                        'exit_time': row['timestamp'],
                        'pnl_pct': pnl_pct,
                        'num_entries': len(entries),
                        'exit_reason': 'SL'
                    })
                    position = None
                    entries = []
                    continue

                # Check TP
                tp_target = position['avg_entry'] * (1 - tp_pct / 100)
                if low <= tp_target or low <= listing_price:
                    exit_price = max(tp_target, listing_price * 0.99)
                    pnl_pct = (position['avg_entry'] - exit_price) / position['avg_entry'] * 100
                    all_trades.append({
                        'symbol': symbol,
                        'exit_time': row['timestamp'],
                        'pnl_pct': pnl_pct,
                        'num_entries': len(entries),
                        'exit_reason': 'TP'
                    })
                    position = None
                    entries = []
                    continue

            # Check entry
            pump_pct = (price / listing_price - 1) * 100

            if pump_pct >= pump_threshold:
                if position is None:
                    entries = [price]
                    position = {
                        'avg_entry': price,
                        'sl_price': price * (1 + sl_pct / 100)
                    }
                elif len(entries) < max_entries:
                    if price >= entries[-1] * (1 + entry_step / 100):
                        entries.append(price)
                        position['avg_entry'] = np.mean(entries)
                        position['sl_price'] = price * (1 + sl_pct / 100)

        # Close open position
        if position:
            exit_price = df.iloc[-1]['close']
            pnl_pct = (position['avg_entry'] - exit_price) / position['avg_entry'] * 100
            all_trades.append({
                'symbol': symbol,
                'exit_time': df.iloc[-1]['timestamp'],
                'pnl_pct': pnl_pct,
                'num_entries': len(entries),
                'exit_reason': 'END'
            })

    if not all_trades:
        return None

    # Calculate equity curve
    trades_df = pd.DataFrame(all_trades)
    trades_df = trades_df.sort_values('exit_time').reset_index(drop=True)

    equity = 100.0
    max_equity = 100.0
    max_dd = 0

    for _, trade in trades_df.iterrows():
        total_risk = risk_per_entry * trade['num_entries']
        position_value = equity * (total_risk / sl_pct)
        pnl_dollars = position_value * trade['pnl_pct'] / 100
        equity += pnl_dollars

        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)

    total_return = (equity / 100 - 1) * 100
    win_rate = (trades_df['pnl_pct'] > 0).mean() * 100
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    return {
        'wait_hours': wait_hours,
        'pump_threshold': pump_threshold,
        'max_entries': max_entries,
        'entry_step': entry_step,
        'sl_pct': sl_pct,
        'tp_pct': tp_pct,
        'risk_per_entry': risk_per_entry,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'final_equity': equity
    }

async def main():
    # Load or download data
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached data from {CACHE_FILE}...")
        with open(CACHE_FILE, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded {len(data)} coins")
    else:
        listings = pd.read_csv('trading/listings_2025.csv')
        listings['listing_date'] = pd.to_datetime(listings['listing_date'])
        listings = listings[listings['days_listed'] >= 30].reset_index(drop=True)

        config = load_config(os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot', 'config_donchian.yaml'))
        bingx = BingXClient(api_key=config.bingx.api_key, api_secret=config.bingx.api_secret, testnet=False)
        data = await download_all_data(bingx, listings)
        await bingx.close()

    print("="*80)
    print("GRID SEARCH: Finding optimal parameters")
    print("Target: Max R:R with DD < 40%")
    print("="*80)

    # Parameter grid
    param_grid = {
        'wait_hours': [6, 12, 24, 48],
        'pump_threshold': [5, 10, 15, 20, 30],
        'max_entries': [1, 2, 3],
        'entry_step': [5, 10],
        'sl_pct': [10, 15, 20],
        'tp_pct': [20, 30, 40, 50],
        'risk_per_entry': [0.5, 1.0, 1.5]
    }

    results = []
    total_combos = (len(param_grid['wait_hours']) * len(param_grid['pump_threshold']) *
                    len(param_grid['max_entries']) * len(param_grid['entry_step']) *
                    len(param_grid['sl_pct']) * len(param_grid['tp_pct']) *
                    len(param_grid['risk_per_entry']))

    print(f"\nTesting {total_combos} parameter combinations...")

    count = 0
    for wait in param_grid['wait_hours']:
        for pump in param_grid['pump_threshold']:
            for max_e in param_grid['max_entries']:
                for step in param_grid['entry_step']:
                    for sl in param_grid['sl_pct']:
                        for tp in param_grid['tp_pct']:
                            for risk in param_grid['risk_per_entry']:
                                result = backtest_params(data, wait, pump, max_e, step, sl, tp, risk)
                                if result and result['trades'] >= 50:  # Min 50 trades
                                    results.append(result)
                                count += 1
                                if count % 500 == 0:
                                    print(f"  Progress: {count}/{total_combos}")

    results_df = pd.DataFrame(results)

    # Filter for DD < 40%
    valid = results_df[results_df['max_dd'] < 40].copy()

    if len(valid) == 0:
        print("\nNo combinations with DD < 40%. Showing best with DD < 50%:")
        valid = results_df[results_df['max_dd'] < 50].copy()

    # Sort by R:R ratio
    valid = valid.sort_values('rr_ratio', ascending=False)

    print(f"\n{'='*80}")
    print(f"TOP 10 RESULTS (DD < 40%, sorted by R:R)")
    print(f"{'='*80}")

    cols = ['wait_hours', 'pump_threshold', 'max_entries', 'sl_pct', 'tp_pct',
            'risk_per_entry', 'trades', 'win_rate', 'total_return', 'max_dd', 'rr_ratio']

    print(valid[cols].head(10).to_string(index=False))

    # Best result
    best = valid.iloc[0]
    print(f"\n{'='*80}")
    print("BEST PARAMETERS")
    print(f"{'='*80}")
    print(f"Wait: {best['wait_hours']}h")
    print(f"Pump threshold: {best['pump_threshold']}%")
    print(f"Max entries: {best['max_entries']}")
    print(f"Entry step: {best['entry_step']}%")
    print(f"SL: {best['sl_pct']}%")
    print(f"TP: {best['tp_pct']}%")
    print(f"Risk per entry: {best['risk_per_entry']}%")
    print(f"\nResults:")
    print(f"  Trades: {best['trades']}")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  Total Return: {best['total_return']:+.1f}%")
    print(f"  Max Drawdown: {best['max_dd']:.1f}%")
    print(f"  R:R Ratio: {best['rr_ratio']:.2f}x")

    # Save all results
    results_df.to_csv('trading/results/new_listings_optimization.csv', index=False)
    print(f"\n✅ Saved all {len(results_df)} results to trading/results/new_listings_optimization.csv")

if __name__ == '__main__':
    asyncio.run(main())
