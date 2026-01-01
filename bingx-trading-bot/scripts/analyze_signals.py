import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('bot_data_last_8h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 80)
print("SIGNAL ANALYSIS - Last 8 Hours of Bot Data")
print("=" * 80)

# ==============================================================================
# STRATEGY 1: FARTCOIN ATR LIMIT
# ==============================================================================
print("\n1. FARTCOIN ATR Limit Strategy Analysis")
print("-" * 80)

fart = df[df['symbol'] == 'FARTCOIN-USDT'].copy()
fart = fart.sort_values('timestamp')

# Calculate ATR expansion (need rolling average)
fart['atr_ma_20'] = fart['atr'].rolling(20).mean()
fart['atr_expansion'] = fart['atr'] / fart['atr_ma_20']

# Calculate EMA distance (approximation - we'd need EMA(20) which we don't have logged)
# Using SMA(20) as proxy
fart['ema_distance_pct'] = abs(fart['close'] - fart['sma_20']) / fart['close'] * 100

# Check conditions
fart['atr_expanded'] = fart['atr_expansion'] > 1.5
fart['within_ema'] = fart['ema_distance_pct'] <= 3.0
fart['is_bullish'] = fart['direction'] == 'BULLISH'
fart['is_bearish'] = fart['direction'] == 'BEARISH'

# Count signals
fart_signals = fart[
    (fart['atr_expanded']) & 
    (fart['within_ema']) & 
    ((fart['is_bullish']) | (fart['is_bearish']))
]

print(f"Total candles: {len(fart)}")
print(f"ATR expanded (>1.5x): {fart['atr_expanded'].sum()}")
print(f"Within 3% of EMA(20): {fart['within_ema'].sum()}")
print(f"Directional candles: {(fart['is_bullish'] | fart['is_bearish']).sum()}")
print(f"ALL CONDITIONS MET: {len(fart_signals)}")

if len(fart_signals) > 0:
    print(f"\nSignals would have been generated at:")
    for _, row in fart_signals.head(10).iterrows():
        print(f"  {row['timestamp']}: {row['direction']}, ATR exp={row['atr_expansion']:.2f}x, EMA dist={row['ema_distance_pct']:.2f}%")

# ==============================================================================
# STRATEGY 2: TRUMPSOL CONTRARIAN
# ==============================================================================
print("\n2. TRUMPSOL Contrarian Strategy Analysis")
print("-" * 80)

trump = df[df['symbol'] == 'TRUMPSOL-USDT'].copy()
trump = trump.sort_values('timestamp')

# We need 5-minute returns but only have 1-min data logged
# Approximate by looking at 5-bar rolling returns
trump['ret_5m_approx'] = (trump['close'].shift(-5) - trump['close']) / trump['close'] * 100

# Check conditions (approximate - we don't have exact vol_ratio and atr_ratio vs 30-bar MA)
trump['extreme_move'] = abs(trump['ret_5m_approx']) >= 1.0
trump['high_volume'] = trump['vol_ratio'] >= 1.0  # Approximation
# Note: We don't have ATR ratio vs 30-bar MA in logs, can't check atr_ratio_min

print(f"Total candles: {len(trump)}")
print(f"Extreme 5m moves (≥1%): {trump['extreme_move'].sum()}")
print(f"High volume (ratio ≥1x): {trump['high_volume'].sum()}")
print(f"Note: Cannot verify ATR ratio condition (not logged)")

trump_candidates = trump[
    (trump['extreme_move']) & 
    (trump['high_volume'])
]

print(f"Potential signals (vol + move): {len(trump_candidates)}")

if len(trump_candidates) > 0:
    print(f"\nPotential signals at:")
    for _, row in trump_candidates.head(10).iterrows():
        direction = 'SHORT' if row['ret_5m_approx'] > 0 else 'LONG'
        print(f"  {row['timestamp']}: {direction}, 5m ret={row['ret_5m_approx']:.2f}%, vol={row['vol_ratio']:.2f}x")

# ==============================================================================
# STRATEGY 3: PEPE CONTRARIAN SHORT
# ==============================================================================
print("\n3. PEPE Contrarian SHORT Strategy Analysis")
print("-" * 80)

# PEPE data (logged as 1000PEPE-USDT but we need to check the logs)
# Let's check what symbols we actually have
print(f"Available symbols: {df['symbol'].unique()}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Note: Analysis is limited by available logged data.")
print("- FARTCOIN: Can partially verify (missing EMA calculation)")
print("- TRUMPSOL: Cannot fully verify (missing 5m timeframe data & ATR ratio)")
print("- PEPE: No data logged (1000PEPE not monitored in this period)")
