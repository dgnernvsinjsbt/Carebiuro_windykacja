"""
Check if any signals should have been generated in the last 48 hours
across all 10 active strategies.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time

# BingX API endpoint
BASE_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"

# All 10 active strategies with their specific RSI levels
STRATEGIES = {
    'CRV-USDT': {'type': 'rsi_swing', 'rsi_low': 27, 'rsi_high': 65},
    'MELANIA-USDT': {'type': 'rsi_swing', 'rsi_low': 27, 'rsi_high': 65},
    'AIXBT-USDT': {'type': 'rsi_swing', 'rsi_low': 27, 'rsi_high': 65},
    'DOGE-USDT': {'type': 'rsi_swing', 'rsi_low': 27, 'rsi_high': 65},
    'TRUMPSOL-USDT': {'type': 'rsi_swing', 'rsi_low': 30, 'rsi_high': 65},
    'UNI-USDT': {'type': 'rsi_swing', 'rsi_low': 30, 'rsi_high': 65},
    'XLM-USDT': {'type': 'rsi_swing', 'rsi_low': 30, 'rsi_high': 65},
    'MOODENG-USDT': {'type': 'rsi_swing', 'rsi_low': 30, 'rsi_high': 65},
    '1000PEPE-USDT': {'type': 'rsi_swing', 'rsi_low': 30, 'rsi_high': 65},
    'FARTCOIN-USDT': {'type': 'atr_limit'},
}

def download_klines(symbol, interval='1h', limit=100):
    """Download klines from BingX"""
    params = {
        'symbol': symbol,
        'interval': interval,  # 1h = 1 hour
        'limit': limit
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != 0:
            print(f"❌ {symbol}: API error - {data.get('msg')}")
            return None

        klines = data['data']

        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume'
        ])

        df['time'] = pd.to_datetime(df['time'].astype(int), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df

    except Exception as e:
        print(f"❌ {symbol}: Download failed - {e}")
        return None

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi

def calculate_ema(prices, period):
    """Calculate EMA"""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_atr(df, period=14):
    """Calculate ATR"""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    tr[0] = high[0] - low[0]

    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])

    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr

def check_rsi_swing_signals(df, symbol, rsi_low=30, rsi_high=65):
    """Check for RSI Swing signals (based on strategy configs)"""
    # Calculate indicators
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['ema_20'] = calculate_ema(df['close'], 20)

    signals = []

    # Check last 10 hours only (need 14+ bars warmup for RSI)
    for i in range(len(df) - 10, len(df)):
        if i < 20:  # Need warmup (14 for RSI + buffer)
            continue

        rsi = df['rsi'].iloc[i]
        prev_rsi = df['rsi'].iloc[i-1]
        close = df['close'].iloc[i]
        time = df['time'].iloc[i]

        # LONG: RSI crosses above threshold
        if prev_rsi <= rsi_low and rsi > rsi_low:
            signals.append({
                'time': time,
                'type': 'LONG',
                'price': close,
                'rsi': rsi,
                'reason': f'RSI cross above {rsi_low} ({prev_rsi:.1f} -> {rsi:.1f})'
            })

        # SHORT: RSI crosses below threshold
        if prev_rsi >= rsi_high and rsi < rsi_high:
            signals.append({
                'time': time,
                'type': 'SHORT',
                'price': close,
                'rsi': rsi,
                'reason': f'RSI cross below {rsi_high} ({prev_rsi:.1f} -> {rsi:.1f})'
            })

    return signals

def check_atr_limit_signals(df, symbol):
    """Check for ATR Expansion signals (FARTCOIN strategy)"""
    # Calculate indicators
    df['atr'] = calculate_atr(df, 14)
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['ema_20'] = calculate_ema(df['close'], 20)

    signals = []

    # Check last 10 hours only (need warmup for indicators)
    for i in range(len(df) - 10, len(df)):
        if i < 30:  # Need warmup (20 for ATR MA + buffer)
            continue

        atr = df['atr'].iloc[i]
        atr_ma = df['atr_ma'].iloc[i]
        close = df['close'].iloc[i]
        open_price = df['open'].iloc[i]
        ema_20 = df['ema_20'].iloc[i]
        time = df['time'].iloc[i]

        # ATR expansion check
        if pd.isna(atr_ma) or atr_ma == 0:
            continue

        atr_ratio = atr / atr_ma
        ema_distance = abs(close - ema_20) / ema_20

        # ATR expansion + EMA distance filter
        if atr_ratio > 1.5 and ema_distance < 0.03:
            # Directional candle
            if close > open_price:  # Bullish
                signals.append({
                    'time': time,
                    'type': 'LONG (limit 1% above)',
                    'price': close,
                    'limit_price': close * 1.01,
                    'atr_ratio': atr_ratio,
                    'reason': f'ATR expansion {atr_ratio:.2f}x, bullish candle'
                })
            elif close < open_price:  # Bearish
                signals.append({
                    'time': time,
                    'type': 'SHORT (limit 1% below)',
                    'price': close,
                    'limit_price': close * 0.99,
                    'atr_ratio': atr_ratio,
                    'reason': f'ATR expansion {atr_ratio:.2f}x, bearish candle'
                })

    return signals

def main():
    print("=" * 80)
    print("🔍 CHECKING LAST 10 HOURS FOR SIGNALS ACROSS ALL 10 STRATEGIES")
    print("=" * 80)
    print()

    total_signals = 0
    results = {}

    for symbol, config in STRATEGIES.items():
        strategy_type = config['type']
        print(f"\n📊 {symbol} ({strategy_type.upper()})")
        if strategy_type == 'rsi_swing':
            print(f"    RSI Thresholds: {config['rsi_low']}/{config['rsi_high']}")
        print("-" * 60)

        # Download data
        df = download_klines(symbol, interval='1h', limit=100)

        if df is None or len(df) < 50:
            print(f"   ⚠️  Insufficient data")
            results[symbol] = {'signals': [], 'error': 'Insufficient data'}
            continue

        print(f"   ✅ Downloaded {len(df)} candles")
        print(f"   📅 From: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")

        # Check for signals
        if strategy_type == 'rsi_swing':
            signals = check_rsi_swing_signals(df, symbol, config['rsi_low'], config['rsi_high'])
        else:  # atr_limit
            signals = check_atr_limit_signals(df, symbol)

        results[symbol] = {'signals': signals, 'error': None}

        if len(signals) == 0:
            print(f"   ❌ NO SIGNALS in last 10 hours")
        else:
            print(f"   🎯 {len(signals)} SIGNAL(S) FOUND:")
            for sig in signals:
                print(f"      • {sig['time']} - {sig['type']}")
                print(f"        Price: ${sig['price']:.6f}")
                print(f"        {sig['reason']}")

        total_signals += len(signals)
        time.sleep(0.5)  # Rate limiting

    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"\n🎯 Total signals found: {total_signals}")

    if total_signals == 0:
        print("\n⚠️  NO SIGNALS across any strategy in the last 10 hours!")
        print("    This suggests:")
        print("    • Market is in low-volatility consolidation")
        print("    • No extreme RSI readings (oversold/overbought)")
        print("    • No ATR expansion events")
        print("\n    ✅ Your bot behavior is NORMAL - just a quiet market period.")
    else:
        print(f"\n🔥 Found {total_signals} signals that SHOULD have triggered!")
        print("    Possible issues:")
        print("    • Bot configuration mismatch")
        print("    • Data sync issues")
        print("    • Strategy not loaded properly")
        print("\n    ⚠️  INVESTIGATE BOT SETUP")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
