#!/usr/bin/env python3
"""
Check last 24 hours for all strategy signals and calculate P/L
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

async def check_moodeng_signals(client):
    """Check MOODENG RSI strategy signals"""

    # Fetch last 24h + extra for indicators
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(hours=25)).timestamp() * 1000)

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1500
    )

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Get last 24h only
    cutoff = (now - timedelta(hours=24)).replace(tzinfo=None)
    df_24h = df[df['timestamp'] >= cutoff].copy()

    # Find signals
    signals = []

    for i in range(1, len(df_24h)):
        idx = df_24h.index[i]
        prev_idx = df_24h.index[i-1]

        current = df_24h.loc[idx]
        prev = df_24h.loc[prev_idx]

        # MOODENG strategy conditions
        if pd.notna(prev['rsi']) and pd.notna(current['rsi']) and pd.notna(current['sma_20']) and pd.notna(current['atr']):
            # RSI crosses above 55
            rsi_cross = prev['rsi'] < 55 and current['rsi'] >= 55

            # Bullish candle with body > 0.5%
            body = abs(current['close'] - current['open'])
            body_pct = (body / current['open']) * 100
            is_bullish = current['close'] > current['open']
            strong_body = body_pct > 0.5

            # Price above SMA(20)
            above_sma = current['close'] > current['sma_20']

            if rsi_cross and is_bullish and strong_body and above_sma:
                entry_price = current['close']
                stop_loss = entry_price - (1.0 * current['atr'])
                take_profit = entry_price + (4.0 * current['atr'])

                # Check outcome
                future = df[df['timestamp'] > current['timestamp']].head(60)  # Max 60 bars

                outcome = 'OPEN'
                exit_price = None
                exit_time = None
                pnl_pct = 0

                if len(future) > 0:
                    for _, bar in future.iterrows():
                        # Check SL
                        if bar['low'] <= stop_loss:
                            outcome = 'STOP_LOSS'
                            exit_price = stop_loss
                            exit_time = bar['timestamp']
                            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10  # 0.10% fees
                            break
                        # Check TP
                        if bar['high'] >= take_profit:
                            outcome = 'TAKE_PROFIT'
                            exit_price = take_profit
                            exit_time = bar['timestamp']
                            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                            break

                    # Time exit if still open after 60 bars
                    if outcome == 'OPEN' and len(future) >= 60:
                        outcome = 'TIME_EXIT'
                        exit_price = future.iloc[-1]['close']
                        exit_time = future.iloc[-1]['timestamp']
                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10

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
                    'pnl_pct': pnl_pct,
                    'rsi': current['rsi']
                })

    return signals

async def check_uni_signals(client):
    """Check UNI Volume Zones strategy signals"""

    # Fetch last 24h + extra for indicators
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(hours=25)).timestamp() * 1000)

    klines = await client.get_klines(
        symbol='UNI-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1500
    )

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Get last 24h only
    cutoff = (now - timedelta(hours=24)).replace(tzinfo=None)
    df_24h = df[df['timestamp'] >= cutoff].copy()

    # Find signals
    signals = []

    for i in range(20, len(df_24h)):  # Need lookback for local extreme
        idx = df_24h.index[i]
        current = df_24h.loc[idx]

        if pd.notna(current['vol_ratio']) and pd.notna(current['atr']):
            # Look back to find volume zone
            lookback = df_24h.iloc[max(0, i-10):i+1]

            # Count consecutive elevated volume bars ending at current
            consecutive = 0
            for j in range(len(lookback)-1, -1, -1):
                if lookback.iloc[j]['vol_ratio'] >= 1.3:
                    consecutive += 1
                else:
                    break

            # Need at least 3 consecutive bars
            if consecutive >= 3:
                # Check if at local low (accumulation)
                window = df_24h.iloc[max(0, i-20):min(len(df_24h), i+20)]
                is_local_low = current['low'] <= window['low'].quantile(0.2)

                if is_local_low:
                    entry_price = current['close']
                    stop_loss = entry_price - (2.0 * current['atr'])
                    take_profit = entry_price + (4.0 * (entry_price - stop_loss))  # 4:1 R:R

                    # Check outcome
                    future = df[df['timestamp'] > current['timestamp']].head(90)

                    outcome = 'OPEN'
                    exit_price = None
                    exit_time = None
                    pnl_pct = 0

                    if len(future) > 0:
                        for _, bar in future.iterrows():
                            # Check SL
                            if bar['low'] <= stop_loss:
                                outcome = 'STOP_LOSS'
                                exit_price = stop_loss
                                exit_time = bar['timestamp']
                                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                                break
                            # Check TP
                            if bar['high'] >= take_profit:
                                outcome = 'TAKE_PROFIT'
                                exit_price = take_profit
                                exit_time = bar['timestamp']
                                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
                                break

                        # Time exit
                        if outcome == 'OPEN' and len(future) >= 90:
                            outcome = 'TIME_EXIT'
                            exit_price = future.iloc[-1]['close']
                            exit_time = future.iloc[-1]['timestamp']
                            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10

                    signals.append({
                        'symbol': 'UNI-USDT',
                        'strategy': 'Volume Zones',
                        'timestamp': current['timestamp'],
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
    print("CHECKING LAST 24 HOURS FOR TRADE SIGNALS")
    print("=" * 80)
    print(f"Analysis time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    # Check MOODENG
    print("📊 MOODENG RSI Momentum Strategy")
    print("-" * 80)
    moodeng_signals = await check_moodeng_signals(client)

    if len(moodeng_signals) == 0:
        print("  No signals found")
    else:
        total_pnl = 0
        for sig in moodeng_signals:
            print(f"\n  Signal: {sig['timestamp'].strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"    Entry:  ${sig['entry']:.6f}")
            print(f"    SL:     ${sig['stop_loss']:.6f}")
            print(f"    TP:     ${sig['take_profit']:.6f}")
            print(f"    RSI:    {sig['rsi']:.2f}")
            print(f"    Outcome: {sig['outcome']}")
            if sig['exit_price']:
                print(f"    Exit:   ${sig['exit_price']:.6f} at {sig['exit_time'].strftime('%Y-%m-%d %H:%M')}")
                print(f"    P/L:    {sig['pnl_pct']:+.2f}%")
                total_pnl += sig['pnl_pct']

        print(f"\n  Total signals: {len(moodeng_signals)}")
        print(f"  Total P/L: {total_pnl:+.2f}%")

    print()
    print()

    # Check UNI
    print("📊 UNI Volume Zones Strategy")
    print("-" * 80)
    uni_signals = await check_uni_signals(client)

    if len(uni_signals) == 0:
        print("  No signals found")
    else:
        total_pnl = 0
        for sig in uni_signals:
            print(f"\n  Signal: {sig['timestamp'].strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"    Entry:  ${sig['entry']:.4f}")
            print(f"    SL:     ${sig['stop_loss']:.4f}")
            print(f"    TP:     ${sig['take_profit']:.4f}")
            print(f"    Vol Ratio: {sig['vol_ratio']:.2f}x ({sig['consecutive_bars']} bars)")
            print(f"    Outcome: {sig['outcome']}")
            if sig['exit_price']:
                print(f"    Exit:   ${sig['exit_price']:.4f} at {sig['exit_time'].strftime('%Y-%m-%d %H:%M')}")
                print(f"    P/L:    {sig['pnl_pct']:+.2f}%")
                total_pnl += sig['pnl_pct']

        print(f"\n  Total signals: {len(uni_signals)}")
        print(f"  Total P/L: {total_pnl:+.2f}%")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_signals = moodeng_signals + uni_signals
    if len(all_signals) == 0:
        print("No trades in last 24 hours")
    else:
        total_pnl = sum(s['pnl_pct'] for s in all_signals if s['exit_price'])
        open_trades = [s for s in all_signals if s['outcome'] == 'OPEN']
        closed_trades = [s for s in all_signals if s['outcome'] != 'OPEN']

        print(f"Total signals: {len(all_signals)}")
        print(f"Closed trades: {len(closed_trades)}")
        print(f"Open trades: {len(open_trades)}")
        print(f"Total P/L (closed): {total_pnl:+.2f}%")

        if open_trades:
            print()
            print("Open positions:")
            for sig in open_trades:
                print(f"  {sig['symbol']} {sig['strategy']} @ ${sig['entry']:.4f} (since {sig['timestamp'].strftime('%H:%M')})")

    print()
    print("=" * 80)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
