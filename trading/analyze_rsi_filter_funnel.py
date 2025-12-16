#!/usr/bin/env python3
"""
Analyze Daily RSI > 50 filter:
1. Total signals generated
2. Limit orders placed
3. Fills achieved
4. Equity curve
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

print("=" * 80)
print("DAILY RSI > 50 FILTER - SIGNAL FUNNEL ANALYSIS")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df):,} candles (60 days)")

# Calculate 1m indicators
df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']

# Calculate daily indicators
df_daily = df.set_index('timestamp').resample('1D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

# Merge back
df = df.set_index('timestamp')
df = df.join(df_daily[['rsi_daily']], how='left')
df = df.ffill()
df = df.reset_index()

print("✅ Indicators ready")

# STEP 1: Count all LONG signals (before RSI filter)
print("\n" + "=" * 80)
print("STEP 1: ALL LONG SIGNALS (before Daily RSI filter)")
print("=" * 80)

all_signals = []
for i in range(len(df)):
    row = df.iloc[i]
    if (row['atr_ratio'] > 1.5 and
        row['distance'] < 3.0 and
        row['bullish']):
        all_signals.append({
            'idx': i,
            'timestamp': row['timestamp'],
            'price': row['close'],
            'daily_rsi': row['rsi_daily']
        })

print(f"Total LONG signals: {len(all_signals)}")

# STEP 2: Apply RSI filter
print("\n" + "=" * 80)
print("STEP 2: SIGNALS AFTER Daily RSI > 50 filter")
print("=" * 80)

filtered_signals = [s for s in all_signals if not pd.isna(s['daily_rsi']) and s['daily_rsi'] > 50]

print(f"Signals with RSI > 50: {len(filtered_signals)}")
print(f"Filtered out: {len(all_signals) - len(filtered_signals)} ({(len(all_signals) - len(filtered_signals)) / len(all_signals) * 100:.1f}%)")

# STEP 3: Try to fill limit orders
print("\n" + "=" * 80)
print("STEP 3: LIMIT ORDER FILLS")
print("=" * 80)

limit_orders_placed = 0
limit_orders_filled = 0
trades = []

for signal in filtered_signals:
    idx = signal['idx']

    if idx >= len(df) - 1:
        continue

    signal_price = signal['price']
    signal_atr = df['atr'].iloc[idx]

    if pd.isna(signal_atr) or signal_atr == 0:
        continue

    # Place limit order
    limit_orders_placed += 1
    limit_price = signal_price * 1.01

    # Try to fill in next 3 bars
    filled = False
    fill_idx = None

    for i in range(idx + 1, min(idx + 4, len(df))):
        if df['high'].iloc[i] >= limit_price:
            filled = True
            fill_idx = i
            break

    if not filled:
        continue

    # Order filled
    limit_orders_filled += 1

    entry_price = limit_price
    entry_atr = df['atr'].iloc[fill_idx]

    sl_price = entry_price - (2.0 * entry_atr)
    tp_price = entry_price + (8.0 * entry_atr)

    # Find exit
    exit_idx = None
    exit_price = None
    exit_reason = None

    for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
        if df['low'].iloc[i] <= sl_price:
            exit_idx = i
            exit_price = sl_price
            exit_reason = 'SL'
            break
        if df['high'].iloc[i] >= tp_price:
            exit_idx = i
            exit_price = tp_price
            exit_reason = 'TP'
            break

    if exit_idx is None:
        exit_idx = min(fill_idx + 199, len(df) - 1)
        exit_price = df['close'].iloc[exit_idx]
        exit_reason = 'TIME'

    pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.10

    trades.append({
        'entry_time': df['timestamp'].iloc[fill_idx],
        'exit_time': df['timestamp'].iloc[exit_idx],
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': pnl_pct,
        'exit_reason': exit_reason,
        'daily_rsi': signal['daily_rsi']
    })

print(f"Limit orders placed: {limit_orders_placed}")
print(f"Limit orders filled: {limit_orders_filled}")
print(f"Fill rate: {limit_orders_filled / limit_orders_placed * 100:.1f}%")
print(f"Unfilled: {limit_orders_placed - limit_orders_filled}")

# SUMMARY
print("\n" + "=" * 80)
print("SIGNAL FUNNEL SUMMARY")
print("=" * 80)

print(f"""
Step 1: ALL LONG signals (ATR expansion + bullish)
  → {len(all_signals)} signals

Step 2: Apply Daily RSI > 50 filter
  → {len(filtered_signals)} signals ({len(filtered_signals) / len(all_signals) * 100:.1f}% pass)
  → {len(all_signals) - len(filtered_signals)} rejected ({(len(all_signals) - len(filtered_signals)) / len(all_signals) * 100:.1f}%)

Step 3: Place limit orders 1% away
  → {limit_orders_placed} orders placed

Step 4: Wait for fill (max 3 bars)
  → {limit_orders_filled} orders filled ({limit_orders_filled / limit_orders_placed * 100:.1f}% fill rate)
  → {limit_orders_placed - limit_orders_filled} orders cancelled ({(limit_orders_placed - limit_orders_filled) / limit_orders_placed * 100:.1f}%)

FINAL: {limit_orders_filled} trades executed
""")

print(f"Overall conversion: {len(all_signals)} signals → {limit_orders_filled} trades ({limit_orders_filled / len(all_signals) * 100:.1f}%)")

# EQUITY CURVE
print("\n" + "=" * 80)
print("EQUITY CURVE")
print("=" * 80)

df_trades = pd.DataFrame(trades)

if len(trades) > 0:
    df_trades['cumulative'] = df_trades['pnl_pct'].cumsum()
    df_trades['equity'] = 100 + df_trades['cumulative']

    # Calculate drawdown
    df_trades['peak'] = df_trades['equity'].cummax()
    df_trades['drawdown'] = (df_trades['equity'] - df_trades['peak']) / df_trades['peak'] * 100

    # Stats
    total_return = df_trades['pnl_pct'].sum()
    max_dd = df_trades['drawdown'].min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0
    winners = df_trades[df_trades['pnl_pct'] > 0]
    win_rate = len(winners) / len(df_trades) * 100
    tp_rate = (df_trades['exit_reason'] == 'TP').sum() / len(df_trades) * 100

    print(f"\nPerformance:")
    print(f"  Trades: {len(df_trades)}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  TP Rate: {tp_rate:.1f}%")
    print(f"  Total Return: {total_return:+.2f}%")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Return/DD: {return_dd:.2f}x")

    print(f"\n  Starting equity: $100.00")
    print(f"  Final equity: ${df_trades['equity'].iloc[-1]:.2f}")
    print(f"  Peak equity: ${df_trades['equity'].max():.2f}")

    # Trade breakdown
    print(f"\n  Avg winner: {winners['pnl_pct'].mean():.2f}%")
    losers = df_trades[df_trades['pnl_pct'] <= 0]
    print(f"  Avg loser: {losers['pnl_pct'].mean():.2f}%")

    print(f"\n  Largest win: {df_trades['pnl_pct'].max():.2f}%")
    print(f"  Largest loss: {df_trades['pnl_pct'].min():.2f}%")

    # Exit breakdown
    print(f"\n  TP exits: {(df_trades['exit_reason'] == 'TP').sum()}")
    print(f"  SL exits: {(df_trades['exit_reason'] == 'SL').sum()}")
    print(f"  TIME exits: {(df_trades['exit_reason'] == 'TIME').sum()}")

    # Print equity curve
    print(f"\n" + "=" * 80)
    print("EQUITY CURVE DATA")
    print("=" * 80)

    print(f"\n{'Trade':<6} {'Date':<20} {'P&L':<8} {'Equity':<10} {'DD':<8} {'Exit':<6}")
    print("-" * 70)

    for i, row in df_trades.iterrows():
        print(f"{i+1:<6} {row['entry_time'].strftime('%Y-%m-%d %H:%M'):<20} "
              f"{row['pnl_pct']:+7.2f}% ${row['equity']:9.2f} {row['drawdown']:7.2f}% {row['exit_reason']:<6}")

    # Visual equity curve (ASCII)
    print(f"\n" + "=" * 80)
    print("EQUITY CURVE (ASCII)")
    print("=" * 80)

    equity_values = df_trades['equity'].values
    min_equity = equity_values.min()
    max_equity = equity_values.max()

    # Normalize to 0-50 range for display
    height = 20
    normalized = ((equity_values - min_equity) / (max_equity - min_equity) * (height - 1)).astype(int)

    for h in range(height - 1, -1, -1):
        line = f"${min_equity + (max_equity - min_equity) * h / (height - 1):6.1f} |"
        for val in normalized:
            if val == h:
                line += "█"
            elif val > h:
                line += "│"
            else:
                line += " "
        print(line)

    print(" " * 8 + "└" + "─" * len(normalized))
    print(" " * 9 + "Trade number →")

    # Save trades
    df_trades.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_rsi_filtered_trades.csv', index=False)
    print(f"\n✅ Trade log saved to: trading/results/fartcoin_rsi_filtered_trades.csv")

print("\n" + "=" * 80)
