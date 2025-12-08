#!/usr/bin/env python3
"""
Download 1m 30-day data from LBank for multiple coins
and run BB3 strategy variations on each
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os

# Coins to test (symbol format for LBank)
COINS = [
    'BTC/USDT',
    'DOGE/USDT',
    'XRP/USDT',
    'SOL/USDT',
    'PEPE/USDT',
    'SHIB/USDT',
    'AVAX/USDT',
    'LINK/USDT',
    'UNI/USDT',
    'XLM/USDT',
]

MAKER_FEE = 0.0002
TAKER_FEE = 0.0005
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def download_coin(symbol, days=30):
    """Download 1m data from LBank"""
    exchange = ccxt.lbank({'enableRateLimit': True})

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    print(f"\nDownloading {symbol}...")

    all_candles = []
    current_start = start_time
    chunk_size = timedelta(minutes=1000)

    while current_start < end_time:
        current_end = min(current_start + chunk_size, end_time)

        try:
            since = int(current_start.timestamp() * 1000)
            candles = exchange.fetch_ohlcv(symbol=symbol, timeframe='1m', since=since, limit=1000)

            if candles:
                all_candles.extend(candles)
                print(f"  {current_start.strftime('%m-%d')}: {len(candles)} candles")

            current_start = current_end
            time.sleep(exchange.rateLimit / 1000)

        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2)
            current_start = current_end
            continue

    if not all_candles:
        print(f"  Failed to download {symbol}")
        return None

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Save
    coin_name = symbol.replace('/', '_').lower()
    filename = f'{coin_name}_1m_lbank.csv'
    df.to_csv(filename, index=False)
    print(f"  Saved: {filename} ({len(df):,} candles)")

    return df

def run_bb3_strategy(df, bb_std=3, atr_sl=2, atr_tp=4, use_trend_filter=True, name=""):
    """Run BB3 strategy on dataframe"""

    if df is None or len(df) < 500:
        return None

    df = df.copy()

    # BB indicators
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + bb_std * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - bb_std * df['bb_std']
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()

    # 1H trend filter
    if use_trend_filter:
        df_1h = df.set_index('timestamp').resample('1h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
        df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

        df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
        df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

    df = df.dropna().reset_index(drop=True)

    df['long_signal'] = df['close'] < df['bb_lower']
    df['short_signal'] = df['close'] > df['bb_upper']

    # Run backtest
    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row.get('trend_1h', 'BEAR') if use_trend_filter else 'BEAR'

        if not in_position:
            # LONG in BEAR
            if row['long_signal'] and trend == 'BEAR':
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * atr_sl)
                take_profit = entry_price + (atr * atr_tp)

            # SHORT in BEAR
            elif row['short_signal'] and trend == 'BEAR':
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * atr_sl)
                take_profit = entry_price - (atr * atr_tp)

        elif in_position:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'STOP', 'entry_time': entry_time, 'exit_time': row['timestamp']})
                    in_position = False
                elif high >= take_profit:
                    trades.append({'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'TP', 'entry_time': entry_time, 'exit_time': row['timestamp']})
                    in_position = False
            else:
                if high >= stop_loss:
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'STOP', 'entry_time': entry_time, 'exit_time': row['timestamp']})
                    in_position = False
                elif low <= take_profit:
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'TP', 'entry_time': entry_time, 'exit_time': row['timestamp']})
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    def get_extremes(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            d = eth_idx.loc[mask]
            return pd.Series({'max_p': d['high'].max(), 'min_p': d['low'].min()})
        except:
            return pd.Series({'max_p': row['entry'], 'min_p': row['entry']})

    ext = trades_df.apply(get_extremes, axis=1)
    trades_df['max_price'] = ext['max_p']
    trades_df['min_price'] = ext['min_p']

    # Simulate with limit orders
    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit_price = signal * (1 - LIMIT_OFFSET)
            filled = row['min_price'] <= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
        else:
            limit_price = signal * (1 + LIMIT_OFFSET)
            filled = row['max_price'] >= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_price) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results.append({'filled': True, 'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0})
        else:
            results.append({'filled': False, 'gross': 0, 'net': 0, 'balance': balance, 'win': False})

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    if len(filled) == 0:
        return None

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    profit = balance - STARTING_BALANCE
    max_dd = abs(dd.min())

    return {
        'name': name,
        'trades': len(filled),
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net_pct': filled['net'].sum(),
        'max_dd': max_dd,
        'profit': profit,
        'rr': profit / (max_dd * 100) if max_dd > 0 else 0
    }


def main():
    print("=" * 100)
    print("BB3 STRATEGY - MULTI-COIN TEST")
    print("=" * 100)

    # Strategy variations
    strategies = [
        {'name': 'Conservative (2/4)', 'bb_std': 3, 'atr_sl': 2, 'atr_tp': 4},
        {'name': 'Optimized (3/6)', 'bb_std': 3, 'atr_sl': 3, 'atr_tp': 6},
        {'name': 'Aggressive (2.5/5)', 'bb_std': 2.5, 'atr_sl': 2.5, 'atr_tp': 5},
    ]

    all_results = []

    for symbol in COINS:
        coin_name = symbol.replace('/USDT', '')
        filename = f'{symbol.replace("/", "_").lower()}_1m_lbank.csv'

        # Check if already downloaded
        if os.path.exists(filename):
            print(f"\n{coin_name}: Loading existing data...")
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df = download_coin(symbol, days=30)

        if df is None or len(df) < 1000:
            print(f"  {coin_name}: Insufficient data, skipping")
            continue

        print(f"\n{coin_name} Data: {len(df):,} candles, {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")

        for strat in strategies:
            r = run_bb3_strategy(df, bb_std=strat['bb_std'], atr_sl=strat['atr_sl'],
                                atr_tp=strat['atr_tp'], use_trend_filter=True,
                                name=f"{coin_name} {strat['name']}")
            if r:
                r['coin'] = coin_name
                r['strategy'] = strat['name']
                all_results.append(r)

    # Print results
    print("\n" + "=" * 120)
    print("RESULTS SUMMARY")
    print("=" * 120)

    print(f"\n{'Coin':<8} {'Strategy':<20} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET%':<10} {'MaxDD%':<10} {'Profit':<12} {'R:R':<8}")
    print("-" * 120)

    for r in sorted(all_results, key=lambda x: x['profit'], reverse=True):
        wl = f"{r['wins']}/{r['losses']}"
        print(f"{r['coin']:<8} {r['strategy']:<20} {r['trades']:<8} {wl:<10} {r['win_rate']:.1f}%    {r['net_pct']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}      {r['rr']:.2f}x")

    # Find profitable strategies
    profitable = [r for r in all_results if r['profit'] > 0]

    print("\n" + "=" * 120)
    print(f"PROFITABLE STRATEGIES: {len(profitable)} / {len(all_results)}")
    print("=" * 120)

    if profitable:
        print("\nTop 5 by Profit:")
        for r in sorted(profitable, key=lambda x: x['profit'], reverse=True)[:5]:
            print(f"  {r['coin']} {r['strategy']}: ${r['profit']:+,.0f} ({r['rr']:.2f}x R:R, {r['win_rate']:.1f}% WR)")

        print("\nTop 5 by Risk:Reward:")
        for r in sorted(profitable, key=lambda x: x['rr'], reverse=True)[:5]:
            print(f"  {r['coin']} {r['strategy']}: {r['rr']:.2f}x R:R (${r['profit']:+,.0f}, {r['max_dd']:.2f}% DD)")

    # Save results
    if all_results:
        pd.DataFrame(all_results).to_csv('results/bb3_multi_coin_results.csv', index=False)
        print("\nSaved: results/bb3_multi_coin_results.csv")


if __name__ == "__main__":
    main()
