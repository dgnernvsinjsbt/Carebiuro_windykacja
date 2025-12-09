#!/usr/bin/env python3
"""
Check last 24 hours for ALL strategy signals and calculate P/L
"""

import asyncio
import yaml
import pandas as pd
from datetime import datetime, timedelta, timezone
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator

# Load credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def fetch_and_analyze(client, symbol):
    """Fetch data and calculate indicators"""
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(hours=25)).timestamp() * 1000)

    klines = await client.get_klines(
        symbol=symbol,
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1500
    )

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    cutoff = (now - timedelta(hours=24)).replace(tzinfo=None)
    df_24h = df[df['timestamp'] >= cutoff].copy()

    return df, df_24h

def check_signal_outcome(df, entry_time, entry_price, stop_loss, take_profit, max_bars):
    """Check if a signal hit TP, SL, or timed out"""
    future = df[df['timestamp'] > entry_time].head(max_bars)

    outcome = 'OPEN'
    exit_price = None
    exit_time = None
    pnl_pct = 0

    if len(future) > 0:
        for _, bar in future.iterrows():
            if bar['low'] <= stop_loss:
                outcome = 'STOP_LOSS'
                exit_price = stop_loss
                exit_time = bar['timestamp']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                break
            if bar['high'] >= take_profit:
                outcome = 'TAKE_PROFIT'
                exit_price = take_profit
                exit_time = bar['timestamp']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                break

        if outcome == 'OPEN' and len(future) >= max_bars:
            outcome = 'TIME_EXIT'
            exit_price = future.iloc[-1]['close']
            exit_time = future.iloc[-1]['timestamp']
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10

    return outcome, exit_price, exit_time, pnl_pct

async def check_fartcoin_long(client):
    """Multi-timeframe LONG strategy"""
    df, df_24h = await fetch_and_analyze(client, 'FARTCOIN-USDT')

    # Build 5-min candles
    df_full = df.copy()
    df_5min = df_full.resample('5min', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    calc_5min = IndicatorCalculator(df_5min)
    df_5min = calc_5min.add_all_indicators()

    signals = []

    for i in range(1, len(df_24h)):
        current = df_24h.iloc[i]

        if pd.notna(current['atr']) and pd.notna(current['rsi']) and pd.notna(current['vol_ratio']):
            # Explosive bullish candle
            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bullish = current['close'] > current['open']

            upper_wick = current['high'] - max(current['open'], current['close'])
            lower_wick = min(current['open'], current['close']) - current['low']
            max_wick = max(upper_wick, lower_wick)
            wick_ratio = max_wick / body if body > 0 else 999

            if (body_pct > 1.2 and current['vol_ratio'] > 3.0 and
                wick_ratio < 0.35 and is_bullish and 45 <= current['rsi'] <= 75):

                # Check 5-min filter
                current_5min_time = current['timestamp'].replace(second=0, microsecond=0)
                current_5min_time = current_5min_time - timedelta(minutes=current_5min_time.minute % 5)
                current_5min = df_5min[df_5min['timestamp'] == current_5min_time]

                if len(current_5min) > 0:
                    c5 = current_5min.iloc[0]
                    if (pd.notna(c5['rsi']) and pd.notna(c5['sma_50']) and
                        c5['rsi'] > 57 and c5['close'] > c5['sma_50']):

                        distance_pct = ((c5['close'] - c5['sma_50']) / c5['sma_50']) * 100
                        if distance_pct > 0.6:
                            entry_price = current['close']
                            stop_loss = entry_price - (3.0 * current['atr'])
                            take_profit = entry_price + (12.0 * current['atr'])

                            outcome, exit_price, exit_time, pnl_pct = check_signal_outcome(
                                df_full, current['timestamp'], entry_price, stop_loss, take_profit, 1440
                            )

                            signals.append({
                                'symbol': 'FARTCOIN-USDT',
                                'strategy': 'Multi-TF LONG',
                                'timestamp': current['timestamp'],
                                'entry': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'outcome': outcome,
                                'exit_price': exit_price,
                                'exit_time': exit_time,
                                'pnl_pct': pnl_pct
                            })

    return signals

async def check_fartcoin_short(client):
    """Trend Distance SHORT strategy"""
    df, df_24h = await fetch_and_analyze(client, 'FARTCOIN-USDT')

    signals = []

    for i in range(1, len(df_24h)):
        current = df_24h.iloc[i]

        if (pd.notna(current['atr']) and pd.notna(current['rsi']) and
            pd.notna(current['sma_50']) and pd.notna(current['sma_200']) and
            pd.notna(current['vol_ratio'])):

            # Explosive bearish candle
            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bearish = current['close'] < current['open']

            upper_wick = current['high'] - max(current['open'], current['close'])
            lower_wick = min(current['open'], current['close']) - current['low']
            max_wick = max(upper_wick, lower_wick)
            wick_ratio = max_wick / body if body > 0 else 999

            # Strong downtrend
            below_50 = current['close'] < current['sma_50']
            below_200 = current['close'] < current['sma_200']
            distance_from_50 = ((current['sma_50'] - current['close']) / current['sma_50']) * 100

            if (body_pct > 1.2 and current['vol_ratio'] > 3.0 and
                wick_ratio < 0.35 and is_bearish and 25 <= current['rsi'] <= 55 and
                below_50 and below_200 and distance_from_50 >= 2.0):

                entry_price = current['close']
                stop_loss = entry_price + (3.0 * current['atr'])
                take_profit = entry_price - (15.0 * current['atr'])

                # For SHORT: check if high hits SL or low hits TP
                future = df[df['timestamp'] > current['timestamp']].head(1440)

                outcome = 'OPEN'
                exit_price = None
                exit_time = None
                pnl_pct = 0

                if len(future) > 0:
                    for _, bar in future.iterrows():
                        if bar['high'] >= stop_loss:
                            outcome = 'STOP_LOSS'
                            exit_price = stop_loss
                            exit_time = bar['timestamp']
                            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10  # SHORT P/L
                            break
                        if bar['low'] <= take_profit:
                            outcome = 'TAKE_PROFIT'
                            exit_price = take_profit
                            exit_time = bar['timestamp']
                            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
                            break

                    if outcome == 'OPEN' and len(future) >= 1440:
                        outcome = 'TIME_EXIT'
                        exit_price = future.iloc[-1]['close']
                        exit_time = future.iloc[-1]['timestamp']
                        pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10

                signals.append({
                    'symbol': 'FARTCOIN-USDT',
                    'strategy': 'Trend Distance SHORT',
                    'timestamp': current['timestamp'],
                    'entry': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'exit_time': exit_time,
                    'pnl_pct': pnl_pct
                })

    return signals

async def check_volume_zones(client, symbol, strategy_name, config):
    """Generic volume zones strategy"""
    df, df_24h = await fetch_and_analyze(client, symbol)

    signals = []

    for i in range(20, len(df_24h)):
        current = df_24h.iloc[i]

        if pd.notna(current['vol_ratio']) and pd.notna(current['atr']):
            # Check session filter
            hour_utc = current['timestamp'].hour

            if config['session_filter'] == 'overnight':
                in_session = hour_utc >= 21 or hour_utc < 7
            elif config['session_filter'] == 'asia_eu':
                in_session = 0 <= hour_utc < 14
            else:
                in_session = True

            if not in_session:
                continue

            # Look back for volume zone
            lookback = df_24h.iloc[max(0, i-10):i+1]

            consecutive = 0
            for j in range(len(lookback)-1, -1, -1):
                if lookback.iloc[j]['vol_ratio'] >= config['volume_threshold']:
                    consecutive += 1
                else:
                    break

            if consecutive >= config['min_zone_bars']:
                # Check for local extreme
                window = df_24h.iloc[max(0, i-config['lookback_bars']):min(len(df_24h), i+config['lookback_bars'])]
                is_local_low = current['low'] <= window['low'].quantile(0.2)
                is_local_high = current['high'] >= window['high'].quantile(0.8)

                # Determine direction
                direction = None
                if is_local_low:
                    direction = 'LONG'
                elif is_local_high:
                    direction = 'SHORT'

                if direction:
                    entry_price = current['close']

                    # Calculate SL/TP based on config
                    if config.get('sl_type') == 'fixed_pct':
                        sl_distance = entry_price * (config['sl_value'] / 100)
                    else:
                        sl_distance = config['stop_atr_mult'] * current['atr']

                    if direction == 'LONG':
                        stop_loss = entry_price - sl_distance
                        take_profit = entry_price + (config['rr_ratio'] * sl_distance)
                    else:  # SHORT
                        stop_loss = entry_price + sl_distance
                        take_profit = entry_price - (config['rr_ratio'] * sl_distance)

                    # Check outcome
                    future = df[df['timestamp'] > current['timestamp']].head(config['max_hold_bars'])

                    outcome = 'OPEN'
                    exit_price = None
                    exit_time = None
                    pnl_pct = 0

                    if len(future) > 0:
                        for _, bar in future.iterrows():
                            if direction == 'LONG':
                                if bar['low'] <= stop_loss:
                                    outcome = 'STOP_LOSS'
                                    exit_price = stop_loss
                                    exit_time = bar['timestamp']
                                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                                    break
                                if bar['high'] >= take_profit:
                                    outcome = 'TAKE_PROFIT'
                                    exit_price = take_profit
                                    exit_time = bar['timestamp']
                                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                                    break
                            else:  # SHORT
                                if bar['high'] >= stop_loss:
                                    outcome = 'STOP_LOSS'
                                    exit_price = stop_loss
                                    exit_time = bar['timestamp']
                                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
                                    break
                                if bar['low'] <= take_profit:
                                    outcome = 'TAKE_PROFIT'
                                    exit_price = take_profit
                                    exit_time = bar['timestamp']
                                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
                                    break

                        if outcome == 'OPEN' and len(future) >= config['max_hold_bars']:
                            outcome = 'TIME_EXIT'
                            exit_price = future.iloc[-1]['close']
                            exit_time = future.iloc[-1]['timestamp']
                            if direction == 'LONG':
                                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                            else:
                                pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10

                    signals.append({
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'timestamp': current['timestamp'],
                        'direction': direction,
                        'entry': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'outcome': outcome,
                        'exit_price': exit_price,
                        'exit_time': exit_time,
                        'pnl_pct': pnl_pct,
                        'vol_ratio': current['vol_ratio'],
                        'consecutive_bars': consecutive
                    })

    return signals

async def main():
    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 80)
    print("CHECKING LAST 24 HOURS FOR ALL STRATEGIES")
    print("=" * 80)
    print(f"Analysis time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    all_results = []

    # 1. FARTCOIN Multi-TF LONG
    print("📊 FARTCOIN - Multi-Timeframe LONG")
    print("-" * 80)
    signals = await check_fartcoin_long(client)
    all_results.append(('FARTCOIN LONG', signals))

    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['exit_price'])
        print(f"  Signals: {len(signals)}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            if s['exit_price']:
                print(f"    {s['timestamp'].strftime('%H:%M')} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 2. FARTCOIN Trend Distance SHORT
    print("📊 FARTCOIN - Trend Distance SHORT")
    print("-" * 80)
    signals = await check_fartcoin_short(client)
    all_results.append(('FARTCOIN SHORT', signals))

    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['exit_price'])
        print(f"  Signals: {len(signals)}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            if s['exit_price']:
                print(f"    {s['timestamp'].strftime('%H:%M')} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 3. MOODENG RSI (already have this, use existing function)
    print("📊 MOODENG - RSI Momentum")
    print("-" * 80)
    df, df_24h = await fetch_and_analyze(client, 'MOODENG-USDT')
    signals = []

    for i in range(1, len(df_24h)):
        idx = df_24h.index[i]
        prev_idx = df_24h.index[i-1]
        current = df_24h.loc[idx]
        prev = df_24h.loc[prev_idx]

        if pd.notna(prev['rsi']) and pd.notna(current['rsi']) and pd.notna(current['sma_20']) and pd.notna(current['atr']):
            rsi_cross = prev['rsi'] < 55 and current['rsi'] >= 55
            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bullish = current['close'] > current['open']
            strong_body = body_pct > 0.5
            above_sma = current['close'] > current['sma_20']

            if rsi_cross and is_bullish and strong_body and above_sma:
                entry_price = current['close']
                stop_loss = entry_price - (1.0 * current['atr'])
                take_profit = entry_price + (4.0 * current['atr'])

                outcome, exit_price, exit_time, pnl_pct = check_signal_outcome(
                    df, current['timestamp'], entry_price, stop_loss, take_profit, 60
                )

                signals.append({
                    'symbol': 'MOODENG-USDT',
                    'strategy': 'RSI Momentum',
                    'timestamp': current['timestamp'],
                    'entry': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'exit_time': exit_time,
                    'pnl_pct': pnl_pct
                })

    all_results.append(('MOODENG RSI', signals))

    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['exit_price'])
        print(f"  Signals: {len(signals)}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            if s['exit_price']:
                print(f"    {s['timestamp'].strftime('%H:%M')} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 4-7. Volume Zones strategies
    volume_configs = [
        ('DOGE-USDT', 'DOGE Volume Zones', {
            'volume_threshold': 1.5, 'min_zone_bars': 5, 'lookback_bars': 20,
            'stop_atr_mult': 2.0, 'rr_ratio': 2.0, 'max_hold_bars': 90,
            'session_filter': 'overnight'
        }),
        ('1000PEPE-USDT', 'PEPE Volume Zones', {
            'volume_threshold': 1.5, 'min_zone_bars': 5, 'lookback_bars': 20,
            'stop_atr_mult': 1.0, 'rr_ratio': 2.0, 'max_hold_bars': 90,
            'session_filter': 'overnight'
        }),
        ('TRUMPSOL-USDT', 'TRUMP Volume Zones', {
            'volume_threshold': 1.5, 'min_zone_bars': 5, 'lookback_bars': 20,
            'sl_type': 'fixed_pct', 'sl_value': 0.5, 'rr_ratio': 4.0, 'max_hold_bars': 90,
            'session_filter': 'overnight'
        }),
        ('UNI-USDT', 'UNI Volume Zones', {
            'volume_threshold': 1.3, 'min_zone_bars': 3, 'lookback_bars': 20,
            'stop_atr_mult': 1.0, 'rr_ratio': 4.0, 'max_hold_bars': 90,
            'session_filter': 'asia_eu'
        }),
    ]

    for symbol, name, config in volume_configs:
        print(f"📊 {name}")
        print("-" * 80)
        signals = await check_volume_zones(client, symbol, name, config)
        all_results.append((name, signals))

        if len(signals) == 0:
            print("  No signals")
        else:
            total_pnl = sum(s['pnl_pct'] for s in signals if s['exit_price'])
            print(f"  Signals: {len(signals)}, P/L: {total_pnl:+.2f}%")
            for s in signals:
                if s['exit_price']:
                    dir_label = s.get('direction', 'LONG')
                    print(f"    {s['timestamp'].strftime('%H:%M')} {dir_label} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY - ALL STRATEGIES")
    print("=" * 80)

    grand_total_signals = 0
    grand_total_pnl = 0

    for strategy_name, signals in all_results:
        if len(signals) > 0:
            pnl = sum(s['pnl_pct'] for s in signals if s['exit_price'])
            closed = len([s for s in signals if s['exit_price']])
            grand_total_signals += len(signals)
            grand_total_pnl += pnl
            print(f"{strategy_name:30s}: {len(signals):2d} signals, {closed:2d} closed, {pnl:+6.2f}%")

    print("-" * 80)
    print(f"{'TOTAL':30s}: {grand_total_signals:2d} signals, P/L: {grand_total_pnl:+6.2f}%")
    print("=" * 80)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
