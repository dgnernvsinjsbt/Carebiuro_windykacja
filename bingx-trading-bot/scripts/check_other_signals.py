import pandas as pd
import re
from datetime import datetime, timedelta

# Parse data from logs
data = []

with open('bot.log', 'r') as f:
    current_symbol = None
    current_timestamp = None
    current_data = {}

    for line in f:
        # Extract symbol and timestamp
        symbol_match = re.search(r'(FARTCOIN-USDT|TRUMPSOL-USDT|1000PEPE-USDT|DOGE-USDT) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if symbol_match:
            if current_symbol and current_data and 'close' in current_data:
                data.append({
                    'symbol': current_symbol,
                    'timestamp': current_timestamp,
                    **current_data
                })
            current_symbol = symbol_match.group(1)
            current_timestamp = symbol_match.group(2)
            current_data = {}
            continue

        if current_symbol:
            for pattern, key in [
                (r'Open:\s+\$([0-9.]+)', 'open'),
                (r'Close:\s+\$([0-9.]+)', 'close'),
                (r'Volume:\s+([0-9,]+)', 'volume'),
                (r'RSI\(14\):\s+([0-9.]+)', 'rsi'),
                (r'Vol Ratio:\s+([0-9.]+)x', 'vol_ratio'),
                (r'ATR\(14\):\s+\$([0-9.]+)', 'atr'),
            ]:
                match = re.search(pattern, line)
                if match:
                    if key == 'volume':
                        current_data[key] = float(match.group(1).replace(',', ''))
                    else:
                        current_data[key] = float(match.group(1))

# Add last entry
if current_symbol and current_data and 'close' in current_data:
    data.append({
        'symbol': current_symbol,
        'timestamp': current_timestamp,
        **current_data
    })

df = pd.DataFrame(data)
if len(df) == 0:
    print("No data found")
    exit()

df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 80)
print("TRUMPSOL & PEPE SIGNAL ANALYSIS")
print("=" * 80)

# ==============================================================================
# TRUMPSOL CONTRARIAN
# ==============================================================================
print("\n1. TRUMPSOL CONTRARIAN - Looking for ≥1% 5-min moves with volume")
print("-" * 80)

trump = df[df['symbol'] == 'TRUMPSOL-USDT'].sort_values('timestamp').copy()

if len(trump) > 0:
    # Calculate 5-minute returns (5 bars = 5 minutes)
    trump['ret_5m'] = ((trump['close'] - trump['close'].shift(5)) / trump['close'].shift(5) * 100)

    # Calculate ATR rolling average (30-bar MA)
    trump['atr_ma_30'] = trump['atr'].rolling(30).mean()
    trump['atr_ratio'] = trump['atr'] / trump['atr_ma_30']

    print(f"Period: {trump['timestamp'].min()} to {trump['timestamp'].max()}")
    print(f"Total candles: {len(trump)}")
    print(f"\nConditions check:")
    print(f"  Extreme moves (|5m ret| ≥ 1.0%): {(abs(trump['ret_5m']) >= 1.0).sum()}")
    print(f"  High volume (vol_ratio ≥ 1.0x): {(trump['vol_ratio'] >= 1.0).sum()}")
    print(f"  High ATR (atr_ratio ≥ 1.1x): {(trump['atr_ratio'] >= 1.1).sum()}")

    # Full signal conditions
    trump_signals = trump[
        (abs(trump['ret_5m']) >= 1.0) &
        (trump['vol_ratio'] >= 1.0) &
        (trump['atr_ratio'] >= 1.1)
    ]

    print(f"\n✓ ALL CONDITIONS MET: {len(trump_signals)} signals")

    if len(trump_signals) > 0:
        print("\nSignals that should have triggered:")
        for _, row in trump_signals.iterrows():
            direction = 'LONG' if row['ret_5m'] < 0 else 'SHORT'  # Contrarian!
            print(f"  {row['timestamp']}: {direction} (5m ret={row['ret_5m']:.2f}%, vol={row['vol_ratio']:.2f}x, atr={row['atr_ratio']:.2f}x)")
else:
    print("No TRUMPSOL data found")

# ==============================================================================
# PEPE CONTRARIAN SHORT
# ==============================================================================
print("\n2. PEPE CONTRARIAN SHORT - Looking for ≥1.5% pumps with volume/ATR")
print("-" * 80)

pepe = df[df['symbol'] == '1000PEPE-USDT'].sort_values('timestamp').copy()

if len(pepe) > 0:
    # Calculate 5-minute returns
    pepe['ret_5m'] = ((pepe['close'] - pepe['close'].shift(5)) / pepe['close'].shift(5) * 100)

    # Calculate ATR rolling average (30-bar MA)
    pepe['atr_ma_30'] = pepe['atr'].rolling(30).mean()
    pepe['atr_ratio'] = pepe['atr'] / pepe['atr_ma_30']

    print(f"Period: {pepe['timestamp'].min()} to {pepe['timestamp'].max()}")
    print(f"Total candles: {len(pepe)}")
    print(f"\nConditions check:")
    print(f"  Pumps (5m ret ≥ 1.5%): {(pepe['ret_5m'] >= 1.5).sum()}")
    print(f"  High volume (vol_ratio ≥ 2.0x): {(pepe['vol_ratio'] >= 2.0).sum()}")
    print(f"  High ATR (atr_ratio ≥ 1.3x): {(pepe['atr_ratio'] >= 1.3).sum()}")

    # Full signal conditions (SHORT only - fade pumps)
    pepe_signals = pepe[
        (pepe['ret_5m'] >= 1.5) &
        (pepe['vol_ratio'] >= 2.0) &
        (pepe['atr_ratio'] >= 1.3)
    ]

    print(f"\n✓ ALL CONDITIONS MET: {len(pepe_signals)} signals")

    if len(pepe_signals) > 0:
        print("\nSHORT signals that should have triggered:")
        for _, row in pepe_signals.iterrows():
            print(f"  {row['timestamp']}: SHORT @ ${row['close']:.6f} (pump={row['ret_5m']:.2f}%, vol={row['vol_ratio']:.2f}x, atr={row['atr_ratio']:.2f}x)")
else:
    print("No PEPE data found")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Analysis based on all logged candles with proper 5m calculations")
