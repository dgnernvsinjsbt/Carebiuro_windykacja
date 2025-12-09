#!/usr/bin/env python3
"""
Analyze why baseline strategies failed on BingX data
"""

import pandas as pd
import numpy as np

def analyze_signal_frequency():
    """Check why SHORT strategy found only 3 trades"""

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print("="*80)
    print("SIGNAL FREQUENCY ANALYSIS")
    print("="*80)

    # Calculate indicators
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    df['sma_distance'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

    # Trend analysis
    df['downtrend'] = (df['close'] < df['sma50']) & (df['close'] < df['sma200'])
    df['uptrend'] = (df['close'] > df['sma50']) & (df['close'] > df['sma200'])
    df['below_2pct'] = df['sma_distance'] < -2.0

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi_short_range'] = (df['rsi'] >= 25) & (df['rsi'] <= 55)

    # Volume
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    df['volume_spike'] = df['volume_ratio'] > 3.0

    # Candle metrics
    df['body'] = abs(df['close'] - df['open'])
    df['body_pct'] = (df['body'] / df['open']) * 100
    df['is_bearish'] = df['close'] < df['open']
    df['explosive_body'] = df['body_pct'] > 1.2

    df['upper_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['lower_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / df['body'].replace(0, np.nan)
    df['minimal_wicks'] = df['wick_ratio'] < 0.35

    # Filter after warmup
    df_valid = df[200:].copy()

    print(f"\n📊 MARKET REGIME ANALYSIS (after 200-bar warmup)")
    print(f"  Total candles: {len(df_valid):,}")
    print(f"  Downtrend (below both SMAs): {df_valid['downtrend'].sum():,} ({df_valid['downtrend'].mean()*100:.1f}%)")
    print(f"  Uptrend (above both SMAs):   {df_valid['uptrend'].sum():,} ({df_valid['uptrend'].mean()*100:.1f}%)")
    print(f"  Below 2% from SMA50:         {df_valid['below_2pct'].sum():,} ({df_valid['below_2pct'].mean()*100:.1f}%)")

    print(f"\n🎯 SHORT STRATEGY FILTERS (sequential)")
    total = len(df_valid)
    print(f"  1. Total candles:            {total:,} (100.0%)")

    step1 = df_valid['downtrend'].sum()
    print(f"  2. Downtrend:                {step1:,} ({step1/total*100:.1f}%)")

    step2 = (df_valid['downtrend'] & df_valid['below_2pct']).sum()
    print(f"  3. + Below 2%:               {step2:,} ({step2/total*100:.1f}%)")

    step3 = (df_valid['downtrend'] & df_valid['below_2pct'] & df_valid['is_bearish']).sum()
    print(f"  4. + Bearish candle:         {step3:,} ({step3/total*100:.1f}%)")

    step4 = (df_valid['downtrend'] & df_valid['below_2pct'] & df_valid['is_bearish'] & df_valid['explosive_body']).sum()
    print(f"  5. + Explosive body:         {step4:,} ({step4/total*100:.1f}%)")

    step5 = (df_valid['downtrend'] & df_valid['below_2pct'] & df_valid['is_bearish'] &
             df_valid['explosive_body'] & df_valid['volume_spike']).sum()
    print(f"  6. + Volume spike:           {step5:,} ({step5/total*100:.1f}%)")

    step6 = (df_valid['downtrend'] & df_valid['below_2pct'] & df_valid['is_bearish'] &
             df_valid['explosive_body'] & df_valid['volume_spike'] & df_valid['minimal_wicks']).sum()
    print(f"  7. + Minimal wicks:          {step6:,} ({step6/total*100:.1f}%)")

    step7 = (df_valid['downtrend'] & df_valid['below_2pct'] & df_valid['is_bearish'] &
             df_valid['explosive_body'] & df_valid['volume_spike'] & df_valid['minimal_wicks'] &
             df_valid['rsi_short_range']).sum()
    print(f"  8. + RSI 25-55:              {step7:,} ({step7/total*100:.1f}%)")

    print(f"\n🎯 LONG STRATEGY FILTERS (simplified)")
    df['is_bullish'] = df['close'] > df['open']
    df['rsi_long_range'] = (df['rsi'] >= 45) & (df['rsi'] <= 75)

    df_valid = df[200:].copy()  # Reset after adding new columns

    long_step1 = df_valid['is_bullish'].sum()
    print(f"  1. Bullish candle:           {long_step1:,} ({long_step1/total*100:.1f}%)")

    long_step2 = (df_valid['is_bullish'] & df_valid['explosive_body']).sum()
    print(f"  2. + Explosive body:         {long_step2:,} ({long_step2/total*100:.1f}%)")

    long_step3 = (df_valid['is_bullish'] & df_valid['explosive_body'] & df_valid['volume_spike']).sum()
    print(f"  3. + Volume spike:           {long_step3:,} ({long_step3/total*100:.1f}%)")

    long_step4 = (df_valid['is_bullish'] & df_valid['explosive_body'] & df_valid['volume_spike'] &
                  df_valid['minimal_wicks']).sum()
    print(f"  4. + Minimal wicks:          {long_step4:,} ({long_step4/total*100:.1f}%)")

    long_step5 = (df_valid['is_bullish'] & df_valid['explosive_body'] & df_valid['volume_spike'] &
                  df_valid['minimal_wicks'] & df_valid['rsi_long_range']).sum()
    print(f"  5. + RSI 45-75:              {long_step5:,} ({long_step5/total*100:.1f}%)")

    print(f"\n💡 KEY INSIGHTS")
    print(f"  - SHORT strategy severely constrained by 2% distance requirement")
    print(f"  - Only {step2/total*100:.1f}% of candles meet downtrend + 2% below SMA50")
    print(f"  - Explosive breakdown requirement drops this to {step7/total*100:.1f}%")
    print(f"  - LONG strategy less constrained but still requires rare explosive conditions")

    # Volatility analysis
    print(f"\n📊 VOLATILITY METRICS")
    print(f"  Avg ATR: ${df_valid['atr'].mean():.6f}")
    print(f"  Avg candle range: {df_valid['body_pct'].mean():.3f}%")
    print(f"  Candles > 1.2% body: {(df_valid['body_pct'] > 1.2).sum():,} ({(df_valid['body_pct'] > 1.2).mean()*100:.1f}%)")
    print(f"  Volume spikes (3x+): {df_valid['volume_spike'].sum():,} ({df_valid['volume_spike'].mean()*100:.1f}%)")

    print("="*80)


def analyze_price_differences():
    """Compare BingX price action to understand why LBank strategies failed"""

    print("\n" + "="*80)
    print("BINGX VS LBANK PRICE CHARACTERISTICS")
    print("="*80)

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Calculate metrics
    df['returns'] = df['close'].pct_change()
    df['range_pct'] = ((df['high'] - df['low']) / df['close']) * 100

    print(f"\n📊 BINGX CHARACTERISTICS")
    print(f"  Avg 1-min return: {df['returns'].mean()*100:.4f}%")
    print(f"  Volatility (std): {df['returns'].std()*100:.4f}%")
    print(f"  Avg range:        {df['range_pct'].mean():.3f}%")
    print(f"  Avg volume:       {df['volume'].mean():,.0f}")

    print(f"\n💡 HYPOTHESIS")
    print(f"  - BingX may have different microstructure (perpetual futures vs spot)")
    print(f"  - Higher volume but potentially different price action characteristics")
    print(f"  - Explosive patterns may behave differently due to futures dynamics")
    print(f"  - Stop distances (3x ATR) may be too tight for BingX volatility")

    print("="*80)


if __name__ == "__main__":
    analyze_signal_frequency()
    analyze_price_differences()
