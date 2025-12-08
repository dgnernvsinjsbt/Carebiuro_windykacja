#!/usr/bin/env python3
import pandas as pd
import numpy as np

def run_bb3_backtest_fast(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Run BB3 backtest with given parameters - optimized version"""
    if len(df) < 100:
        return None

    # Calculate indicators
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

    # Map bear trend back to 1m data
    df = df.set_index('timestamp')
    df['hour'] = df.index.floor('1h')
    df['is_bear'] = df['hour'].map(df_1h['bear']).fillna(False)
    df = df.reset_index()

    # Detect signals
    df['long_signal'] = (
        (df['close'].shift(1) > df['bb_lower'].shift(1)) &
        (df['close'] < df['bb_lower']) &
        df['is_bear']
    )
    df['short_signal'] = (
        (df['close'].shift(1) < df['bb_upper'].shift(1)) &
        (df['close'] > df['bb_upper']) &
        df['is_bear']
    )

    df = df.dropna().reset_index(drop=True)

    # Simulate trades
    balance = 10000
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_idx = 0

    FEE_RT = 0.0007

    for i in range(len(df)):
        row = df.iloc[i]

        if in_position:
            # Check exit
            if position_type == 'LONG':
                if row['low'] <= stop_loss:
                    pnl = (stop_loss - entry_price) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append({'type': 'LONG', 'pnl': pnl, 'result': 'SL'})
                    in_position = False
                elif row['high'] >= take_profit:
                    pnl = (take_profit - entry_price) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append({'type': 'LONG', 'pnl': pnl, 'result': 'TP'})
                    in_position = False
            else:  # SHORT
                if row['high'] >= stop_loss:
                    pnl = (entry_price - stop_loss) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append({'type': 'SHORT', 'pnl': pnl, 'result': 'SL'})
                    in_position = False
                elif row['low'] <= take_profit:
                    pnl = (entry_price - take_profit) / entry_price - FEE_RT
                    balance *= (1 + pnl)
                    trades.append({'type': 'SHORT', 'pnl': pnl, 'result': 'TP'})
                    in_position = False

        if not in_position:
            # Check for new entry
            if row['long_signal']:
                entry_price = row['close']
                stop_loss = entry_price - atr_sl * row['atr']
                take_profit = entry_price + atr_tp * row['atr']
                in_position = True
                position_type = 'LONG'
                entry_idx = i
            elif row['short_signal']:
                entry_price = row['close']
                stop_loss = entry_price + atr_sl * row['atr']
                take_profit = entry_price - atr_tp * row['atr']
                in_position = True
                position_type = 'SHORT'
                entry_idx = i

    if not trades:
        return None

    # Calculate metrics
    wins = sum(1 for t in trades if t['pnl'] > 0)
    total_pnl = (balance - 10000) / 10000 * 100

    # Max drawdown
    running = 10000
    peak = 10000
    max_dd = 0
    for t in trades:
        running *= (1 + t['pnl'])
        peak = max(peak, running)
        dd = (peak - running) / peak * 100
        max_dd = max(max_dd, dd)

    # Average win/loss
    winning_trades = [t['pnl'] for t in trades if t['pnl'] > 0]
    losing_trades = [t['pnl'] for t in trades if t['pnl'] < 0]
    avg_win = np.mean(winning_trades) * 100 if winning_trades else 0
    avg_loss = np.mean(losing_trades) * 100 if losing_trades else 0

    return {
        'trades': len(trades),
        'wins': wins,
        'win_rate': wins / len(trades) * 100,
        'net_pnl': total_pnl,
        'max_dd': max_dd,
        'rr_ratio': total_pnl / max_dd if max_dd > 0 else 0,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'final_balance': balance
    }

# Load XLM data
print("\n" + "="*60)
print("TESTING XLM/USDT")
print("="*60)

df = pd.read_csv('xlm_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Use last 7 days for faster testing
df = df.tail(10080)  # 7 days * 24h * 60m

print(f"Loaded {len(df):,} candles (last 7 days)")
print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Test 3 strategies
strategies = [
    ('Conservative', 3.0, 2.0, 4.0),
    ('Optimized', 3.0, 3.0, 6.0),
    ('Aggressive', 2.5, 2.5, 5.0),
]

results = []
for name, bb_std, atr_sl, atr_tp in strategies:
    result = run_bb3_backtest_fast(df, bb_std, atr_sl, atr_tp)
    if result:
        result['strategy'] = name
        result['coin'] = 'XLM'
        results.append(result)
        print(f"\n{name} (BB{bb_std}, ATR SL/TP {atr_sl}/{atr_tp}x):")
        print(f"  Trades: {result['trades']}, Win Rate: {result['win_rate']:.1f}%")
        print(f"  Net P&L: {result['net_pnl']:+.2f}%, Max DD: -{result['max_dd']:.2f}%")
        print(f"  R:R Ratio: {result['rr_ratio']:.2f}x")
        print(f"  Avg Win/Loss: +{result['avg_win']:.2f}% / {result['avg_loss']:.2f}%")
    else:
        print(f"\n{name}: No trades")

# Find best strategy
if results:
    best = max(results, key=lambda x: x['rr_ratio'])
    print(f"\n{'*'*60}")
    print(f"WINNER: {best['strategy']} strategy")
    print(f"  R:R Ratio: {best['rr_ratio']:.2f}x")
    print(f"  Net P&L: {best['net_pnl']:+.2f}%")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"{'*'*60}")

print(f"\n{'='*60}\n")
