#!/usr/bin/env python3
"""
FARTCOIN/USDT Pattern Recognition Trading Strategy
Identifies high-probability candlestick patterns for 8:1+ R:R setups
Uses only OHLCV data with volume confirmation
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class PatternRecognitionStrategy:
    """
    Advanced pattern recognition strategy optimized for 8:1 risk:reward.
    Detects candlestick patterns, chart patterns, and market structure.
    """

    def __init__(self, data_path: str, risk_reward_target: float = 8.0):
        self.data_path = data_path
        self.risk_reward_target = risk_reward_target
        self.fee_rate = 0.001  # 0.1% per trade (0.2% round trip)
        self.df = None
        self.trades = []
        self.pattern_stats = {}

    def load_data(self) -> pd.DataFrame:
        """Load and prepare OHLCV data"""
        print("Loading FARTCOIN/USDT data...")
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # Calculate basic features
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['range'] = self.df['high'] - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']

        # Volume features
        self.df['vol_ma_10'] = self.df['volume'].rolling(10).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma_10']

        # Price momentum
        self.df['returns'] = self.df['close'].pct_change()

        print(f"Loaded {len(self.df)} candles from {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        return self.df

    def identify_swing_points(self, lookback: int = 5) -> None:
        """Identify swing highs and lows for support/resistance"""
        self.df['swing_high'] = False
        self.df['swing_low'] = False
        self.df['resistance'] = np.nan
        self.df['support'] = np.nan

        for i in range(lookback, len(self.df) - lookback):
            # Swing high: highest high in window
            if self.df.loc[i, 'high'] == self.df.loc[i-lookback:i+lookback, 'high'].max():
                self.df.loc[i, 'swing_high'] = True
                self.df.loc[i, 'resistance'] = self.df.loc[i, 'high']

            # Swing low: lowest low in window
            if self.df.loc[i, 'low'] == self.df.loc[i-lookback:i+lookback, 'low'].min():
                self.df.loc[i, 'swing_low'] = True
                self.df.loc[i, 'support'] = self.df.loc[i, 'low']

        # Forward fill support/resistance levels
        self.df['resistance'] = self.df['resistance'].fillna(method='ffill')
        self.df['support'] = self.df['support'].fillna(method='ffill')

    def detect_hammer(self, idx: int) -> Optional[Dict]:
        """
        Hammer pattern: Small body, long lower wick, at support
        Bullish reversal signal
        """
        if idx < 20:
            return None

        candle = self.df.loc[idx]

        # Hammer criteria (relaxed)
        body_small = candle['body_pct'] < 0.5
        lower_wick_long = candle['lower_wick'] > 1.5 * candle['body']
        upper_wick_small = candle['upper_wick'] < 0.7 * candle['body']
        volume_surge = candle['vol_ratio'] > 1.2

        # Downtrend context (price declining on average)
        recent_trend = self.df.loc[idx-10:idx, 'close'].diff().mean() < -0.0001

        if body_small and lower_wick_long and upper_wick_small and volume_surge and recent_trend:
            return {
                'pattern': 'Hammer',
                'direction': 'long',
                'quality': 'A',
                'stop': candle['low'] - (candle['range'] * 0.2),  # Below wick
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_shooting_star(self, idx: int) -> Optional[Dict]:
        """
        Shooting Star: Small body, long upper wick, at resistance
        Bearish reversal signal
        """
        if idx < 20:
            return None

        candle = self.df.loc[idx]

        # Shooting star criteria (relaxed)
        body_small = candle['body_pct'] < 0.5
        upper_wick_long = candle['upper_wick'] > 1.5 * candle['body']
        lower_wick_small = candle['lower_wick'] < 0.7 * candle['body']
        volume_surge = candle['vol_ratio'] > 1.2

        # Uptrend context (price rising on average)
        recent_trend = self.df.loc[idx-10:idx, 'close'].diff().mean() > 0.0001

        if body_small and upper_wick_long and lower_wick_small and volume_surge and recent_trend:
            return {
                'pattern': 'Shooting Star',
                'direction': 'short',
                'quality': 'A',
                'stop': candle['high'] + (candle['range'] * 0.2),  # Above wick
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_bullish_engulfing(self, idx: int) -> Optional[Dict]:
        """
        Bullish Engulfing: Large bullish candle engulfs previous bearish candle
        Strong reversal signal
        """
        if idx < 20:
            return None

        prev = self.df.loc[idx - 1]
        curr = self.df.loc[idx]

        # Engulfing criteria (relaxed)
        prev_bearish = not prev['is_bullish']
        curr_bullish = curr['is_bullish']
        engulfs = curr['open'] <= prev['close'] and curr['close'] >= prev['open']
        strong_body = curr['body_pct'] > 0.4
        volume_surge = curr['vol_ratio'] > 1.3

        # Downtrend context
        downtrend = self.df.loc[idx-10:idx-1, 'close'].diff().mean() < -0.0001

        if prev_bearish and curr_bullish and engulfs and strong_body and volume_surge and downtrend:
            return {
                'pattern': 'Bullish Engulfing',
                'direction': 'long',
                'quality': 'A',
                'stop': min(prev['low'], curr['low']) - (curr['range'] * 0.15),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_bearish_engulfing(self, idx: int) -> Optional[Dict]:
        """
        Bearish Engulfing: Large bearish candle engulfs previous bullish candle
        Strong reversal signal
        """
        if idx < 20:
            return None

        prev = self.df.loc[idx - 1]
        curr = self.df.loc[idx]

        # Engulfing criteria (relaxed)
        prev_bullish = prev['is_bullish']
        curr_bearish = not curr['is_bullish']
        engulfs = curr['open'] >= prev['close'] and curr['close'] <= prev['open']
        strong_body = curr['body_pct'] > 0.4
        volume_surge = curr['vol_ratio'] > 1.3

        # Uptrend context
        uptrend = self.df.loc[idx-10:idx-1, 'close'].diff().mean() > 0.0001

        if prev_bullish and curr_bearish and engulfs and strong_body and volume_surge and uptrend:
            return {
                'pattern': 'Bearish Engulfing',
                'direction': 'short',
                'quality': 'A',
                'stop': max(prev['high'], curr['high']) + (curr['range'] * 0.15),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_inside_bar_breakout(self, idx: int) -> Optional[Dict]:
        """
        Inside Bar followed by breakout
        Continuation pattern after consolidation
        """
        if idx < 20:
            return None

        mother = self.df.loc[idx - 2]
        inside = self.df.loc[idx - 1]
        breakout = self.df.loc[idx]

        # Inside bar: range contained within previous candle
        is_inside = (inside['high'] <= mother['high'] and
                     inside['low'] >= mother['low'])

        # Breakout with volume
        bullish_breakout = breakout['close'] > mother['high'] and breakout['is_bullish']
        bearish_breakout = breakout['close'] < mother['low'] and not breakout['is_bullish']
        volume_confirms = breakout['vol_ratio'] > 1.4
        strong_move = breakout['body_pct'] > 0.4

        if is_inside and volume_confirms and strong_move:
            if bullish_breakout:
                return {
                    'pattern': 'Inside Bar Bullish Breakout',
                    'direction': 'long',
                    'quality': 'A',
                    'stop': inside['low'] - (mother['range'] * 0.15),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
            elif bearish_breakout:
                return {
                    'pattern': 'Inside Bar Bearish Breakout',
                    'direction': 'short',
                    'quality': 'A',
                    'stop': inside['high'] + (mother['range'] * 0.15),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
        return None

    def detect_three_white_soldiers(self, idx: int) -> Optional[Dict]:
        """
        Three White Soldiers: Three consecutive strong bullish candles
        Powerful continuation signal
        """
        if idx < 20:
            return None

        candles = [self.df.loc[idx - 2], self.df.loc[idx - 1], self.df.loc[idx]]

        # All bullish with strong bodies
        all_bullish = all(c['is_bullish'] for c in candles)
        strong_bodies = all(c['body_pct'] > 0.4 for c in candles)
        higher_closes = candles[1]['close'] > candles[0]['close'] and candles[2]['close'] > candles[1]['close']
        volume_increasing = candles[1]['volume'] > candles[0]['volume'] and candles[2]['volume'] > candles[1]['volume']

        if all_bullish and strong_bodies and higher_closes and volume_increasing:
            return {
                'pattern': 'Three White Soldiers',
                'direction': 'long',
                'quality': 'A+',
                'stop': min(c['low'] for c in candles) - (candles[2]['range'] * 0.2),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_three_black_crows(self, idx: int) -> Optional[Dict]:
        """
        Three Black Crows: Three consecutive strong bearish candles
        Powerful reversal/continuation signal
        """
        if idx < 20:
            return None

        candles = [self.df.loc[idx - 2], self.df.loc[idx - 1], self.df.loc[idx]]

        # All bearish with strong bodies
        all_bearish = all(not c['is_bullish'] for c in candles)
        strong_bodies = all(c['body_pct'] > 0.4 for c in candles)
        lower_closes = candles[1]['close'] < candles[0]['close'] and candles[2]['close'] < candles[1]['close']
        volume_increasing = candles[1]['volume'] > candles[0]['volume'] and candles[2]['volume'] > candles[1]['volume']

        if all_bearish and strong_bodies and lower_closes and volume_increasing:
            return {
                'pattern': 'Three Black Crows',
                'direction': 'short',
                'quality': 'A+',
                'stop': max(c['high'] for c in candles) + (candles[2]['range'] * 0.2),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_morning_star(self, idx: int) -> Optional[Dict]:
        """
        Morning Star: Three candle reversal pattern
        Bearish -> Small body -> Strong bullish
        """
        if idx < 20:
            return None

        first = self.df.loc[idx - 2]
        star = self.df.loc[idx - 1]
        third = self.df.loc[idx]

        # Pattern criteria
        first_bearish = not first['is_bullish'] and first['body_pct'] > 0.5
        star_small = star['body_pct'] < 0.2
        third_bullish = third['is_bullish'] and third['body_pct'] > 0.5
        gap_down = star['close'] < first['close']
        gap_up = third['open'] > star['close']
        volume_surge = third['vol_ratio'] > 1.5

        if first_bearish and star_small and third_bullish and gap_down and gap_up and volume_surge:
            return {
                'pattern': 'Morning Star',
                'direction': 'long',
                'quality': 'A+',
                'stop': star['low'] - (third['range'] * 0.2),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_evening_star(self, idx: int) -> Optional[Dict]:
        """
        Evening Star: Three candle reversal pattern
        Bullish -> Small body -> Strong bearish
        """
        if idx < 20:
            return None

        first = self.df.loc[idx - 2]
        star = self.df.loc[idx - 1]
        third = self.df.loc[idx]

        # Pattern criteria
        first_bullish = first['is_bullish'] and first['body_pct'] > 0.5
        star_small = star['body_pct'] < 0.2
        third_bearish = not third['is_bullish'] and third['body_pct'] > 0.5
        gap_up = star['close'] > first['close']
        gap_down = third['open'] < star['close']
        volume_surge = third['vol_ratio'] > 1.5

        if first_bullish and star_small and third_bearish and gap_up and gap_down and volume_surge:
            return {
                'pattern': 'Evening Star',
                'direction': 'short',
                'quality': 'A+',
                'stop': star['high'] + (third['range'] * 0.2),
                'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
            }
        return None

    def detect_volume_climax(self, idx: int) -> Optional[Dict]:
        """
        Volume Climax: Extreme volume spike indicating exhaustion
        Often marks reversals
        """
        if idx < 20:
            return None

        candle = self.df.loc[idx]

        # Extreme volume (2.5x+ average)
        climax_volume = candle['vol_ratio'] > 2.5
        large_range = candle['range'] / candle['open'] > 0.008

        # Check if at extreme: uptrend exhaustion or downtrend exhaustion
        recent_trend = self.df.loc[idx-10:idx, 'close'].diff().mean()

        if climax_volume and large_range:
            if recent_trend > 0.0001 and not candle['is_bullish']:
                # Uptrend exhaustion
                return {
                    'pattern': 'Volume Climax Bearish',
                    'direction': 'short',
                    'quality': 'A',
                    'stop': candle['high'] + (candle['range'] * 0.25),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
            elif recent_trend < -0.0001 and candle['is_bullish']:
                # Downtrend exhaustion
                return {
                    'pattern': 'Volume Climax Bullish',
                    'direction': 'long',
                    'quality': 'A',
                    'stop': candle['low'] - (candle['range'] * 0.25),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
        return None

    def detect_strong_momentum_breakout(self, idx: int) -> Optional[Dict]:
        """
        Strong Momentum Breakout: Large candle breaking recent range with volume
        Powerful continuation signal
        """
        if idx < 20:
            return None

        candle = self.df.loc[idx]

        # Strong momentum criteria
        large_body = candle['body_pct'] > 0.6
        volume_spike = candle['vol_ratio'] > 1.8
        small_wicks = (candle['upper_wick'] + candle['lower_wick']) < candle['body']

        # Recent consolidation followed by breakout
        recent_range = self.df.loc[idx-10:idx-1, 'high'].max() - self.df.loc[idx-10:idx-1, 'low'].min()
        recent_avg_range = self.df.loc[idx-10:idx-1, 'range'].mean()

        # Breakout size relative to recent range
        breakout_strength = candle['range'] > (recent_avg_range * 1.8)

        if large_body and volume_spike and small_wicks and breakout_strength:
            if candle['is_bullish']:
                return {
                    'pattern': 'Strong Momentum Breakout Long',
                    'direction': 'long',
                    'quality': 'A',
                    'stop': candle['low'] - (candle['range'] * 0.2),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
            else:
                return {
                    'pattern': 'Strong Momentum Breakout Short',
                    'direction': 'short',
                    'quality': 'A',
                    'stop': candle['high'] + (candle['range'] * 0.2),
                    'entry': self.df.loc[idx + 1, 'open'] if idx + 1 < len(self.df) else None
                }
        return None

    def scan_all_patterns(self, idx: int) -> Optional[Dict]:
        """Scan for all pattern types at given index"""
        patterns_to_check = [
            self.detect_hammer,
            self.detect_shooting_star,
            self.detect_bullish_engulfing,
            self.detect_bearish_engulfing,
            self.detect_inside_bar_breakout,
            self.detect_three_white_soldiers,
            self.detect_three_black_crows,
            self.detect_morning_star,
            self.detect_evening_star,
            self.detect_volume_climax,
            self.detect_strong_momentum_breakout,
        ]

        for pattern_func in patterns_to_check:
            pattern = pattern_func(idx)
            if pattern and pattern['quality'] in ['A+', 'A']:  # Trade A and A+ quality
                return pattern

        return None

    def calculate_target(self, entry: float, stop: float, direction: str) -> float:
        """Calculate target price based on risk:reward ratio"""
        risk = abs(entry - stop)
        reward = risk * self.risk_reward_target

        if direction == 'long':
            return entry + reward
        else:
            return entry - reward

    def simulate_trade(self, entry_idx: int, pattern_info: Dict) -> Optional[Dict]:
        """Simulate trade execution and outcome"""
        if entry_idx >= len(self.df) - 1:
            return None

        entry_price = pattern_info['entry']
        if entry_price is None:
            return None

        stop_price = pattern_info['stop']
        direction = pattern_info['direction']
        target_price = self.calculate_target(entry_price, stop_price, direction)

        # Risk amount
        risk_pct = abs(entry_price - stop_price) / entry_price

        # Skip if risk too large (>1%)
        if risk_pct > 0.01:
            return None

        # Track trade through subsequent candles
        entry_time = self.df.loc[entry_idx, 'timestamp']
        exit_price = None
        exit_time = None
        exit_reason = None
        max_bars = 120  # Max 2 hours for trade

        for i in range(entry_idx, min(entry_idx + max_bars, len(self.df))):
            candle = self.df.loc[i]

            if direction == 'long':
                # Check stop hit
                if candle['low'] <= stop_price:
                    exit_price = stop_price
                    exit_time = candle['timestamp']
                    exit_reason = 'Stop Loss'
                    break
                # Check target hit
                if candle['high'] >= target_price:
                    exit_price = target_price
                    exit_time = candle['timestamp']
                    exit_reason = 'Target Hit'
                    break
            else:  # short
                # Check stop hit
                if candle['high'] >= stop_price:
                    exit_price = stop_price
                    exit_time = candle['timestamp']
                    exit_reason = 'Stop Loss'
                    break
                # Check target hit
                if candle['low'] <= target_price:
                    exit_price = target_price
                    exit_time = candle['timestamp']
                    exit_reason = 'Target Hit'
                    break

        # If no exit, close at current price (timeout)
        if exit_price is None:
            exit_price = self.df.loc[min(entry_idx + max_bars - 1, len(self.df) - 1), 'close']
            exit_time = self.df.loc[min(entry_idx + max_bars - 1, len(self.df) - 1), 'timestamp']
            exit_reason = 'Timeout'

        # Calculate P&L
        if direction == 'long':
            pnl_pct = ((exit_price - entry_price) / entry_price) - (2 * self.fee_rate)
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) - (2 * self.fee_rate)

        # Calculate R-multiple
        risk_amount = abs(entry_price - stop_price)
        actual_pnl = abs(exit_price - entry_price)

        if direction == 'long':
            r_multiple = (exit_price - entry_price) / risk_amount if risk_amount > 0 else 0
        else:
            r_multiple = (entry_price - exit_price) / risk_amount if risk_amount > 0 else 0

        return {
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pattern': pattern_info['pattern'],
            'direction': direction,
            'quality': pattern_info['quality'],
            'entry_price': entry_price,
            'stop_price': stop_price,
            'target_price': target_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'r_multiple': r_multiple,
            'exit_reason': exit_reason,
            'risk_pct': risk_pct
        }

    def backtest(self) -> List[Dict]:
        """Run complete backtest scanning all patterns"""
        print("\nScanning for patterns...")

        self.identify_swing_points()

        signal_count = 0
        for idx in range(30, len(self.df) - 120):
            pattern = self.scan_all_patterns(idx)

            if pattern:
                signal_count += 1
                trade = self.simulate_trade(idx + 1, pattern)
                if trade:
                    self.trades.append(trade)

        print(f"Found {signal_count} pattern signals")
        print(f"Executed {len(self.trades)} valid trades")

        return self.trades

    def analyze_performance(self) -> Dict:
        """Comprehensive performance analysis"""
        if not self.trades:
            return {}

        df_trades = pd.DataFrame(self.trades)

        # Overall metrics
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl_pct'] > 0])
        losing_trades = len(df_trades[df_trades['pnl_pct'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        avg_win = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
        avg_rr = df_trades[df_trades['pnl_pct'] > 0]['r_multiple'].mean() if winning_trades > 0 else 0

        total_return = df_trades['pnl_pct'].sum()

        # Profit factor
        gross_profit = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Expected value per trade
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Target achievement
        target_hits = len(df_trades[df_trades['exit_reason'] == 'Target Hit'])
        target_rate = target_hits / total_trades if total_trades > 0 else 0

        # Pattern-specific analysis
        pattern_performance = {}
        for pattern in df_trades['pattern'].unique():
            pattern_trades = df_trades[df_trades['pattern'] == pattern]
            pattern_wins = len(pattern_trades[pattern_trades['pnl_pct'] > 0])
            pattern_wr = pattern_wins / len(pattern_trades) if len(pattern_trades) > 0 else 0
            pattern_targets = len(pattern_trades[pattern_trades['exit_reason'] == 'Target Hit'])
            pattern_target_rate = pattern_targets / len(pattern_trades) if len(pattern_trades) > 0 else 0

            pattern_avg_rr = pattern_trades[pattern_trades['pnl_pct'] > 0]['r_multiple'].mean()
            pattern_pf = (pattern_trades[pattern_trades['pnl_pct'] > 0]['pnl_pct'].sum() /
                         abs(pattern_trades[pattern_trades['pnl_pct'] < 0]['pnl_pct'].sum())
                         if len(pattern_trades[pattern_trades['pnl_pct'] < 0]) > 0 else 0)

            pattern_performance[pattern] = {
                'trade_count': len(pattern_trades),
                'win_rate': pattern_wr,
                'target_rate': pattern_target_rate,
                'avg_rr': pattern_avg_rr,
                'profit_factor': pattern_pf,
                'total_pnl': pattern_trades['pnl_pct'].sum()
            }

        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'target_hit_rate': target_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'avg_rr_on_wins': avg_rr,
            'total_return_pct': total_return,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'pattern_performance': pattern_performance
        }

        return results

    def generate_reports(self):
        """Generate all output files"""
        if not self.trades:
            print("No trades to report")
            return

        # 1. Trade log CSV
        df_trades = pd.DataFrame(self.trades)
        trade_log_path = '/workspaces/Carebiuro_windykacja/strategies/pattern-trades.csv'
        df_trades.to_csv(trade_log_path, index=False)
        print(f"\nTrade log saved: {trade_log_path}")

        # 2. Pattern performance CSV
        performance = self.analyze_performance()
        pattern_perf = []
        for pattern, stats in performance['pattern_performance'].items():
            pattern_perf.append({
                'pattern': pattern,
                'trade_count': stats['trade_count'],
                'win_rate': stats['win_rate'],
                'target_hit_rate': stats['target_rate'],
                'avg_rr': stats['avg_rr'],
                'profit_factor': stats['profit_factor'],
                'total_pnl_pct': stats['total_pnl']
            })

        df_pattern_perf = pd.DataFrame(pattern_perf)
        df_pattern_perf = df_pattern_perf.sort_values('profit_factor', ascending=False)
        pattern_perf_path = '/workspaces/Carebiuro_windykacja/strategies/pattern-performance.csv'
        df_pattern_perf.to_csv(pattern_perf_path, index=False)
        print(f"Pattern performance saved: {pattern_perf_path}")

        # 3. Equity curve
        df_trades['cumulative_pnl'] = df_trades['pnl_pct'].cumsum()
        equity_curve = df_trades[['entry_time', 'cumulative_pnl']].copy()
        equity_curve.columns = ['timestamp', 'cumulative_return_pct']
        equity_path = '/workspaces/Carebiuro_windykacja/strategies/pattern-equity-curve.csv'
        equity_curve.to_csv(equity_path, index=False)
        print(f"Equity curve saved: {equity_path}")

        return performance


def main():
    """Main execution"""
    print("="*70)
    print("FARTCOIN/USDT PATTERN RECOGNITION STRATEGY")
    print("Target: 8:1 Risk:Reward with High-Probability Patterns")
    print("="*70)

    data_path = '/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv'

    strategy = PatternRecognitionStrategy(data_path, risk_reward_target=8.0)
    strategy.load_data()
    strategy.backtest()
    performance = strategy.generate_reports()

    # Print summary
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(f"Total Trades: {performance['total_trades']}")
    print(f"Win Rate: {performance['win_rate']:.1%}")
    print(f"Target Hit Rate (8R): {performance['target_hit_rate']:.1%}")
    print(f"Average Win: {performance['avg_win_pct']:.2%}")
    print(f"Average Loss: {performance['avg_loss_pct']:.2%}")
    print(f"Average R:R on Wins: {performance['avg_rr_on_wins']:.2f}R")
    print(f"Total Return: {performance['total_return_pct']:.2%}")
    print(f"Profit Factor: {performance['profit_factor']:.2f}")
    print(f"Expectancy per Trade: {performance['expectancy']:.3%}")

    print("\n" + "="*70)
    print("TOP PATTERNS (by Profit Factor)")
    print("="*70)

    sorted_patterns = sorted(performance['pattern_performance'].items(),
                           key=lambda x: x[1]['profit_factor'],
                           reverse=True)

    for pattern, stats in sorted_patterns[:5]:
        print(f"\n{pattern}:")
        print(f"  Trades: {stats['trade_count']}")
        print(f"  Win Rate: {stats['win_rate']:.1%}")
        print(f"  Target Rate: {stats['target_rate']:.1%}")
        print(f"  Avg R:R: {stats['avg_rr']:.2f}R")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  Total P&L: {stats['total_pnl']:.2%}")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
