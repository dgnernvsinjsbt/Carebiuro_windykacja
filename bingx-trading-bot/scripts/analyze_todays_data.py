#!/usr/bin/env python3
"""
Fetch today's FARTCOIN data and check for strategy signals
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Try to import BingX client
try:
    from execution.bingx_client import BingXClient
    import asyncio

    async def fetch_todays_data():
        """Fetch today's 1-min FARTCOIN data"""
        # Load config
        import config
        client = BingXClient(config.BINGX_API_KEY, config.BINGX_SECRET_KEY)

        # Get today's data (last 24 hours)
        symbol = "FARTCOIN-USDT"
        interval = "1m"
        limit = 1440  # 24 hours of 1-min candles

        try:
            klines = await client.get_klines(symbol, interval, limit)

            if not klines:
                print("❌ No data returned from BingX")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            return df

        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None

    def calculate_indicators(df):
        """Calculate strategy indicators"""
        # SMA
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma200'] = df['close'].rolling(200).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume average
        df['volume_avg'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_avg']

        # Candle body
        df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

        # Distance from SMA50
        df['dist_from_sma50'] = (df['close'] - df['sma50']) / df['sma50'] * 100

        return df

    def check_signals(df):
        """Check for strategy signals in today's data"""
        print("\n" + "=" * 60)
        print("ANALYZING TODAY'S FARTCOIN DATA")
        print("=" * 60)

        if len(df) == 0:
            print("❌ No data to analyze")
            return

        print(f"Data period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Total candles: {len(df)}")
        print()

        # Filter to only today's candles (last 24h)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        df_today = df[df['timestamp'] >= today_start].copy()

        print(f"Today's candles (since {today_start}): {len(df_today)}")
        print()

        # Check for LONG signals (explosive breakouts)
        print("🔍 CHECKING FOR LONG SIGNALS (Explosive Breakouts)")
        print("-" * 60)

        long_signals = df_today[
            (df_today['body_pct'] > 1.2) &
            (df_today['volume_ratio'] > 3.0) &
            (df_today['rsi'] >= 45) &
            (df_today['rsi'] <= 75)
        ]

        if len(long_signals) > 0:
            print(f"✅ Found {len(long_signals)} potential LONG signals!")
            print("\nTop 5 signals:")
            for idx, row in long_signals.nlargest(5, 'body_pct').iterrows():
                print(f"  {row['timestamp']}: Body={row['body_pct']:.2f}%, "
                      f"Volume={row['volume_ratio']:.1f}x, RSI={row['rsi']:.1f}")
        else:
            print("❌ No LONG signals found today")

        print()

        # Check for SHORT signals (breakdowns)
        print("🔍 CHECKING FOR SHORT SIGNALS (Breakdowns)")
        print("-" * 60)

        short_signals = df_today[
            (df_today['close'] < df_today['sma50']) &
            (df_today['close'] < df_today['sma200']) &
            (df_today['dist_from_sma50'] < -2.0) &
            (df_today['body_pct'] > 1.2) &
            (df_today['volume_ratio'] > 3.0) &
            (df_today['rsi'] >= 25) &
            (df_today['rsi'] <= 55)
        ]

        if len(short_signals) > 0:
            print(f"✅ Found {len(short_signals)} potential SHORT signals!")
            print("\nTop 5 signals:")
            for idx, row in short_signals.nlargest(5, 'body_pct').iterrows():
                print(f"  {row['timestamp']}: Body={row['body_pct']:.2f}%, "
                      f"Volume={row['volume_ratio']:.1f}x, RSI={row['rsi']:.1f}, "
                      f"Dist={row['dist_from_sma50']:.2f}%")
        else:
            print("❌ No SHORT signals found today")

        print()

        # Market stats
        print("=" * 60)
        print("TODAY'S MARKET STATS")
        print("=" * 60)

        if len(df_today) > 0:
            print(f"Current Price: ${df_today['close'].iloc[-1]:.6f}")
            print(f"High: ${df_today['high'].max():.6f}")
            print(f"Low: ${df_today['low'].min():.6f}")
            print(f"Range: {(df_today['high'].max() / df_today['low'].min() - 1) * 100:.2f}%")

            # Explosive candles
            explosive = df_today[df_today['body_pct'] > 1.2]
            print(f"\nExplosive candles (>1.2% body): {len(explosive)}")

            # Volume spikes
            vol_spikes = df_today[df_today['volume_ratio'] > 3.0]
            print(f"Volume spikes (>3x avg): {len(vol_spikes)}")

            # Current trend
            current_price = df_today['close'].iloc[-1]
            current_sma50 = df_today['sma50'].iloc[-1]
            if not pd.isna(current_sma50):
                trend = "UPTREND" if current_price > current_sma50 else "DOWNTREND"
                print(f"\nCurrent trend: {trend}")
                print(f"Distance from SMA50: {(current_price / current_sma50 - 1) * 100:.2f}%")

        print("=" * 60)

    async def main():
        print("📊 Fetching today's FARTCOIN data from BingX...")

        df = await fetch_todays_data()

        if df is None:
            return

        df = calculate_indicators(df)
        check_signals(df)

    if __name__ == "__main__":
        asyncio.run(main())

except ImportError as e:
    print(f"❌ Cannot import BingX client: {e}")
    print("\nRun this script from the bingx-trading-bot directory")
    print("or check that config.py and execution/bingx_client.py exist")
