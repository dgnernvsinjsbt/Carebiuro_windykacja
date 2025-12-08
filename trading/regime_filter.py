#!/usr/bin/env python3
"""
Regime Detection Filters for Short Strategy
Based on FARTCOIN regime analysis findings:
- Weak Uptrends are UNPROFITABLE (-15.20% over 38 trades)
- Strong Uptrends are PROFITABLE (+32.24% over 26 trades)
- Filter should target Weak Uptrends ONLY, not all uptrends
"""

import pandas as pd
import numpy as np
from typing import Dict, Literal

RegimeType = Literal['Strong Uptrend', 'Weak Uptrend', 'Sideways', 'Weak Downtrend', 'Strong Downtrend']


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()


def classify_regime(df: pd.DataFrame, idx: int) -> Dict:
    """
    Classify market regime at given index

    Regimes (from analysis):
    - Strong Uptrend: price > EMA100 by 2%+ AND EMA50 slope > 0.5%
    - Weak Uptrend: price > EMA100 OR EMA50 slope > 0 (but not strong)
    - Strong Downtrend: price < EMA100 by 5%+ AND EMA50 slope < -0.5%
    - Weak Downtrend: price < EMA100 (but not strong)
    - Sideways: neither up nor down

    Args:
        df: DataFrame with OHLC data and indicators
        idx: Current bar index

    Returns:
        Dict with regime classification and metrics
    """
    row = df.iloc[idx]

    # Price vs long-term EMAs
    price_vs_ema50 = (row['close'] - row['ema50']) / row['ema50'] * 100 if row['ema50'] > 0 else 0
    price_vs_ema100 = (row['close'] - row['ema100']) / row['ema100'] * 100 if row['ema100'] > 0 else 0

    # EMA slopes (look back 20 bars)
    ema50_slope = 0
    if idx >= 20:
        ema50_slope = (row['ema50'] - df.iloc[idx-20]['ema50']) / df.iloc[idx-20]['ema50'] * 100

    # Recent price momentum
    price_7d = 0
    price_14d = 0
    if idx >= 28:  # 28 bars = 7 days at 15m
        price_7d = (row['close'] / df.iloc[idx-28]['close'] - 1) * 100
    if idx >= 56:  # 56 bars = 14 days
        price_14d = (row['close'] / df.iloc[idx-56]['close'] - 1) * 100

    # Classification logic
    regime_type: RegimeType
    short_favorable: bool

    if price_vs_ema100 > 2 and ema50_slope > 0.5:
        regime_type = 'Strong Uptrend'
        short_favorable = True  # Analysis shows this is profitable!
    elif price_vs_ema100 > 0 or ema50_slope > 0:
        regime_type = 'Weak Uptrend'
        short_favorable = False  # ONLY unprofitable regime
    elif price_vs_ema100 < -5 and ema50_slope < -0.5:
        regime_type = 'Strong Downtrend'
        short_favorable = True
    elif price_vs_ema100 < 0:
        regime_type = 'Weak Downtrend'
        short_favorable = True
    else:
        regime_type = 'Sideways'
        short_favorable = True  # Neutral, allow trading

    return {
        'type': regime_type,
        'short_favorable': short_favorable,
        'price_vs_ema50': price_vs_ema50,
        'price_vs_ema100': price_vs_ema100,
        'ema50_slope': ema50_slope,
        'price_7d_change': price_7d,
        'price_14d_change': price_14d,
    }


def should_trade(df: pd.DataFrame, idx: int, filter_type: str = 'optimal') -> bool:
    """
    Determine if we should take a trade based on regime filter

    Filter types:
    - 'none': Always trade (no filter)
    - 'optimal': Filter out Weak Uptrends only (recommended)
    - 'conservative': Filter out all uptrends
    - 'aggressive': Only trade in Strong Downtrends

    Args:
        df: DataFrame with OHLC data and calculated indicators
        idx: Current bar index
        filter_type: Type of filter to apply

    Returns:
        True if should trade, False if should skip
    """
    if filter_type == 'none':
        return True

    # Ensure indicators are calculated
    if 'ema50' not in df.columns or 'ema100' not in df.columns:
        raise ValueError("DataFrame must have ema50 and ema100 columns. Calculate indicators first.")

    regime = classify_regime(df, idx)

    if filter_type == 'optimal':
        # Filter out ONLY Weak Uptrends
        return regime['short_favorable']

    elif filter_type == 'conservative':
        # Filter out ALL uptrends
        return regime['type'] not in ['Strong Uptrend', 'Weak Uptrend']

    elif filter_type == 'aggressive':
        # Only trade in Strong Downtrends
        return regime['type'] == 'Strong Downtrend'

    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare DataFrame with all required indicators for regime detection

    Args:
        df: Raw OHLC DataFrame with columns: timestamp, open, high, low, close

    Returns:
        DataFrame with added indicators: ema5, ema20, ema50, ema100, ema200
    """
    df = df.copy()

    # Calculate all EMAs needed for strategy and regime detection
    df['ema5'] = calculate_ema(df['close'], 5)
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['ema100'] = calculate_ema(df['close'], 100)
    df['ema200'] = calculate_ema(df['close'], 200)

    return df


# Filter configurations with descriptions
FILTER_CONFIGS = {
    'none': {
        'name': 'No Filter (Baseline)',
        'description': 'Trade all signals, no regime filtering',
        'expected_trades': 'All signals',
    },
    'optimal': {
        'name': 'Optimal Filter (Recommended)',
        'description': 'Filter out Weak Uptrends only',
        'expected_trades': '~50-60 trades (avoid 40% of signals)',
        'rationale': 'Analysis shows Weak Uptrends are ONLY unprofitable regime',
    },
    'conservative': {
        'name': 'Conservative Filter',
        'description': 'Filter out ALL uptrends',
        'expected_trades': '~24 trades (downtrends only)',
        'rationale': 'Avoid all uptrend risk, but misses Strong Uptrend profits',
    },
    'aggressive': {
        'name': 'Aggressive Filter',
        'description': 'Only trade Strong Downtrends',
        'expected_trades': '~8 trades (very selective)',
        'rationale': 'Highest win rate (75%) but very few opportunities',
    },
}


def get_filter_description(filter_type: str) -> str:
    """Get human-readable description of a filter configuration"""
    config = FILTER_CONFIGS.get(filter_type, {})
    if not config:
        return f"Unknown filter: {filter_type}"

    desc = f"{config['name']}\n"
    desc += f"  Description: {config['description']}\n"
    desc += f"  Expected trades: {config['expected_trades']}"
    if 'rationale' in config:
        desc += f"\n  Rationale: {config['rationale']}"

    return desc


if __name__ == '__main__':
    # Example usage
    print("=" * 80)
    print("REGIME FILTER CONFIGURATIONS")
    print("=" * 80)

    for filter_type in FILTER_CONFIGS.keys():
        print(f"\n{get_filter_description(filter_type)}")

    print("\n" + "=" * 80)
    print("KEY INSIGHT FROM ANALYSIS")
    print("=" * 80)
    print("\n⚠️  COUNTERINTUITIVE FINDING:")
    print("   Strong Uptrends are PROFITABLE for shorts (+32% return, 50% win rate)")
    print("   Only Weak Uptrends are unprofitable (-15% return, 37% win rate)")
    print("\n✅ OPTIMAL STRATEGY:")
    print("   Filter Weak Uptrends ONLY, keep Strong Uptrends")
    print("   This preserves ~+112% return while cutting 43% of trades")
    print("\n" + "=" * 80)