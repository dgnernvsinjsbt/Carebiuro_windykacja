#!/usr/bin/env python3
"""
7-Day Performance Analysis vs 30-Day Backtest Benchmarks
Generates comprehensive markdown report at trading/results/7DAY_VS_BACKTEST_ANALYSIS.md

IMPORTANT CLASSIFICATION RULE:
- TIME exits that are profitable = WINS
- Only SL (stop loss) exits are losses
- TP (take profit) exits are wins
"""

import asyncio
import yaml
import pandas as pd
from datetime import datetime, timedelta, timezone
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator
import os

# Load credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

# FIXED Backtest Benchmarks (original discovery backtests)
BACKTEST_BENCHMARKS = {
    'MOODENG RSI': {
        'return_pct': 24.02,
        'max_drawdown': -2.25,
        'win_rate': 31.0,
        'trades_30d': 129,
        'rr_ratio': 5.75,
        'period_days': 30
    },
    'FARTCOIN LONG': {
        'return_pct': 10.38,
        'max_drawdown': -1.45,
        'win_rate': None,  # Not specified
        'trades_30d': None,
        'rr_ratio': 7.14,
        'period_days': 30
    },
    'FARTCOIN SHORT': {
        'return_pct': 20.08,
        'max_drawdown': -2.26,
        'win_rate': None,
        'trades_30d': None,
        'rr_ratio': 8.88,
        'period_days': 30
    },
    'DOGE Volume Zones': {
        'return_pct': 8.14,
        'max_drawdown': -1.14,
        'win_rate': 52.0,
        'trades_30d': 25,
        'rr_ratio': 7.15,
        'period_days': 30
    },
    'PEPE Volume Zones': {
        'return_pct': 2.57,
        'max_drawdown': -0.38,
        'win_rate': 66.7,
        'trades_30d': 15,
        'rr_ratio': 6.80,
        'period_days': 30
    },
    'TRUMP Volume Zones': {
        'return_pct': 8.06,
        'max_drawdown': -0.76,
        'win_rate': 61.9,
        'trades_30d': 21,
        'rr_ratio': 10.56,
        'period_days': 30
    },
    'UNI Volume Zones': {
        'return_pct': 31.99,
        'max_drawdown': -1.78,
        'win_rate': 45.1,
        'trades_30d': 65,  # 195 trades / 3 months = ~65/month
        'rr_ratio': 17.98,
        'period_days': 90  # 3 months backtest
    }
}

async def fetch_data_7days(client, symbol):
    """Fetch 7+ days of data and calculate indicators"""
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)

    # Fetch in chunks - need ~10500 candles for 7 days + buffer
    all_klines = []

    for i in range(8):  # 8 chunks of 1440 = ~8 days
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

    cutoff = (now - timedelta(days=7)).replace(tzinfo=None)
    df_7d = df[df['timestamp'] >= cutoff].copy()

    return df, df_7d

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
    df, df_7d = await fetch_data_7days(client, 'FARTCOIN-USDT')

    # Build 5-min candles
    df_5min = df.resample('5min', on='timestamp').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    calc_5min = IndicatorCalculator(df_5min)
    df_5min = calc_5min.add_all_indicators()

    signals = []

    for i in range(1, len(df_7d)):
        current = df_7d.iloc[i]

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
                                'direction': 'LONG',
                                'entry': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'outcome': outcome,
                                'exit_price': exit_price,
                                'pnl_pct': pnl_pct
                            })

    return signals

async def check_fartcoin_short(client):
    """Trend Distance SHORT strategy"""
    df, df_7d = await fetch_data_7days(client, 'FARTCOIN-USDT')

    signals = []

    for i in range(1, len(df_7d)):
        current = df_7d.iloc[i]

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
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct
                })

    return signals

async def check_moodeng_rsi(client):
    """MOODENG RSI Momentum strategy"""
    df, df_7d = await fetch_data_7days(client, 'MOODENG-USDT')

    signals = []

    for i in range(1, len(df_7d)):
        idx = df_7d.index[i]
        prev_idx = df_7d.index[i-1]
        current = df_7d.loc[idx]
        prev = df_7d.loc[prev_idx]

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
                    'direction': 'LONG',
                    'entry': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct
                })

    return signals

async def check_volume_zones(client, symbol, config):
    """Generic volume zones strategy"""
    df, df_7d = await fetch_data_7days(client, symbol)

    signals = []

    for i in range(20, len(df_7d)):
        current = df_7d.iloc[i]

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

            lookback = df_7d.iloc[max(0, i-10):i+1]

            consecutive = 0
            for j in range(len(lookback)-1, -1, -1):
                if lookback.iloc[j]['vol_ratio'] >= config['volume_threshold']:
                    consecutive += 1
                else:
                    break

            if consecutive >= config['min_zone_bars']:
                window = df_7d.iloc[max(0, i-config['lookback_bars']):min(len(df_7d), i+config['lookback_bars'])]
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
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'outcome': outcome,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct
                    })

    return signals

def calculate_metrics(signals, strategy_name):
    """Calculate comprehensive metrics for a strategy"""
    if not signals:
        return {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'tp_count': 0,
            'sl_count': 0,
            'time_count': 0,
            'max_losing_streak': 0
        }

    closed_signals = [s for s in signals if s['outcome'] != 'OPEN']

    # Count by exit type
    tp_count = len([s for s in closed_signals if s['outcome'] == 'TAKE_PROFIT'])
    sl_count = len([s for s in closed_signals if s['outcome'] == 'STOP_LOSS'])
    time_count = len([s for s in closed_signals if s['outcome'] == 'TIME_EXIT'])

    # IMPORTANT: Profitable TIME exits = WINS
    profitable_time = len([s for s in closed_signals if s['outcome'] == 'TIME_EXIT' and s['pnl_pct'] > 0])
    unprofitable_time = time_count - profitable_time

    wins = tp_count + profitable_time
    losses = sl_count + unprofitable_time

    total_pnl = sum(s['pnl_pct'] for s in closed_signals)

    # Calculate max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for s in closed_signals:
        cumulative += s['pnl_pct']
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    # Calculate max losing streak
    max_streak = 0
    current_streak = 0
    for s in closed_signals:
        # Loss = SL exit OR TIME exit with negative P/L
        is_loss = s['outcome'] == 'STOP_LOSS' or (s['outcome'] == 'TIME_EXIT' and s['pnl_pct'] < 0)
        if is_loss:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    win_rate = (wins / len(closed_signals) * 100) if closed_signals else 0

    return {
        'trades': len(closed_signals),
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'max_drawdown': -max_dd,  # Negative for display
        'tp_count': tp_count,
        'sl_count': sl_count,
        'time_count': time_count,
        'profitable_time': profitable_time,
        'max_losing_streak': max_streak
    }

def get_health_score(live_metrics, backtest):
    """Rate strategy health: HEALTHY / WATCH / CONCERN"""
    if live_metrics['trades'] == 0:
        return 'NO DATA', 'No trades in period'

    issues = []

    # Check win rate deviation
    if backtest.get('win_rate'):
        wr_diff = abs(live_metrics['win_rate'] - backtest['win_rate'])
        if wr_diff > 20:
            issues.append(f"Win rate deviation: {wr_diff:.1f}%")
        elif wr_diff > 10:
            issues.append(f"Win rate slightly off: {wr_diff:.1f}%")

    # Check trade count (7 days should be ~23% of 30 days)
    if backtest.get('trades_30d'):
        expected = backtest['trades_30d'] * (7 / 30)
        if expected > 0:
            trade_ratio = live_metrics['trades'] / expected
            if trade_ratio < 0.5:
                issues.append(f"Low trade count: {live_metrics['trades']} vs {expected:.0f} expected")
            elif trade_ratio > 2.0:
                issues.append(f"High trade count: {live_metrics['trades']} vs {expected:.0f} expected")

    # Check P/L vs expected
    expected_pnl_7d = backtest['return_pct'] * (7 / backtest['period_days'])
    pnl_diff = abs(live_metrics['total_pnl'] - expected_pnl_7d)

    if live_metrics['total_pnl'] < -2:  # Losing more than 2%
        issues.append(f"Negative P/L: {live_metrics['total_pnl']:.2f}%")

    if len(issues) == 0:
        return 'HEALTHY', 'Within expected parameters'
    elif len(issues) == 1 or pnl_diff < expected_pnl_7d * 0.4:
        return 'WATCH', '; '.join(issues)
    else:
        return 'CONCERN', '; '.join(issues)

def generate_report(results, analysis_time, period_start):
    """Generate comprehensive markdown report"""

    report = f"""# 7-Day vs Backtest Performance Analysis

**Generated:** {analysis_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
**Analysis Period:** {period_start.strftime('%Y-%m-%d %H:%M')} to {analysis_time.strftime('%Y-%m-%d %H:%M')} UTC (7 days)

---

## Executive Summary

"""

    # Calculate portfolio totals
    total_trades = sum(r['metrics']['trades'] for r in results.values())
    total_pnl = sum(r['metrics']['total_pnl'] for r in results.values())
    total_wins = sum(r['metrics']['wins'] for r in results.values())
    total_losses = sum(r['metrics']['losses'] for r in results.values())

    # Portfolio max DD (simplified - would need proper equity curve for true portfolio DD)
    all_trades_sorted = []
    for name, r in results.items():
        for s in r['signals']:
            if s['outcome'] != 'OPEN':
                all_trades_sorted.append((s['timestamp'], s['pnl_pct']))
    all_trades_sorted.sort(key=lambda x: x[0])

    portfolio_dd = 0
    cumulative = 0
    peak = 0
    for _, pnl in all_trades_sorted:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > portfolio_dd:
            portfolio_dd = dd

    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    # Health assessment
    healthy = len([r for r in results.values() if r['health'][0] == 'HEALTHY'])
    watch = len([r for r in results.values() if r['health'][0] == 'WATCH'])
    concern = len([r for r in results.values() if r['health'][0] == 'CONCERN'])
    no_data = len([r for r in results.values() if r['health'][0] == 'NO DATA'])

    report += f"""The portfolio generated **{total_trades} trades** over the last 7 days with a combined **{total_pnl:+.2f}% P/L**. """

    if total_pnl >= 0:
        report += f"Performance is positive with {healthy} strategies healthy, {watch} on watch, and {concern} concerns. "
    else:
        report += f"Performance is negative, requiring attention. {healthy} strategies healthy, {watch} on watch, {concern} concerns. "

    if no_data > 0:
        report += f"{no_data} strategies had no signals (rare signal strategies). "

    report += f"Overall win rate is {overall_wr:.1f}% ({total_wins}W/{total_losses}L)."

    report += f"""

---

## Portfolio Summary

| Metric | Value |
|--------|-------|
| **Total P/L** | **{total_pnl:+.2f}%** |
| **Max Drawdown** | **-{portfolio_dd:.2f}%** |
| **Total Trades** | {total_trades} |
| **Win Rate** | {overall_wr:.1f}% ({total_wins}W/{total_losses}L) |
| **Strategies Active** | {len(results) - no_data} of {len(results)} |

---

## Per-Strategy Breakdown

"""

    for strategy_name, data in results.items():
        m = data['metrics']
        h = data['health']
        b = BACKTEST_BENCHMARKS.get(strategy_name, {})

        # Health badge
        if h[0] == 'HEALTHY':
            badge = '✅ HEALTHY'
        elif h[0] == 'WATCH':
            badge = '⚠️ WATCH'
        elif h[0] == 'CONCERN':
            badge = '🔴 CONCERN'
        else:
            badge = '⬜ NO DATA'

        expected_pnl = b.get('return_pct', 0) * (7 / b.get('period_days', 30))
        expected_trades = (b.get('trades_30d', 0) or 0) * (7 / 30)

        report += f"""### {strategy_name}

**Status:** {badge}
**Assessment:** {h[1]}

| Metric | Live 7d | Expected 7d | Backtest Ref |
|--------|---------|-------------|--------------|
| P/L | {m['total_pnl']:+.2f}% | {expected_pnl:+.2f}% | {b.get('return_pct', 'N/A')}% / {b.get('period_days', 30)}d |
| Max DD | {m['max_drawdown']:.2f}% | - | {b.get('max_drawdown', 'N/A')}% |
| Win Rate | {m['win_rate']:.1f}% | - | {b.get('win_rate', 'N/A')}% |
| Trades | {m['trades']} | {expected_trades:.0f} | {b.get('trades_30d', 'N/A')} / 30d |

**Exit Distribution:** TP: {m['tp_count']} | SL: {m['sl_count']} | TIME: {m['time_count']} (profitable: {m.get('profitable_time', 0)})
**Max Losing Streak:** {m['max_losing_streak']}

"""

        # Add trade log for strategies with trades
        if m['trades'] > 0 and data['signals']:
            report += "**Trade Log:**\n```\n"
            for s in data['signals']:
                if s['outcome'] != 'OPEN':
                    report += f"{s['timestamp'].strftime('%m-%d %H:%M')} {s['direction']:5s} @ ${s['entry']:.4f} → {s['outcome']:11s} {s['pnl_pct']:+.2f}%\n"
            report += "```\n\n"

    report += """---

## Comparison Table: Live 7d vs Backtest

| Strategy | Live P/L | Expected P/L | Live WR | BT WR | Live Trades | Expected | Health |
|----------|----------|--------------|---------|-------|-------------|----------|--------|
"""

    for name, data in results.items():
        m = data['metrics']
        b = BACKTEST_BENCHMARKS.get(name, {})
        h = data['health']

        expected_pnl = b.get('return_pct', 0) * (7 / b.get('period_days', 30))
        expected_trades = (b.get('trades_30d', 0) or 0) * (7 / 30)

        bt_wr = f"{b.get('win_rate', 'N/A')}%" if b.get('win_rate') else "N/A"

        health_icon = '✅' if h[0] == 'HEALTHY' else ('⚠️' if h[0] == 'WATCH' else ('🔴' if h[0] == 'CONCERN' else '⬜'))

        report += f"| {name} | {m['total_pnl']:+.2f}% | {expected_pnl:+.2f}% | {m['win_rate']:.1f}% | {bt_wr} | {m['trades']} | {expected_trades:.0f} | {health_icon} |\n"

    report += f"""
---

## Recommendations

"""

    concerns = [(name, data) for name, data in results.items() if data['health'][0] == 'CONCERN']
    watches = [(name, data) for name, data in results.items() if data['health'][0] == 'WATCH']

    if concerns:
        report += "### Strategies Requiring Attention\n\n"
        for name, data in concerns:
            report += f"- **{name}**: {data['health'][1]}\n"
        report += "\n"

    if watches:
        report += "### Strategies to Monitor\n\n"
        for name, data in watches:
            report += f"- **{name}**: {data['health'][1]}\n"
        report += "\n"

    if not concerns and not watches:
        report += "All active strategies are performing within expected parameters. No immediate action required.\n\n"

    report += f"""---

## Conclusion

"""

    if total_pnl >= 0 and len(concerns) == 0:
        report += f"The portfolio is performing well with {total_pnl:+.2f}% returns over 7 days. "
        report += "All strategies are operating within expected parameters from backtests. "
        report += "Continue monitoring and maintain current configuration.\n"
    elif total_pnl >= 0:
        report += f"The portfolio is net positive ({total_pnl:+.2f}%) but {len(concerns)} strategy(ies) require attention. "
        report += "Review the concern strategies and consider parameter adjustments if underperformance persists.\n"
    else:
        report += f"The portfolio is currently negative ({total_pnl:+.2f}%) over 7 days. "
        report += "This may be normal variance, especially for strategies with lower trade counts. "
        report += "Monitor closely over the next week before making configuration changes.\n"

    report += f"""
---

**Classification Note:** TIME exits with positive P/L are counted as WINS, not losses. Only SL (stop loss) exits are counted as losses.

**Report generated by:** `check_all_strategies_7day.py`
"""

    return report

async def main():
    client = BingXClient(api_key=api_key, api_secret=api_secret)

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=7)

    print("=" * 80)
    print("7-DAY PERFORMANCE ANALYSIS VS BACKTEST BENCHMARKS")
    print("=" * 80)
    print(f"Analysis time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Period: {period_start.strftime('%Y-%m-%d %H:%M')} to now")
    print()

    results = {}

    # 1. FARTCOIN LONG
    print("📊 Fetching FARTCOIN LONG...")
    signals = await check_fartcoin_long(client)
    metrics = calculate_metrics(signals, 'FARTCOIN LONG')
    health = get_health_score(metrics, BACKTEST_BENCHMARKS['FARTCOIN LONG'])
    results['FARTCOIN LONG'] = {'signals': signals, 'metrics': metrics, 'health': health}
    print(f"   {metrics['trades']} trades, {metrics['total_pnl']:+.2f}% P/L")

    # 2. FARTCOIN SHORT
    print("📊 Fetching FARTCOIN SHORT...")
    signals = await check_fartcoin_short(client)
    metrics = calculate_metrics(signals, 'FARTCOIN SHORT')
    health = get_health_score(metrics, BACKTEST_BENCHMARKS['FARTCOIN SHORT'])
    results['FARTCOIN SHORT'] = {'signals': signals, 'metrics': metrics, 'health': health}
    print(f"   {metrics['trades']} trades, {metrics['total_pnl']:+.2f}% P/L")

    # 3. MOODENG RSI
    print("📊 Fetching MOODENG RSI...")
    signals = await check_moodeng_rsi(client)
    metrics = calculate_metrics(signals, 'MOODENG RSI')
    health = get_health_score(metrics, BACKTEST_BENCHMARKS['MOODENG RSI'])
    results['MOODENG RSI'] = {'signals': signals, 'metrics': metrics, 'health': health}
    print(f"   {metrics['trades']} trades, {metrics['total_pnl']:+.2f}% P/L")

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
        print(f"📊 Fetching {name}...")
        signals = await check_volume_zones(client, symbol, config)
        metrics = calculate_metrics(signals, name)
        health = get_health_score(metrics, BACKTEST_BENCHMARKS[name])
        results[name] = {'signals': signals, 'metrics': metrics, 'health': health}
        print(f"   {metrics['trades']} trades, {metrics['total_pnl']:+.2f}% P/L")

    await client.close()

    # Generate report
    print()
    print("📝 Generating report...")
    report = generate_report(results, now, period_start)

    # Save report
    report_path = '/workspaces/Carebiuro_windykacja/trading/results/7DAY_VS_BACKTEST_ANALYSIS.md'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ Report saved to: {report_path}")
    print()

    # Print summary to console
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_trades = sum(r['metrics']['trades'] for r in results.values())
    total_pnl = sum(r['metrics']['total_pnl'] for r in results.values())

    for name, data in results.items():
        m = data['metrics']
        h = data['health']
        health_icon = '✅' if h[0] == 'HEALTHY' else ('⚠️' if h[0] == 'WATCH' else ('🔴' if h[0] == 'CONCERN' else '⬜'))
        print(f"{name:25s}: {m['trades']:3d} trades, {m['win_rate']:5.1f}% WR, {m['total_pnl']:+7.2f}% P/L  {health_icon} {h[0]}")

    print("-" * 80)
    print(f"{'PORTFOLIO TOTAL':25s}: {total_trades:3d} trades, {total_pnl:+15.2f}% P/L")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
