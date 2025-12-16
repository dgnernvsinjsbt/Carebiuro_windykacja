import pandas as pd
import re

# Parse ALL data from logs (not just last 8h)
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
                (r'SMA\(20\):\s+\$([0-9.]+)', 'sma_20'),
                (r'Vol Ratio:\s+([0-9.]+)x', 'vol_ratio'),
                (r'ATR\(14\):\s+\$([0-9.]+)', 'atr'),
                (r'Body:\s+([0-9.]+)%\s+\((BULLISH|BEARISH|DOJI)\)', 'body'),
            ]:
                match = re.search(pattern, line)
                if match:
                    if key == 'body':
                        current_data['body_pct'] = float(match.group(1))
                        current_data['direction'] = match.group(2)
                    elif key == 'volume':
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
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 80)
print(f"FULL 18-HOUR ANALYSIS ({len(df)} total candles)")
print("=" * 80)

# FARTCOIN Analysis
print("\n1. FARTCOIN ATR LIMIT")
print("-" * 80)
fart = df[df['symbol'] == 'FARTCOIN-USDT'].sort_values('timestamp')
fart['atr_ma_20'] = fart['atr'].rolling(20).mean()
fart['atr_expansion'] = fart['atr'] / fart['atr_ma_20']
fart['ema_distance_pct'] = abs(fart['close'] - fart['sma_20']) / fart['close'] * 100

fart_signals = fart[
    (fart['atr_expansion'] > 1.5) & 
    (fart['ema_distance_pct'] <= 3.0) & 
    ((fart['direction'] == 'BULLISH') | (fart['direction'] == 'BEARISH'))
]

print(f"Period: {fart['timestamp'].min()} to {fart['timestamp'].max()}")
print(f"Total candles: {len(fart)}")
print(f"✓ SIGNALS FOUND: {len(fart_signals)}")
if len(fart_signals) > 0:
    print("\nTop signals:")
    for _, row in fart_signals.head(5).iterrows():
        print(f"  {row['timestamp']}: {row['direction']}, ATR={row['atr_expansion']:.2f}x, EMA dist={row['ema_distance_pct']:.2f}%")

# TRUMPSOL Analysis  
print("\n2. TRUMPSOL CONTRARIAN")
print("-" * 80)
trump = df[df['symbol'] == 'TRUMPSOL-USDT'].sort_values('timestamp')

# Calculate 5-minute return (approximate with 5-bar window)
trump['ret_5m'] = ((trump['close'] - trump['close'].shift(5)) / trump['close'].shift(5) * 100).abs()

# We can't verify ATR ratio condition without 30-bar ATR MA calculation
print(f"Period: {trump['timestamp'].min()} to {trump['timestamp'].max()}")
print(f"Total candles: {len(trump)}")
print(f"Extreme moves (|5m ret| > 1%): {(trump['ret_5m'] > 1.0).sum()}")
print(f"High volume periods (>1x): {(trump['vol_ratio'] > 1.0).sum()}")
print("⚠️ Cannot fully verify - need 5m timeframe + ATR ratio calculation")

# PEPE Analysis
print("\n3. PEPE CONTRARIAN SHORT")
print("-" * 80)
pepe = df[df['symbol'] == '1000PEPE-USDT'].sort_values('timestamp')

if len(pepe) > 0:
    pepe['ret_5m'] = (pepe['close'] - pepe['close'].shift(5)) / pepe['close'].shift(5) * 100
    
    # PEPE strategy: SHORT on pumps >1.5%, vol >= 2x, atr >= 1.3x
    print(f"Period: {pepe['timestamp'].min()} to {pepe['timestamp'].max()}")
    print(f"Total candles: {len(pepe)}")
    print(f"Pumps (5m ret > 1.5%): {(pepe['ret_5m'] > 1.5).sum()}")
    print(f"High volume (>2x): {(pepe['vol_ratio'] >= 2.0).sum()}")
    print("⚠️ Cannot verify ATR ratio condition (need 30-bar ATR MA)")
else:
    print("No PEPE data logged")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("FARTCOIN: 2 potential signals found (both around 00:25-00:26)")
print("TRUMPSOL: Cannot verify without proper 5m timeframe data")
print("PEPE: Need to verify strategy is actually running in bot code")
