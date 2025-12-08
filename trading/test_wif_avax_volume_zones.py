#!/usr/bin/env python3
"""
Test Volume Zones strategy on WIF and AVAX
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def load_data(token):
    """Load 1m data for token"""
    path = f'/workspaces/Carebiuro_windykacja/trading/{token.lower()}_usdt_1m_lbank.csv'
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df

def calculate_indicators(df):
    """Calculate ATR and volume moving average"""
    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # Volume MA
    df['vol_ma'] = df['volume'].rolling(20).mean()

    # Local highs/lows (20 bar lookback)
    df['local_high'] = df['high'].rolling(20).max()
    df['local_low'] = df['low'].rolling(20).min()

    return df

def get_session(timestamp):
    """Determine trading session"""
    hour = timestamp.hour
    if 21 <= hour or hour < 7:
        return 'overnight'
    elif 7 <= hour < 14:
        return 'asia_eu'
    else:
        return 'us'

def detect_volume_zones(df, volume_threshold=1.5, min_zone_bars=5):
    """Detect accumulation and distribution zones"""
    zones = []

    df['high_vol'] = df['volume'] > df['vol_ma'] * volume_threshold

    i = 0
    while i < len(df) - min_zone_bars:
        # Check for consecutive high volume bars
        consecutive = 0
        start_idx = i

        while i < len(df) and df['high_vol'].iloc[i]:
            consecutive += 1
            i += 1

        if consecutive >= min_zone_bars:
            zone_data = df.iloc[start_idx:i]
            zone_high = zone_data['high'].max()
            zone_low = zone_data['low'].min()
            zone_end = df.index[i-1]

            # Determine if accumulation (at local low) or distribution (at local high)
            at_local_low = zone_low <= df['local_low'].iloc[i-1] * 1.005
            at_local_high = zone_high >= df['local_high'].iloc[i-1] * 0.995

            if at_local_low:
                zones.append({
                    'type': 'accumulation',
                    'end_idx': i,
                    'end_time': zone_end,
                    'entry_price': df['close'].iloc[i-1],
                    'atr': df['atr'].iloc[i-1],
                    'bars': consecutive
                })
            elif at_local_high:
                zones.append({
                    'type': 'distribution',
                    'end_idx': i,
                    'end_time': zone_end,
                    'entry_price': df['close'].iloc[i-1],
                    'atr': df['atr'].iloc[i-1],
                    'bars': consecutive
                })

        i += 1

    return zones

def backtest_volume_zones(df, config):
    """Backtest volume zones strategy with given config"""
    volume_threshold = config.get('volume_threshold', 1.5)
    min_zone_bars = config.get('min_zone_bars', 5)
    sl_mult = config.get('sl_mult', 1.5)
    rr_ratio = config.get('rr_ratio', 2.0)
    session_filter = config.get('session', 'all')
    max_hold = config.get('max_hold', 90)
    fee_pct = config.get('fee_pct', 0.10)  # 0.1% round trip for market orders

    zones = detect_volume_zones(df, volume_threshold, min_zone_bars)

    trades = []

    for zone in zones:
        idx = zone['end_idx']
        if idx >= len(df) - max_hold:
            continue

        entry_time = zone['end_time']
        session = get_session(entry_time)

        # Session filter
        if session_filter != 'all' and session != session_filter:
            continue

        entry_price = zone['entry_price']
        atr = zone['atr']

        if pd.isna(atr) or atr == 0:
            continue

        # Determine direction
        if zone['type'] == 'accumulation':
            direction = 'LONG'
            sl_price = entry_price - (sl_mult * atr)
            tp_price = entry_price + (sl_mult * atr * rr_ratio)
        else:
            direction = 'SHORT'
            sl_price = entry_price + (sl_mult * atr)
            tp_price = entry_price - (sl_mult * atr * rr_ratio)

        # Simulate trade
        exit_price = None
        exit_reason = None
        exit_time = None

        for j in range(1, max_hold + 1):
            if idx + j >= len(df):
                break

            bar = df.iloc[idx + j]

            if direction == 'LONG':
                # Check SL first
                if bar['low'] <= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    exit_time = bar.name
                    break
                # Check TP
                if bar['high'] >= tp_price:
                    exit_price = tp_price
                    exit_reason = 'TP'
                    exit_time = bar.name
                    break
            else:  # SHORT
                # Check SL first
                if bar['high'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    exit_time = bar.name
                    break
                # Check TP
                if bar['low'] <= tp_price:
                    exit_price = tp_price
                    exit_reason = 'TP'
                    exit_time = bar.name
                    break

        # Time exit if no SL/TP hit
        if exit_price is None and idx + max_hold < len(df):
            exit_price = df['close'].iloc[idx + max_hold]
            exit_reason = 'TIME'
            exit_time = df.index[idx + max_hold]

        if exit_price is None:
            continue

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Subtract fees
        pnl_pct -= fee_pct

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'session': session
        })

    return trades

def analyze_results(trades, token):
    """Analyze backtest results"""
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    total_return = df_trades['pnl_pct'].sum()

    # Calculate max drawdown
    cumulative = df_trades['pnl_pct'].cumsum()
    rolling_max = cumulative.cummax()
    drawdown = cumulative - rolling_max
    max_dd = drawdown.min()

    win_rate = (df_trades['pnl_pct'] > 0).sum() / len(df_trades) * 100

    winners = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct']
    losers = df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct']

    avg_win = winners.mean() if len(winners) > 0 else 0
    avg_loss = abs(losers.mean()) if len(losers) > 0 else 0

    rr_actual = avg_win / avg_loss if avg_loss > 0 else 0
    rr_ratio = total_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'token': token,
        'trades': len(df_trades),
        'return_pct': total_return,
        'max_dd_pct': max_dd,
        'rr_ratio': rr_ratio,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'actual_rr': rr_actual,
        'longs': len(df_trades[df_trades['direction'] == 'LONG']),
        'shorts': len(df_trades[df_trades['direction'] == 'SHORT']),
        'trades_df': df_trades
    }

def test_token(token):
    """Test multiple configurations for a token"""
    print(f"\n{'='*80}")
    print(f"TESTING {token} VOLUME ZONES")
    print(f"{'='*80}")

    df = load_data(token)
    df = calculate_indicators(df)

    print(f"Data: {len(df)} candles, {(df.index[-1] - df.index[0]).days} days")
    print(f"Price range: ${df['close'].min():.4f} - ${df['close'].max():.4f}")
    print()

    # Test configurations
    configs = [
        # Session variations
        {'name': 'All Sessions 2:1', 'session': 'all', 'sl_mult': 1.5, 'rr_ratio': 2.0},
        {'name': 'Overnight 2:1', 'session': 'overnight', 'sl_mult': 1.5, 'rr_ratio': 2.0},
        {'name': 'US Session 2:1', 'session': 'us', 'sl_mult': 1.5, 'rr_ratio': 2.0},

        # R:R variations (overnight)
        {'name': 'Overnight 3:1', 'session': 'overnight', 'sl_mult': 1.5, 'rr_ratio': 3.0},
        {'name': 'Overnight 4:1', 'session': 'overnight', 'sl_mult': 1.5, 'rr_ratio': 4.0},

        # SL variations (overnight)
        {'name': 'Overnight Tight SL', 'session': 'overnight', 'sl_mult': 1.0, 'rr_ratio': 2.0},
        {'name': 'Overnight Wide SL', 'session': 'overnight', 'sl_mult': 2.0, 'rr_ratio': 2.0},

        # All sessions variations
        {'name': 'All 3:1', 'session': 'all', 'sl_mult': 1.5, 'rr_ratio': 3.0},
        {'name': 'All Tight SL 2:1', 'session': 'all', 'sl_mult': 1.0, 'rr_ratio': 2.0},
    ]

    results = []

    for config in configs:
        trades = backtest_volume_zones(df, config)
        analysis = analyze_results(trades, token)

        if analysis:
            analysis['config'] = config['name']
            results.append(analysis)

    # Sort by R:R ratio
    results.sort(key=lambda x: x['rr_ratio'], reverse=True)

    print(f"{'Config':<25} {'Trades':>6} {'Return':>8} {'MaxDD':>8} {'R:R':>8} {'WinRate':>8}")
    print("-" * 75)

    for r in results:
        print(f"{r['config']:<25} {r['trades']:>6} {r['return_pct']:>+7.2f}% {r['max_dd_pct']:>+7.2f}% {r['rr_ratio']:>7.2f}x {r['win_rate']:>7.1f}%")

    # Best config
    if results:
        best = results[0]
        print()
        print(f"🏆 BEST CONFIG: {best['config']}")
        print(f"   Return: {best['return_pct']:+.2f}%")
        print(f"   Max DD: {best['max_dd_pct']:.2f}%")
        print(f"   R:R Ratio: {best['rr_ratio']:.2f}x")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Trades: {best['trades']} (L:{best['longs']}/S:{best['shorts']})")

        # Save best trades
        best['trades_df'].to_csv(f'/workspaces/Carebiuro_windykacja/trading/results/{token}_volume_zones_trades.csv', index=False)
        print(f"   Saved: results/{token}_volume_zones_trades.csv")

    return results

if __name__ == "__main__":
    print("=" * 80)
    print("VOLUME ZONES STRATEGY BACKTEST - WIF & AVAX")
    print("=" * 80)

    all_results = {}

    for token in ['WIF', 'AVAX']:
        results = test_token(token)
        if results:
            all_results[token] = results[0]  # Best config

    print("\n" + "=" * 80)
    print("SUMMARY - BEST CONFIGS")
    print("=" * 80)
    print()

    for token, best in all_results.items():
        print(f"{token}:")
        print(f"  Config: {best['config']}")
        print(f"  Return: {best['return_pct']:+.2f}% | Max DD: {best['max_dd_pct']:.2f}% | R:R: {best['rr_ratio']:.2f}x")
        print()

    # Compare with existing strategies
    print("=" * 80)
    print("COMPARISON WITH EXISTING VOLUME ZONES STRATEGIES")
    print("=" * 80)
    print()
    print(f"{'Token':<10} {'Return':>10} {'Max DD':>10} {'R:R':>10}")
    print("-" * 45)

    # Existing from CLAUDE.md
    existing = [
        ('DOGE', 8.14, -1.14, 7.15),
        ('PEPE', 2.57, -0.38, 6.80),
        ('PENGU', 17.39, -4.00, 4.35),
        ('ETH', 3.78, -1.05, 3.60),
    ]

    for token, ret, dd, rr in existing:
        print(f"{token:<10} {ret:>+9.2f}% {dd:>+9.2f}% {rr:>9.2f}x")

    print("-" * 45)
    print("NEW:")
    for token, best in all_results.items():
        print(f"{token:<10} {best['return_pct']:>+9.2f}% {best['max_dd_pct']:>+9.2f}% {best['rr_ratio']:>9.2f}x")
