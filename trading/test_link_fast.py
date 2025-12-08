#!/usr/bin/env python3
"""
Fast vectorized BB3 backtest for LINK
"""
import pandas as pd
import numpy as np
from datetime import timedelta

def run_bb3_vectorized(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Vectorized BB3 backtest"""
    df = df.copy()

    # Calculate indicators
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

    # Map 1H bear trend to 1m
    df['hour'] = df['timestamp'].dt.floor('h')
    df = df.merge(df_1h[['bear']].reset_index().rename(columns={'timestamp': 'hour'}), on='hour', how='left')
    df['bear'] = df['bear'].fillna(False)

    df = df.dropna().reset_index(drop=True)

    # Generate signals
    df['long_signal'] = (
        (df['close'].shift(1) > df['bb_lower'].shift(1)) &
        (df['close'] < df['bb_lower']) &
        df['bear']
    )

    df['short_signal'] = (
        (df['close'].shift(1) < df['bb_upper'].shift(1)) &
        (df['close'] > df['bb_upper']) &
        df['bear']
    )

    # Simple backtest: take every signal, exit at SL or TP
    trades = []
    FEE_RT = 0.0007

    i = 0
    while i < len(df):
        if df.iloc[i]['long_signal']:
            entry = df.iloc[i]['close']
            atr = df.iloc[i]['atr']
            sl = entry - atr_sl * atr
            tp = entry + atr_tp * atr

            # Find exit
            for j in range(i+1, min(i+500, len(df))):  # Max 500 candles = ~8 hours
                if df.iloc[j]['low'] <= sl:
                    pnl = (sl - entry) / entry - FEE_RT
                    trades.append({'pnl': pnl, 'type': 'LONG', 'result': 'SL'})
                    i = j
                    break
                elif df.iloc[j]['high'] >= tp:
                    pnl = (tp - entry) / entry - FEE_RT
                    trades.append({'pnl': pnl, 'type': 'LONG', 'result': 'TP'})
                    i = j
                    break
            else:
                i += 1

        elif df.iloc[i]['short_signal']:
            entry = df.iloc[i]['close']
            atr = df.iloc[i]['atr']
            sl = entry + atr_sl * atr
            tp = entry - atr_tp * atr

            # Find exit
            for j in range(i+1, min(i+500, len(df))):
                if df.iloc[j]['high'] >= sl:
                    pnl = (entry - sl) / entry - FEE_RT
                    trades.append({'pnl': pnl, 'type': 'SHORT', 'result': 'SL'})
                    i = j
                    break
                elif df.iloc[j]['low'] <= tp:
                    pnl = (entry - tp) / entry - FEE_RT
                    trades.append({'pnl': pnl, 'type': 'SHORT', 'result': 'TP'})
                    i = j
                    break
            else:
                i += 1
        else:
            i += 1

    if not trades:
        return None

    # Calculate metrics
    wins = sum(1 for t in trades if t['pnl'] > 0)

    # Calculate balance progression
    balance = 10000
    running_balance = [balance]
    for t in trades:
        balance *= (1 + t['pnl'])
        running_balance.append(balance)

    total_pnl = (balance - 10000) / 10000 * 100

    # Max drawdown
    running_balance = np.array(running_balance)
    peak = np.maximum.accumulate(running_balance)
    dd = (peak - running_balance) / peak * 100
    max_dd = dd.max()

    avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) * 100 if wins > 0 else 0
    avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) * 100 if wins < len(trades) else 0

    return {
        'trades': len(trades),
        'wins': wins,
        'win_rate': wins / len(trades) * 100,
        'net_pnl': total_pnl,
        'max_dd': max_dd,
        'rr_ratio': total_pnl / max_dd if max_dd > 0 else 0,
        'final_balance': balance,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }

def main():
    print("\n" + "="*60)
    print("TESTING LINK/USDT - Fast Vectorized")
    print("="*60)

    # Load data
    df = pd.read_csv('link_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Limit to last 30 days
    cutoff = df['timestamp'].max() - timedelta(days=30)
    df = df[df['timestamp'] >= cutoff].reset_index(drop=True)

    print(f"  Loaded {len(df):,} candles (last 30 days)")
    print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test 3 strategies
    strategies = [
        ('Conservative', 3.0, 2.0, 4.0),
        ('Optimized', 3.0, 3.0, 6.0),
        ('Aggressive', 2.5, 2.5, 5.0),
    ]

    results = []
    for name, bb_std, atr_sl, atr_tp in strategies:
        print(f"\nTesting {name} (BB{bb_std}, ATR SL/TP {atr_sl}/{atr_tp})...")
        result = run_bb3_vectorized(df, bb_std, atr_sl, atr_tp)
        if result:
            result['strategy'] = name
            results.append(result)
            print(f"  Trades: {result['trades']}, Win Rate: {result['win_rate']:.1f}%")
            print(f"  Net P&L: {result['net_pnl']:+.2f}%, Max DD: -{result['max_dd']:.2f}%")
            print(f"  R:R Ratio: {result['rr_ratio']:.2f}x")
            print(f"  Avg Win: {result['avg_win']:.2f}%, Avg Loss: {result['avg_loss']:.2f}%")
        else:
            print(f"  No trades generated")

    # Find best strategy
    if results:
        print("\n" + "="*60)
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"BEST STRATEGY: {best['strategy']}")
        print(f"  R:R Ratio: {best['rr_ratio']:.2f}x")
        print(f"  Net P&L: {best['net_pnl']:+.2f}%")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Trades: {best['trades']}")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
