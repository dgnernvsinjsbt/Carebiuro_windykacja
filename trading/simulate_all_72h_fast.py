"""
72h Simulation for ALL strategies - FAST VERSION
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def download_bingx_72h(symbol):
    """Download 72h of 1-min data (4320 candles) in 3 batches"""
    base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)

    # 72h = 4320 candles, get in 3 batches of 1440
    for batch in range(3):
        params = {
            "symbol": symbol,
            "interval": "1m",
            "endTime": end_time,
            "limit": 1440
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            data = response.json()

            if 'data' not in data or not data['data']:
                break

            batch_data = data['data']
            all_data = batch_data + all_data
            end_time = int(batch_data[0]['time']) - 1
        except Exception as e:
            print(f"Error: {e}")
            break

    if not all_data:
        return None

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').reset_index(drop=True)

def add_indicators(df):
    """Add all required indicators"""
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['ret_5m'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
    df['vol_ma_30'] = df['volume'].rolling(30).mean()
    df['vol_ratio_30'] = df['volume'] / df['vol_ma_30']
    df['atr_ma_30'] = df['atr'].rolling(30).mean()
    df['atr_ratio_30'] = df['atr'] / df['atr_ma_30']

    return df

def backtest_pippin(df, fee_pct=0.10):
    """PIPPIN Fresh Crosses"""
    df = df.copy()
    df['ema9_above'] = df['ema_9'] > df['ema_21']
    df['cross_up'] = df['ema9_above'] & ~df['ema9_above'].shift(1).fillna(False)
    df['cross_down'] = ~df['ema9_above'] & df['ema9_above'].shift(1).fillna(True)

    trades = []
    for i in range(50, len(df) - 120):
        row = df.iloc[i]

        if row['cross_up'] or row['cross_down']:
            if pd.isna(row['rsi']) or pd.isna(row['body_pct']) or pd.isna(row['atr']):
                continue
            if row['rsi'] >= 55 and row['body_pct'] <= 0.06:
                entry = row['close']
                atr = row['atr']
                direction = 'LONG' if row['cross_up'] else 'SHORT'

                if direction == 'LONG':
                    sl, tp = entry - 1.5*atr, entry + 10*atr
                else:
                    sl, tp = entry + 1.5*atr, entry - 10*atr

                for j in range(i+1, min(i+121, len(df))):
                    if direction == 'LONG':
                        if df['low'].iloc[j] <= sl:
                            trades.append({'dir': direction, 'pnl': -1.5*atr/entry*100-fee_pct, 'exit': 'SL'})
                            break
                        if df['high'].iloc[j] >= tp:
                            trades.append({'dir': direction, 'pnl': 10*atr/entry*100-fee_pct, 'exit': 'TP'})
                            break
                    else:
                        if df['high'].iloc[j] >= sl:
                            trades.append({'dir': direction, 'pnl': -1.5*atr/entry*100-fee_pct, 'exit': 'SL'})
                            break
                        if df['low'].iloc[j] <= tp:
                            trades.append({'dir': direction, 'pnl': 10*atr/entry*100-fee_pct, 'exit': 'TP'})
                            break
                else:
                    exit_p = df['close'].iloc[min(i+120, len(df)-1)]
                    pnl = ((exit_p-entry)/entry if direction=='LONG' else (entry-exit_p)/entry)*100-fee_pct
                    trades.append({'dir': direction, 'pnl': pnl, 'exit': 'TIME'})
    return trades

def backtest_doge(df, fee_pct=0.10):
    """DOGE Volume Zones"""
    trades = []
    in_zone = False
    zone_bars = 0
    zone_highs, zone_lows = [], []

    for i in range(50, len(df) - 90):
        row = df.iloc[i]
        hour = row['timestamp'].hour
        if not (7 <= hour < 14):
            in_zone, zone_bars, zone_highs, zone_lows = False, 0, [], []
            continue

        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0

        if vol_ratio >= 1.5:
            if not in_zone:
                in_zone, zone_bars = True, 1
                zone_highs, zone_lows = [row['high']], [row['low']]
            else:
                zone_bars += 1
                zone_highs.append(row['high'])
                zone_lows.append(row['low'])
        else:
            if in_zone and zone_bars >= 5:
                zone_high, zone_low = max(zone_highs), min(zone_lows)
                lookback = df.iloc[max(0,i-25):i]
                window_low, window_high = lookback['low'].min(), lookback['high'].max()

                entry, atr = row['close'], row['atr']
                direction = None

                if zone_low <= window_low * 1.002:
                    direction = 'LONG'
                elif zone_high >= window_high * 0.998:
                    direction = 'SHORT'

                if direction and not pd.isna(atr):
                    sl_mult, tp_mult = 1.5, 4.0
                    if direction == 'LONG':
                        sl, tp = entry - sl_mult*atr, entry + tp_mult*atr
                    else:
                        sl, tp = entry + sl_mult*atr, entry - tp_mult*atr

                    for j in range(i+1, min(i+91, len(df))):
                        if direction == 'LONG':
                            if df['low'].iloc[j] <= sl:
                                trades.append({'dir': direction, 'pnl': -sl_mult*atr/entry*100-fee_pct, 'exit': 'SL'})
                                break
                            if df['high'].iloc[j] >= tp:
                                trades.append({'dir': direction, 'pnl': tp_mult*atr/entry*100-fee_pct, 'exit': 'TP'})
                                break
                        else:
                            if df['high'].iloc[j] >= sl:
                                trades.append({'dir': direction, 'pnl': -sl_mult*atr/entry*100-fee_pct, 'exit': 'SL'})
                                break
                            if df['low'].iloc[j] <= tp:
                                trades.append({'dir': direction, 'pnl': tp_mult*atr/entry*100-fee_pct, 'exit': 'TP'})
                                break
                    else:
                        exit_p = df['close'].iloc[min(i+90, len(df)-1)]
                        pnl = ((exit_p-entry)/entry if direction=='LONG' else (entry-exit_p)/entry)*100-fee_pct
                        trades.append({'dir': direction, 'pnl': pnl, 'exit': 'TIME'})

            in_zone, zone_bars, zone_highs, zone_lows = False, 0, [], []
    return trades

def backtest_trumpsol(df, fee_pct=0.10):
    """TRUMPSOL Contrarian"""
    trades = []
    excluded_hours = [1, 5, 17]

    for i in range(50, len(df) - 15):
        row = df.iloc[i]
        if row['timestamp'].hour in excluded_hours:
            continue

        ret_5m = row['ret_5m']
        vol_ratio = row['vol_ratio_30'] if not pd.isna(row['vol_ratio_30']) else 0
        atr_ratio = row['atr_ratio_30'] if not pd.isna(row['atr_ratio_30']) else 0

        if pd.isna(ret_5m) or abs(ret_5m) < 1.0 or vol_ratio < 1.0 or atr_ratio < 1.1:
            continue

        entry = row['close']
        direction = 'SHORT' if ret_5m >= 1.0 else 'LONG'

        if direction == 'LONG':
            sl, tp = entry * 0.99, entry * 1.015
        else:
            sl, tp = entry * 1.01, entry * 0.985

        for j in range(i+1, min(i+16, len(df))):
            if direction == 'LONG':
                if df['low'].iloc[j] <= sl:
                    trades.append({'dir': direction, 'pnl': -1.0-fee_pct, 'exit': 'SL'})
                    break
                if df['high'].iloc[j] >= tp:
                    trades.append({'dir': direction, 'pnl': 1.5-fee_pct, 'exit': 'TP'})
                    break
            else:
                if df['high'].iloc[j] >= sl:
                    trades.append({'dir': direction, 'pnl': -1.0-fee_pct, 'exit': 'SL'})
                    break
                if df['low'].iloc[j] <= tp:
                    trades.append({'dir': direction, 'pnl': 1.5-fee_pct, 'exit': 'TP'})
                    break
        else:
            exit_p = df['close'].iloc[min(i+15, len(df)-1)]
            pnl = ((exit_p-entry)/entry if direction=='LONG' else (entry-exit_p)/entry)*100-fee_pct
            trades.append({'dir': direction, 'pnl': pnl, 'exit': 'TIME'})
    return trades

def analyze(trades, name, days=3):
    if not trades:
        return {'name': name, 'trades': 0, 'tpd': 0, 'wr': 0, 'pnl': 0, 'dd': 0, 'rdd': 0, 'tp_rate': 0}

    df = pd.DataFrame(trades)
    df['cum'] = df['pnl'].cumsum()
    equity = 100 + df['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    pnl = df['pnl'].sum()

    return {
        'name': name,
        'trades': len(trades),
        'tpd': len(trades)/days,
        'wr': (df['pnl'] > 0).sum() / len(trades) * 100,
        'pnl': pnl,
        'dd': dd,
        'rdd': pnl / abs(dd) if dd != 0 else 0,
        'tp_rate': (df['exit'] == 'TP').sum() / len(trades) * 100
    }

def main():
    print("=" * 80)
    print("72h SIMULATION - ALL STRATEGIES")
    print("=" * 80)

    original = {
        'PIPPIN': {'days': 7, 'trades': 10, 'wr': 50.0, 'pnl': 21.76, 'dd': -1.71, 'rdd': 12.71, 'tpd': 1.43},
        'DOGE': {'days': 32, 'trades': 22, 'wr': 63.6, 'pnl': 5.15, 'dd': -0.48, 'rdd': 10.75, 'tpd': 0.69},
        'TRUMPSOL': {'days': 32, 'trades': 77, 'wr': 68.8, 'pnl': 17.49, 'dd': -3.38, 'rdd': 5.17, 'tpd': 2.41}
    }

    symbols = {'PIPPIN': 'PIPPIN-USDT', 'DOGE': 'DOGE-USDT', 'TRUMPSOL': 'TRUMPSOL-USDT'}

    print("\nDownloading 72h data from BingX...")
    data = {}
    for name, symbol in symbols.items():
        print(f"  {name}...", end=" ", flush=True)
        df = download_bingx_72h(symbol)
        if df is not None:
            df = add_indicators(df)
            data[name] = df
            print(f"{len(df)} candles")
        else:
            print("FAILED")

    results = []
    for name, df in data.items():
        print(f"\n{'='*60}")
        print(f"{name}")
        print(f"{'='*60}")

        if name == 'PIPPIN':
            trades = backtest_pippin(df)
        elif name == 'DOGE':
            trades = backtest_doge(df)
        else:
            trades = backtest_trumpsol(df)

        r = analyze(trades, name)
        results.append(r)
        o = original[name]

        print(f"\n72h Results:                    | Original ({o['days']}d):")
        print(f"  Trades:     {r['trades']:>3} ({r['tpd']:.1f}/day)       | {o['trades']} ({o['tpd']:.1f}/day)")
        print(f"  Win Rate:   {r['wr']:>5.1f}%              | {o['wr']:.1f}%")
        print(f"  TP Rate:    {r['tp_rate']:>5.1f}%              |")
        print(f"  P/L:        {r['pnl']:>+6.2f}%             | {o['pnl']:+.2f}%")
        print(f"  Max DD:     {r['dd']:>6.2f}%             | {o['dd']:.2f}%")
        print(f"  Return/DD:  {r['rdd']:>6.2f}x             | {o['rdd']:.2f}x")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n{'Strategy':<12} {'Trades':<8} {'T/day':<8} {'WR%':<8} {'P/L%':<10} {'MaxDD%':<10} {'R/DD':<8}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<12} {r['trades']:<8} {r['tpd']:<8.1f} {r['wr']:<8.1f} {r['pnl']:<+10.2f} {r['dd']:<10.2f} {r['rdd']:<8.2f}")

    print(f"\n{'--- ORIGINAL BACKTEST ---'}")
    for name, o in original.items():
        print(f"{name:<12} {o['trades']:<8} {o['tpd']:<8.1f} {o['wr']:<8.1f} {o['pnl']:<+10.2f} {o['dd']:<10.2f} {o['rdd']:<8.2f}")

if __name__ == '__main__':
    main()
