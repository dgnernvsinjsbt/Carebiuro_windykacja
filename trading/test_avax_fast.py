#!/usr/bin/env python3
"""Fast AVAX backtest using vectorized operations"""
import pandas as pd
import numpy as np

def run_bb3_backtest_vectorized(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Vectorized BB3 backtest"""
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

    # Map bear trend to 1m data
    df = df.set_index('timestamp')
    df['bear'] = df_1h['bear'].reindex(df.index, method='ffill')
    df = df.reset_index()

    df = df.dropna().reset_index(drop=True)

    # Detect signals
    df['long_signal'] = (
        df['bear'] &
        (df['close'].shift(1) > df['bb_lower'].shift(1)) &
        (df['close'] < df['bb_lower'])
    )

    df['short_signal'] = (
        df['bear'] &
        (df['close'].shift(1) < df['bb_upper'].shift(1)) &
        (df['close'] > df['bb_upper'])
    )

    # Simulate trades (simplified - no overlapping positions)
    trades = []
    in_position = False
    FEE_RT = 0.0007

    for i in range(len(df)):
        row = df.iloc[i]

        if not in_position:
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
        else:
            # Check exit
            if position_type == 'LONG':
                if row['low'] <= stop_loss:
                    pnl = (stop_loss - entry_price) / entry_price - FEE_RT
                    trades.append({'pnl': pnl, 'result': 'SL'})
                    in_position = False
                elif row['high'] >= take_profit:
                    pnl = (take_profit - entry_price) / entry_price - FEE_RT
                    trades.append({'pnl': pnl, 'result': 'TP'})
                    in_position = False
            else:  # SHORT
                if row['high'] >= stop_loss:
                    pnl = (entry_price - stop_loss) / entry_price - FEE_RT
                    trades.append({'pnl': pnl, 'result': 'SL'})
                    in_position = False
                elif row['low'] <= take_profit:
                    pnl = (entry_price - take_profit) / entry_price - FEE_RT
                    trades.append({'pnl': pnl, 'result': 'TP'})
                    in_position = False

    if not trades:
        return None

    # Calculate metrics
    wins = sum(1 for t in trades if t['pnl'] > 0)

    # Calculate balance progression
    balance = 10000
    balances = [balance]
    for t in trades:
        balance *= (1 + t['pnl'])
        balances.append(balance)

    total_pnl = (balance - 10000) / 10000 * 100

    # Max drawdown
    balances = np.array(balances)
    peaks = np.maximum.accumulate(balances)
    drawdowns = (peaks - balances) / peaks * 100
    max_dd = drawdowns.max()

    return {
        'trades': len(trades),
        'wins': wins,
        'win_rate': wins / len(trades) * 100,
        'net_pnl': total_pnl,
        'max_dd': max_dd,
        'rr_ratio': total_pnl / max_dd if max_dd > 0 else 0,
        'final_balance': balance
    }

def main():
    print("\n" + "="*60)
    print("TESTING AVAX/USDT")
    print("="*60)

    # Load data
    print("Loading AVAX data...")
    df = pd.read_csv('avax_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"  Loaded {len(df):,} candles")
    print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test 3 strategies
    strategies = [
        ('Conservative', 3.0, 2.0, 4.0),
        ('Optimized', 3.0, 3.0, 6.0),
        ('Aggressive', 2.5, 2.5, 5.0),
    ]

    results = []
    for name, bb_std, atr_sl, atr_tp in strategies:
        print(f"\nTesting {name} (BB{bb_std}, ATR {atr_sl}/{atr_tp})...")
        result = run_bb3_backtest_vectorized(df, bb_std, atr_sl, atr_tp)
        if result:
            result['strategy'] = name
            result['coin'] = 'AVAX'
            results.append(result)
            print(f"  Trades: {result['trades']}, Win Rate: {result['win_rate']:.1f}%")
            print(f"  Net P&L: {result['net_pnl']:+.2f}%, Max DD: -{result['max_dd']:.2f}%")
            print(f"  R:R Ratio: {result['rr_ratio']:.2f}x")
            print(f"  Final Balance: ${result['final_balance']:,.2f}")
        else:
            print(f"  {name}: No trades")

    # Find best strategy
    if results:
        print("\n" + "="*60)
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"*** BEST: {best['strategy']} with R:R {best['rr_ratio']:.2f}x ***")
        print(f"    {best['trades']} trades, {best['win_rate']:.1f}% WR, {best['net_pnl']:+.2f}% P&L")
        print("="*60 + "\n")
    else:
        print("\nNo trades generated by any strategy.\n")

if __name__ == "__main__":
    main()
