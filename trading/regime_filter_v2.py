#!/usr/bin/env python3
"""
Enhanced Regime Detection Filters - Version 2
Goal: Achieve <30% max drawdown while maintaining strong returns

Key insight from analysis:
- March 2025 catastrophe: +77% rally, 30 trades lost -75%
- Need to detect SUSTAINED uptrends, not just weak pullbacks
- Focus on multi-timeframe momentum and EMA alignment
"""

import pandas as pd
import numpy as np
from typing import Dict, Literal

RegimeType = Literal['Avoid', 'Caution', 'Favorable', 'Highly Favorable']


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def prepare_dataframe_v2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare DataFrame with comprehensive indicators

    Args:
        df: Raw OHLC DataFrame

    Returns:
        DataFrame with all technical indicators
    """
    df = df.copy()

    # EMAs
    df['ema5'] = calculate_ema(df['close'], 5)
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['ema100'] = calculate_ema(df['close'], 100)
    df['ema200'] = calculate_ema(df['close'], 200)

    # Price vs EMAs (percentage deviation)
    df['price_vs_ema50'] = (df['close'] - df['ema50']) / df['ema50'] * 100
    df['price_vs_ema100'] = (df['close'] - df['ema100']) / df['ema100'] * 100
    df['price_vs_ema200'] = (df['close'] - df['ema200']) / df['ema200'] * 100

    # EMA slopes (20-bar lookback)
    df['ema20_slope'] = df['ema20'].pct_change(20) * 100
    df['ema50_slope'] = df['ema50'].pct_change(20) * 100
    df['ema100_slope'] = df['ema100'].pct_change(20) * 100

    # Multi-timeframe momentum
    df['momentum_1d'] = df['close'].pct_change(4) * 100    # 1 hour = 4 bars
    df['momentum_3d'] = df['close'].pct_change(12) * 100   # 3 hours = 12 bars
    df['momentum_5d'] = df['close'].pct_change(20) * 100   # 5 hours = 20 bars
    df['momentum_10d'] = df['close'].pct_change(40) * 100  # 10 hours = 40 bars
    df['momentum_20d'] = df['close'].pct_change(80) * 100  # 20 hours = 80 bars

    # Volatility
    df['returns'] = df['close'].pct_change()
    df['volatility_20'] = df['returns'].rolling(20).std() * 100
    df['volatility_50'] = df['returns'].rolling(50).std() * 100

    # ATR
    df['atr'] = calculate_atr(df, 14)
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Recent strength (how many of last N bars were up)
    df['up_bars_5'] = (df['close'] > df['close'].shift(1)).rolling(5).sum()
    df['up_bars_10'] = (df['close'] > df['close'].shift(1)).rolling(10).sum()
    df['up_bars_20'] = (df['close'] > df['close'].shift(1)).rolling(20).sum()

    return df


def detect_sustained_uptrend(df: pd.DataFrame, idx: int) -> Dict:
    """
    Detect if we're in a SUSTAINED uptrend (like March 2025 rally)
    This is the killer condition we need to AVOID

    Characteristics of March catastrophe:
    - Price rallied +77% in 3 weeks
    - EMA50 slope: +0.63%, EMA100 slope: +0.63%
    - Price vs EMA100: +1.5%
    - All EMAs rising together

    Args:
        df: DataFrame with calculated indicators
        idx: Current bar index

    Returns:
        Dict with uptrend detection results
    """
    row = df.iloc[idx]

    # Count uptrend signals
    uptrend_score = 0
    reasons = []

    # 1. Price above ALL major EMAs
    if row['price_vs_ema50'] > 0 and row['price_vs_ema100'] > 0 and row['price_vs_ema200'] > 0:
        uptrend_score += 3
        reasons.append("Price above all EMAs")

    # 2. ALL EMAs rising (aligned uptrend)
    if row['ema50_slope'] > 0.3 and row['ema100_slope'] > 0.3:
        uptrend_score += 3
        reasons.append("Strong EMA slopes")

    # 3. Positive momentum across multiple timeframes
    positive_momentum_count = sum([
        row['momentum_5d'] > 0,
        row['momentum_10d'] > 0,
        row['momentum_20d'] > 0,
    ])
    if positive_momentum_count >= 2:
        uptrend_score += 2
        reasons.append(f"{positive_momentum_count}/3 timeframes positive")

    # 4. Recent bars mostly up (buying pressure)
    if row['up_bars_20'] > 12:  # More than 60% of last 20 bars are up
        uptrend_score += 2
        reasons.append(f"{row['up_bars_20']}/20 recent bars up")

    # Classification
    if uptrend_score >= 7:
        severity = 'Strong'  # Like March 2025 - AVOID AT ALL COSTS
    elif uptrend_score >= 5:
        severity = 'Moderate'  # Risky, likely avoid
    elif uptrend_score >= 3:
        severity = 'Weak'  # Proceed with caution
    else:
        severity = 'None'  # Safe to trade

    return {
        'score': uptrend_score,
        'severity': severity,
        'reasons': reasons,
        'avoid': uptrend_score >= 5,  # Avoid Moderate and Strong uptrends
    }


def classify_regime_v2(df: pd.DataFrame, idx: int) -> Dict:
    """
    Enhanced regime classification

    Returns:
        Dict with regime assessment and trading recommendation
    """
    row = df.iloc[idx]

    # First, check for sustained uptrend (DANGER)
    uptrend_check = detect_sustained_uptrend(df, idx)

    if uptrend_check['severity'] == 'Strong':
        return {
            'regime': 'Avoid',
            'should_trade': False,
            'confidence': 'High',
            'reason': 'Strong sustained uptrend detected - March 2025 pattern',
            'details': uptrend_check,
        }

    if uptrend_check['severity'] == 'Moderate':
        return {
            'regime': 'Caution',
            'should_trade': False,
            'confidence': 'Medium',
            'reason': 'Moderate uptrend - risky for shorts',
            'details': uptrend_check,
        }

    # Check for favorable downtrend conditions
    downtrend_score = 0

    # Strong downtrend indicators
    if row['price_vs_ema100'] < -3:
        downtrend_score += 2
    if row['ema100_slope'] < -0.5:
        downtrend_score += 2
    if row['momentum_10d'] < -5:
        downtrend_score += 2
    if row['up_bars_20'] < 8:  # Less than 40% up bars
        downtrend_score += 1

    if downtrend_score >= 5:
        return {
            'regime': 'Highly Favorable',
            'should_trade': True,
            'confidence': 'High',
            'reason': 'Strong downtrend conditions',
            'details': {'downtrend_score': downtrend_score},
        }

    if downtrend_score >= 3:
        return {
            'regime': 'Favorable',
            'should_trade': True,
            'confidence': 'Medium',
            'reason': 'Decent downtrend setup',
            'details': {'downtrend_score': downtrend_score},
        }

    # Weak/unclear conditions
    if uptrend_check['severity'] == 'Weak':
        return {
            'regime': 'Caution',
            'should_trade': False,
            'confidence': 'Low',
            'reason': 'Weak uptrend present',
            'details': uptrend_check,
        }

    # Neutral/sideways
    return {
        'regime': 'Favorable',
        'should_trade': True,
        'confidence': 'Low',
        'reason': 'Neutral conditions, allow trading',
        'details': {},
    }


def should_trade_v2(df: pd.DataFrame, idx: int, filter_level: str = 'balanced') -> bool:
    """
    Determine if we should trade based on regime analysis

    Filter levels:
    - 'conservative': Avoid all uptrends, only trade Highly Favorable (targets <20% DD)
    - 'balanced': Avoid Strong/Moderate uptrends (targets <30% DD)
    - 'aggressive': Only avoid Strong uptrends (targets <40% DD)

    Args:
        df: DataFrame with calculated indicators
        idx: Current bar index
        filter_level: Risk tolerance level

    Returns:
        True if should take trade, False otherwise
    """
    regime = classify_regime_v2(df, idx)

    if filter_level == 'conservative':
        return regime['regime'] == 'Highly Favorable'

    elif filter_level == 'balanced':
        return regime['should_trade'] and regime['regime'] != 'Avoid'

    elif filter_level == 'aggressive':
        return regime['regime'] != 'Avoid'

    else:
        raise ValueError(f"Unknown filter_level: {filter_level}")


# Filter configurations
FILTER_CONFIGS_V2 = {
    'none': {
        'name': 'No Filter',
        'description': 'Trade all signals',
        'target_dd': 'N/A',
    },
    'aggressive': {
        'name': 'Aggressive Filter',
        'description': 'Only avoid Strong sustained uptrends (March 2025 pattern)',
        'target_dd': '<40%',
        'rationale': 'Filters catastrophic periods while keeping most trades',
    },
    'balanced': {
        'name': 'Balanced Filter',
        'description': 'Avoid Strong and Moderate uptrends',
        'target_dd': '<30%',
        'rationale': 'Good balance between safety and opportunity',
    },
    'conservative': {
        'name': 'Conservative Filter',
        'description': 'Only trade Highly Favorable downtrends',
        'target_dd': '<20%',
        'rationale': 'Maximum safety, fewer trades',
    },
}


if __name__ == '__main__':
    print("=" * 80)
    print("ENHANCED REGIME FILTER - VERSION 2")
    print("=" * 80)

    print("\nKey Improvements:")
    print("1. Multi-timeframe momentum analysis")
    print("2. Sustained uptrend detection (March 2025 pattern)")
    print("3. Recent bar strength analysis")
    print("4. Adjustable risk levels")

    print("\n" + "=" * 80)
    print("FILTER CONFIGURATIONS")
    print("=" * 80)

    for level, config in FILTER_CONFIGS_V2.items():
        print(f"\n{config['name']}:")
        print(f"  Description: {config['description']}")
        print(f"  Target DD: {config['target_dd']}")
        if 'rationale' in config:
            print(f"  Rationale: {config['rationale']}")