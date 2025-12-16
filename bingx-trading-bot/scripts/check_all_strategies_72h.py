#!/usr/bin/env python3
"""
Check last 72 hours for ALL strategy signals and calculate P/L
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

async def fetch_data_72h(client, symbol):
    """Fetch 72h+ data and calculate indicators"""
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)

    # Fetch in chunks (BingX limit is 1440 per call)
    all_klines = []

    # Need ~4500 candles for 72h + buffer
    for i in range(4):
        chunk_end = end_time - (i * 1440 * 60 * 1000)
        chunk_start = chunk_end - (1440 * 60 * 1000)

        klines = await client.get_klines(
            symbol=symbol,
            interval='1m',
            start_time=chunk_start,
            end_time=chunk_end,
            limit=1440
        )
        all_klines.extend(klines)
        await asyncio.sleep(0.1)  # Rate limit

    # Deduplicate and sort
    df = pd.DataFrame(all_klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    cutoff = (now - timedelta(hours=72)).replace(tzinfo=None)
    df_72h = df[df['timestamp'] >= cutoff].copy()

    return df, df_72h

def check_signal_outcome(df, entry_time, entry_price, stop_loss, take_profit, max_bars, direction='LONG'):
    """Check if a signal hit TP, SL, or timed out"""
    future = df[df['timestamp'] > entry_time].head(max_bars)

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

        if outcome == 'OPEN' and len(future) >= max_bars:
            outcome = 'TIME_EXIT'
            exit_price = future.iloc[-1]['close']
            exit_time = future.iloc[-1]['timestamp']
            if direction == 'LONG':
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10

    return outcome, exit_price, exit_time, pnl_pct

async def check_fartcoin_long(client):
    """Multi-timeframe LONG strategy"""
    df, df_72h = await fetch_data_72h(client, 'FARTCOIN-USDT')

    # Build 5-min candles
    df_5min = df.resample('5min', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    calc_5min = IndicatorCalculator(df_5min)
    df_5min = calc_5min.add_all_indicators()

    signals = []

    for i in range(1, len(df_72h)):
        current = df_72h.iloc[i]

        if pd.notna(current['atr']) and pd.notna(current['rsi']) and pd.notna(current['vol_ratio']):
            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bullish = current['close'] > current['open']

            upper_wick = current['high'] - max(current['open'], current['close'])
            lower_wick = min(current['open'], current['close']) - current['low']
            max_wick = max(upper_wick, lower_wick)
            wick_ratio = max_wick / body if body > 0 else 999

            if (body_pct > 1.2 and current['vol_ratio'] > 3.0 and
                wick_ratio < 0.35 and is_bullish and 45 <= current['rsi'] <= 75):

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
                                df, current['timestamp'], entry_price, stop_loss, take_profit, 1440, 'LONG'
                            )

                            signals.append({
                                'timestamp': current['timestamp'],
                                'entry': entry_price,
                                'outcome': outcome,
                                'pnl_pct': pnl_pct
                            })

    return signals

async def check_fartcoin_short(client):
    """Trend Distance SHORT strategy"""
    df, df_72h = await fetch_data_72h(client, 'FARTCOIN-USDT')

    signals = []

    for i in range(1, len(df_72h)):
        current = df_72h.iloc[i]

        if (pd.notna(current['atr']) and pd.notna(current['rsi']) and
            pd.notna(current['sma_50']) and pd.notna(current['sma_200']) and
            pd.notna(current['vol_ratio'])):

            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bearish = current['close'] < current['open']

            upper_wick = current['high'] - max(current['open'], current['close'])
            lower_wick = min(current['open'], current['close']) - current['low']
            max_wick = max(upper_wick, lower_wick)
            wick_ratio = max_wick / body if body > 0 else 999

            below_50 = current['close'] < current['sma_50']
            below_200 = current['close'] < current['sma_200']
            distance_from_50 = ((current['sma_50'] - current['close']) / current['sma_50']) * 100

            if (body_pct > 1.2 and current['vol_ratio'] > 3.0 and
                wick_ratio < 0.35 and is_bearish and 25 <= current['rsi'] <= 55 and
                below_50 and below_200 and distance_from_50 >= 2.0):

                entry_price = current['close']
                stop_loss = entry_price + (3.0 * current['atr'])
                take_profit = entry_price - (15.0 * current['atr'])

                outcome, exit_price, exit_time, pnl_pct = check_signal_outcome(
                    df, current['timestamp'], entry_price, stop_loss, take_profit, 1440, 'SHORT'
                )

                signals.append({
                    'timestamp': current['timestamp'],
                    'entry': entry_price,
                    'outcome': outcome,
                    'pnl_pct': pnl_pct
                })

    return signals

async def check_moodeng_rsi(client):
    """MOODENG RSI Momentum strategy"""
    df, df_72h = await fetch_data_72h(client, 'MOODENG-USDT')

    signals = []

    for i in range(1, len(df_72h)):
        idx = df_72h.index[i]
        prev_idx = df_72h.index[i-1]
        current = df_72h.loc[idx]
        prev = df_72h.loc[prev_idx]

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
                    df, current['timestamp'], entry_price, stop_loss, take_profit, 60, 'LONG'
                )

                signals.append({
                    'timestamp': current['timestamp'],
                    'entry': entry_price,
                    'outcome': outcome,
                    'pnl_pct': pnl_pct
                })

    return signals

async def check_volume_zones(client, symbol, config):
    """Generic volume zones strategy"""
    df, df_72h = await fetch_data_72h(client, symbol)

    signals = []

    for i in range(20, len(df_72h)):
        current = df_72h.iloc[i]

        if pd.notna(current['vol_ratio']) and pd.notna(current['atr']):
            hour_utc = current['timestamp'].hour

            if config['session_filter'] == 'overnight':
                in_session = hour_utc >= 21 or hour_utc < 7
            elif config['session_filter'] == 'asia_eu':
                in_session = 0 <= hour_utc < 14
            else:
                in_session = True

            if not in_session:
                continue

            lookback = df_72h.iloc[max(0, i-10):i+1]

            consecutive = 0
            for j in range(len(lookback)-1, -1, -1):
                if lookback.iloc[j]['vol_ratio'] >= config['volume_threshold']:
                    consecutive += 1
                else:
                    break

            if consecutive >= config['min_zone_bars']:
                window = df_72h.iloc[max(0, i-config['lookback_bars']):min(len(df_72h), i+config['lookback_bars'])]
                is_local_low = current['low'] <= window['low'].quantile(0.2)
                is_local_high = current['high'] >= window['high'].quantile(0.8)

                direction = None
                if is_local_low:
                    direction = 'LONG'
                elif is_local_high:
                    direction = 'SHORT'

                if direction:
                    entry_price = current['close']

                    if config.get('sl_type') == 'fixed_pct':
                        sl_distance = entry_price * (config['sl_value'] / 100)
                    else:
                        sl_distance = config['stop_atr_mult'] * current['atr']

                    if direction == 'LONG':
                        stop_loss = entry_price - sl_distance
                        take_profit = entry_price + (config['rr_ratio'] * sl_distance)
                    else:
                        stop_loss = entry_price + sl_distance
                        take_profit = entry_price - (config['rr_ratio'] * sl_distance)

                    outcome, exit_price, exit_time, pnl_pct = check_signal_outcome(
                        df, current['timestamp'], entry_price, stop_loss, take_profit,
                        config['max_hold_bars'], direction
                    )

                    signals.append({
                        'timestamp': current['timestamp'],
                        'direction': direction,
                        'entry': entry_price,
                        'outcome': outcome,
                        'pnl_pct': pnl_pct
                    })

    return signals

async def main():
    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 80)
    print("CHECKING LAST 72 HOURS FOR ALL STRATEGIES")
    print("=" * 80)
    print(f"Analysis time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Period: {(datetime.now(timezone.utc) - timedelta(hours=72)).strftime('%Y-%m-%d %H:%M')} to now")
    print()

    all_results = []

    # 1. FARTCOIN LONG
    print("📊 FARTCOIN - Multi-Timeframe LONG")
    print("-" * 80)
    signals = await check_fartcoin_long(client)
    all_results.append(('FARTCOIN LONG', signals))
    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['outcome'] != 'OPEN')
        wins = len([s for s in signals if s['outcome'] == 'TAKE_PROFIT'])
        losses = len([s for s in signals if s['outcome'] == 'STOP_LOSS'])
        print(f"  Signals: {len(signals)}, Wins: {wins}, Losses: {losses}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            print(f"    {s['timestamp'].strftime('%m-%d %H:%M')} @ ${s['entry']:.4f} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 2. FARTCOIN SHORT
    print("📊 FARTCOIN - Trend Distance SHORT")
    print("-" * 80)
    signals = await check_fartcoin_short(client)
    all_results.append(('FARTCOIN SHORT', signals))
    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['outcome'] != 'OPEN')
        wins = len([s for s in signals if s['outcome'] == 'TAKE_PROFIT'])
        losses = len([s for s in signals if s['outcome'] == 'STOP_LOSS'])
        print(f"  Signals: {len(signals)}, Wins: {wins}, Losses: {losses}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            print(f"    {s['timestamp'].strftime('%m-%d %H:%M')} @ ${s['entry']:.4f} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 3. MOODENG RSI
    print("📊 MOODENG - RSI Momentum")
    print("-" * 80)
    signals = await check_moodeng_rsi(client)
    all_results.append(('MOODENG RSI', signals))
    if len(signals) == 0:
        print("  No signals")
    else:
        total_pnl = sum(s['pnl_pct'] for s in signals if s['outcome'] != 'OPEN')
        wins = len([s for s in signals if s['outcome'] == 'TAKE_PROFIT'])
        losses = len([s for s in signals if s['outcome'] == 'STOP_LOSS'])
        print(f"  Signals: {len(signals)}, Wins: {wins}, Losses: {losses}, P/L: {total_pnl:+.2f}%")
        for s in signals:
            print(f"    {s['timestamp'].strftime('%m-%d %H:%M')} @ ${s['entry']:.6f} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
    print()

    # 4-7. Volume Zones
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
        signals = await check_volume_zones(client, symbol, config)
        all_results.append((name, signals))

        if len(signals) == 0:
            print("  No signals")
        else:
            total_pnl = sum(s['pnl_pct'] for s in signals if s['outcome'] != 'OPEN')
            wins = len([s for s in signals if s['outcome'] == 'TAKE_PROFIT'])
            losses = len([s for s in signals if s['outcome'] == 'STOP_LOSS'])
            print(f"  Signals: {len(signals)}, Wins: {wins}, Losses: {losses}, P/L: {total_pnl:+.2f}%")
            for s in signals:
                dir_label = s.get('direction', 'LONG')
                print(f"    {s['timestamp'].strftime('%m-%d %H:%M')} {dir_label} @ ${s['entry']:.4f} → {s['outcome']}: {s['pnl_pct']:+.2f}%")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY - 72 HOURS ALL STRATEGIES")
    print("=" * 80)

    grand_total_signals = 0
    grand_total_pnl = 0
    grand_wins = 0
    grand_losses = 0

    for strategy_name, signals in all_results:
        if len(signals) > 0:
            pnl = sum(s['pnl_pct'] for s in signals if s['outcome'] != 'OPEN')
            wins = len([s for s in signals if s['outcome'] == 'TAKE_PROFIT'])
            losses = len([s for s in signals if s['outcome'] == 'STOP_LOSS'])
            grand_total_signals += len(signals)
            grand_total_pnl += pnl
            grand_wins += wins
            grand_losses += losses
            win_rate = (wins / len(signals) * 100) if len(signals) > 0 else 0
            print(f"{strategy_name:25s}: {len(signals):3d} trades, {wins:2d}W/{losses:2d}L ({win_rate:4.1f}%), {pnl:+7.2f}%")

    print("-" * 80)
    overall_win_rate = (grand_wins / grand_total_signals * 100) if grand_total_signals > 0 else 0
    print(f"{'GRAND TOTAL':25s}: {grand_total_signals:3d} trades, {grand_wins:2d}W/{grand_losses:2d}L ({overall_win_rate:4.1f}%), {grand_total_pnl:+7.2f}%")
    print("=" * 80)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
