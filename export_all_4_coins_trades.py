#!/usr/bin/env python3
"""Export ALL 4 SHORT REVERSAL strategies trades to single CSV"""
import pandas as pd
import numpy as np

def calculate_indicators(df):
    """Calculate RSI and ATR"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    return df

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

def backtest_coin(coin_name, data_file, rsi_trigger, limit_offset, tp_pct, lookback=5, max_wait=20):
    """Run backtest for one coin"""
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = calculate_indicators(df)

    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_price = None
    limit_placed_idx = None
    swing_high_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_offset)
                swing_high_for_sl = find_swing_high(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

        if limit_pending:
            if i - limit_placed_idx > max_wait:
                limit_pending = False
                continue

            if row['high'] >= limit_price:
                entry_price = limit_price
                atr = row['atr']
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:
                    limit_pending = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)

                hit_sl = False
                hit_tp = False
                exit_bar = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        exit_bar = j
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        exit_bar = j
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar

                trades.append({
                    'coin': coin_name,
                    'signal_time': df.iloc[signal_idx]['timestamp'],
                    'entry_time': row['timestamp'],
                    'exit_time': df.iloc[exit_bar]['timestamp'],
                    'rsi_at_signal': df.iloc[signal_idx]['rsi'],
                    'swing_low': swing_low,
                    'swing_high_sl': swing_high_for_sl,
                    'limit_price': limit_price,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'sl_dist_pct': sl_dist_pct,
                    'position_size': size,
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'equity_before': equity - pnl_dollar,
                    'equity_after': equity
                })

                limit_pending = False

    return pd.DataFrame(trades)

print("="*80)
print("EXPORTING 4-COIN SHORT REVERSAL PORTFOLIO TRADES")
print("="*80)

# Strategy parameters from live bot
coins = [
    {
        'name': 'FARTCOIN',
        'file': 'trading/fartcoin_6months_bingx_15m.csv',
        'rsi': 70,
        'offset': 1.0,
        'tp': 8.0
    },
    {
        'name': 'MOODENG',
        'file': 'trading/moodeng_6months_bingx_15m.csv',
        'rsi': 70,
        'offset': 0.8,
        'tp': 8.0
    },
    {
        'name': 'MELANIA',
        'file': 'trading/melania_6months_bingx.csv',
        'rsi': 72,
        'offset': 0.8,
        'tp': 10.0
    },
    {
        'name': 'DOGE',
        'file': 'trading/doge_6months_bingx_15m.csv',
        'rsi': 72,
        'offset': 0.6,
        'tp': 6.0
    }
]

all_trades = []

for coin in coins:
    print(f"\n📊 Backtesting {coin['name']}...")
    print(f"   RSI: {coin['rsi']} | Offset: {coin['offset']} ATR | TP: {coin['tp']}%")

    trades_df = backtest_coin(
        coin['name'],
        coin['file'],
        coin['rsi'],
        coin['offset'],
        coin['tp']
    )

    print(f"   ✅ {len(trades_df)} trades")
    all_trades.append(trades_df)

# Combine all trades
print("\n" + "="*80)
print("COMBINING ALL TRADES")
print("="*80)

combined = pd.concat(all_trades, ignore_index=True)

# Sort chronologically by entry time
combined = combined.sort_values('entry_time').reset_index(drop=True)

# Add sequential trade number
combined.insert(0, 'trade_num', range(1, len(combined) + 1))

# Add month column
combined['month'] = pd.to_datetime(combined['entry_time']).dt.to_period('M')

# Save to CSV
combined.to_csv('4_coin_portfolio_all_trades.csv', index=False)

print(f"\n✅ Exported {len(combined)} total trades to: 4_coin_portfolio_all_trades.csv")
print(f"\n📊 Breakdown by coin:")
for coin_name in combined['coin'].unique():
    count = len(combined[combined['coin'] == coin_name])
    total_pnl = combined[combined['coin'] == coin_name]['pnl_dollar'].sum()
    win_rate = (combined[(combined['coin'] == coin_name) & (combined['pnl_dollar'] > 0)].shape[0] / count * 100)
    print(f"   {coin_name:12s}: {count:3d} trades, ${total_pnl:+8.2f}, {win_rate:5.1f}% win rate")

print(f"\n📅 Breakdown by month:")
for month in sorted(combined['month'].unique()):
    month_data = combined[combined['month'] == month]
    print(f"   {month}: {len(month_data):3d} trades, ${month_data['pnl_dollar'].sum():+8.2f}")

print("\n" + "="*80)
