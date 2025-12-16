"""
Show current RSI levels and recent volatility for all 10 coins
"""
import pandas as pd
import numpy as np
import requests

BASE_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"

COINS = ['CRV-USDT', 'MELANIA-USDT', 'AIXBT-USDT', 'TRUMPSOL-USDT',
         'UNI-USDT', 'DOGE-USDT', 'XLM-USDT', 'MOODENG-USDT',
         'FARTCOIN-USDT', '1000PEPE-USDT']

def download_klines(symbol, interval='1h', limit=50):
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()
        if data.get('code') != 0:
            return None
        klines = data['data']
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'].astype(int), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except:
        return None

def calculate_rsi(prices, period=14):
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

def main():
    print("=" * 90)
    print("📊 CURRENT RSI LEVELS & VOLATILITY - LAST 10 HOURS")
    print("=" * 90)
    print()

    results = []

    for symbol in COINS:
        df = download_klines(symbol, '1h', 50)
        if df is None or len(df) < 20:
            continue

        df['rsi'] = calculate_rsi(df['close'].values, 14)

        # Get last 10 hours
        recent = df.tail(10)
        current_rsi = df['rsi'].iloc[-1]
        min_rsi_10h = recent['rsi'].min()
        max_rsi_10h = recent['rsi'].max()

        # Volatility (max price move in last 10h)
        price_range = ((recent['high'].max() - recent['low'].min()) / recent['close'].iloc[0]) * 100

        results.append({
            'symbol': symbol.replace('-USDT', ''),
            'current_rsi': current_rsi,
            'min_rsi_10h': min_rsi_10h,
            'max_rsi_10h': max_rsi_10h,
            'volatility_10h': price_range
        })

    # Sort by how close to oversold
    results.sort(key=lambda x: x['min_rsi_10h'])

    print(f"{'Coin':<12} {'Current RSI':>12} {'Min (10h)':>12} {'Max (10h)':>12} {'Vol (10h)':>12}  Status")
    print("-" * 90)

    for r in results:
        current = r['current_rsi']
        min_rsi = r['min_rsi_10h']
        max_rsi = r['max_rsi_10h']
        vol = r['volatility_10h']

        # Status based on proximity to signal zones
        if min_rsi <= 30 or max_rsi >= 70:
            status = "🔥 SIGNAL!"
        elif min_rsi <= 35:
            status = "⚠️  Close to oversold"
        elif max_rsi >= 65:
            status = "⚠️  Close to overbought"
        else:
            status = "😴 Neutral"

        print(f"{r['symbol']:<12} {current:>12.1f} {min_rsi:>12.1f} {max_rsi:>12.1f} {vol:>11.2f}%  {status}")

    print("\n" + "=" * 90)
    print("📈 INTERPRETATION:")
    print("=" * 90)
    print()
    print("🎯 SIGNAL ZONES:")
    print("   • BUY:  RSI crosses above 30 (oversold → reversal)")
    print("   • SELL: RSI crosses below 70 (overbought → reversal)")
    print()

    oversold = [r for r in results if r['min_rsi_10h'] <= 30]
    overbought = [r for r in results if r['max_rsi_10h'] >= 70]
    neutral = [r for r in results if r['min_rsi_10h'] > 35 and r['max_rsi_10h'] < 65]

    if oversold:
        print(f"🔥 OVERSOLD (RSI ≤ 30): {len(oversold)} coins - SHOULD have buy signals")
    else:
        print("❌ OVERSOLD (RSI ≤ 30): 0 coins - No buy signals expected")

    if overbought:
        print(f"🔥 OVERBOUGHT (RSI ≥ 70): {len(overbought)} coins - SHOULD have sell signals")
    else:
        print("❌ OVERBOUGHT (RSI ≥ 70): 0 coins - No sell signals expected")

    if neutral:
        print(f"😴 NEUTRAL (RSI 35-65): {len(neutral)} coins - Very calm, no signals")

    avg_vol = sum(r['volatility_10h'] for r in results) / len(results)
    print(f"\n📊 Average 10h volatility: {avg_vol:.2f}%")

    if avg_vol < 3:
        print("   → VERY LOW volatility (< 3%) - Consolidation phase")
    elif avg_vol < 5:
        print("   → LOW volatility (3-5%) - Quiet market")
    elif avg_vol < 10:
        print("   → MODERATE volatility (5-10%) - Normal trading")
    else:
        print("   → HIGH volatility (> 10%) - Active trading")

    print("\n" + "=" * 90)

if __name__ == "__main__":
    main()
