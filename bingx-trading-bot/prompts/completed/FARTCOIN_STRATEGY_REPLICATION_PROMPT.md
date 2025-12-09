# FARTCOIN ATR Expansion Strategy - Replication Guide

## Overview
Test the FARTCOIN ATR Expansion strategy on your cryptocurrency data. This strategy achieved **8.44x Return/DD ratio** (+101.11% return, -11.98% max drawdown) over 32 days on FARTCOIN/USDT BingX data.

---

## Strategy Mechanics

### Core Concept
**Volatility Breakout + Limit Order Filter**

The strategy catches explosive pump/dump moves at their beginning by:
1. Detecting ATR expansion (volatility breakout)
2. Filtering overextended entries (EMA distance)
3. Using limit orders 1% away to filter fake breakouts

### Entry Conditions (ALL must be true)

**1. ATR Expansion (Volatility Breakout)**
```python
# Calculate current ATR(14)
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])),
    axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()

# Calculate 20-bar rolling average of ATR
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()

# ATR Expansion Filter
atr_expansion = df['atr_14'].iloc[-1] > 1.5 * df['atr_avg_20'].iloc[-1]
```

**2. EMA Distance Filter (Prevent Late Entries)**
```python
# Calculate EMA(20)
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

# Distance from EMA
ema_distance_pct = abs(df['close'].iloc[-1] - df['ema_20'].iloc[-1]) / df['ema_20'].iloc[-1] * 100

# Must be within 3% of EMA
ema_filter = ema_distance_pct <= 3.0
```

**3. Directional Candle**
```python
# LONG: Bullish candle
long_candle = df['close'].iloc[-1] > df['open'].iloc[-1]

# SHORT: Bearish candle
short_candle = df['close'].iloc[-1] < df['open'].iloc[-1]
```

**4. Limit Order Placement (CRITICAL - 79% of signals filtered here)**
```python
# Signal price (current close)
signal_price = df['close'].iloc[-1]

# LONG: Place limit 1% ABOVE signal price
if long_candle and atr_expansion and ema_filter:
    limit_price_long = signal_price * 1.01  # +1% offset
    # Wait max 3 bars for fill
    # If price goes above limit_price_long within 3 bars → FILL
    # Otherwise → NO TRADE

# SHORT: Place limit 1% BELOW signal price
if short_candle and atr_expansion and ema_filter:
    limit_price_short = signal_price * 0.99  # -1% offset
    # Wait max 3 bars for fill
    # If price goes below limit_price_short within 3 bars → FILL
    # Otherwise → NO TRADE
```

### Exit Rules

**1. Stop Loss: 2.0x ATR(14) from fill price**
```python
atr_at_entry = df['atr_14'].iloc[entry_index]

if direction == 'LONG':
    stop_loss = fill_price - (2.0 * atr_at_entry)
elif direction == 'SHORT':
    stop_loss = fill_price + (2.0 * atr_at_entry)
```

**2. Take Profit: 8.0x ATR(14) from fill price (R:R = 4:1)**
```python
if direction == 'LONG':
    take_profit = fill_price + (8.0 * atr_at_entry)
elif direction == 'SHORT':
    take_profit = fill_price - (8.0 * atr_at_entry)
```

**3. Time Exit: 200 bars (3.3 hours)**
```python
if bars_held >= 200:
    exit_reason = 'TIME'
    exit_price = current_close
```

### Fee Structure
```python
ENTRY_FEE = 0.05%  # BingX taker fee (market order assumed if filled)
EXIT_FEE = 0.05%   # BingX taker fee
ROUND_TRIP = 0.10%
```

---

## Implementation Instructions

### Step 1: Prepare Your Data

**Required format:** CSV with 1-minute OHLCV candles

```python
import pandas as pd

# Load your data
df = pd.read_csv('your_coin_1m_data.csv')

# Required columns:
# - timestamp (datetime)
# - open (float)
# - high (float)
# - low (float)
# - close (float)
# - volume (float)

# Ensure timestamp is datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
```

### Step 2: Calculate Indicators

```python
import numpy as np

# True Range
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(
        row['high'] - row['low'],
        abs(row['high'] - row['close']),
        abs(row['low'] - row['close'])
    ), axis=1
)

# ATR(14)
df['atr_14'] = df['tr'].rolling(window=14).mean()

# 20-bar ATR average
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()

# EMA(20)
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

# Drop NaN rows
df = df.dropna().reset_index(drop=True)
```

### Step 3: Generate Signals

```python
signals = []

for i in range(20, len(df)):  # Start after lookback periods
    row = df.iloc[i]

    # 1. ATR Expansion Filter
    atr_expansion = row['atr_14'] > 1.5 * row['atr_avg_20']
    if not atr_expansion:
        continue

    # 2. EMA Distance Filter
    ema_distance_pct = abs(row['close'] - row['ema_20']) / row['ema_20'] * 100
    if ema_distance_pct > 3.0:
        continue

    # 3. Directional Candle
    is_bullish = row['close'] > row['open']
    is_bearish = row['close'] < row['open']

    if is_bullish:
        signals.append({
            'index': i,
            'timestamp': row['timestamp'],
            'direction': 'LONG',
            'signal_price': row['close'],
            'limit_price': row['close'] * 1.01,  # +1% for LONG
            'atr': row['atr_14']
        })
    elif is_bearish:
        signals.append({
            'index': i,
            'timestamp': row['timestamp'],
            'direction': 'SHORT',
            'signal_price': row['close'],
            'limit_price': row['close'] * 0.99,  # -1% for SHORT
            'atr': row['atr_14']
        })

print(f"Generated {len(signals)} signals")
```

### Step 4: Simulate Limit Order Fills

```python
filled_trades = []

for signal in signals:
    entry_index = signal['index']
    limit_price = signal['limit_price']
    direction = signal['direction']

    # Look ahead max 3 bars for fill
    filled = False
    fill_price = None
    fill_index = None

    for j in range(1, 4):  # Check next 3 bars
        if entry_index + j >= len(df):
            break

        future_bar = df.iloc[entry_index + j]

        if direction == 'LONG':
            # LONG fill: price must go ABOVE limit
            if future_bar['high'] >= limit_price:
                fill_price = limit_price
                fill_index = entry_index + j
                filled = True
                break

        elif direction == 'SHORT':
            # SHORT fill: price must go BELOW limit
            if future_bar['low'] <= limit_price:
                fill_price = limit_price
                fill_index = entry_index + j
                filled = True
                break

    if filled:
        filled_trades.append({
            'signal_index': entry_index,
            'fill_index': fill_index,
            'direction': direction,
            'fill_price': fill_price,
            'atr': signal['atr'],
            'timestamp': df.iloc[fill_index]['timestamp']
        })

print(f"Filled: {len(filled_trades)} / {len(signals)} ({len(filled_trades)/len(signals)*100:.1f}%)")
```

### Step 5: Backtest Trades

```python
equity = 10000  # Starting capital
trades_log = []

for trade in filled_trades:
    entry_index = trade['fill_index']
    entry_price = trade['fill_price']
    direction = trade['direction']
    atr = trade['atr']

    # Calculate SL/TP
    if direction == 'LONG':
        stop_loss = entry_price - (2.0 * atr)
        take_profit = entry_price + (8.0 * atr)
    else:  # SHORT
        stop_loss = entry_price + (2.0 * atr)
        take_profit = entry_price - (8.0 * atr)

    # Simulate trade
    exit_price = None
    exit_reason = None
    bars_held = 0

    for j in range(1, 201):  # Max 200 bars
        if entry_index + j >= len(df):
            break

        bar = df.iloc[entry_index + j]
        bars_held = j

        # Check SL/TP
        if direction == 'LONG':
            if bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                break
            elif bar['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                break
        else:  # SHORT
            if bar['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                break
            elif bar['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                break

    # Time exit if neither SL/TP hit
    if exit_price is None:
        exit_price = df.iloc[entry_index + bars_held]['close']
        exit_reason = 'TIME'

    # Calculate P&L with fees
    if direction == 'LONG':
        pnl_pct = (exit_price - entry_price) / entry_price
    else:  # SHORT
        pnl_pct = (entry_price - exit_price) / entry_price

    # Subtract fees (0.1% round-trip)
    pnl_pct -= 0.001

    # Update equity
    equity *= (1 + pnl_pct)

    trades_log.append({
        'timestamp': trade['timestamp'],
        'direction': direction,
        'entry': entry_price,
        'exit': exit_price,
        'exit_reason': exit_reason,
        'pnl_pct': pnl_pct * 100,
        'bars_held': bars_held,
        'equity': equity
    })

# Convert to DataFrame
trades_df = pd.DataFrame(trades_log)
```

### Step 6: Calculate Performance Metrics

```python
# Total Return
total_return = (equity - 10000) / 10000 * 100

# Max Drawdown
equity_curve = trades_df['equity'].values
running_max = np.maximum.accumulate(equity_curve)
drawdown = (equity_curve - running_max) / running_max * 100
max_drawdown = drawdown.min()

# Return/DD Ratio
return_dd_ratio = total_return / abs(max_drawdown)

# Win Rate
winners = trades_df[trades_df['pnl_pct'] > 0]
win_rate = len(winners) / len(trades_df) * 100

# Average Win/Loss
avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
losers = trades_df[trades_df['pnl_pct'] <= 0]
avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

print("=" * 60)
print("PERFORMANCE METRICS")
print("=" * 60)
print(f"Total Return:     {total_return:+.2f}%")
print(f"Max Drawdown:     {max_drawdown:.2f}%")
print(f"Return/DD Ratio:  {return_dd_ratio:.2f}x")
print(f"Trades:           {len(trades_df)}")
print(f"Win Rate:         {win_rate:.1f}%")
print(f"Avg Win:          {avg_win:+.2f}%")
print(f"Avg Loss:         {avg_loss:.2f}%")
print("=" * 60)

# Exit Breakdown
exit_counts = trades_df['exit_reason'].value_counts()
print("\nExit Breakdown:")
for reason, count in exit_counts.items():
    pct = count / len(trades_df) * 100
    print(f"  {reason}: {count} ({pct:.1f}%)")
```

---

## Expected Results (FARTCOIN baseline)

For reference, here are the metrics achieved on FARTCOIN/USDT (32 days):

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **8.44x** |
| Total Return | +101.11% |
| Max Drawdown | -11.98% |
| Win Rate | 42.6% |
| Trades | 94 (from 444 signals = 21% fill rate) |
| Avg Win | +4.97% |
| Avg Loss | -2.23% |
| Exits | 40% TP, 47% SL, 13% TIME |

---

## Task for You

1. **Load your coin's 1-minute data** (minimum 30 days recommended)
2. **Implement the strategy exactly as described above**
3. **Run the backtest** and report:
   - Total Return
   - Max Drawdown
   - Return/DD Ratio
   - Win Rate
   - Number of trades
   - Fill rate (filled trades / total signals)
4. **Compare to FARTCOIN results**
5. **Optional: Try variations:**
   - Different limit offsets (0.5%, 1.5%, 2.0%)
   - Different TP multipliers (6x, 10x, 12x ATR)
   - Different ATR expansion thresholds (1.3x, 1.7x, 2.0x)

---

## Key Success Factors

**✅ What makes this strategy work:**
1. **ATR expansion** catches beginning of explosive moves (not late entries)
2. **Limit orders 1% away** filter 79% of fake breakouts (only real moves fill)
3. **EMA distance** prevents overextended entries (must be near EMA)
4. **Wide TP (8x ATR)** captures full pump/dump moves (avg winner: 4.97%)
5. **Tight SL (2x ATR)** limits downside (avg loser: -2.23%)

**⚠️ Why it might fail on your coin:**
- Low volatility (ATR expansion won't occur often)
- Mean-reverting price action (breakouts fade immediately)
- Different fee structure (>0.1% will hurt returns)
- Very short dataset (<30 days may not be representative)

---

## Questions to Answer

1. **Is the strategy profitable on your coin?** (Return > 0%)
2. **Is the risk-adjusted return good?** (Return/DD > 3.0x)
3. **Is the fill rate reasonable?** (15-30% is ideal, <10% too selective, >50% too loose)
4. **What's the exit distribution?** (Healthy: 30-50% TP, <60% SL)
5. **How does it compare to FARTCOIN?** (Better/worse/similar?)

---

## Full Code Template

Save this as `test_fartcoin_strategy.py` and run it:

```python
import pandas as pd
import numpy as np

# 1. LOAD DATA
df = pd.read_csv('your_coin_1m_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# 2. CALCULATE INDICATORS
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df = df.dropna().reset_index(drop=True)

# 3. GENERATE SIGNALS
signals = []
for i in range(20, len(df)):
    row = df.iloc[i]
    if row['atr_14'] <= 1.5 * row['atr_avg_20']:
        continue
    ema_dist = abs(row['close'] - row['ema_20']) / row['ema_20'] * 100
    if ema_dist > 3.0:
        continue

    if row['close'] > row['open']:  # LONG
        signals.append({
            'index': i, 'direction': 'LONG',
            'limit_price': row['close'] * 1.01,
            'atr': row['atr_14']
        })
    elif row['close'] < row['open']:  # SHORT
        signals.append({
            'index': i, 'direction': 'SHORT',
            'limit_price': row['close'] * 0.99,
            'atr': row['atr_14']
        })

# 4. SIMULATE FILLS
filled = []
for s in signals:
    for j in range(1, 4):
        if s['index'] + j >= len(df):
            break
        bar = df.iloc[s['index'] + j]
        if s['direction'] == 'LONG' and bar['high'] >= s['limit_price']:
            filled.append({**s, 'fill_index': s['index'] + j, 'fill_price': s['limit_price']})
            break
        elif s['direction'] == 'SHORT' and bar['low'] <= s['limit_price']:
            filled.append({**s, 'fill_index': s['index'] + j, 'fill_price': s['limit_price']})
            break

# 5. BACKTEST
equity = 10000
trades = []
for t in filled:
    entry_idx = t['fill_index']
    entry_price = t['fill_price']
    atr = t['atr']
    direction = t['direction']

    sl = entry_price - 2*atr if direction == 'LONG' else entry_price + 2*atr
    tp = entry_price + 8*atr if direction == 'LONG' else entry_price - 8*atr

    exit_price, exit_reason = None, None
    for j in range(1, 201):
        if entry_idx + j >= len(df):
            break
        bar = df.iloc[entry_idx + j]
        if direction == 'LONG':
            if bar['low'] <= sl:
                exit_price, exit_reason = sl, 'SL'
                break
            elif bar['high'] >= tp:
                exit_price, exit_reason = tp, 'TP'
                break
        else:
            if bar['high'] >= sl:
                exit_price, exit_reason = sl, 'SL'
                break
            elif bar['low'] <= tp:
                exit_price, exit_reason = tp, 'TP'
                break

    if exit_price is None:
        exit_price = df.iloc[entry_idx + j]['close']
        exit_reason = 'TIME'

    pnl_pct = ((exit_price - entry_price) / entry_price if direction == 'LONG'
               else (entry_price - exit_price) / entry_price) - 0.001
    equity *= (1 + pnl_pct)
    trades.append({'pnl_pct': pnl_pct * 100, 'equity': equity, 'exit': exit_reason})

# 6. METRICS
tdf = pd.DataFrame(trades)
ret = (equity - 10000) / 100
eq = tdf['equity'].values
dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq) * 100).min()
wr = (tdf['pnl_pct'] > 0).sum() / len(tdf) * 100

print(f"Return: {ret:+.2f}% | DD: {dd:.2f}% | R/DD: {ret/abs(dd):.2f}x")
print(f"Trades: {len(tdf)} | Fill Rate: {len(filled)/len(signals)*100:.1f}% | WR: {wr:.1f}%")
print(f"Exits: {tdf['exit'].value_counts().to_dict()}")
```

---

Good luck! Report back with your results. 🚀
