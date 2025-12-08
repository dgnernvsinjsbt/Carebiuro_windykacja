#!/usr/bin/env python3
"""Fast SHIB backtest - last 7 days only"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load data
df = pd.read_csv('shib_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Take only last 7 days
cutoff = df['timestamp'].max() - timedelta(days=7)
df = df[df['timestamp'] >= cutoff].reset_index(drop=True)

print(f"Testing SHIB with {len(df):,} candles (last 7 days)")

def run_bb3_backtest(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Run BB3 backtest"""
    df = df.copy()
    df['sma20'] = df['close'].rolling(20).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['bb_lower'] = df['sma20'] - bb_std * df['std20']
    df['bb_upper'] = df['sma20'] + bb_std * df['std20']

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # 1H trend filter
    df_1h = df.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    df_1h['ema50'] = df_1h['close'].ewm(span=50).mean()
    df_1h['bear'] = df_1h['close'] < df_1h['ema50']

    df = df.dropna().reset_index(drop=True)

    # Backtest
    balance = 10000
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0

    FEE_RT = 0.0007

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        hour_ts = row['timestamp'].floor('h')
        is_bear = df_1h.loc[:hour_ts, 'bear'].iloc[-1] if hour_ts in df_1h.index or len(df_1h.loc[:hour_ts]) > 0 else False

        if in_position:
            if position_type == 'LONG':
                if row['low'] <= stop_loss:
                    pnl = (stop_loss - entry_price) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append(pnl)
                    in_position = False
                elif row['high'] >= take_profit:
                    pnl = (take_profit - entry_price) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append(pnl)
                    in_position = False
            else:  # SHORT
                if row['high'] >= stop_loss:
                    pnl = (entry_price - stop_loss) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append(pnl)
                    in_position = False
                elif row['low'] <= take_profit:
                    pnl = (entry_price - take_profit) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append(pnl)
                    in_position = False
        else:
            if is_bear:
                atr = row['atr']

                if prev['close'] > prev['bb_lower'] and row['close'] < row['bb_lower']:
                    entry_price = row['close']
                    stop_loss = entry_price - atr_sl * atr
                    take_profit = entry_price + atr_tp * atr
                    in_position = True
                    position_type = 'LONG'

                elif prev['close'] < prev['bb_upper'] and row['close'] > row['bb_upper']:
                    entry_price = row['close']
                    stop_loss = entry_price + atr_sl * atr
                    take_profit = entry_price - atr_tp * atr
                    in_position = True
                    position_type = 'SHORT'

    if not trades:
        return None

    wins = sum(1 for t in trades if t > 0)
    total_pnl = (balance - 10000) / 10000 * 100

    # Max drawdown
    running = 10000
    peak = 10000
    max_dd = 0
    for t in trades:
        running *= (1 + t)
        peak = max(peak, running)
        dd = (peak - running) / peak * 100
        max_dd = max(max_dd, dd)

    return {
        'trades': len(trades),
        'wins': wins,
        'win_rate': wins / len(trades) * 100,
        'net_pnl': total_pnl,
        'max_dd': max_dd,
        'rr_ratio': total_pnl / max_dd if max_dd > 0 else 0
    }

# Test strategies
strategies = [
    ('Conservative', 3.0, 2.0, 4.0),
    ('Optimized', 3.0, 3.0, 6.0),
    ('Aggressive', 2.5, 2.5, 5.0),
]

print("\n" + "="*60)
print("SHIB/USDT BACKTEST RESULTS")
print("="*60)

results = []
for name, bb_std, atr_sl, atr_tp in strategies:
    result = run_bb3_backtest(df, bb_std, atr_sl, atr_tp)
    if result:
        results.append((name, result))
        print(f"\n{name} (BB{bb_std}, ATR SL:{atr_sl}x TP:{atr_tp}x):")
        print(f"  Trades: {result['trades']}")
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print(f"  Net P&L: {result['net_pnl']:+.2f}%")
        print(f"  Max DD: -{result['max_dd']:.2f}%")
        print(f"  R:R Ratio: {result['rr_ratio']:.2f}x")
    else:
        print(f"\n{name}: No trades")

if results:
    best = max(results, key=lambda x: x[1]['rr_ratio'])
    print(f"\n{'='*60}")
    print(f"*** BEST: {best[0]} with R:R {best[1]['rr_ratio']:.2f}x ***")
    print(f"{'='*60}\n")
