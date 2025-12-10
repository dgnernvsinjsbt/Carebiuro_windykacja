#!/usr/bin/env python3
"""Try multiple symbol formats and markets for PIPPIN on BingX"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def test_symbol_spot(symbol):
    """Test if symbol exists on BingX spot market"""
    url = "https://open-api.bingx.com/openApi/spot/v1/market/kline"
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)

    params = {
        'symbol': symbol,
        'interval': '1m',
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('code') == 0 and data.get('data'):
            return True, 'spot', len(data.get('data', []))
        else:
            return False, 'spot', data.get('msg', 'No data')
    except Exception as e:
        return False, 'spot', str(e)

def test_symbol_futures(symbol):
    """Test if symbol exists on BingX perpetual futures"""
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)

    params = {
        'symbol': symbol,
        'interval': '1m',
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('code') == 0 and data.get('data'):
            return True, 'futures', len(data.get('data', []))
        else:
            return False, 'futures', data.get('msg', 'No data')
    except Exception as e:
        return False, 'futures', str(e)

def fetch_bingx_klines_spot(symbol, interval, start_time, end_time):
    """Fetch kline data from BingX spot API"""
    url = "https://open-api.bingx.com/openApi/spot/v1/market/kline"
    all_data = []
    current_end = end_time
    chunk_size = timedelta(minutes=1000)

    while current_end > start_time:
        current_start = max(start_time, current_end - chunk_size)

        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(current_end.timestamp() * 1000),
            'limit': 1000
        }

        print(f"  {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end=' ')

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('code') != 0:
                print(f"Error: {data.get('msg')}")
                break

            klines = data.get('data', [])
            if not klines:
                print("No data")
                break
            else:
                all_data.extend(klines)
                print(f"{len(klines)} candles")

            current_end = current_start - timedelta(minutes=1)
            time.sleep(0.3)

        except Exception as e:
            print(f"Error: {e}")
            break

    return all_data

def fetch_bingx_klines_futures(symbol, interval, start_time, end_time):
    """Fetch kline data from BingX futures API"""
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
    all_data = []
    current_end = end_time
    chunk_size = timedelta(minutes=1000)

    while current_end > start_time:
        current_start = max(start_time, current_end - chunk_size)

        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(current_end.timestamp() * 1000),
            'limit': 1000
        }

        print(f"  {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end=' ')

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('code') != 0:
                print(f"Error: {data.get('msg')}")
                break

            klines = data.get('data', [])
            if not klines:
                print("No data")
                break
            else:
                all_data.extend(klines)
                print(f"{len(klines)} candles")

            current_end = current_start - timedelta(minutes=1)
            time.sleep(0.3)

        except Exception as e:
            print(f"Error: {e}")
            break

    return all_data

# Test different symbol formats
print('=' * 80)
print('Testing PIPPIN symbol formats on BingX...')
print('=' * 80)
print()

symbol_formats = [
    'PIPPIN-USDT',   # Spot with dash
    'PIPPINUSDT',    # Spot without dash
    'PIPPIN-USD',    # Spot USD
    'PIPPINUSD',     # Spot USD no dash
    'PIPPIN-PERP',   # Futures perp
    'PIPPIN-USDT',   # Futures (same as spot format)
]

found_symbols = []

for symbol in symbol_formats:
    print(f"Testing {symbol:20s} ", end='')

    # Test spot
    exists, market, result = test_symbol_spot(symbol)
    if exists:
        print(f"✅ FOUND on SPOT ({result} candles)")
        found_symbols.append((symbol, 'spot'))
    else:
        # Test futures
        exists_fut, market_fut, result_fut = test_symbol_futures(symbol)
        if exists_fut:
            print(f"✅ FOUND on FUTURES ({result_fut} candles)")
            found_symbols.append((symbol, 'futures'))
        else:
            print(f"❌ Not found")

    time.sleep(0.2)

print()
print('=' * 80)

if found_symbols:
    print(f"Found {len(found_symbols)} working symbol(s):")
    for symbol, market in found_symbols:
        print(f"  - {symbol} ({market})")
    print()

    # Download the first found symbol
    symbol, market = found_symbols[0]
    print(f"Downloading data for {symbol} from {market} market...")
    print('=' * 80)
    print()

    interval = '1m'
    end_time = datetime.now()
    start_time = end_time - timedelta(days=10)

    if market == 'spot':
        klines = fetch_bingx_klines_spot(symbol, interval, start_time, end_time)
    else:
        klines = fetch_bingx_klines_futures(symbol, interval, start_time, end_time)

    if klines:
        df = pd.DataFrame(klines)
        df = df.iloc[:, :6]
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

        duration_days = (df["timestamp"].max() - df["timestamp"].min()).days
        filename = f'pippin_{duration_days}d_bingx.csv'
        df.to_csv(filename, index=False)

        print()
        print('=' * 80)
        print('DOWNLOAD COMPLETE')
        print('=' * 80)
        print(f'Symbol: {symbol}')
        print(f'Market: {market}')
        print(f'Total candles: {len(df):,}')
        print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
        print(f'Duration: {duration_days} days ({len(df) / 1440:.1f} days of 1m data)')
        print(f'File saved: {filename}')
        print()

        print('Price Statistics:')
        print(f'  Starting: ${df["close"].iloc[0]:.6f}')
        print(f'  Ending: ${df["close"].iloc[-1]:.6f}')
        print(f'  Change: {(df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100:+.2f}%')
        print(f'  High: ${df["high"].max():.6f}')
        print(f'  Low: ${df["low"].min():.6f}')
        print(f'  Avg Volume: {df["volume"].mean():.2f}')
        print()

        df['pct_change'] = df['close'].pct_change().abs() * 100
        print('Volatility:')
        print(f'  Avg candle move: {df["pct_change"].mean():.3f}%')
        print(f'  Max candle move: {df["pct_change"].max():.3f}%')
        print(f'  Volatile candles (>1%): {(df["pct_change"] > 1.0).sum()} ({(df["pct_change"] > 1.0).sum() / len(df) * 100:.1f}%)')
        print()
        print('=' * 80)

else:
    print("❌ PIPPIN not found on BingX")
    print()
    print("Suggestions:")
    print("  1. Check BingX website for exact symbol name")
    print("  2. Token might be listed under different ticker")
    print("  3. Try other exchanges (Gate.io, MEXC, etc.)")
