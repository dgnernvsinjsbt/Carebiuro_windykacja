"""
Deep analysis of FARTCOIN 5m data to find what actually works
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
data = pd.read_csv('fartcoin_5m_max.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])

print("=" * 80)
print("FARTCOIN 5M DATA ANALYSIS")
print("=" * 80)
print(f"\nTotal candles: {len(data)}")
print(f"Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
print(f"Days: {(data['timestamp'].max() - data['timestamp'].min()).days}")

# Price statistics
print("\n" + "=" * 80)
print("PRICE STATISTICS")
print("=" * 80)
print(f"Starting price: ${data['close'].iloc[0]:.4f}")
print(f"Ending price: ${data['close'].iloc[-1]:.4f}")
print(f"Overall return: {(data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100:.2f}%")
print(f"Highest: ${data['high'].max():.4f}")
print(f"Lowest: ${data['low'].min():.4f}")
print(f"Max intraday range: ${(data['high'] - data['low']).max():.4f}")

# Volatility analysis
data['return'] = data['close'].pct_change() * 100
print(f"\nAverage 5m return: {data['return'].mean():.4f}%")
print(f"Std dev of returns: {data['return'].std():.4f}%")
print(f"Max positive move: {data['return'].max():.2f}%")
print(f"Max negative move: {data['return'].min():.2f}%")

# Count big moves
big_up = (data['return'] > 2).sum()
big_down = (data['return'] < -2).sum()
print(f"\nBig moves (>2%): {big_up} up, {big_down} down")

# Calculate indicators
data['ema_20'] = data['close'].ewm(span=20).mean()
data['ema_50'] = data['close'].ewm(span=50).mean()

# RSI
delta = data['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
data['rsi'] = 100 - (100 / (1 + rs))

# Bollinger
data['bb_mid'] = data['close'].rolling(20).mean()
bb_std = data['close'].rolling(20).std()
data['bb_upper'] = data['bb_mid'] + 2 * bb_std
data['bb_lower'] = data['bb_mid'] - 2 * bb_std

# ATR
high_low = data['high'] - data['low']
high_close = (data['high'] - data['close'].shift()).abs()
low_close = (data['low'] - data['close'].shift()).abs()
ranges = pd.concat([high_low, high_close, low_close], axis=1)
tr = ranges.max(axis=1)
data['atr'] = tr.rolling(14).mean()

print("\n" + "=" * 80)
print("TREND ANALYSIS")
print("=" * 80)

# Uptrends vs downtrends
uptrend = (data['ema_20'] > data['ema_50']).sum()
downtrend = (data['ema_20'] < data['ema_50']).sum()
print(f"Uptrend periods (EMA20 > EMA50): {uptrend} ({uptrend/len(data)*100:.1f}%)")
print(f"Downtrend periods (EMA20 < EMA50): {downtrend} ({downtrend/len(data)*100:.1f}%)")

# Test simple strategies
print("\n" + "=" * 80)
print("SIMPLE STRATEGY TESTS (Buy & Hold vs Strategies)")
print("=" * 80)

# Buy & Hold
bh_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100
print(f"\nBuy & Hold Return: {bh_return:.2f}%")

# Test 1: Buy when RSI < 30, sell when RSI > 70
print("\n1. RSI Extremes (Buy <30, Sell >70):")
position = None
trades_rsi = []
for idx in range(100, len(data)):
    if position is None:
        if data['rsi'].iloc[idx] < 30 and data['rsi'].iloc[idx] > data['rsi'].iloc[idx-1]:
            position = data['close'].iloc[idx]
    else:
        if data['rsi'].iloc[idx] > 70 or data['close'].iloc[idx] < position * 0.95:
            pnl = (data['close'].iloc[idx] / position - 1) * 100
            trades_rsi.append(pnl)
            position = None

if len(trades_rsi) > 0:
    print(f"  Trades: {len(trades_rsi)}")
    print(f"  Avg return: {np.mean(trades_rsi):.2f}%")
    print(f"  Win rate: {sum(1 for t in trades_rsi if t > 0) / len(trades_rsi) * 100:.1f}%")
    print(f"  Total return: {sum(trades_rsi):.2f}%")
else:
    print("  No trades")

# Test 2: Buy lower BB bounce
print("\n2. Bollinger Lower Band Bounce:")
position = None
trades_bb = []
for idx in range(100, len(data)):
    if position is None:
        if (data['low'].iloc[idx] <= data['bb_lower'].iloc[idx] and
            data['close'].iloc[idx] > data['open'].iloc[idx]):
            position = data['close'].iloc[idx]
            stop = data['bb_lower'].iloc[idx] * 0.995
            target = data['bb_mid'].iloc[idx]
            entry_idx = idx
    else:
        if (data['low'].iloc[idx] <= stop or
            data['high'].iloc[idx] >= target or
            idx - entry_idx > 50):
            if data['low'].iloc[idx] <= stop:
                exit_price = stop
            elif data['high'].iloc[idx] >= target:
                exit_price = target
            else:
                exit_price = data['close'].iloc[idx]
            pnl = (exit_price / position - 1) * 100
            trades_bb.append(pnl)
            position = None

if len(trades_bb) > 0:
    print(f"  Trades: {len(trades_bb)}")
    print(f"  Avg return: {np.mean(trades_bb):.2f}%")
    print(f"  Win rate: {sum(1 for t in trades_bb if t > 0) / len(trades_bb) * 100:.1f}%")
    print(f"  Total return: {sum(trades_bb):.2f}%")
else:
    print("  No trades")

# Test 3: EMA pullback LONG
print("\n3. EMA Pullback Long:")
position = None
trades_ema = []
for idx in range(100, len(data)):
    if position is None:
        if (data['ema_20'].iloc[idx] > data['ema_50'].iloc[idx] and
            data['close'].iloc[idx] < data['ema_20'].iloc[idx] and
            data['close'].iloc[idx] > data['ema_50'].iloc[idx]):
            position = data['close'].iloc[idx]
            stop = data['ema_50'].iloc[idx] * 0.995
            target = data['close'].iloc[idx] * 1.015
            entry_idx = idx
    else:
        if (data['low'].iloc[idx] <= stop or
            data['high'].iloc[idx] >= target or
            idx - entry_idx > 50):
            if data['low'].iloc[idx] <= stop:
                exit_price = stop
            elif data['high'].iloc[idx] >= target:
                exit_price = target
            else:
                exit_price = data['close'].iloc[idx]
            pnl = (exit_price / position - 1) * 100
            trades_ema.append(pnl)
            position = None

if len(trades_ema) > 0:
    print(f"  Trades: {len(trades_ema)}")
    print(f"  Avg return: {np.mean(trades_ema):.2f}%")
    print(f"  Win rate: {sum(1 for t in trades_ema if t > 0) / len(trades_ema) * 100:.1f}%")
    print(f"  Total return: {sum(trades_ema):.2f}%")
else:
    print("  No trades")

# Test 4: Simple momentum - buy on strong up moves
print("\n4. Momentum Following (Buy 1%+ moves):")
position = None
trades_mom = []
for idx in range(100, len(data)):
    if position is None:
        if data['return'].iloc[idx] > 1.0 and data['rsi'].iloc[idx] < 75:
            position = data['close'].iloc[idx]
            stop = data['close'].iloc[idx] * 0.993
            target = data['close'].iloc[idx] * 1.015
            entry_idx = idx
    else:
        if (data['low'].iloc[idx] <= stop or
            data['high'].iloc[idx] >= target or
            idx - entry_idx > 20):
            if data['low'].iloc[idx] <= stop:
                exit_price = stop
            elif data['high'].iloc[idx] >= target:
                exit_price = target
            else:
                exit_price = data['close'].iloc[idx]
            pnl = (exit_price / position - 1) * 100
            trades_mom.append(pnl)
            position = None

if len(trades_mom) > 0:
    print(f"  Trades: {len(trades_mom)}")
    print(f"  Avg return: {np.mean(trades_mom):.2f}%")
    print(f"  Win rate: {sum(1 for t in trades_mom if t > 0) / len(trades_mom) * 100:.1f}%")
    print(f"  Total return: {sum(trades_mom):.2f}%")
else:
    print("  No trades")

# Test 5: SHORT mean reversion - sell into strength
print("\n5. Mean Reversion SHORT (Sell BB upper):")
position = None
trades_short = []
for idx in range(100, len(data)):
    if position is None:
        if (data['high'].iloc[idx] >= data['bb_upper'].iloc[idx] and
            data['close'].iloc[idx] < data['open'].iloc[idx] and
            data['rsi'].iloc[idx] > 65):
            position = data['close'].iloc[idx]
            stop = data['bb_upper'].iloc[idx] * 1.005
            target = data['bb_mid'].iloc[idx]
            entry_idx = idx
    else:
        # SHORT: profit when price goes down
        if (data['high'].iloc[idx] >= stop or
            data['low'].iloc[idx] <= target or
            idx - entry_idx > 50):
            if data['high'].iloc[idx] >= stop:
                exit_price = stop
            elif data['low'].iloc[idx] <= target:
                exit_price = target
            else:
                exit_price = data['close'].iloc[idx]
            pnl = (position - exit_price) / position * 100
            trades_short.append(pnl)
            position = None

if len(trades_short) > 0:
    print(f"  Trades: {len(trades_short)}")
    print(f"  Avg return: {np.mean(trades_short):.2f}%")
    print(f"  Win rate: {sum(1 for t in trades_short if t > 0) / len(trades_short) * 100:.1f}%")
    print(f"  Total return: {sum(trades_short):.2f}%")
else:
    print("  No trades")

# Monthly analysis
print("\n" + "=" * 80)
print("MONTHLY PERFORMANCE ANALYSIS")
print("=" * 80)

data['month'] = data['timestamp'].dt.to_period('M')
monthly = data.groupby('month').agg({
    'close': ['first', 'last', 'min', 'max'],
    'return': ['mean', 'std', 'min', 'max']
})

print("\nMonthly Returns:")
for month in data['month'].unique():
    month_data = data[data['month'] == month]
    ret = (month_data['close'].iloc[-1] / month_data['close'].iloc[0] - 1) * 100
    vol = month_data['return'].std()
    print(f"{month}: {ret:+.2f}% (vol: {vol:.2f}%)")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print(f"""
Best performing simple strategy found:
""")

all_results = [
    ("RSI Extremes", trades_rsi),
    ("BB Bounce", trades_bb),
    ("EMA Pullback", trades_ema),
    ("Momentum", trades_mom),
    ("SHORT Mean Reversion", trades_short)
]

best_total = -999999
best_name = None
for name, trades in all_results:
    if len(trades) > 0:
        total = sum(trades)
        if total > best_total:
            best_total = total
            best_name = name
            best_trades = trades

if best_name:
    print(f"\n{best_name}:")
    print(f"  Total Return: {best_total:.2f}% (vs Buy&Hold: {bh_return:.2f}%)")
    print(f"  Number of Trades: {len(best_trades)}")
    print(f"  Average per trade: {np.mean(best_trades):.2f}%")
    print(f"  Win Rate: {sum(1 for t in best_trades if t > 0) / len(best_trades) * 100:.1f}%")
