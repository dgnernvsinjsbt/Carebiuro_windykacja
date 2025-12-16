"""
FARTCOIN/USDT Momentum Breakout Strategy V2 - OPTIMIZED
Target: 8:1+ Risk:Reward via high-quality breakouts

Key improvements:
- Stricter breakout filtering (higher quality setups)
- Longer consolidation detection (10 -> 15 periods)
- Higher volume surge requirement (2x -> 2.5x)
- Tighter compression threshold (0.5 -> 0.4)
- Removed early momentum death exit (let winners run)
- Extended time stop (30 -> 60 minutes)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class BreakoutStrategyV2:
    def __init__(self,
                 consolidation_periods: int = 15,
                 atr_period: int = 14,
                 volume_ma_period: int = 20,
                 volume_surge_multiplier: float = 2.5,
                 compression_threshold: float = 0.4,
                 risk_reward_target: float = 8.0,
                 secondary_target: float = 12.0,
                 trailing_activation: float = 6.0,
                 max_trade_duration_mins: int = 60,
                 fee_percent: float = 0.1):
        """
        Initialize optimized breakout strategy

        Key changes from V1:
        - consolidation_periods: 10 -> 15 (longer compression)
        - volume_surge_multiplier: 2.0 -> 2.5 (stronger volume)
        - compression_threshold: 0.5 -> 0.4 (tighter compression)
        - trailing_activation: 5.0 -> 6.0 (later activation)
        - max_trade_duration_mins: 30 -> 60 (hold longer)
        """
        self.consolidation_periods = consolidation_periods
        self.atr_period = atr_period
        self.volume_ma_period = volume_ma_period
        self.volume_surge_multiplier = volume_surge_multiplier
        self.compression_threshold = compression_threshold
        self.risk_reward_target = risk_reward_target
        self.secondary_target = secondary_target
        self.trailing_activation = trailing_activation
        self.max_trade_duration_mins = max_trade_duration_mins
        self.fee_percent = fee_percent / 100

    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load and prepare OHLCV data"""
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()

        return atr

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = df.copy()

        # ATR for volatility measurement
        df['atr'] = self.calculate_atr(df)
        df['atr_ma'] = df['atr'].rolling(window=self.consolidation_periods).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Price range analysis
        df['candle_range'] = df['high'] - df['low']
        df['candle_body'] = abs(df['close'] - df['open'])
        df['body_ratio'] = df['candle_body'] / df['candle_range']

        # Consolidation zone detection
        df['high_high'] = df['high'].rolling(window=self.consolidation_periods).max()
        df['low_low'] = df['low'].rolling(window=self.consolidation_periods).min()
        df['consolidation_range'] = df['high_high'] - df['low_low']
        df['consolidation_range_pct'] = (df['consolidation_range'] / df['close']) * 100

        # Directional strength
        df['bullish'] = (df['close'] > df['open']).astype(int)
        df['bearish'] = (df['close'] < df['open']).astype(int)

        # Additional filters for quality
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['close_position'] = df['close_position'].fillna(0.5)

        return df

    def detect_breakout(self, df: pd.DataFrame, idx: int) -> Tuple[str, float, float]:
        """
        Detect high-quality breakout with strict filtering
        """
        if idx < self.consolidation_periods + self.atr_period + 1:
            return None, None, None

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Require strong compression in previous candle
        is_compressed = previous['atr_ratio'] < self.compression_threshold

        if not is_compressed:
            return None, None, None

        # Require significant volume surge
        has_volume_surge = current['volume_ratio'] >= self.volume_surge_multiplier

        if not has_volume_surge:
            return None, None, None

        # Additional filter: consolidation range should be meaningful but not too wide
        if previous['consolidation_range_pct'] < 0.5 or previous['consolidation_range_pct'] > 4.0:
            return None, None, None

        # Check for bullish breakout
        if (current['close'] > previous['high_high'] and
            current['bullish'] == 1 and
            current['body_ratio'] > 0.6 and  # Strong directional candle
            current['close_position'] > 0.7):  # Close near high

            entry = current['close']
            stop = previous['low_low'] - (current['atr'] * 0.3)  # Tighter buffer

            risk_pct = abs(entry - stop) / entry * 100
            if risk_pct < 0.4 or risk_pct > 2.5:  # Stricter risk range
                return None, None, None

            return 'LONG', entry, stop

        # Check for bearish breakout
        elif (current['close'] < previous['low_low'] and
              current['bearish'] == 1 and
              current['body_ratio'] > 0.6 and
              current['close_position'] < 0.3):  # Close near low

            entry = current['close']
            stop = previous['high_high'] + (current['atr'] * 0.3)

            risk_pct = abs(entry - stop) / entry * 100
            if risk_pct < 0.4 or risk_pct > 2.5:
                return None, None, None

            return 'SHORT', entry, stop

        return None, None, None

    def calculate_targets(self, direction: str, entry: float, stop: float) -> Dict[str, float]:
        """Calculate profit targets based on risk"""
        risk = abs(entry - stop)

        if direction == 'LONG':
            target_1 = entry + (risk * self.risk_reward_target)
            target_2 = entry + (risk * self.secondary_target)
            trailing_trigger = entry + (risk * self.trailing_activation)
        else:
            target_1 = entry - (risk * self.risk_reward_target)
            target_2 = entry - (risk * self.secondary_target)
            trailing_trigger = entry - (risk * self.trailing_activation)

        return {
            'target_1': target_1,
            'target_2': target_2,
            'trailing_trigger': trailing_trigger,
            'risk': risk
        }

    def manage_trade(self, df: pd.DataFrame, trade: Dict, current_idx: int) -> Dict:
        """
        Manage open trade - SIMPLIFIED to let winners run

        Removed early exits:
        - No momentum death check (let it run)
        - Only exits: stop loss, target hit, trailing stop, time stop
        """
        current = df.iloc[current_idx]
        entry_idx = trade['entry_idx']
        direction = trade['direction']
        entry = trade['entry']
        stop = trade['stop']
        targets = trade['targets']

        # Check time stop
        minutes_in_trade = current_idx - entry_idx
        if minutes_in_trade >= self.max_trade_duration_mins:
            return {
                **trade,
                'exit_price': current['close'],
                'exit_idx': current_idx,
                'exit_reason': 'TIME_STOP'
            }

        if direction == 'LONG':
            # Check stop loss
            if current['low'] <= stop:
                return {
                    **trade,
                    'exit_price': stop,
                    'exit_idx': current_idx,
                    'exit_reason': 'STOP_LOSS'
                }

            # Check target 1 (main target)
            if current['high'] >= targets['target_1']:
                return {
                    **trade,
                    'exit_price': targets['target_1'],
                    'exit_idx': current_idx,
                    'exit_reason': 'TARGET_8R'
                }

            # Check trailing stop activation (after 6R)
            peak_price = trade.get('peak_price', entry)
            if peak_price >= targets['trailing_trigger']:
                # Trail at 4R profit
                trail_stop = entry + (targets['risk'] * 4)
                if current['low'] <= trail_stop:
                    return {
                        **trade,
                        'exit_price': trail_stop,
                        'exit_idx': current_idx,
                        'exit_reason': 'TRAILING_4R'
                    }

            # Update peak
            trade['peak_price'] = max(trade.get('peak_price', entry), current['high'])

        else:  # SHORT
            # Check stop loss
            if current['high'] >= stop:
                return {
                    **trade,
                    'exit_price': stop,
                    'exit_idx': current_idx,
                    'exit_reason': 'STOP_LOSS'
                }

            # Check target 1
            if current['low'] <= targets['target_1']:
                return {
                    **trade,
                    'exit_price': targets['target_1'],
                    'exit_idx': current_idx,
                    'exit_reason': 'TARGET_8R'
                }

            # Check trailing stop
            low_price = trade.get('low_price', entry)
            if low_price <= targets['trailing_trigger']:
                trail_stop = entry - (targets['risk'] * 4)
                if current['high'] >= trail_stop:
                    return {
                        **trade,
                        'exit_price': trail_stop,
                        'exit_idx': current_idx,
                        'exit_reason': 'TRAILING_4R'
                    }

            # Update low
            trade['low_price'] = min(trade.get('low_price', entry), current['low'])

        return trade

    def calculate_pnl(self, trade: Dict) -> Dict:
        """Calculate P&L and R-multiple for completed trade"""
        direction = trade['direction']
        entry = trade['entry']
        exit_price = trade['exit_price']
        stop = trade['stop']

        # Calculate gross P&L
        if direction == 'LONG':
            gross_pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            gross_pnl_pct = ((entry - exit_price) / entry) * 100

        # Subtract fees
        net_pnl_pct = gross_pnl_pct - (self.fee_percent * 2 * 100)

        # Calculate R-multiple
        risk = abs(entry - stop)
        realized_pnl = abs(exit_price - entry) if gross_pnl_pct > 0 else -abs(exit_price - entry)
        r_multiple = realized_pnl / risk

        if direction == 'SHORT' and exit_price > entry:
            r_multiple = -abs(r_multiple)
        elif direction == 'LONG' and exit_price < entry:
            r_multiple = -abs(r_multiple)

        return {
            **trade,
            'gross_pnl_pct': gross_pnl_pct,
            'net_pnl_pct': net_pnl_pct,
            'r_multiple': r_multiple,
            'win': 1 if net_pnl_pct > 0 else 0
        }

    def backtest(self, df: pd.DataFrame) -> Tuple[List[Dict], pd.DataFrame]:
        """Run backtest on historical data"""
        df = self.calculate_indicators(df)

        trades = []
        open_trade = None
        equity = [1.0]
        cumulative_pnl = 0.0

        print("Starting backtest...")
        print(f"Total candles: {len(df)}")

        for idx in range(len(df)):
            if idx % 5000 == 0:
                print(f"Processing candle {idx}/{len(df)}...")

            # Look for new breakout if no open trade
            if open_trade is None:
                direction, entry, stop = self.detect_breakout(df, idx)

                if direction is not None:
                    targets = self.calculate_targets(direction, entry, stop)

                    open_trade = {
                        'entry_idx': idx,
                        'entry_timestamp': df.iloc[idx]['timestamp'],
                        'direction': direction,
                        'entry': entry,
                        'stop': stop,
                        'targets': targets
                    }

                    risk_pct = ((abs(entry-stop)/entry)*100)
                    print(f"\n{'='*60}")
                    print(f"NEW {direction} TRADE #{len(trades)+1} at {df.iloc[idx]['timestamp']}")
                    print(f"Entry: ${entry:.5f} | Stop: ${stop:.5f}")
                    print(f"Target 8R: ${targets['target_1']:.5f}")
                    print(f"Risk: {risk_pct:.2f}% | Target R:R: 8:1")
                    print(f"Volume surge: {df.iloc[idx]['volume_ratio']:.2f}x")
                    print(f"ATR compression: {df.iloc[idx-1]['atr_ratio']:.3f}")

            # Manage open trade
            else:
                updated_trade = self.manage_trade(df, open_trade, idx)

                if 'exit_price' in updated_trade:
                    completed_trade = self.calculate_pnl(updated_trade)
                    completed_trade['exit_timestamp'] = df.iloc[idx]['timestamp']

                    trades.append(completed_trade)

                    cumulative_pnl += completed_trade['net_pnl_pct']
                    equity.append(1.0 + (cumulative_pnl / 100))

                    print(f"CLOSED: {completed_trade['exit_reason']}")
                    print(f"Exit: ${completed_trade['exit_price']:.5f}")
                    print(f"P&L: {completed_trade['net_pnl_pct']:.2f}% | R: {completed_trade['r_multiple']:.2f}R")
                    print(f"Duration: {idx - completed_trade['entry_idx']} minutes")
                    print(f"Cumulative P&L: {cumulative_pnl:.2f}%")
                    print(f"{'='*60}\n")

                    open_trade = None
                else:
                    open_trade = updated_trade

        print(f"\nBacktest complete! Total trades: {len(trades)}")

        equity_df = pd.DataFrame({
            'equity': equity,
            'cumulative_pnl_pct': [(e - 1) * 100 for e in equity]
        })

        return trades, equity_df

    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance statistics"""
        if len(trades) == 0:
            return {'error': 'No trades executed'}

        trades_df = pd.DataFrame(trades)

        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['win'] == 1]
        losing_trades = trades_df[trades_df['win'] == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

        total_pnl = trades_df['net_pnl_pct'].sum()
        avg_win = winning_trades['net_pnl_pct'].mean() if win_count > 0 else 0
        avg_loss = losing_trades['net_pnl_pct'].mean() if loss_count > 0 else 0

        avg_r_multiple = trades_df['r_multiple'].mean()
        avg_win_r = winning_trades['r_multiple'].mean() if win_count > 0 else 0
        avg_loss_r = losing_trades['r_multiple'].mean() if loss_count > 0 else 0

        gross_profit = winning_trades['net_pnl_pct'].sum() if win_count > 0 else 0
        gross_loss = abs(losing_trades['net_pnl_pct'].sum()) if loss_count > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        expected_value = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        cumulative_pnl = trades_df['net_pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()

        trades_df['duration_minutes'] = trades_df['exit_idx'] - trades_df['entry_idx']
        avg_duration = trades_df['duration_minutes'].mean()

        # Target analysis
        target_hits = len(trades_df[trades_df['exit_reason'] == 'TARGET_8R'])
        trailing_exits = len(trades_df[trades_df['exit_reason'] == 'TRAILING_4R'])

        long_trades = trades_df[trades_df['direction'] == 'LONG']
        short_trades = trades_df[trades_df['direction'] == 'SHORT']

        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl_pct': total_pnl,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'avg_r_multiple': avg_r_multiple,
            'avg_win_r': avg_win_r,
            'avg_loss_r': avg_loss_r,
            'profit_factor': profit_factor,
            'expected_value': expected_value,
            'max_drawdown_pct': max_drawdown,
            'avg_trade_duration_mins': avg_duration,
            'target_8r_hits': target_hits,
            'trailing_4r_exits': trailing_exits,
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate': (len(long_trades[long_trades['win'] == 1]) / len(long_trades) * 100) if len(long_trades) > 0 else 0,
            'short_win_rate': (len(short_trades[short_trades['win'] == 1]) / len(short_trades) * 100) if len(short_trades) > 0 else 0,
        }


def main():
    """Main execution function"""
    print("=" * 80)
    print("FARTCOIN/USDT MOMENTUM BREAKOUT STRATEGY V2 - OPTIMIZED")
    print("=" * 80)
    print()

    strategy = BreakoutStrategyV2(
        consolidation_periods=15,
        atr_period=14,
        volume_ma_period=20,
        volume_surge_multiplier=2.5,
        compression_threshold=0.4,
        risk_reward_target=8.0,
        secondary_target=12.0,
        trailing_activation=6.0,
        max_trade_duration_mins=60,
        fee_percent=0.1
    )

    print("Loading FARTCOIN/USDT data...")
    df = strategy.load_data('/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv')
    print(f"Loaded {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    trades, equity_curve = strategy.backtest(df)

    print("\n" + "=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)

    metrics = strategy.calculate_performance_metrics(trades)

    print(f"\n📊 TRADE STATISTICS")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Winning Trades: {metrics['winning_trades']}")
    print(f"Losing Trades: {metrics['losing_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print(f"8R Target Hits: {metrics['target_8r_hits']}")
    print(f"Trailing 4R Exits: {metrics['trailing_4r_exits']}")
    print()
    print(f"💰 P&L METRICS")
    print(f"Total P&L: {metrics['total_pnl_pct']:.2f}%")
    print(f"Average Win: {metrics['avg_win_pct']:.2f}%")
    print(f"Average Loss: {metrics['avg_loss_pct']:.2f}%")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Expected Value: {metrics['expected_value']:.3f}%")
    print()
    print(f"📈 RISK:REWARD ANALYSIS")
    print(f"Average R-Multiple: {metrics['avg_r_multiple']:.2f}R")
    print(f"Average Win R: {metrics['avg_win_r']:.2f}R")
    print(f"Average Loss R: {metrics['avg_loss_r']:.2f}R")
    print()
    print(f"📉 RISK METRICS")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Average Trade Duration: {metrics['avg_trade_duration_mins']:.1f} minutes")
    print()
    print(f"🎯 DIRECTION BREAKDOWN")
    print(f"Long Trades: {metrics['long_trades']} (Win Rate: {metrics['long_win_rate']:.2f}%)")
    print(f"Short Trades: {metrics['short_trades']} (Win Rate: {metrics['short_win_rate']:.2f}%)")
    print()

    # Save results
    print("Saving results...")

    trades_df = pd.DataFrame(trades)
    if len(trades_df) > 0:
        trades_df[['entry_timestamp', 'direction', 'entry', 'stop', 'targets',
                   'exit_timestamp', 'exit_price', 'exit_reason', 'net_pnl_pct', 'r_multiple']].to_csv(
            '/workspaces/Carebiuro_windykacja/strategies/breakout-trades-v2.csv',
            index=False
        )
        print("✓ Saved breakout-trades-v2.csv")

    equity_curve.to_csv(
        '/workspaces/Carebiuro_windykacja/strategies/breakout-equity-curve-v2.csv',
        index=False
    )
    print("✓ Saved breakout-equity-curve-v2.csv")

    print("\nAll results saved to ./strategies/")
    print("=" * 80)

    return metrics, trades, equity_curve


if __name__ == "__main__":
    metrics, trades, equity_curve = main()
