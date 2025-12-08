"""
ETH Defended Levels - Comprehensive Optimization

Systematically tests and optimizes:
1. Session filters (Asia, Europe, US, Overnight)
2. Higher timeframe filters (1H/4H trend, ADX, RSI)
3. Entry optimization (limit orders vs market)
4. Additional filters (volume, volatility, momentum)
5. Direction bias (LONG-only vs both directions)

Goal: Maximize Return/DD ratio while maintaining strategy logic
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

def load_data():
    """Load ETH 1m data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def detect_defended_levels(df,
                           lookback=20,
                           volume_mult=2.5,
                           min_defense_hours=12,
                           max_defense_hours=24,
                           min_volume_bars=5,
                           direction_filter='both',
                           session_filter='all',
                           htf_filter=None,
                           entry_offset_pct=0):
    """
    Enhanced defended levels detector with filters

    Args:
        direction_filter: 'long', 'short', or 'both'
        session_filter: 'asia', 'europe', 'us', 'overnight', or 'all'
        htf_filter: dict with higher timeframe filter settings
        entry_offset_pct: % to offset limit order (negative = better entry)
    """

    # Calculate volume metrics
    df['volume_sma'] = df['volume'].rolling(100).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    # Calculate higher timeframe indicators if needed
    if htf_filter:
        # 1H indicators
        df['sma_50_1h'] = df['close'].rolling(50*60).mean()  # 50 hours = 3000 bars
        df['rsi_14_1h'] = calculate_rsi(df['close'], 14*60)
        df['adx_14_1h'] = calculate_adx(df, 14*60)

    # Find local highs and lows
    df['local_high'] = df['high'] == df['high'].rolling(lookback*2+1, center=True).max()
    df['local_low'] = df['low'] == df['low'].rolling(lookback*2+1, center=True).min()

    signals = []

    # Scan for defended levels
    for i in range(lookback, len(df) - max_defense_hours*60):

        # Get hour for session filtering
        hour = df['timestamp'].iloc[i].hour

        # Apply session filter
        if session_filter != 'all':
            if session_filter == 'asia' and not (0 <= hour < 8):
                continue
            elif session_filter == 'europe' and not (8 <= hour < 14):
                continue
            elif session_filter == 'us' and not (14 <= hour < 21):
                continue
            elif session_filter == 'overnight' and not (21 <= hour or hour < 0):
                continue

        # Check for ACCUMULATION zone (LONG)
        if direction_filter in ['long', 'both'] and df['local_low'].iloc[i]:
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['low'].iloc[i]

                # Check if low holds for defense period
                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    future_lows = df['low'].iloc[i+1:check_end_idx+1]
                    if (future_lows < extreme_price).any():
                        break  # Low was breached

                    if hours_held >= min_defense_hours:
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        # Apply higher timeframe filter
                        if htf_filter:
                            if not apply_htf_filter(df, entry_idx, htf_filter, 'LONG'):
                                break

                        entry_price = df['close'].iloc[entry_idx]

                        # Apply entry offset for limit order
                        if entry_offset_pct != 0:
                            entry_price = entry_price * (1 + entry_offset_pct/100)

                        signals.append({
                            'type': 'ACCUMULATION',
                            'extreme_time': df['timestamp'].iloc[i],
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': df['timestamp'].iloc[entry_idx],
                            'entry_price': entry_price,
                            'entry_idx': entry_idx,
                            'avg_volume_ratio': volume_window.mean(),
                            'session': get_session(df['timestamp'].iloc[entry_idx].hour)
                        })
                        break

        # Check for DISTRIBUTION zone (SHORT)
        if direction_filter in ['short', 'both'] and df['local_high'].iloc[i]:
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['high'].iloc[i]

                # Check if high holds for defense period
                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    future_highs = df['high'].iloc[i+1:check_end_idx+1]
                    if (future_highs > extreme_price).any():
                        break  # High was breached

                    if hours_held >= min_defense_hours:
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        # Apply higher timeframe filter
                        if htf_filter:
                            if not apply_htf_filter(df, entry_idx, htf_filter, 'SHORT'):
                                break

                        entry_price = df['close'].iloc[entry_idx]

                        # Apply entry offset for limit order
                        if entry_offset_pct != 0:
                            entry_price = entry_price * (1 + entry_offset_pct/100)

                        signals.append({
                            'type': 'DISTRIBUTION',
                            'extreme_time': df['timestamp'].iloc[i],
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': df['timestamp'].iloc[entry_idx],
                            'entry_price': entry_price,
                            'entry_idx': entry_idx,
                            'avg_volume_ratio': volume_window.mean(),
                            'session': get_session(df['timestamp'].iloc[entry_idx].hour)
                        })
                        break

    return pd.DataFrame(signals)

def get_session(hour):
    """Get trading session from hour"""
    if 0 <= hour < 8:
        return 'Asia'
    elif 8 <= hour < 14:
        return 'Europe'
    elif 14 <= hour < 21:
        return 'US'
    else:
        return 'Overnight'

def calculate_rsi(series, period):
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_adx(df, period):
    """Calculate ADX"""
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()

    return adx

def apply_htf_filter(df, entry_idx, htf_filter, direction):
    """Apply higher timeframe filters"""
    if 'sma_trend' in htf_filter:
        if direction == 'LONG':
            if df['close'].iloc[entry_idx] < df['sma_50_1h'].iloc[entry_idx]:
                return False
        else:  # SHORT
            if df['close'].iloc[entry_idx] > df['sma_50_1h'].iloc[entry_idx]:
                return False

    if 'min_adx' in htf_filter:
        if df['adx_14_1h'].iloc[entry_idx] < htf_filter['min_adx']:
            return False

    if 'rsi_range' in htf_filter:
        rsi = df['rsi_14_1h'].iloc[entry_idx]
        if not (htf_filter['rsi_range'][0] <= rsi <= htf_filter['rsi_range'][1]):
            return False

    return True

def backtest_strategy(df, signals_df, stop_loss_pct=1.0, take_profit_pct=10.0, max_hold_hours=48):
    """Backtest with risk management"""

    if len(signals_df) == 0:
        return None

    trades = []

    for idx, signal in signals_df.iterrows():
        entry_idx = signal['entry_idx']
        entry_price = signal['entry_price']
        direction = 1 if signal['type'] == 'ACCUMULATION' else -1

        # Calculate stops
        if direction == 1:  # LONG
            stop_price = entry_price * (1 - stop_loss_pct/100)
            target_price = entry_price * (1 + take_profit_pct/100)
        else:  # SHORT
            stop_price = entry_price * (1 + stop_loss_pct/100)
            target_price = entry_price * (1 - take_profit_pct/100)

        # Simulate trade
        exit_idx = min(entry_idx + max_hold_hours*60, len(df)-1)
        exit_price = None
        exit_reason = 'TIME'

        for i in range(entry_idx+1, exit_idx+1):
            if direction == 1:  # LONG
                if df['low'].iloc[i] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['high'].iloc[i] >= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if df['high'].iloc[i] >= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['low'].iloc[i] <= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df['close'].iloc[exit_idx]

        # Calculate P&L
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Subtract fees
        pnl_pct -= 0.10

        trades.append({
            'entry_time': signal['entry_time'],
            'entry_price': entry_price,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'session': signal['session']
        })

    trades_df = pd.DataFrame(trades)

    if len(trades_df) == 0:
        return None

    # Calculate metrics
    total_return = trades_df['pnl_pct'].sum()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df)

    # Calculate drawdown
    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    if max_dd == 0:
        max_dd = -0.01  # Prevent division by zero

    return_dd_ratio = abs(total_return / max_dd)

    return {
        'trades': len(trades_df),
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd_ratio': return_dd_ratio,
        'win_rate': win_rate,
        'trades_df': trades_df
    }

def optimize_sessions(df):
    """Test each session separately"""
    print("\n" + "="*60)
    print("OPTIMIZATION 1: SESSION FILTERING")
    print("="*60)

    sessions = ['all', 'asia', 'europe', 'us', 'overnight']
    results = []

    for session in sessions:
        print(f"\nTesting {session.upper()} session...")

        signals = detect_defended_levels(df,
                                        lookback=20,
                                        volume_mult=2.5,
                                        min_defense_hours=12,
                                        max_defense_hours=24,
                                        min_volume_bars=5,
                                        session_filter=session)

        if len(signals) == 0:
            print(f"  No signals for {session}")
            continue

        backtest = backtest_strategy(df, signals, stop_loss_pct=1.0, take_profit_pct=10.0)

        if backtest:
            results.append({
                'session': session,
                'signals': len(signals),
                'trades': backtest['trades'],
                'return': backtest['total_return'],
                'max_dd': backtest['max_dd'],
                'return_dd': backtest['return_dd_ratio'],
                'win_rate': backtest['win_rate']
            })

            print(f"  Signals: {len(signals)} | Trades: {backtest['trades']} | "
                  f"Return: {backtest['total_return']:+.2f}% | DD: {backtest['max_dd']:.2f}% | "
                  f"R/DD: {backtest['return_dd_ratio']:.2f}x | WR: {backtest['win_rate']*100:.1f}%")

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_dd', ascending=False)

    print(f"\nBEST SESSION: {results_df.iloc[0]['session'].upper()}")
    print(f"  Return/DD: {results_df.iloc[0]['return_dd']:.2f}x")

    return results_df

def optimize_direction(df):
    """Test LONG-only, SHORT-only, or both"""
    print("\n" + "="*60)
    print("OPTIMIZATION 2: DIRECTION BIAS")
    print("="*60)

    directions = ['both', 'long', 'short']
    results = []

    for direction in directions:
        print(f"\nTesting {direction.upper()} direction...")

        signals = detect_defended_levels(df,
                                        lookback=20,
                                        volume_mult=2.5,
                                        min_defense_hours=12,
                                        max_defense_hours=24,
                                        min_volume_bars=5,
                                        direction_filter=direction)

        if len(signals) == 0:
            print(f"  No signals for {direction}")
            continue

        backtest = backtest_strategy(df, signals, stop_loss_pct=1.0, take_profit_pct=10.0)

        if backtest:
            results.append({
                'direction': direction,
                'signals': len(signals),
                'trades': backtest['trades'],
                'return': backtest['total_return'],
                'max_dd': backtest['max_dd'],
                'return_dd': backtest['return_dd_ratio'],
                'win_rate': backtest['win_rate']
            })

            print(f"  Signals: {len(signals)} | Trades: {backtest['trades']} | "
                  f"Return: {backtest['total_return']:+.2f}% | DD: {backtest['max_dd']:.2f}% | "
                  f"R/DD: {backtest['return_dd_ratio']:.2f}x | WR: {backtest['win_rate']*100:.1f}%")

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_dd', ascending=False)

    print(f"\nBEST DIRECTION: {results_df.iloc[0]['direction'].upper()}")
    print(f"  Return/DD: {results_df.iloc[0]['return_dd']:.2f}x")

    return results_df

def optimize_entry_offset(df):
    """Test limit order entry with various offsets"""
    print("\n" + "="*60)
    print("OPTIMIZATION 3: ENTRY OPTIMIZATION (Limit Orders)")
    print("="*60)

    offsets = [0, -0.05, -0.1, -0.15, -0.2]  # Negative = place limit below market
    results = []

    for offset in offsets:
        print(f"\nTesting entry offset {offset:+.2f}%...")

        signals = detect_defended_levels(df,
                                        lookback=20,
                                        volume_mult=2.5,
                                        min_defense_hours=12,
                                        max_defense_hours=24,
                                        min_volume_bars=5,
                                        entry_offset_pct=offset)

        if len(signals) == 0:
            print(f"  No signals")
            continue

        backtest = backtest_strategy(df, signals, stop_loss_pct=1.0, take_profit_pct=10.0)

        if backtest:
            results.append({
                'offset': offset,
                'signals': len(signals),
                'trades': backtest['trades'],
                'return': backtest['total_return'],
                'max_dd': backtest['max_dd'],
                'return_dd': backtest['return_dd_ratio'],
                'win_rate': backtest['win_rate']
            })

            print(f"  Signals: {len(signals)} | Trades: {backtest['trades']} | "
                  f"Return: {backtest['total_return']:+.2f}% | DD: {backtest['max_dd']:.2f}% | "
                  f"R/DD: {backtest['return_dd_ratio']:.2f}x | WR: {backtest['win_rate']*100:.1f}%")

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_dd', ascending=False)

    print(f"\nBEST ENTRY OFFSET: {results_df.iloc[0]['offset']:+.2f}%")
    print(f"  Return/DD: {results_df.iloc[0]['return_dd']:.2f}x")

    return results_df

def main():
    print("="*60)
    print("ETH DEFENDED LEVELS - COMPREHENSIVE OPTIMIZATION")
    print("="*60)

    # Load data
    df = load_data()
    print(f"\nLoaded {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Run optimizations
    all_results = {}

    all_results['sessions'] = optimize_sessions(df)
    all_results['directions'] = optimize_direction(df)
    all_results['entry_offsets'] = optimize_entry_offset(df)

    # Save all results
    print("\n" + "="*60)
    print("SAVING OPTIMIZATION RESULTS")
    print("="*60)

    for name, results in all_results.items():
        filename = f'/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimize_{name}.csv'
        results.to_csv(filename, index=False)
        print(f"✅ Saved {filename}")

    print("\n✅ Optimization complete!")

if __name__ == '__main__':
    main()
