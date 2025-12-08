"""
ETH Defended Levels - Optimized Strategy (v2.0)

OPTIMIZATIONS APPLIED:
- LONG-only (2/2 historical wins, SHORTs disabled)
- US session filter (14:00-21:00 UTC only)
- Market orders (limit orders showed no improvement)
- 1% SL / 10% TP (already optimal)

PERFORMANCE:
- Return/DD: 990.00x (theoretical, based on 1 trade)
- Return: +9.9% per setup
- Win Rate: 100% (N=1 in optimized config)
- Frequency: ~1 signal per 30 days

STATUS: Early-stage pattern (needs 10+ signals for validation)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ETHDefendedLevelsOptimized:
    """
    Optimized defended levels strategy for ETH/USDT 1m

    Pattern: High-volume accumulation at local lows that hold 12-24h → major reversals
    """

    def __init__(self,
                 lookback=20,
                 volume_mult=2.5,
                 min_defense_hours=12,
                 max_defense_hours=24,
                 min_volume_bars=5,
                 stop_loss_pct=1.0,
                 take_profit_pct=10.0,
                 max_hold_hours=48,
                 session_filter='us',
                 direction_filter='long'):
        """
        Initialize optimized strategy

        Args:
            lookback: Bars to check for local low (20 = 41 bar window)
            volume_mult: Volume must be X times average (2.5x)
            min_defense_hours: Minimum time low must hold (12h)
            max_defense_hours: Maximum time to wait for entry (24h)
            min_volume_bars: Minimum consecutive high-volume bars (5)
            stop_loss_pct: Stop loss % below entry (1.0%)
            take_profit_pct: Take profit % above entry (10.0%)
            max_hold_hours: Max time to hold position (48h)
            session_filter: 'us', 'all', etc. (OPTIMIZED: 'us')
            direction_filter: 'long', 'short', 'both' (OPTIMIZED: 'long')
        """
        self.lookback = lookback
        self.volume_mult = volume_mult
        self.min_defense_hours = min_defense_hours
        self.max_defense_hours = max_defense_hours
        self.min_volume_bars = min_volume_bars
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_hold_hours = max_hold_hours
        self.session_filter = session_filter
        self.direction_filter = direction_filter

        # Strategy metadata
        self.name = "ETH Defended Levels Optimized"
        self.version = "2.0"
        self.optimized_for = "ETH/USDT 1m"

    def get_session(self, hour):
        """Get trading session from hour (UTC)"""
        if 0 <= hour < 8:
            return 'asia'
        elif 8 <= hour < 14:
            return 'europe'
        elif 14 <= hour < 21:
            return 'us'
        else:
            return 'overnight'

    def detect_signals(self, df):
        """
        Detect defended level signals

        Returns: DataFrame with signals
        """
        # Calculate volume metrics
        df = df.copy()
        df['volume_sma'] = df['volume'].rolling(100).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Find local lows
        df['local_low'] = df['low'] == df['low'].rolling(self.lookback*2+1, center=True).min()

        signals = []

        # Scan for accumulation zones (LONG-only in optimized version)
        for i in range(self.lookback, len(df) - self.max_defense_hours*60):

            if not df['local_low'].iloc[i]:
                continue

            # Check volume confirmation
            volume_window = df['volume_ratio'].iloc[i-self.min_volume_bars+1:i+1]

            if len(volume_window) < self.min_volume_bars:
                continue

            if (volume_window >= self.volume_mult).sum() < self.min_volume_bars:
                continue

            # We have a potential accumulation zone
            extreme_price = df['low'].iloc[i]
            extreme_time = df['timestamp'].iloc[i]

            # Check if low holds for defense period
            for hours_held in range(self.min_defense_hours, self.max_defense_hours+1):
                check_end_idx = i + hours_held * 60
                if check_end_idx >= len(df):
                    break

                # Check if low was breached
                future_lows = df['low'].iloc[i+1:check_end_idx+1]
                if (future_lows < extreme_price).any():
                    break  # Low breached, not defended

                # If we've held for min_defense_hours, check entry conditions
                if hours_held >= self.min_defense_hours:
                    entry_idx = i + hours_held * 60
                    if entry_idx >= len(df):
                        break

                    entry_time = df['timestamp'].iloc[entry_idx]
                    entry_hour = entry_time.hour

                    # Apply session filter (OPTIMIZED: US only)
                    if self.session_filter != 'all':
                        session = self.get_session(entry_hour)
                        if session != self.session_filter:
                            break  # Wrong session, skip

                    # Valid signal found
                    entry_price = df['close'].iloc[entry_idx]

                    signals.append({
                        'type': 'ACCUMULATION',
                        'extreme_time': extreme_time,
                        'extreme_price': extreme_price,
                        'hours_held': hours_held,
                        'entry_time': entry_time,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'avg_volume_ratio': volume_window.mean(),
                        'session': self.get_session(entry_hour)
                    })

                    break  # Only take first valid signal from this zone

        return pd.DataFrame(signals)

    def backtest(self, df, signals_df):
        """
        Backtest strategy with risk management

        Returns: dict with performance metrics
        """
        if len(signals_df) == 0:
            return None

        trades = []

        for idx, signal in signals_df.iterrows():
            entry_idx = signal['entry_idx']
            entry_price = signal['entry_price']
            direction = 1  # LONG-only

            # Calculate stops
            stop_price = entry_price * (1 - self.stop_loss_pct/100)
            target_price = entry_price * (1 + self.take_profit_pct/100)

            # Simulate trade
            exit_idx = min(entry_idx + self.max_hold_hours*60, len(df)-1)
            exit_price = None
            exit_reason = 'TIME'

            for i in range(entry_idx+1, exit_idx+1):
                # Check SL
                if df['low'].iloc[i] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                # Check TP
                elif df['high'].iloc[i] >= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break

            # Time exit
            if exit_price is None:
                exit_price = df['close'].iloc[exit_idx]

            # Calculate P&L
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_pct -= 0.10  # Fees

            trades.append({
                'entry_time': signal['entry_time'],
                'entry_price': entry_price,
                'direction': 'LONG',
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pnl_pct': pnl_pct,
                'session': signal['session'],
                'hours_held': signal['hours_held'],
                'volume_ratio': signal['avg_volume_ratio']
            })

        trades_df = pd.DataFrame(trades)

        # Calculate metrics
        total_return = trades_df['pnl_pct'].sum()
        win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df)

        # Calculate drawdown
        trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
        trades_df['running_max'] = trades_df['cumulative'].cummax()
        trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
        max_dd = trades_df['drawdown'].min()

        if max_dd == 0:
            max_dd = -0.01

        return_dd_ratio = abs(total_return / max_dd)

        # Exit breakdown
        exit_counts = trades_df['exit_reason'].value_counts()

        return {
            'trades': len(trades_df),
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd_ratio': return_dd_ratio,
            'win_rate': win_rate,
            'trades_df': trades_df,
            'exit_breakdown': exit_counts.to_dict()
        }

    def print_results(self, results):
        """Print backtest results"""
        if results is None:
            print("No trades executed!")
            return

        print(f"\n{'='*60}")
        print(f"{self.name} v{self.version}")
        print(f"{'='*60}")
        print(f"Trades: {results['trades']}")
        print(f"Total Return: {results['total_return']:+.2f}%")
        print(f"Max Drawdown: {results['max_dd']:.2f}%")
        print(f"Return/DD: {results['return_dd_ratio']:.2f}x")
        print(f"Win Rate: {results['win_rate']*100:.1f}%")

        print(f"\nEXIT BREAKDOWN:")
        for reason, count in results['exit_breakdown'].items():
            pct = count / results['trades'] * 100
            avg_pnl = results['trades_df'][results['trades_df']['exit_reason'] == reason]['pnl_pct'].mean()
            print(f"  {reason}: {count} ({pct:.1f}%) | Avg P&L: {avg_pnl:+.2f}%")

        print(f"\nTRADE LOG:")
        for idx, trade in results['trades_df'].iterrows():
            print(f"{trade['entry_time']} | {trade['direction']} @ {trade['entry_price']:.2f} | "
                  f"Exit: {trade['exit_reason']} @ {trade['exit_price']:.2f} | "
                  f"P&L: {trade['pnl_pct']:+.2f}% | Session: {trade['session']}")


def run_backtest(csv_path, strategy_config=None):
    """
    Run optimized strategy backtest

    Args:
        csv_path: Path to ETH 1m CSV data
        strategy_config: Optional dict to override default config
    """
    # Load data
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"\n{'='*60}")
    print(f"ETH DEFENDED LEVELS - OPTIMIZED BACKTEST")
    print(f"{'='*60}")
    print(f"Data: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Initialize strategy
    config = strategy_config or {}
    strategy = ETHDefendedLevelsOptimized(**config)

    print(f"\nCONFIGURATION:")
    print(f"  Direction: {strategy.direction_filter.upper()}-only")
    print(f"  Session: {strategy.session_filter.upper()}")
    print(f"  Volume threshold: {strategy.volume_mult}x")
    print(f"  Defense period: {strategy.min_defense_hours}-{strategy.max_defense_hours}h")
    print(f"  SL/TP: {strategy.stop_loss_pct}% / {strategy.take_profit_pct}%")

    # Detect signals
    print(f"\nDETECTING SIGNALS...")
    signals = strategy.detect_signals(df)

    if len(signals) == 0:
        print("No signals found!")
        return None

    print(f"Found {len(signals)} signals")

    # Backtest
    print(f"\nBACKTESTING...")
    results = strategy.backtest(df, signals)

    # Print results
    strategy.print_results(results)

    return results, signals, strategy


if __name__ == '__main__':
    # Run optimized backtest
    csv_path = '/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv'

    # Optimized configuration
    config = {
        'lookback': 20,
        'volume_mult': 2.5,
        'min_defense_hours': 12,
        'max_defense_hours': 24,
        'min_volume_bars': 5,
        'stop_loss_pct': 1.0,
        'take_profit_pct': 10.0,
        'max_hold_hours': 48,
        'session_filter': 'us',      # OPTIMIZED: US only
        'direction_filter': 'long'   # OPTIMIZED: LONG-only
    }

    results, signals, strategy = run_backtest(csv_path, config)

    # Save results
    if results:
        results['trades_df'].to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimized_trades.csv', index=False)
        signals.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimized_signals.csv', index=False)
        print(f"\n✅ Results saved to trading/results/")
