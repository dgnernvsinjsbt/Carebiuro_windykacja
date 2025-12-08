import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

def detect_defended_levels(df,
                           lookback=20,
                           volume_mult=2.0,
                           min_defense_hours=12,
                           max_defense_hours=36,
                           min_volume_bars=3):
    """
    Detect accumulation/distribution zones where price extremes are defended.

    Logic:
    - Find local highs/lows with elevated volume
    - Check if the extreme holds (not breached) for X hours
    - Enter expecting reversal after defense period

    Args:
        lookback: bars to check for local high/low
        volume_mult: volume must be X times the average
        min_defense_hours: minimum time extreme must hold
        max_defense_hours: maximum time to wait for entry
        min_volume_bars: minimum consecutive bars with elevated volume
    """

    print(f"\n{'='*60}")
    print("DEFENDED LEVELS PATTERN DETECTOR")
    print(f"{'='*60}")
    print(f"Lookback: {lookback} bars")
    print(f"Volume threshold: {volume_mult}x average")
    print(f"Defense period: {min_defense_hours}-{max_defense_hours} hours")
    print(f"Min volume bars: {min_volume_bars}")

    # Calculate rolling average volume
    df['volume_sma'] = df['volume'].rolling(100).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    # Find local highs and lows
    df['local_high'] = df['high'] == df['high'].rolling(lookback*2+1, center=True).max()
    df['local_low'] = df['low'] == df['low'].rolling(lookback*2+1, center=True).min()

    signals = []

    # Scan for defended levels
    for i in range(lookback, len(df) - max_defense_hours*60):

        # Check for DISTRIBUTION zone (local high with volume)
        if df['local_high'].iloc[i]:
            # Check if we have elevated volume around this high
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['high'].iloc[i]
                extreme_time = df['timestamp'].iloc[i]

                # Check if high holds (not breached) for the defense period
                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    # Check if high was breached in this period
                    future_highs = df['high'].iloc[i+1:check_end_idx+1]
                    if (future_highs > extreme_price).any():
                        break  # High was breached, not a defended level

                    # If we've held for at least min_defense_hours, we have a signal
                    if hours_held >= min_defense_hours:
                        # Entry at the point where we confirm defense
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        entry_price = df['close'].iloc[entry_idx]
                        entry_time = df['timestamp'].iloc[entry_idx]

                        # Look for the outcome over next 48 hours
                        exit_idx = min(entry_idx + 48*60, len(df)-1)
                        future_low = df['low'].iloc[entry_idx:exit_idx+1].min()
                        future_high = df['high'].iloc[entry_idx:exit_idx+1].max()

                        max_profit = ((future_low - entry_price) / entry_price) * 100  # SHORT
                        max_loss = ((future_high - entry_price) / entry_price) * 100

                        signals.append({
                            'type': 'DISTRIBUTION',
                            'extreme_time': extreme_time,
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'avg_volume_ratio': volume_window.mean(),
                            'max_profit_pct': max_profit,
                            'max_loss_pct': max_loss,
                            'follow_through': max_profit < -2.0  # Did we get 2%+ breakdown?
                        })

                        break  # Only take first valid signal from this level

        # Check for ACCUMULATION zone (local low with volume)
        if df['local_low'].iloc[i]:
            # Check if we have elevated volume around this low
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['low'].iloc[i]
                extreme_time = df['timestamp'].iloc[i]

                # Check if low holds (not breached) for the defense period
                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    # Check if low was breached in this period
                    future_lows = df['low'].iloc[i+1:check_end_idx+1]
                    if (future_lows < extreme_price).any():
                        break  # Low was breached, not a defended level

                    # If we've held for at least min_defense_hours, we have a signal
                    if hours_held >= min_defense_hours:
                        # Entry at the point where we confirm defense
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        entry_price = df['close'].iloc[entry_idx]
                        entry_time = df['timestamp'].iloc[entry_idx]

                        # Look for the outcome over next 48 hours
                        exit_idx = min(entry_idx + 48*60, len(df)-1)
                        future_high = df['high'].iloc[entry_idx:exit_idx+1].max()
                        future_low = df['low'].iloc[entry_idx:exit_idx+1].min()

                        max_profit = ((future_high - entry_price) / entry_price) * 100  # LONG
                        max_loss = ((future_low - entry_price) / entry_price) * 100

                        signals.append({
                            'type': 'ACCUMULATION',
                            'extreme_time': extreme_time,
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'avg_volume_ratio': volume_window.mean(),
                            'max_profit_pct': max_profit,
                            'max_loss_pct': max_loss,
                            'follow_through': max_profit > 2.0  # Did we get 2%+ rally?
                        })

                        break  # Only take first valid signal from this level

    return pd.DataFrame(signals)


def analyze_pattern(df, signals_df):
    """Analyze the defended levels pattern"""

    print(f"\n{'='*60}")
    print("PATTERN ANALYSIS")
    print(f"{'='*60}")

    if len(signals_df) == 0:
        print("No signals found!")
        return

    print(f"\nTotal signals: {len(signals_df)}")
    print(f"  - Accumulation (LONG): {(signals_df['type'] == 'ACCUMULATION').sum()}")
    print(f"  - Distribution (SHORT): {(signals_df['type'] == 'DISTRIBUTION').sum()}")

    # Analyze by type
    for signal_type in ['ACCUMULATION', 'DISTRIBUTION']:
        type_signals = signals_df[signals_df['type'] == signal_type]
        if len(type_signals) == 0:
            continue

        print(f"\n{signal_type} ZONES:")
        print(f"  Signals: {len(type_signals)}")
        print(f"  Avg hours held: {type_signals['hours_held'].mean():.1f}")
        print(f"  Avg volume ratio: {type_signals['avg_volume_ratio'].mean():.2f}x")
        print(f"  Follow-through rate: {type_signals['follow_through'].mean()*100:.1f}%")
        print(f"  Avg max profit: {type_signals['max_profit_pct'].mean():.2f}%")
        print(f"  Avg max loss: {type_signals['max_loss_pct'].mean():.2f}%")

        # Show big winners (>3% move)
        big_winners = type_signals[abs(type_signals['max_profit_pct']) > 3.0]
        print(f"  Big moves (>3%): {len(big_winners)} ({len(big_winners)/len(type_signals)*100:.1f}%)")
        if len(big_winners) > 0:
            print(f"    Avg size: {big_winners['max_profit_pct'].abs().mean():.2f}%")

    # Show top 10 signals by absolute profit
    print(f"\n{'='*60}")
    print("TOP 10 SIGNALS BY ABSOLUTE PROFIT:")
    print(f"{'='*60}")
    signals_df['abs_profit'] = signals_df['max_profit_pct'].abs()
    top_signals = signals_df.nlargest(10, 'abs_profit')
    for idx, row in top_signals.iterrows():
        direction = "LONG" if row['type'] == 'ACCUMULATION' else "SHORT"
        print(f"{row['entry_time']} | {direction} @ {row['entry_price']:.2f} | "
              f"Held {row['hours_held']}h | Max P/L: {row['max_profit_pct']:+.2f}% | "
              f"Vol: {row['avg_volume_ratio']:.2f}x | Follow: {'✓' if row['follow_through'] else '✗'}")

    return signals_df


def backtest_strategy(df, signals_df, stop_loss_pct=1.5, take_profit_pct=3.0, max_hold_hours=48):
    """
    Backtest the defended levels strategy with risk management
    """

    print(f"\n{'='*60}")
    print("BACKTEST WITH RISK MANAGEMENT")
    print(f"{'='*60}")
    print(f"Stop Loss: {stop_loss_pct}%")
    print(f"Take Profit: {take_profit_pct}%")
    print(f"Max Hold: {max_hold_hours} hours")
    print(f"Fees: 0.10% per trade (0.05% x2)")

    trades = []

    for idx, signal in signals_df.iterrows():
        entry_idx = df[df['timestamp'] == signal['entry_time']].index[0]
        entry_price = signal['entry_price']
        direction = 1 if signal['type'] == 'ACCUMULATION' else -1  # 1=LONG, -1=SHORT

        # Calculate stop and target
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

        # If no SL/TP hit, exit at time limit
        if exit_price is None:
            exit_price = df['close'].iloc[exit_idx]

        # Calculate P&L
        if direction == 1:  # LONG
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Subtract fees (0.10% round-trip)
        pnl_pct -= 0.10

        trades.append({
            'entry_time': signal['entry_time'],
            'entry_price': entry_price,
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'hours_held': signal['hours_held'],
            'volume_ratio': signal['avg_volume_ratio']
        })

    trades_df = pd.DataFrame(trades)

    if len(trades_df) == 0:
        print("No trades executed!")
        return None

    # Calculate metrics
    total_return = trades_df['pnl_pct'].sum()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df)
    avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] > 0).any() else 0
    avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] < 0).any() else 0

    # Calculate drawdown
    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    print(f"\nRESULTS:")
    print(f"  Total trades: {len(trades_df)}")
    print(f"  Total return: {total_return:+.2f}%")
    print(f"  Max drawdown: {max_dd:.2f}%")
    print(f"  Return/DD: {abs(total_return/max_dd):.2f}x" if max_dd != 0 else "  Return/DD: N/A")
    print(f"  Win rate: {win_rate*100:.1f}%")
    print(f"  Avg win: {avg_win:+.2f}%")
    print(f"  Avg loss: {avg_loss:+.2f}%")
    print(f"  Profit factor: {abs(avg_win/avg_loss):.2f}x" if avg_loss != 0 else "  Profit factor: N/A")

    # Exit breakdown
    print(f"\nEXIT BREAKDOWN:")
    exit_counts = trades_df['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        pct = count / len(trades_df) * 100
        avg_pnl = trades_df[trades_df['exit_reason'] == reason]['pnl_pct'].mean()
        print(f"  {reason}: {count} ({pct:.1f}%) | Avg P&L: {avg_pnl:+.2f}%")

    # Direction breakdown
    print(f"\nDIRECTION BREAKDOWN:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = trades_df[trades_df['direction'] == direction]
        if len(dir_trades) > 0:
            print(f"  {direction}: {len(dir_trades)} trades | Return: {dir_trades['pnl_pct'].sum():+.2f}% | "
                  f"Win rate: {(dir_trades['pnl_pct'] > 0).sum()/len(dir_trades)*100:.1f}%")

    return trades_df


if __name__ == '__main__':
    # Load data
    print("Loading ETH 1m data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"Loaded {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test different parameter combinations
    configs = [
        {'lookback': 20, 'volume_mult': 2.0, 'min_defense_hours': 18, 'max_defense_hours': 30, 'min_volume_bars': 3},
        {'lookback': 20, 'volume_mult': 2.5, 'min_defense_hours': 12, 'max_defense_hours': 24, 'min_volume_bars': 5},
        {'lookback': 30, 'volume_mult': 2.0, 'min_defense_hours': 24, 'max_defense_hours': 36, 'min_volume_bars': 3},
    ]

    best_result = None
    best_ratio = -999

    for i, config in enumerate(configs):
        print(f"\n{'#'*60}")
        print(f"CONFIG #{i+1}")
        print(f"{'#'*60}")

        # Detect patterns
        signals_df = detect_defended_levels(df, **config)

        if len(signals_df) == 0:
            print("No signals found with this config")
            continue

        # Analyze
        analyze_pattern(df, signals_df)

        # Backtest
        trades_df = backtest_strategy(df, signals_df,
                                      stop_loss_pct=1.5,
                                      take_profit_pct=3.0,
                                      max_hold_hours=48)

        if trades_df is not None:
            total_return = trades_df['pnl_pct'].sum()
            max_dd = (trades_df['pnl_pct'].cumsum() - trades_df['pnl_pct'].cumsum().cummax()).min()
            ratio = abs(total_return / max_dd) if max_dd != 0 else 0

            if ratio > best_ratio:
                best_ratio = ratio
                best_result = {
                    'config': config,
                    'trades_df': trades_df,
                    'signals_df': signals_df,
                    'total_return': total_return,
                    'max_dd': max_dd,
                    'ratio': ratio
                }

    # Save best result
    if best_result:
        print(f"\n{'='*60}")
        print(f"BEST CONFIG FOUND!")
        print(f"{'='*60}")
        print(f"Config: {best_result['config']}")
        print(f"Return: {best_result['total_return']:+.2f}%")
        print(f"Max DD: {best_result['max_dd']:.2f}%")
        print(f"Return/DD: {best_result['ratio']:.2f}x")

        best_result['trades_df'].to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_trades.csv', index=False)
        best_result['signals_df'].to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_signals.csv', index=False)
        print(f"\nSaved results to trading/results/")
