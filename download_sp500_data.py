#!/usr/bin/env python3
"""
Download S&P 500 futures data and compare volatility
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

print("="*80)
print("S&P 500 FUTURES DATA DOWNLOAD")
print("="*80)

# Download ES futures (S&P 500) - last 60 days (yfinance limit for 15m), 15m intervals
end_date = datetime.now()
start_date = end_date - timedelta(days=59)

print(f"\n📊 Downloading S&P 500 futures data...")
print(f"   Period: {start_date.date()} to {end_date.date()}")
print(f"   Interval: 15m")

try:
    # Try ES=F (S&P 500 E-mini futures)
    sp = yf.download("ES=F", start=start_date, end=end_date, interval="15m", progress=False)

    if len(sp) == 0:
        print("   ⚠️  ES=F returned no data, trying SPY (S&P 500 ETF)...")
        sp = yf.download("SPY", start=start_date, end=end_date, interval="15m", progress=False)

    print(f"   ✅ Downloaded {len(sp)} candles")

    # Prepare dataframe
    sp = sp.reset_index()
    sp.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    # Calculate ATR
    sp['tr'] = np.maximum(
        sp['high'] - sp['low'],
        np.maximum(
            abs(sp['high'] - sp['close'].shift(1)),
            abs(sp['low'] - sp['close'].shift(1))
        )
    )
    sp['atr'] = sp['tr'].rolling(14).mean()
    sp['atr_pct'] = (sp['atr'] / sp['close']) * 100

    # Save
    sp.to_csv('trading/sp500_3months_15m.csv', index=False)

    print(f"\n💾 Saved to: trading/sp500_3months_15m.csv")
    print(f"\n📊 S&P 500 Stats:")
    print(f"   Avg Price: ${sp['close'].mean():.2f}")
    print(f"   Avg ATR: ${sp['atr'].mean():.2f}")
    print(f"   Avg ATR %: {sp['atr_pct'].mean():.3f}%")

    # Load NASDAQ for comparison
    nasdaq = pd.read_csv('trading/nasdaq_3months_15m.csv')
    nasdaq['tr'] = np.maximum(
        nasdaq['high'] - nasdaq['low'],
        np.maximum(
            abs(nasdaq['high'] - nasdaq['close'].shift(1)),
            abs(nasdaq['low'] - nasdaq['close'].shift(1))
        )
    )
    nasdaq['atr'] = nasdaq['tr'].rolling(14).mean()
    nasdaq['atr_pct'] = (nasdaq['atr'] / nasdaq['close']) * 100

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

    print(f"\n📊 NASDAQ Stats (for comparison):")
    print(f"   Avg Price: ${nasdaq['close'].mean():.2f}")
    print(f"   Avg ATR: ${nasdaq['atr'].mean():.2f}")
    print(f"   Avg ATR %: {nasdaq['atr_pct'].mean():.3f}%")

    print(f"\n📊 MELANIA Stats (for comparison):")
    print(f"   Avg Price: ${melania['close'].mean():.2f}")
    print(f"   Avg ATR: ${melania['atr'].mean():.4f}")
    print(f"   Avg ATR %: {melania['atr_pct'].mean():.3f}%")

    # Calculate volatility ratios
    sp_nasdaq_ratio = sp['atr_pct'].mean() / nasdaq['atr_pct'].mean()
    sp_melania_ratio = melania['atr_pct'].mean() / sp['atr_pct'].mean()

    print(f"\n🔥 VOLATILITY COMPARISON:")
    print(f"   S&P 500 ATR%:  {sp['atr_pct'].mean():.3f}%")
    print(f"   NASDAQ ATR%:   {nasdaq['atr_pct'].mean():.3f}%")
    print(f"   MELANIA ATR%:  {melania['atr_pct'].mean():.3f}%")
    print()
    print(f"   S&P 500 / NASDAQ: {sp_nasdaq_ratio:.2f}x")
    print(f"   MELANIA / S&P 500: {sp_melania_ratio:.2f}x")

    print(f"\n🎯 STRATEGY EXPECTATIONS:")
    if sp_nasdaq_ratio > 0.8 and sp_nasdaq_ratio < 1.2:
        print(f"   S&P 500 volatility similar to NASDAQ ({sp_nasdaq_ratio:.2f}x)")
        print(f"   → Use NASDAQ parameters (RSI<28, offset 0.20, TP 2.0%)")
        print(f"   → Trailing stop likely to work (activation 0.5%, trail 1.0%)")
    elif sp['atr_pct'].mean() < nasdaq['atr_pct'].mean():
        print(f"   S&P 500 LESS volatile than NASDAQ ({sp_nasdaq_ratio:.2f}x)")
        print(f"   → May need SMALLER offset/TP than NASDAQ")
        print(f"   → Tighter trailing stop may work")
    else:
        print(f"   S&P 500 MORE volatile than NASDAQ ({sp_nasdaq_ratio:.2f}x)")
        print(f"   → May need LARGER offset/TP than NASDAQ")

    print("\n✅ Data ready for backtesting!")

except Exception as e:
    print(f"❌ Error downloading data: {e}")
    print("\nTrying alternative: Downloading SPY ETF instead...")

    try:
        spy = yf.download("SPY", start=start_date, end=end_date, interval="15m", progress=False)
        spy = spy.reset_index()
        spy.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        # Calculate ATR
        spy['tr'] = np.maximum(
            spy['high'] - spy['low'],
            np.maximum(
                abs(spy['high'] - spy['close'].shift(1)),
                abs(spy['low'] - spy['close'].shift(1))
            )
        )
        spy['atr'] = spy['tr'].rolling(14).mean()
        spy['atr_pct'] = (spy['atr'] / spy['close']) * 100

        spy.to_csv('trading/sp500_3months_15m.csv', index=False)

        print(f"✅ Downloaded {len(spy)} candles of SPY")
        print(f"   Avg ATR %: {spy['atr_pct'].mean():.3f}%")

    except Exception as e2:
        print(f"❌ Also failed: {e2}")
        print("\nPlease provide S&P 500 data manually.")

print("="*80)
