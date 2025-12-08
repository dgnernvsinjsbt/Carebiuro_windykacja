"""
UNI/USDT Volume Zones Strategy - Full Optimization
Based on successful DOGE, PEPE, and TRUMP implementations
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def load_data(filepath):
    """Load and prepare 1m data"""
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

def calculate_atr(df, period=14):
    """Calculate ATR"""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def detect_volume_zones(df, volume_threshold=1.5, min_zone_bars=5, lookback=20):
    """
    Detect volume zones for accumulation (lows) and distribution (highs)

    volume_threshold: Multiplier of 20-period volume MA (e.g., 1.5x)
    min_zone_bars: Minimum consecutive bars to form a zone
    lookback: Lookback period for local highs/lows
    """
    df = df.copy()
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    df['high_volume'] = df['volume'] > (df['volume_ma'] * volume_threshold)

    # Find local highs and lows
    df['local_high'] = df['high'].rolling(window=lookback, center=True).max() == df['high']
    df['local_low'] = df['low'].rolling(window=lookback, center=True).min() == df['low']

    # Detect consecutive high-volume bars
    zones = []
    in_zone = False
    zone_start = None
    zone_bars = 0
    zone_prices = []

    for i in range(len(df)):
        if df.iloc[i]['high_volume']:
            if not in_zone:
                in_zone = True
                zone_start = i
                zone_bars = 1
                zone_prices = [df.iloc[i]['close']]
            else:
                zone_bars += 1
                zone_prices.append(df.iloc[i]['close'])
        else:
            if in_zone and zone_bars >= min_zone_bars:
                # Zone ended, check if at local high/low
                zone_avg_price = np.mean(zone_prices)

                # Check if zone was at local low (accumulation) or high (distribution)
                is_accumulation = False
                is_distribution = False

                for j in range(zone_start, zone_start + zone_bars):
                    if j < len(df) and df.iloc[j]['local_low']:
                        is_accumulation = True
                        break

                for j in range(zone_start, zone_start + zone_bars):
                    if j < len(df) and df.iloc[j]['local_high']:
                        is_distribution = True
                        break

                if is_accumulation or is_distribution:
                    zones.append({
                        'end_idx': i - 1,
                        'type': 'accumulation' if is_accumulation else 'distribution',
                        'zone_bars': zone_bars,
                        'avg_price': zone_avg_price
                    })

            in_zone = False
            zone_start = None
            zone_bars = 0
            zone_prices = []

    return zones

def is_in_session(timestamp, session):
    """Check if timestamp is in specified session (UTC)"""
    hour = timestamp.hour

    if session == 'overnight':  # 21:00-07:00 UTC
        return hour >= 21 or hour < 7
    elif session == 'us':  # 14:00-21:00 UTC
        return 14 <= hour < 21
    elif session == 'asia_eu':  # 00:00-14:00 UTC
        return 0 <= hour < 14
    elif session == 'all':
        return True
    return False

def backtest_volume_zones(df, config):
    """
    Backtest volume zones strategy

    config = {
        'volume_threshold': 1.5,
        'min_zone_bars': 5,
        'sl_type': 'atr' or 'fixed_pct',
        'sl_value': 1.0 (atr mult) or 0.5 (percent),
        'tp_type': 'rr_multiple',
        'tp_value': 2.0,
        'session': 'overnight', 'us', 'asia_eu', 'all',
        'max_hold_bars': 90
    }
    """
    df = df.copy()
    df['atr'] = calculate_atr(df, period=14)

    # Detect zones
    zones = detect_volume_zones(
        df,
        volume_threshold=config['volume_threshold'],
        min_zone_bars=config['min_zone_bars']
    )

    trades = []
    fee_pct = 0.10  # 0.10% round-trip (market orders)

    for zone in zones:
        entry_idx = zone['end_idx'] + 1  # Enter after zone ends

        if entry_idx >= len(df):
            continue

        entry_time = df.iloc[entry_idx]['timestamp']

        # Session filter
        if not is_in_session(entry_time, config['session']):
            continue

        direction = 'long' if zone['type'] == 'accumulation' else 'short'
        entry_price = df.iloc[entry_idx]['close']
        entry_atr = df.iloc[entry_idx]['atr']

        if pd.isna(entry_atr) or entry_atr == 0:
            continue

        # Calculate stop loss
        if config['sl_type'] == 'atr':
            sl_distance = entry_atr * config['sl_value']
        else:  # fixed_pct
            sl_distance = entry_price * (config['sl_value'] / 100)

        if direction == 'long':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * config['tp_value'])
        else:  # short
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * config['tp_value'])

        # Simulate trade
        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(entry_idx + 1, min(entry_idx + config['max_hold_bars'], len(df))):
            bar_high = df.iloc[i]['high']
            bar_low = df.iloc[i]['low']

            if direction == 'long':
                if bar_low <= stop_loss:
                    exit_idx = i
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar_high >= take_profit:
                    exit_idx = i
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break
            else:  # short
                if bar_high >= stop_loss:
                    exit_idx = i
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar_low <= take_profit:
                    exit_idx = i
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break

        # Time exit if neither SL/TP hit
        if exit_idx is None:
            exit_idx = min(entry_idx + config['max_hold_bars'], len(df) - 1)
            exit_price = df.iloc[exit_idx]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'long':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_pct -= fee_pct  # Subtract fees

        trades.append({
            'entry_time': entry_time,
            'exit_time': df.iloc[exit_idx]['timestamp'],
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'bars_held': exit_idx - entry_idx
        })

    if len(trades) == 0:
        return {
            'total_return': 0,
            'max_drawdown': 0,
            'return_dd_ratio': 0,
            'win_rate': 0,
            'num_trades': 0,
            'avg_trade': 0,
            'trades': []
        }

    trades_df = pd.DataFrame(trades)

    # Calculate metrics
    total_return = trades_df['pnl_pct'].sum()
    wins = trades_df[trades_df['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades_df) * 100

    # Calculate max drawdown
    equity_curve = (1 + trades_df['pnl_pct'] / 100).cumprod()
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'win_rate': win_rate,
        'num_trades': len(trades_df),
        'avg_trade': trades_df['pnl_pct'].mean(),
        'trades': trades_df
    }

def optimize_volume_zones(df):
    """Test all configurations"""

    configs = []

    # Parameter grid
    volume_thresholds = [1.3, 1.5, 2.0]
    min_zone_bars_list = [3, 5, 7]
    sessions = ['overnight', 'us', 'asia_eu', 'all']

    # ATR-based stops
    for vt in volume_thresholds:
        for mzb in min_zone_bars_list:
            for sess in sessions:
                for sl_mult in [1.0, 1.5, 2.0]:
                    for rr in [2.0, 3.0, 4.0]:
                        configs.append({
                            'volume_threshold': vt,
                            'min_zone_bars': mzb,
                            'sl_type': 'atr',
                            'sl_value': sl_mult,
                            'tp_type': 'rr_multiple',
                            'tp_value': rr,
                            'session': sess,
                            'max_hold_bars': 90
                        })

    # Fixed % stops
    for vt in volume_thresholds:
        for mzb in min_zone_bars_list:
            for sess in sessions:
                for sl_pct in [0.5, 1.0]:
                    for rr in [2.0, 3.0, 4.0]:
                        configs.append({
                            'volume_threshold': vt,
                            'min_zone_bars': mzb,
                            'sl_type': 'fixed_pct',
                            'sl_value': sl_pct,
                            'tp_type': 'rr_multiple',
                            'tp_value': rr,
                            'session': sess,
                            'max_hold_bars': 90
                        })

    results = []

    print(f"Testing {len(configs)} configurations...")

    for i, config in enumerate(configs):
        if (i + 1) % 50 == 0:
            print(f"Progress: {i + 1}/{len(configs)}")

        result = backtest_volume_zones(df, config)

        results.append({
            'volume_threshold': config['volume_threshold'],
            'min_zone_bars': config['min_zone_bars'],
            'sl_type': config['sl_type'],
            'sl_value': config['sl_value'],
            'rr_ratio': config['tp_value'],
            'session': config['session'],
            'total_return': result['total_return'],
            'max_drawdown': result['max_drawdown'],
            'return_dd_ratio': result['return_dd_ratio'],
            'win_rate': result['win_rate'],
            'num_trades': result['num_trades'],
            'avg_trade': result['avg_trade']
        })

    results_df = pd.DataFrame(results)

    # Filter for minimum trade count
    results_df = results_df[results_df['num_trades'] >= 10]

    if len(results_df) == 0:
        print("\n⚠️ No configurations with 10+ trades found!")
        return pd.DataFrame(results), None, None

    # Sort by Return/DD ratio
    results_df = results_df.sort_values('return_dd_ratio', ascending=False)

    return results_df, configs, df

if __name__ == '__main__':
    print("=" * 80)
    print("UNI/USDT Volume Zones Strategy Optimization")
    print("=" * 80)

    # Load data
    filepath = '/workspaces/Carebiuro_windykacja/trading/uni_usdt_1m_lbank.csv'
    df = load_data(filepath)

    print(f"\nLoaded {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Optimize
    results_df, configs, df_with_indicators = optimize_volume_zones(df)

    # Save all results
    output_file = '/workspaces/Carebiuro_windykacja/trading/results/UNI_volume_zones_optimization.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ All results saved to {output_file}")

    if len(results_df) == 0:
        print("\n❌ No profitable configurations found!")
        exit(1)

    # Get best configs
    best_rdd = results_df.iloc[0]
    best_return = results_df.nlargest(1, 'total_return').iloc[0]
    best_wr = results_df.nlargest(1, 'win_rate').iloc[0]

    print("\n" + "=" * 80)
    print("BEST CONFIGURATION BY RETURN/DD RATIO")
    print("=" * 80)
    print(f"Volume Threshold: {best_rdd['volume_threshold']}x")
    print(f"Min Zone Bars: {best_rdd['min_zone_bars']}")
    print(f"Stop Loss: {best_rdd['sl_value']}x {best_rdd['sl_type'].upper()}")
    print(f"R:R Ratio: {best_rdd['rr_ratio']}:1")
    print(f"Session: {best_rdd['session']}")
    print(f"\n📊 Performance:")
    print(f"  Return: {best_rdd['total_return']:.2f}%")
    print(f"  Max DD: {best_rdd['max_drawdown']:.2f}%")
    print(f"  Return/DD: {best_rdd['return_dd_ratio']:.2f}x")
    print(f"  Win Rate: {best_rdd['win_rate']:.1f}%")
    print(f"  Trades: {int(best_rdd['num_trades'])}")

    print("\n" + "=" * 80)
    print("BEST CONFIGURATION BY RETURN")
    print("=" * 80)
    print(f"Return: {best_return['total_return']:.2f}% | DD: {best_return['max_drawdown']:.2f}% | R/DD: {best_return['return_dd_ratio']:.2f}x")
    print(f"Config: {best_return['volume_threshold']}x vol, {best_return['min_zone_bars']} bars, {best_return['sl_value']}x {best_return['sl_type']}, {best_return['rr_ratio']}:1, {best_return['session']}")

    print("\n" + "=" * 80)
    print("BEST CONFIGURATION BY WIN RATE")
    print("=" * 80)
    print(f"Win Rate: {best_wr['win_rate']:.1f}% | Return: {best_wr['total_return']:.2f}% | R/DD: {best_wr['return_dd_ratio']:.2f}x")
    print(f"Config: {best_wr['volume_threshold']}x vol, {best_wr['min_zone_bars']} bars, {best_wr['sl_value']}x {best_wr['sl_type']}, {best_wr['rr_ratio']}:1, {best_wr['session']}")

    # Run detailed backtest on best config
    best_config = {
        'volume_threshold': best_rdd['volume_threshold'],
        'min_zone_bars': int(best_rdd['min_zone_bars']),
        'sl_type': best_rdd['sl_type'],
        'sl_value': best_rdd['sl_value'],
        'tp_type': 'rr_multiple',
        'tp_value': best_rdd['rr_ratio'],
        'session': best_rdd['session'],
        'max_hold_bars': 90
    }

    result = backtest_volume_zones(df, best_config)
    trades_df = result['trades']

    # Save trade-by-trade results
    trades_file = '/workspaces/Carebiuro_windykacja/trading/results/UNI_volume_zones_trades.csv'
    trades_df.to_csv(trades_file, index=False)
    print(f"\n✅ Trade log saved to {trades_file}")

    # Compare to benchmarks
    print("\n" + "=" * 80)
    print("COMPARISON TO BENCHMARKS")
    print("=" * 80)
    print(f"{'Token':<10} {'Return/DD':<12} {'Return':<10} {'Win Rate':<10} {'Trades':<8}")
    print("-" * 80)
    print(f"{'TRUMP':<10} {'10.56x':<12} {'+8.06%':<10} {'61.9%':<10} {'21':<8}")
    print(f"{'DOGE':<10} {'7.15x':<12} {'+8.14%':<10} {'52.0%':<10} {'25':<8}")
    print(f"{'PEPE':<10} {'6.80x':<12} {'+2.57%':<10} {'66.7%':<10} {'15':<8}")
    uni_rdd = f"{best_rdd['return_dd_ratio']:.2f}x"
    uni_ret = f"{best_rdd['total_return']:+.2f}%"
    uni_wr = f"{best_rdd['win_rate']:.1f}%"
    uni_trades = int(best_rdd['num_trades'])
    print(f"{'UNI':<10} {uni_rdd:<12} {uni_ret:<10} {uni_wr:<10} {uni_trades:<8}")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    if best_rdd['return_dd_ratio'] >= 5.0 and best_rdd['total_return'] > 5.0:
        print("✅ UNI IS TRADEABLE with Volume Zones strategy!")
        print(f"   Strong Return/DD ratio ({best_rdd['return_dd_ratio']:.2f}x) and positive returns")
    elif best_rdd['return_dd_ratio'] >= 3.0 and best_rdd['total_return'] > 2.0:
        print("⚠️ UNI IS MARGINALLY TRADEABLE")
        print(f"   Decent metrics but weaker than top performers")
    else:
        print("❌ UNI IS NOT TRADEABLE with Volume Zones")
        print(f"   Return/DD ratio ({best_rdd['return_dd_ratio']:.2f}x) below 3.0x threshold")

    print("\n" + "=" * 80)
