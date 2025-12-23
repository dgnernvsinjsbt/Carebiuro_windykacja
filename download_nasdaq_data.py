#!/usr/bin/env python3
"""
Download NASDAQ-100 futures data and compare volatility to MELANIA
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

print("="*80)
print("NASDAQ-100 FUTURES DATA DOWNLOAD")
print("="*80)

# Download NQ futures (NASDAQ-100) - last 60 days (yfinance limit for 15m), 15m intervals
end_date = datetime.now()
start_date = end_date - timedelta(days=59)  # 59 days to stay within limit

print(f"\n📊 Downloading NQ futures data...")
print(f"   Period: {start_date.date()} to {end_date.date()}")
print(f"   Interval: 15m")

try:
    # Try NQ=F (NASDAQ-100 E-mini futures)
    nq = yf.download("NQ=F", start=start_date, end=end_date, interval="15m", progress=False)

    if len(nq) == 0:
        print("   ⚠️  NQ=F returned no data, trying QQQ (NASDAQ-100 ETF)...")
        nq = yf.download("QQQ", start=start_date, end=end_date, interval="15m", progress=False)

    print(f"   ✅ Downloaded {len(nq)} candles")

    # Prepare dataframe
    nq = nq.reset_index()
    nq.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    # Calculate ATR
    nq['tr'] = np.maximum(
        nq['high'] - nq['low'],
        np.maximum(
            abs(nq['high'] - nq['close'].shift(1)),
            abs(nq['low'] - nq['close'].shift(1))
        )
    )
    nq['atr'] = nq['tr'].rolling(14).mean()
    nq['atr_pct'] = (nq['atr'] / nq['close']) * 100

    # Save
    nq.to_csv('trading/nasdaq_3months_15m.csv', index=False)

    print(f"\n💾 Saved to: trading/nasdaq_3months_15m.csv")
    print(f"\n📊 NASDAQ Stats:")
    print(f"   Avg Price: ${nq['close'].mean():.2f}")
    print(f"   Avg ATR: ${nq['atr'].mean():.2f}")
    print(f"   Avg ATR %: {nq['atr_pct'].mean():.3f}%")

    # Load MELANIA for comparison
    melania = pd.read_csv('trading/melania_6months_bingx.csv')
    melania['tr'] = np.maximum(
        melania['high'] - melania['low'],
        np.maximum(
            abs(melania['high'] - melania['close'].shift(1)),
            abs(melania['low'] - melania['close'].shift(1))
        )
    )
    melania['atr'] = melania['tr'].rolling(14).mean()
    melania['atr_pct'] = (melania['atr'] / melania['close']) * 100

    print(f"\n📊 MELANIA Stats (for comparison):")
    print(f"   Avg Price: ${melania['close'].mean():.2f}")
    print(f"   Avg ATR: ${melania['atr'].mean():.4f}")
    print(f"   Avg ATR %: {melania['atr_pct'].mean():.3f}%")

    # Calculate volatility ratio
    volatility_ratio = melania['atr_pct'].mean() / nq['atr_pct'].mean()

    print(f"\n🔥 VOLATILITY COMPARISON:")
    print(f"   MELANIA ATR%: {melania['atr_pct'].mean():.3f}%")
    print(f"   NASDAQ ATR%:  {nq['atr_pct'].mean():.3f}%")
    print(f"   Ratio: MELANIA is {volatility_ratio:.2f}x more volatile than NASDAQ")

    print(f"\n🎯 PARAMETER SCALING RECOMMENDATIONS:")
    print(f"   MELANIA params → NASDAQ params")
    print(f"   RSI trigger: 72 → 72 (keep same)")
    print(f"   Limit offset: 0.8 ATR → {0.8 / volatility_ratio:.2f} ATR")
    print(f"   TP %: 10.0% → {10.0 / volatility_ratio:.2f}%")
    print(f"   SL (swing high method - dynamic, keep same)")
    print(f"   Max SL %: 10.0% → {10.0 / volatility_ratio:.2f}%")

    print("\n✅ Data ready for backtesting!")

except Exception as e:
    print(f"❌ Error downloading data: {e}")
    print("\nTrying alternative: Downloading QQQ ETF instead...")

    try:
        qqq = yf.download("QQQ", start=start_date, end=end_date, interval="15m", progress=False)
        qqq = qqq.reset_index()
        qqq.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        # Calculate ATR
        qqq['tr'] = np.maximum(
            qqq['high'] - qqq['low'],
            np.maximum(
                abs(qqq['high'] - qqq['close'].shift(1)),
                abs(qqq['low'] - qqq['close'].shift(1))
            )
        )
        qqq['atr'] = qqq['tr'].rolling(14).mean()
        qqq['atr_pct'] = (qqq['atr'] / qqq['close']) * 100

        qqq.to_csv('trading/nasdaq_3months_15m.csv', index=False)

        print(f"✅ Downloaded {len(qqq)} candles of QQQ")
        print(f"   Avg ATR %: {qqq['atr_pct'].mean():.3f}%")

    except Exception as e2:
        print(f"❌ Also failed: {e2}")
        print("\nPlease provide NASDAQ data manually.")

print("="*80)
