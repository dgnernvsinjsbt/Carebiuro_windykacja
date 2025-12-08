#!/usr/bin/env python3
"""
Single coin BB3 strategy test - designed to run in parallel
Usage: python test_single_coin.py COIN
"""
import sys
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

def download_lbank_1m(symbol: str, days: int = 30) -> pd.DataFrame:
    """Download 1m data from LBank"""
    pair = f"{symbol.lower()}_usdt"
    url = "https://api.lbank.com/v2/kline.do"

    all_candles = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    current = start_time
    while current < end_time:
        params = {
            'symbol': pair,
            'size': 1000,
            'type': 'minute1',
            'time': current
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            if data.get('result') != 'true' or not data.get('data'):
                break

            candles = data['data']
            if not candles:
                break

            all_candles.extend(candles)
            current = int(candles[-1][0]) + 60000
            time.sleep(0.1)

        except Exception as e:
            print(f"  Error: {e}")
            break

    if not all_candles:
        return pd.DataFrame()

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df = df.drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
    return df

def run_bb3_backtest(df: pd.DataFrame, bb_std: float, atr_sl: float, atr_tp: float) -> dict:
    """Run BB3 backtest with given parameters"""
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

    df = df.dropna().reset_index(drop=True)

    # Backtest
    balance = 10000
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0

    FEE_RT = 0.0007  # 0.07% round trip

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Get 1H trend
        hour_ts = row['timestamp'].floor('h')
        is_bear = df_1h.loc[:hour_ts, 'bear'].iloc[-1] if hour_ts in df_1h.index or len(df_1h.loc[:hour_ts]) > 0 else False

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
        else:
            # Check entry signals (only in bear trend)
            if is_bear:
                atr = row['atr']

                # LONG signal: close crosses below BB lower
                if prev['close'] > prev['bb_lower'] and row['close'] < row['bb_lower']:
                    entry_price = row['close']
                    stop_loss = entry_price - atr_sl * atr
                    take_profit = entry_price + atr_tp * atr
                    in_position = True
                    position_type = 'LONG'

                # SHORT signal: close crosses above BB upper
                elif prev['close'] < prev['bb_upper'] and row['close'] > row['bb_upper']:
                    entry_price = row['close']
                    stop_loss = entry_price + atr_sl * atr
                    take_profit = entry_price - atr_tp * atr
                    in_position = True
                    position_type = 'SHORT'

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
        print("Usage: python test_single_coin.py COIN")
        sys.exit(1)

    coin = sys.argv[1].upper()
    print(f"\n{'='*60}")
    print(f"TESTING {coin}/USDT")
    print(f"{'='*60}")

    # Try to load existing CSV first
    csv_file = f"{coin.lower()}_usdt_1m_lbank.csv"
    try:
        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Limit to last 30 days for faster processing
        cutoff = df['timestamp'].max() - timedelta(days=30)
        df = df[df['timestamp'] >= cutoff].reset_index(drop=True)
        print(f"  Loaded {len(df):,} candles from {csv_file} (last 30 days)")
    except FileNotFoundError:
        # Download data if file doesn't exist
        print(f"Downloading {coin} 1m data from LBank...")
        df = download_lbank_1m(coin, days=30)
        if df.empty or len(df) < 1000:
            print(f"  ERROR: Not enough data for {coin}")
            sys.exit(1)
        print(f"  Downloaded {len(df):,} candles")

    if df.empty or len(df) < 1000:
        print(f"  ERROR: Not enough data for {coin}")
        sys.exit(1)

    # Test 3 strategies
    strategies = [
        ('Conservative', 3.0, 2.0, 4.0),
        ('Optimized', 3.0, 3.0, 6.0),
        ('Aggressive', 2.5, 2.5, 5.0),
    ]

    results = []
    for name, bb_std, atr_sl, atr_tp in strategies:
        result = run_bb3_backtest(df, bb_std, atr_sl, atr_tp)
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

    # Find best strategy
    if results:
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"\n*** BEST: {best['strategy']} with R:R {best['rr_ratio']:.2f}x ***")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
