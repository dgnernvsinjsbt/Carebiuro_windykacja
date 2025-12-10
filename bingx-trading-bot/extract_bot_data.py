import re
import pandas as pd
from datetime import datetime, timedelta

# Parse log file and extract candle data
data = []

with open('bot.log', 'r') as f:
    current_symbol = None
    current_timestamp = None
    current_data = {}
    
    for line in f:
        # Extract symbol and timestamp
        symbol_match = re.search(r'(FARTCOIN-USDT|TRUMPSOL-USDT|DOGE-USDT) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if symbol_match:
            if current_symbol and current_data:
                data.append({
                    'symbol': current_symbol,
                    'timestamp': current_timestamp,
                    **current_data
                })
            current_symbol = symbol_match.group(1)
            current_timestamp = symbol_match.group(2)
            current_data = {}
            continue
        
        # Extract OHLCV data
        if current_symbol:
            open_match = re.search(r'Open:\s+\$([0-9.]+)', line)
            if open_match:
                current_data['open'] = float(open_match.group(1))
            
            high_match = re.search(r'High:\s+\$([0-9.]+)', line)
            if high_match:
                current_data['high'] = float(high_match.group(1))
            
            low_match = re.search(r'Low:\s+\$([0-9.]+)', line)
            if low_match:
                current_data['low'] = float(low_match.group(1))
            
            close_match = re.search(r'Close:\s+\$([0-9.]+)', line)
            if close_match:
                current_data['close'] = float(close_match.group(1))
            
            volume_match = re.search(r'Volume:\s+([0-9,]+)', line)
            if volume_match:
                current_data['volume'] = float(volume_match.group(1).replace(',', ''))
            
            rsi_match = re.search(r'RSI\(14\):\s+([0-9.]+)', line)
            if rsi_match:
                current_data['rsi'] = float(rsi_match.group(1))
            
            sma20_match = re.search(r'SMA\(20\):\s+\$([0-9.]+)', line)
            if sma20_match:
                current_data['sma_20'] = float(sma20_match.group(1))
            
            sma50_match = re.search(r'SMA\(50\):\s+\$([0-9.]+)', line)
            if sma50_match:
                current_data['sma_50'] = float(sma50_match.group(1))
            
            atr_match = re.search(r'ATR\(14\):\s+\$([0-9.]+)', line)
            if atr_match:
                current_data['atr'] = float(atr_match.group(1))
            
            vol_ratio_match = re.search(r'Vol Ratio:\s+([0-9.]+)x', line)
            if vol_ratio_match:
                current_data['vol_ratio'] = float(vol_ratio_match.group(1))
            
            body_match = re.search(r'Body:\s+([0-9.]+)%\s+\((BULLISH|BEARISH|DOJI)\)', line)
            if body_match:
                current_data['body_pct'] = float(body_match.group(1))
                current_data['direction'] = body_match.group(2)

# Add last entry
if current_symbol and current_data:
    data.append({
        'symbol': current_symbol,
        'timestamp': current_timestamp,
        **current_data
    })

# Create DataFrame
df = pd.DataFrame(data)

if len(df) > 0:
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter last 8 hours
    cutoff = datetime.now() - timedelta(hours=8)
    df = df[df['timestamp'] >= cutoff]
    
    # Sort by timestamp
    df = df.sort_values(['symbol', 'timestamp'])
    
    # Save to CSV
    df.to_csv('bot_data_last_8h.csv', index=False)
    
    print(f"✓ Saved {len(df)} rows to bot_data_last_8h.csv")
    print(f"  Symbols: {df['symbol'].unique().tolist()}")
    print(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Rows per symbol:")
    for symbol in df['symbol'].unique():
        count = len(df[df['symbol'] == symbol])
        print(f"    {symbol}: {count}")
else:
    print("No data found in logs")
