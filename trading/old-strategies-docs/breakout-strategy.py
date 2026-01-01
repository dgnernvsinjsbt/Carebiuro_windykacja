"""
FARTCOIN/USDT Momentum Breakout Strategy - ULTIMATE VERSION
Target: 8:1+ Risk:Reward via compression-expansion patterns

OPTIMIZED FOR:
- 20+ statistical sample size
- 8R target hits
- Extended hold times for winners
- Balanced frequency/quality

Key settings:
- Consolidation: 10 periods (more signals)
- Volume surge: 2.0x (realistic threshold)
- Compression: 0.48 (moderate filter)
- Time stop: 60 minutes (let winners run)
- Smart exits: Remove time stop if profitable
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class MomentumBreakoutStrategy:
    def __init__(self,
                 consolidation_periods: int = 10,
                 atr_period: int = 14,
                 volume_ma_period: int = 20,
                 volume_surge_multiplier: float = 2.0,
                 compression_threshold: float = 0.48,
                 risk_reward_target: float = 8.0,
                 trailing_activation: float = 6.0,
                 trailing_lock: float = 4.0,
                 max_trade_duration_mins: int = 60,
                 fee_percent: float = 0.1):
        """Ultimate optimized parameters"""
        self.consolidation_periods = consolidation_periods
        self.atr_period = atr_period
        self.volume_ma_period = volume_ma_period
        self.volume_surge_multiplier = volume_surge_multiplier
        self.compression_threshold = compression_threshold
        self.risk_reward_target = risk_reward_target
        self.trailing_activation = trailing_activation
        self.trailing_lock = trailing_lock
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

        df['atr'] = self.calculate_atr(df)
        df['atr_ma'] = df['atr'].rolling(window=self.consolidation_periods).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']

        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        df['candle_range'] = df['high'] - df['low']
        df['candle_body'] = abs(df['close'] - df['open'])
        df['body_ratio'] = df['candle_body'] / (df['candle_range'] + 0.00001)

        df['high_high'] = df['high'].rolling(window=self.consolidation_periods).max()
        df['low_low'] = df['low'].rolling(window=self.consolidation_periods).min()
        df['consolidation_range'] = df['high_high'] - df['low_low']
        df['consolidation_range_pct'] = (df['consolidation_range'] / df['close']) * 100

        df['bullish'] = (df['close'] > df['open']).astype(int)
        df['bearish'] = (df['close'] < df['open']).astype(int)

        df['close_position'] = (df['close'] - df['low']) / (df['candle_range'] + 0.00001)
        df['close_position'] = df['close_position'].fillna(0.5)

        return df

    def detect_breakout(self, df: pd.DataFrame, idx: int) -> Tuple[str, float, float, Dict]:
        """Detect breakout with quality metrics"""
        if idx < self.consolidation_periods + self.atr_period + 1:
            return None, None, None, None

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Core filters
        is_compressed = previous['atr_ratio'] < self.compression_threshold
        has_volume_surge = current['volume_ratio'] >= self.volume_surge_multiplier

        if not is_compressed or not has_volume_surge:
            return None, None, None, None

        # Consolidation range filter
        if previous['consolidation_range_pct'] < 0.35 or previous['consolidation_range_pct'] > 4.0:
            return None, None, None, None

        quality_score = {
            'atr_compression': previous['atr_ratio'],
            'volume_surge': current['volume_ratio'],
            'consolidation_range': previous['consolidation_range_pct'],
            'body_ratio': current['body_ratio']
        }

        # Bullish breakout
        if (current['close'] > previous['high_high'] and
            current['bullish'] == 1 and
            current['body_ratio'] > 0.50 and
            current['close_position'] > 0.60):

            entry = current['close']
            stop = previous['low_low'] - (current['atr'] * 0.4)

            risk_pct = abs(entry - stop) / entry * 100
            if risk_pct < 0.3 or risk_pct > 3.0:
                return None, None, None, None

            quality_score['direction'] = 'LONG'
            quality_score['risk_pct'] = risk_pct

            return 'LONG', entry, stop, quality_score

        # Bearish breakout
        elif (current['close'] < previous['low_low'] and
              current['bearish'] == 1 and
              current['body_ratio'] > 0.50 and
              current['close_position'] < 0.40):

            entry = current['close']
            stop = previous['high_high'] + (current['atr'] * 0.4)

            risk_pct = abs(entry - stop) / entry * 100
            if risk_pct < 0.3 or risk_pct > 3.0:
                return None, None, None, None

            quality_score['direction'] = 'SHORT'
            quality_score['risk_pct'] = risk_pct

            return 'SHORT', entry, stop, quality_score

        return None, None, None, None

    def calculate_targets(self, direction: str, entry: float, stop: float) -> Dict[str, float]:
        """Calculate profit targets"""
        risk = abs(entry - stop)

        if direction == 'LONG':
            target_8r = entry + (risk * self.risk_reward_target)
            trailing_trigger = entry + (risk * self.trailing_activation)
            trailing_lock = entry + (risk * self.trailing_lock)
        else:
            target_8r = entry - (risk * self.risk_reward_target)
            trailing_trigger = entry - (risk * self.trailing_activation)
            trailing_lock = entry - (risk * self.trailing_lock)

        return {
            'target_8r': target_8r,
            'trailing_trigger': trailing_trigger,
            'trailing_lock': trailing_lock,
            'risk': risk
        }

    def manage_trade(self, df: pd.DataFrame, trade: Dict, current_idx: int) -> Dict:
        """
        Manage trade with SMART time stop:
        - Apply time stop to losing trades
        - Let profitable trades run longer
        """
        current = df.iloc[current_idx]
        entry_idx = trade['entry_idx']
        direction = trade['direction']
        entry = trade['entry']
        stop = trade['stop']
        targets = trade['targets']

        minutes_in_trade = current_idx - entry_idx

        # Calculate current P&L
        if direction == 'LONG':
            current_pnl = ((current['close'] - entry) / entry) * 100
        else:
            current_pnl = ((entry - current['close']) / entry) * 100

        # Smart time stop: only apply if losing or flat
        if minutes_in_trade >= self.max_trade_duration_mins and current_pnl <= 0.5:
            return {
                **trade,
                'exit_price': current['close'],
                'exit_idx': current_idx,
                'exit_reason': 'TIME_STOP'
            }

        # Extended time stop for profitable trades (90 minutes)
        if minutes_in_trade >= 90:
            return {
                **trade,
                'exit_price': current['close'],
                'exit_idx': current_idx,
                'exit_reason': 'EXTENDED_TIME_STOP'
            }

        if direction == 'LONG':
            # Stop loss
            if current['low'] <= stop:
                return {
                    **trade,
                    'exit_price': stop,
                    'exit_idx': current_idx,
                    'exit_reason': 'STOP_LOSS'
                }

            # 8R TARGET HIT - MAIN GOAL
            if current['high'] >= targets['target_8r']:
                return {
                    **trade,
                    'exit_price': targets['target_8r'],
                    'exit_idx': current_idx,
                    'exit_reason': 'TARGET_8R'
                }

            # Trailing stop after 6R
            peak_price = trade.get('peak_price', entry)
            if peak_price >= targets['trailing_trigger']:
                trail_stop = targets['trailing_lock']
                if current['low'] <= trail_stop:
                    return {
                        **trade,
                        'exit_price': trail_stop,
                        'exit_idx': current_idx,
                        'exit_reason': 'TRAILING_4R'
                    }

            trade['peak_price'] = max(trade.get('peak_price', entry), current['high'])

        else:  # SHORT
            # Stop loss
            if current['high'] >= stop:
                return {
                    **trade,
                    'exit_price': stop,
                    'exit_idx': current_idx,
                    'exit_reason': 'STOP_LOSS'
                }

            # 8R TARGET HIT
            if current['low'] <= targets['target_8r']:
                return {
                    **trade,
                    'exit_price': targets['target_8r'],
                    'exit_idx': current_idx,
                    'exit_reason': 'TARGET_8R'
                }

            # Trailing stop after 6R
            low_price = trade.get('low_price', entry)
            if low_price <= targets['trailing_trigger']:
                trail_stop = targets['trailing_lock']
                if current['high'] >= trail_stop:
                    return {
                        **trade,
                        'exit_price': trail_stop,
                        'exit_idx': current_idx,
                        'exit_reason': 'TRAILING_4R'
                    }

            trade['low_price'] = min(trade.get('low_price', entry), current['low'])

        return trade

    def calculate_pnl(self, trade: Dict) -> Dict:
        """Calculate P&L and R-multiple"""
        direction = trade['direction']
        entry = trade['entry']
        exit_price = trade['exit_price']
        stop = trade['stop']

        if direction == 'LONG':
            gross_pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            gross_pnl_pct = ((entry - exit_price) / entry) * 100

        net_pnl_pct = gross_pnl_pct - (self.fee_percent * 2 * 100)

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
        """Run backtest"""
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

            if open_trade is None:
                direction, entry, stop, quality = self.detect_breakout(df, idx)

                if direction is not None:
                    targets = self.calculate_targets(direction, entry, stop)

                    open_trade = {
                        'entry_idx': idx,
                        'entry_timestamp': df.iloc[idx]['timestamp'],
                        'direction': direction,
                        'entry': entry,
                        'stop': stop,
                        'targets': targets,
                        'quality': quality
                    }

                    print(f"\n{'='*70}")
                    print(f"TRADE #{len(trades)+1} | {direction} | {df.iloc[idx]['timestamp']}")
                    print(f"Entry: ${entry:.5f} | Stop: ${stop:.5f} → Target: ${targets['target_8r']:.5f}")
                    print(f"Risk: {quality['risk_pct']:.2f}% | Vol: {quality['volume_surge']:.1f}x | ATR: {quality['atr_compression']:.3f}")

            else:
                updated_trade = self.manage_trade(df, open_trade, idx)

                if 'exit_price' in updated_trade:
                    completed_trade = self.calculate_pnl(updated_trade)
                    completed_trade['exit_timestamp'] = df.iloc[idx]['timestamp']

                    trades.append(completed_trade)

                    cumulative_pnl += completed_trade['net_pnl_pct']
                    equity.append(1.0 + (cumulative_pnl / 100))

                    symbol = "✅" if completed_trade['win'] == 1 else "❌"
                    print(f"{symbol} {completed_trade['exit_reason']}: ${completed_trade['exit_price']:.5f}")
                    print(f"P&L: {completed_trade['net_pnl_pct']:+.2f}% ({completed_trade['r_multiple']:+.2f}R) | Total: {cumulative_pnl:+.2f}%")
                    print(f"{'='*70}\n")

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
        """Calculate performance statistics"""
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

        # Exit analysis
        target_8r_hits = len(trades_df[trades_df['exit_reason'] == 'TARGET_8R'])
        trailing_exits = len(trades_df[trades_df['exit_reason'] == 'TRAILING_4R'])
        stop_losses = len(trades_df[trades_df['exit_reason'] == 'STOP_LOSS'])
        time_stops = len(trades_df[trades_df['exit_reason'].str.contains('TIME_STOP')])

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
            'target_8r_hits': target_8r_hits,
            'trailing_4r_exits': trailing_exits,
            'stop_losses': stop_losses,
            'time_stops': time_stops,
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate': (len(long_trades[long_trades['win'] == 1]) / len(long_trades) * 100) if len(long_trades) > 0 else 0,
            'short_win_rate': (len(short_trades[short_trades['win'] == 1]) / len(short_trades) * 100) if len(short_trades) > 0 else 0,
        }


def main():
    """Main execution"""
    print("=" * 80)
    print("FARTCOIN/USDT MOMENTUM BREAKOUT STRATEGY - ULTIMATE VERSION")
    print("Target: 8:1 Risk:Reward | 20+ Statistical Sample")
    print("=" * 80)
    print()

    strategy = MomentumBreakoutStrategy(
        consolidation_periods=10,
        atr_period=14,
        volume_ma_period=20,
        volume_surge_multiplier=2.0,
        compression_threshold=0.48,
        risk_reward_target=8.0,
        trailing_activation=6.0,
        trailing_lock=4.0,
        max_trade_duration_mins=60,
        fee_percent=0.1
    )

    print("Loading FARTCOIN/USDT data...")
    df = strategy.load_data('/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv')
    print(f"Loaded {len(df)} candles (30 days)")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    trades, equity_curve = strategy.backtest(df)

    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    metrics = strategy.calculate_performance_metrics(trades)

    print(f"\n📊 TRADE STATISTICS")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Wins: {metrics['winning_trades']} | Losses: {metrics['losing_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print()
    print(f"💰 PROFITABILITY")
    print(f"Total P&L: {metrics['total_pnl_pct']:+.2f}%")
    print(f"Avg Win: {metrics['avg_win_pct']:+.2f}% | Avg Loss: {metrics['avg_loss_pct']:+.2f}%")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Expected Value: {metrics['expected_value']:+.3f}% per trade")
    print()
    print(f"📈 RISK:REWARD")
    print(f"Avg R-Multiple: {metrics['avg_r_multiple']:+.2f}R")
    print(f"Avg Win: {metrics['avg_win_r']:+.2f}R | Avg Loss: {metrics['avg_loss_r']:+.2f}R")
    print()
    print(f"🎯 EXIT BREAKDOWN")
    print(f"8R Target Hits: {metrics['target_8r_hits']} ⭐")
    print(f"Trailing 4R: {metrics['trailing_4r_exits']}")
    print(f"Stop Losses: {metrics['stop_losses']}")
    print(f"Time Stops: {metrics['time_stops']}")
    print()
    print(f"📉 RISK")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Avg Duration: {metrics['avg_trade_duration_mins']:.0f} minutes")
    print()
    print(f"🔄 DIRECTION")
    print(f"LONG: {metrics['long_trades']} trades ({metrics['long_win_rate']:.1f}% WR)")
    print(f"SHORT: {metrics['short_trades']} trades ({metrics['short_win_rate']:.1f}% WR)")
    print()

    # Saveanswers
    print("Saving results...")

    trades_df = pd.DataFrame(trades)
    if len(trades_df) > 0:
        output_df = trades_df[['entry_timestamp', 'direction', 'entry', 'stop',
                                'exit_timestamp', 'exit_price', 'exit_reason',
                                'net_pnl_pct', 'r_multiple']].copy()

        output_df['target_8r'] = trades_df.apply(lambda row: row['targets']['target_8r'], axis=1)
        output_df['risk_pct'] = trades_df.apply(lambda row: row['quality']['risk_pct'], axis=1)

        output_df.to_csv('/workspaces/Carebiuro_windykacja/strategies/breakout-trades.csv', index=False)
        print("✓ breakout-trades.csv")

    equity_curve.to_csv('/workspaces/Carebiuro_windykacja/strategies/breakout-equity-curve.csv', index=False)
    print("✓ breakout-equity-curve.csv")

    print("\n" + "=" * 80)

    return metrics, trades, equity_curve


if __name__ == "__main__":
    metrics, trades, equity_curve = main()
