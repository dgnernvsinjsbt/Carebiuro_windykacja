"""
72h Simulation for ALL strategies: DOGE, PIPPIN, TRUMPSOL
Compare with original backtest stats
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# ============================================
# DATA DOWNLOAD
# ============================================

def download_bingx_72h(symbol):
    """Download 72h of 1-min data from BingX public API"""
    base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=72)).timestamp() * 1000)

    current_end = end_time

    while current_end > start_time:
        params = {
            "symbol": symbol,
            "interval": "1m",
            "endTime": current_end,
            "limit": 1440
        }

        response = requests.get(base_url, params=params)
        data = response.json()

        if 'data' not in data or not data['data']:
            break

        batch = data['data']
        all_data = batch + all_data

        oldest_ts = int(batch[0]['time'])
        if oldest_ts <= start_time:
            break
        current_end = oldest_ts - 1

    if not all_data:
        return None

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    # Filter to exactly 72h
    cutoff = datetime.now() - timedelta(hours=72)
    df = df[df['timestamp'] >= cutoff]

    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').reset_index(drop=True)

def add_indicators(df):
    """Add all required indicators"""
    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    # EMAs
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volume ratio
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']

    # ATR ratio
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']

    # Body size
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

    # 5-min returns
    df['ret_5m'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100

    return df

# ============================================
# STRATEGY 1: PIPPIN Fresh Crosses
# ============================================

def backtest_pippin(df, fee_pct=0.10):
    """PIPPIN Fresh Crosses + RSI/Body Filter"""
    df = df.copy()

    # EMA crosses
    df['ema9_above_ema21'] = df['ema_9'] > df['ema_21']
    df['cross_up'] = df['ema9_above_ema21'] & ~df['ema9_above_ema21'].shift(1).fillna(False)
    df['cross_down'] = ~df['ema9_above_ema21'] & df['ema9_above_ema21'].shift(1).fillna(True)

    # Count consecutive bars
    df['consecutive_ups'] = 0
    df['consecutive_downs'] = 0

    cons_up = 0
    cons_down = 0
    for i in range(len(df)):
        if df['ema9_above_ema21'].iloc[i]:
            cons_up += 1
            cons_down = 0
        else:
            cons_down += 1
            cons_up = 0
        df.loc[df.index[i], 'consecutive_ups'] = cons_up - 1 if cons_up > 0 else 0
        df.loc[df.index[i], 'consecutive_downs'] = cons_down - 1 if cons_down > 0 else 0

    trades = []

    for i in range(50, len(df) - 120):
        row = df.iloc[i]

        # Fresh cross LONG
        if row['cross_up'] and row['consecutive_ups'] == 0:
            if row['rsi'] >= 55 and row['body_pct'] <= 0.06:
                entry = row['close']
                atr = row['atr']
                sl = entry - 1.5 * atr
                tp = entry + 10 * atr

                # Walk forward
                for j in range(i+1, min(i+121, len(df))):
                    if df['low'].iloc[j] <= sl:
                        pnl = -1.5 * atr / entry * 100 - fee_pct
                        trades.append({'direction': 'LONG', 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                        break
                    if df['high'].iloc[j] >= tp:
                        pnl = 10 * atr / entry * 100 - fee_pct
                        trades.append({'direction': 'LONG', 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                        break
                else:
                    exit_price = df['close'].iloc[min(i+120, len(df)-1)]
                    pnl = (exit_price - entry) / entry * 100 - fee_pct
                    trades.append({'direction': 'LONG', 'pnl': pnl, 'exit': 'TIME', 'bars': 120})

        # Fresh cross SHORT
        if row['cross_down'] and row['consecutive_downs'] == 0:
            if row['rsi'] >= 55 and row['body_pct'] <= 0.06:
                entry = row['close']
                atr = row['atr']
                sl = entry + 1.5 * atr
                tp = entry - 10 * atr

                for j in range(i+1, min(i+121, len(df))):
                    if df['high'].iloc[j] >= sl:
                        pnl = -1.5 * atr / entry * 100 - fee_pct
                        trades.append({'direction': 'SHORT', 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                        break
                    if df['low'].iloc[j] <= tp:
                        pnl = 10 * atr / entry * 100 - fee_pct
                        trades.append({'direction': 'SHORT', 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                        break
                else:
                    exit_price = df['close'].iloc[min(i+120, len(df)-1)]
                    pnl = (entry - exit_price) / entry * 100 - fee_pct
                    trades.append({'direction': 'SHORT', 'pnl': pnl, 'exit': 'TIME', 'bars': 120})

    return trades

# ============================================
# STRATEGY 2: DOGE Volume Zones
# ============================================

def backtest_doge(df, fee_pct=0.10):
    """DOGE Volume Zones - Asia/EU session only"""
    df = df.copy()

    trades = []
    in_zone = False
    zone_bars = 0
    zone_highs = []
    zone_lows = []

    for i in range(50, len(df) - 90):
        row = df.iloc[i]

        # Session filter: Asia/EU (07:00-14:00 UTC)
        hour = row['timestamp'].hour
        if not (7 <= hour < 14):
            in_zone = False
            zone_bars = 0
            zone_highs = []
            zone_lows = []
            continue

        # Volume zone detection
        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0

        if vol_ratio >= 1.5:
            if not in_zone:
                in_zone = True
                zone_bars = 1
                zone_highs = [row['high']]
                zone_lows = [row['low']]
            else:
                zone_bars += 1
                zone_highs.append(row['high'])
                zone_lows.append(row['low'])
        else:
            if in_zone and zone_bars >= 5:
                # Zone ended - classify
                zone_high = max(zone_highs)
                zone_low = min(zone_lows)

                # Check if at local extreme
                lookback = df.iloc[max(0, i-25):i]
                window_low = lookback['low'].min()
                window_high = lookback['high'].max()

                entry = row['close']
                atr = row['atr']

                if zone_low <= window_low * 1.002:  # Accumulation
                    direction = 'LONG'
                    sl = entry - 1.5 * atr
                    tp = entry + 4.0 * atr
                elif zone_high >= window_high * 0.998:  # Distribution
                    direction = 'SHORT'
                    sl = entry + 1.5 * atr
                    tp = entry - 4.0 * atr
                else:
                    in_zone = False
                    zone_bars = 0
                    zone_highs = []
                    zone_lows = []
                    continue

                # Walk forward
                for j in range(i+1, min(i+91, len(df))):
                    if direction == 'LONG':
                        if df['low'].iloc[j] <= sl:
                            pnl = -1.5 * atr / entry * 100 - fee_pct
                            trades.append({'direction': direction, 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                            break
                        if df['high'].iloc[j] >= tp:
                            pnl = 4.0 * atr / entry * 100 - fee_pct
                            trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                            break
                    else:
                        if df['high'].iloc[j] >= sl:
                            pnl = -1.5 * atr / entry * 100 - fee_pct
                            trades.append({'direction': direction, 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                            break
                        if df['low'].iloc[j] <= tp:
                            pnl = 4.0 * atr / entry * 100 - fee_pct
                            trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                            break
                else:
                    exit_price = df['close'].iloc[min(i+90, len(df)-1)]
                    if direction == 'LONG':
                        pnl = (exit_price - entry) / entry * 100 - fee_pct
                    else:
                        pnl = (entry - exit_price) / entry * 100 - fee_pct
                    trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TIME', 'bars': 90})

            in_zone = False
            zone_bars = 0
            zone_highs = []
            zone_lows = []

    return trades

# ============================================
# STRATEGY 3: TRUMPSOL Contrarian
# ============================================

def backtest_trumpsol(df, fee_pct=0.10):
    """TRUMPSOL Contrarian - fade violent moves"""
    df = df.copy()

    # Additional indicators for this strategy
    df['vol_ma_30'] = df['volume'].rolling(30).mean()
    df['vol_ratio_30'] = df['volume'] / df['vol_ma_30']
    df['atr_ma_30'] = df['atr'].rolling(30).mean()
    df['atr_ratio_30'] = df['atr'] / df['atr_ma_30']

    trades = []
    excluded_hours = [1, 5, 17]  # Europe/Warsaw exclusions

    for i in range(50, len(df) - 15):
        row = df.iloc[i]

        # Time filter
        hour = row['timestamp'].hour
        if hour in excluded_hours:
            continue

        ret_5m = row['ret_5m']
        vol_ratio = row['vol_ratio_30'] if not pd.isna(row['vol_ratio_30']) else 0
        atr_ratio = row['atr_ratio_30'] if not pd.isna(row['atr_ratio_30']) else 0

        # Check conditions
        if abs(ret_5m) < 1.0:
            continue
        if vol_ratio < 1.0:
            continue
        if atr_ratio < 1.1:
            continue

        entry = row['close']

        # Contrarian: pump -> SHORT, dump -> LONG
        if ret_5m >= 1.0:
            direction = 'SHORT'
            sl = entry * 1.01  # 1% SL
            tp = entry * 0.985  # 1.5% TP
        else:  # ret_5m <= -1.0
            direction = 'LONG'
            sl = entry * 0.99  # 1% SL
            tp = entry * 1.015  # 1.5% TP

        # Walk forward max 15 bars
        for j in range(i+1, min(i+16, len(df))):
            if direction == 'LONG':
                if df['low'].iloc[j] <= sl:
                    pnl = -1.0 - fee_pct
                    trades.append({'direction': direction, 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                    break
                if df['high'].iloc[j] >= tp:
                    pnl = 1.5 - fee_pct
                    trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                    break
            else:
                if df['high'].iloc[j] >= sl:
                    pnl = -1.0 - fee_pct
                    trades.append({'direction': direction, 'pnl': pnl, 'exit': 'SL', 'bars': j-i})
                    break
                if df['low'].iloc[j] <= tp:
                    pnl = 1.5 - fee_pct
                    trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TP', 'bars': j-i})
                    break
        else:
            exit_price = df['close'].iloc[min(i+15, len(df)-1)]
            if direction == 'LONG':
                pnl = (exit_price - entry) / entry * 100 - fee_pct
            else:
                pnl = (entry - exit_price) / entry * 100 - fee_pct
            trades.append({'direction': direction, 'pnl': pnl, 'exit': 'TIME', 'bars': 15})

    return trades

# ============================================
# ANALYSIS
# ============================================

def analyze_trades(trades, name, days=3):
    """Analyze trade results"""
    if not trades:
        return {
            'name': name,
            'trades': 0,
            'trades_per_day': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'max_dd': 0,
            'return_dd': 0,
            'tp_rate': 0,
            'avg_winner': 0,
            'avg_loser': 0
        }

    df = pd.DataFrame(trades)

    # Equity curve
    df['cum_pnl'] = df['pnl'].cumsum()
    equity = 100 + df['cum_pnl']
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_dd = drawdown.min()

    total_pnl = df['pnl'].sum()
    return_dd = total_pnl / abs(max_dd) if max_dd != 0 else 0

    winners = df[df['pnl'] > 0]
    losers = df[df['pnl'] <= 0]

    return {
        'name': name,
        'trades': len(trades),
        'trades_per_day': len(trades) / days,
        'win_rate': len(winners) / len(trades) * 100,
        'total_pnl': total_pnl,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'tp_rate': (df['exit'] == 'TP').sum() / len(trades) * 100,
        'avg_winner': winners['pnl'].mean() if len(winners) > 0 else 0,
        'avg_loser': losers['pnl'].mean() if len(losers) > 0 else 0
    }

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 80)
    print("72h SIMULATION - ALL STRATEGIES")
    print("=" * 80)

    # Original backtest stats for comparison
    original_stats = {
        'PIPPIN': {'days': 7, 'trades': 10, 'win_rate': 50.0, 'pnl': 21.76, 'max_dd': -1.71, 'return_dd': 12.71},
        'DOGE': {'days': 32, 'trades': 22, 'win_rate': 63.6, 'pnl': 5.15, 'max_dd': -0.48, 'return_dd': 10.75},
        'TRUMPSOL': {'days': 32, 'trades': 77, 'win_rate': 68.8, 'pnl': 17.49, 'max_dd': -3.38, 'return_dd': 5.17}
    }

    # Download data
    print("\nDownloading 72h data from BingX...")

    symbols = {
        'PIPPIN': 'PIPPIN-USDT',
        'DOGE': 'DOGE-USDT',
        'TRUMPSOL': 'TRUMPSOL-USDT'
    }

    data = {}
    for name, symbol in symbols.items():
        print(f"  {name}...", end=" ")
        df = download_bingx_72h(symbol)
        if df is not None:
            df = add_indicators(df)
            data[name] = df
            print(f"{len(df)} candles")
        else:
            print("FAILED")

    print()

    # Run backtests
    results = []

    for name, df in data.items():
        print(f"\n{'='*60}")
        print(f"STRATEGY: {name}")
        print(f"{'='*60}")

        if name == 'PIPPIN':
            trades = backtest_pippin(df)
        elif name == 'DOGE':
            trades = backtest_doge(df)
        elif name == 'TRUMPSOL':
            trades = backtest_trumpsol(df)

        result = analyze_trades(trades, name, days=3)
        results.append(result)

        orig = original_stats[name]
        orig_tpd = orig['trades'] / orig['days']

        print(f"\n72h Results:")
        print(f"  Trades:        {result['trades']} ({result['trades_per_day']:.1f}/day)")
        print(f"  Win Rate:      {result['win_rate']:.1f}%")
        print(f"  TP Rate:       {result['tp_rate']:.1f}%")
        print(f"  Total P/L:     {result['total_pnl']:+.2f}%")
        print(f"  Max DD:        {result['max_dd']:.2f}%")
        print(f"  Return/DD:     {result['return_dd']:.2f}x")
        print(f"  Avg Winner:    {result['avg_winner']:+.2f}%")
        print(f"  Avg Loser:     {result['avg_loser']:.2f}%")

        print(f"\nOriginal Backtest ({orig['days']} days):")
        print(f"  Trades:        {orig['trades']} ({orig_tpd:.1f}/day)")
        print(f"  Win Rate:      {orig['win_rate']:.1f}%")
        print(f"  Total P/L:     {orig['pnl']:+.2f}%")
        print(f"  Max DD:        {orig['max_dd']:.2f}%")
        print(f"  Return/DD:     {orig['return_dd']:.2f}x")

        # Comparison
        print(f"\nComparison (72h vs Original):")
        tpd_diff = result['trades_per_day'] - orig_tpd
        wr_diff = result['win_rate'] - orig['win_rate']
        print(f"  Trades/day:    {tpd_diff:+.1f} ({'more' if tpd_diff > 0 else 'less'} active)")
        print(f"  Win Rate:      {wr_diff:+.1f}pp")

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)

    print(f"\n{'Strategy':<12} {'Trades':<8} {'TPD':<8} {'WR%':<8} {'P/L%':<10} {'MaxDD%':<10} {'R/DD':<8}")
    print("-" * 70)

    for r in results:
        print(f"{r['name']:<12} {r['trades']:<8} {r['trades_per_day']:<8.1f} {r['win_rate']:<8.1f} {r['total_pnl']:<+10.2f} {r['max_dd']:<10.2f} {r['return_dd']:<8.2f}")

    print("\nOriginal Backtest (for comparison):")
    print(f"{'Strategy':<12} {'Trades':<8} {'TPD':<8} {'WR%':<8} {'P/L%':<10} {'MaxDD%':<10} {'R/DD':<8}")
    print("-" * 70)

    for name, orig in original_stats.items():
        tpd = orig['trades'] / orig['days']
        print(f"{name:<12} {orig['trades']:<8} {tpd:<8.1f} {orig['win_rate']:<8.1f} {orig['pnl']:<+10.2f} {orig['max_dd']:<10.2f} {orig['return_dd']:<8.2f}")

if __name__ == '__main__':
    main()
