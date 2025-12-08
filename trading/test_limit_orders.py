#!/usr/bin/env python3
"""
BB3 Strategy with proper limit order logic
- 0.035% offset for limit orders
- 0.07% round-trip fees (maker+taker)
"""
import sys
import pandas as pd
import numpy as np

def run_bb3_limit_backtest(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Run BB3 backtest with limit order logic"""
    if len(df) < 100:
        return None

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
    df_1h = df.set_index('timestamp').resample('1H').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    df_1h['ema50'] = df_1h['close'].ewm(span=50).mean()
    df_1h['bear'] = df_1h['close'] < df_1h['ema50']

    df = df.dropna().reset_index(drop=True)

    # Backtest with limit orders
    balance = 10000
    trades = []

    # Limit order parameters
    LIMIT_OFFSET = 0.00035  # 0.035%
    FEE_RT = 0.0007  # 0.07% round trip for limit orders
    ORDER_TIMEOUT = 60  # Cancel unfilled orders after 60 bars (1 hour)

    in_position = False
    pending_order = None
    position_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Get 1H trend
        hour_ts = row['timestamp'].floor('H')
        is_bear = False
        if len(df_1h.loc[:hour_ts]) > 0:
            is_bear = df_1h.loc[:hour_ts, 'bear'].iloc[-1]

        # Check pending limit order
        if pending_order is not None:
            order_type, limit_price, order_sl, order_tp, order_bar = pending_order

            # Check if order timed out
            if i - order_bar > ORDER_TIMEOUT:
                pending_order = None
            # Check if order filled
            elif order_type == 'LONG' and row['low'] <= limit_price:
                # Filled at limit price
                entry_price = limit_price
                stop_loss = order_sl
                take_profit = order_tp
                in_position = True
                position_type = 'LONG'
                pending_order = None
            elif order_type == 'SHORT' and row['high'] >= limit_price:
                # Filled at limit price
                entry_price = limit_price
                stop_loss = order_sl
                take_profit = order_tp
                in_position = True
                position_type = 'SHORT'
                pending_order = None

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
        elif pending_order is None:
            # Check entry signals (only in bear trend)
            if is_bear:
                atr = row['atr']

                # LONG signal: close crosses below BB lower
                if prev['close'] > prev['bb_lower'] and row['close'] < row['bb_lower']:
                    signal_price = row['close']
                    limit_price = signal_price * (1 - LIMIT_OFFSET)  # 0.035% below
                    sl = limit_price - atr_sl * atr
                    tp = limit_price + atr_tp * atr
                    pending_order = ('LONG', limit_price, sl, tp, i)

                # SHORT signal: close crosses above BB upper
                elif prev['close'] < prev['bb_upper'] and row['close'] > row['bb_upper']:
                    signal_price = row['close']
                    limit_price = signal_price * (1 + LIMIT_OFFSET)  # 0.035% above
                    sl = limit_price + atr_sl * atr
                    tp = limit_price - atr_tp * atr
                    pending_order = ('SHORT', limit_price, sl, tp, i)

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
    if len(sys.argv) < 2:
        print("Usage: python test_limit_orders.py COIN")
        sys.exit(1)

    coin = sys.argv[1].upper()
    print(f"\n{'='*60}")
    print(f"TESTING {coin}/USDT (LIMIT ORDERS)")
    print(f"{'='*60}")

    # Load CSV
    csv_file = f"{coin.lower()}_usdt_1m_lbank.csv"
    try:
        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"  Loaded {len(df):,} candles")
    except FileNotFoundError:
        print(f"  ERROR: {csv_file} not found")
        sys.exit(1)

    # Test strategies
    strategies = [
        ('Conservative', 3.0, 2.0, 4.0),
        ('Optimized', 3.0, 3.0, 6.0),
    ]

    results = []
    for name, bb_std, atr_sl, atr_tp in strategies:
        result = run_bb3_limit_backtest(df, bb_std, atr_sl, atr_tp)
        if result:
            result['strategy'] = name
            result['coin'] = coin
            results.append(result)
            print(f"\n{name} (BB{bb_std}, ATR {atr_sl}/{atr_tp}):")
            print(f"  Trades: {result['trades']}, Win Rate: {result['win_rate']:.1f}%")
            print(f"  Net P&L: {result['net_pnl']:+.2f}%, Max DD: -{result['max_dd']:.2f}%")
            print(f"  R:R Ratio: {result['rr_ratio']:.2f}x")
        else:
            print(f"\n{name}: No trades")

    if results:
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"\n*** BEST: {best['strategy']} with R:R {best['rr_ratio']:.2f}x ***")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
