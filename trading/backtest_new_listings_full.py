#!/usr/bin/env python3
"""
FULL BACKTEST: Gradual Short Strategy on ALL 2025 Listings
Downloads first 30 days of 1H data for each coin and tests the strategy
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

# Strategy parameters (from optimization)
WAIT_HOURS = 12
PUMP_THRESHOLD = 5.0  # % above listing
MAX_ENTRIES = 3
ENTRY_STEP = 5.0  # % between entries
SL_PCT = 15.0
TP_PCT = 30.0
RISK_PER_TRADE = 2.0  # % of equity per entry

async def download_first_30_days(bingx, symbol, listing_date):
    """Download first 30 days of 1H data after listing"""
    try:
        start = listing_date + timedelta(hours=1)  # Skip first candle
        end = start + timedelta(days=30)

        all_candles = []

        # Chunk by 7 days
        current = start
        while current < end:
            chunk_end = min(current + timedelta(days=7), end)
            start_time = int(current.timestamp() * 1000)
            end_time = int(chunk_end.timestamp() * 1000)

            candles = await bingx.get_klines(
                symbol=symbol,
                interval='1h',
                start_time=start_time,
                end_time=end_time,
                limit=1000
            )

            if candles:
                all_candles.extend(candles)

            current = chunk_end
            await asyncio.sleep(0.05)

        if not all_candles:
            return None

        df = pd.DataFrame(all_candles)
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
        df = df.sort_values('timestamp').drop_duplicates(subset=['time']).reset_index(drop=True)

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df

    except Exception as e:
        return None

def backtest_gradual_short(df, listing_price, symbol):
    """Backtest gradual short strategy on one coin"""
    if df is None or len(df) < 24:
        return []

    trades = []
    position = None
    entries = []

    for i in range(WAIT_HOURS, len(df)):
        row = df.iloc[i]
        price = row['close']
        high = row['high']
        low = row['low']

        # Check for exit first
        if position:
            # Check SL (high > sl_price)
            if high >= position['sl_price']:
                pnl_pct = -SL_PCT
                trades.append({
                    'symbol': symbol,
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'entry_price': position['avg_entry'],
                    'exit_price': position['sl_price'],
                    'pnl_pct': pnl_pct,
                    'num_entries': len(entries),
                    'exit_reason': 'SL'
                })
                position = None
                entries = []
                continue

            # Check TP (low < tp_price OR low < listing_price)
            tp_target = position['avg_entry'] * (1 - TP_PCT / 100)
            if low <= tp_target or low <= listing_price:
                exit_price = max(tp_target, listing_price * 0.99)
                pnl_pct = (position['avg_entry'] - exit_price) / position['avg_entry'] * 100
                trades.append({
                    'symbol': symbol,
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'entry_price': position['avg_entry'],
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'num_entries': len(entries),
                    'exit_reason': 'TP'
                })
                position = None
                entries = []
                continue

        # Check for entry
        pump_pct = (price / listing_price - 1) * 100

        if pump_pct >= PUMP_THRESHOLD:
            if position is None:
                # First entry
                entries = [price]
                avg_entry = price
                sl_price = price * (1 + SL_PCT / 100)
                position = {
                    'entry_time': row['timestamp'],
                    'avg_entry': avg_entry,
                    'sl_price': sl_price
                }
            elif len(entries) < MAX_ENTRIES:
                # Check if price is higher by entry_step
                if price >= entries[-1] * (1 + ENTRY_STEP / 100):
                    entries.append(price)
                    avg_entry = np.mean(entries)
                    sl_price = price * (1 + SL_PCT / 100)
                    position['avg_entry'] = avg_entry
                    position['sl_price'] = sl_price

    # Close any open position at end
    if position:
        exit_price = df.iloc[-1]['close']
        pnl_pct = (position['avg_entry'] - exit_price) / position['avg_entry'] * 100
        trades.append({
            'symbol': symbol,
            'entry_time': position['entry_time'],
            'exit_time': df.iloc[-1]['timestamp'],
            'entry_price': position['avg_entry'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'num_entries': len(entries),
            'exit_reason': 'END'
        })

    return trades

async def main():
    # Load listings
    listings = pd.read_csv('trading/listings_2025.csv')
    listings['listing_date'] = pd.to_datetime(listings['listing_date'])

    # Filter to coins with at least 30 days of data
    listings = listings[listings['days_listed'] >= 30].reset_index(drop=True)
    print(f"Testing {len(listings)} coins with 30+ days of data")

    config = load_config(os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot', 'config_donchian.yaml'))
    bingx = BingXClient(api_key=config.bingx.api_key, api_secret=config.bingx.api_secret, testnet=False)

    all_trades = []
    processed = 0
    semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads

    async def process_coin(row):
        nonlocal processed
        async with semaphore:
            symbol = row['symbol']
            listing_date = row['listing_date'].to_pydatetime().replace(tzinfo=timezone.utc)
            listing_price = row['first_price']

            df = await download_first_30_days(bingx, symbol, listing_date)
            trades = backtest_gradual_short(df, listing_price, symbol)

            processed += 1
            if processed % 20 == 0:
                print(f"  Progress: {processed}/{len(listings)}")

            return trades

    print("="*80)
    print("BACKTESTING GRADUAL SHORT STRATEGY ON ALL 2025 LISTINGS")
    print("="*80)
    print(f"\nParameters:")
    print(f"  Wait: {WAIT_HOURS}h after listing")
    print(f"  Entry threshold: +{PUMP_THRESHOLD}% above listing")
    print(f"  Max entries: {MAX_ENTRIES} (DCA)")
    print(f"  SL: {SL_PCT}%, TP: {TP_PCT}% or listing price")
    print(f"\nDownloading data and backtesting...")

    tasks = [process_coin(row) for _, row in listings.iterrows()]
    results = await asyncio.gather(*tasks)

    await bingx.close()

    # Flatten trades
    for trades in results:
        all_trades.extend(trades)

    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")

    if not all_trades:
        print("No trades generated!")
        return

    trades_df = pd.DataFrame(all_trades)

    # Calculate equity curve
    equity = 100.0
    max_equity = 100.0
    max_dd = 0
    equities = [100.0]

    trades_df = trades_df.sort_values('exit_time').reset_index(drop=True)

    for _, trade in trades_df.iterrows():
        # Position size based on entries
        total_risk = RISK_PER_TRADE * trade['num_entries']
        position_value = equity * (total_risk / SL_PCT)  # Normalize by SL

        pnl_dollars = position_value * trade['pnl_pct'] / 100
        equity += pnl_dollars

        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)

        equities.append(equity)
        trades_df.loc[trades_df.index == _, 'equity_after'] = equity

    # Stats
    total_return = (equity / 100 - 1) * 100
    win_rate = (trades_df['pnl_pct'] > 0).mean() * 100
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] > 0).any() else 0
    avg_loss = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] <= 0).any() else 0
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    print(f"\n{'Metric':<25} {'Value':>15}")
    print("-" * 42)
    print(f"{'Total Coins Tested':<25} {len(listings):>15}")
    print(f"{'Coins With Trades':<25} {trades_df['symbol'].nunique():>15}")
    print(f"{'Total Trades':<25} {len(trades_df):>15}")
    print(f"{'Win Rate':<25} {win_rate:>14.1f}%")
    print(f"{'Avg Win':<25} {avg_win:>+14.1f}%")
    print(f"{'Avg Loss':<25} {avg_loss:>+14.1f}%")
    print(f"{'Total Return':<25} {total_return:>+14.1f}%")
    print(f"{'Max Drawdown':<25} {max_dd:>14.1f}%")
    print(f"{'R:R Ratio':<25} {rr_ratio:>14.2f}x")
    print(f"{'Final Equity':<25} ${equity:>13.2f}")

    # Exit reason breakdown
    print(f"\nExit Reasons:")
    for reason, count in trades_df['exit_reason'].value_counts().items():
        print(f"  {reason}: {count} ({count/len(trades_df)*100:.1f}%)")

    # Monthly performance
    trades_df['month'] = trades_df['exit_time'].dt.strftime('%Y-%m')
    print(f"\nMonthly Performance:")
    monthly = trades_df.groupby('month').agg({
        'pnl_pct': ['count', 'sum', 'mean']
    }).round(2)
    monthly.columns = ['Trades', 'Total PnL%', 'Avg PnL%']
    print(monthly.to_string())

    # Save results
    trades_df.to_csv('trading/results/new_listings_backtest_full.csv', index=False)
    print(f"\n✅ Saved to trading/results/new_listings_backtest_full.csv")

    # Compare to random (buy and hold)
    avg_listing_change = listings['change_pct'].mean()
    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}")
    print(f"Strategy Return: {total_return:+.1f}%")
    print(f"Buy & Hold (avg): {avg_listing_change:+.1f}%")
    print(f"Edge: {total_return - avg_listing_change:+.1f}%")

if __name__ == '__main__':
    asyncio.run(main())
