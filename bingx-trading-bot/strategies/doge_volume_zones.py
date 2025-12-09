"""
DOGE Volume Zones Strategy (BingX Optimized)

**Rank #3 by Return/DD Ratio: 10.75x** ⭐
+5.15% return, -0.48% DD (shallowest!), 63.6% WR (32-day BingX backtest)

⚠️  OUTLIER-HARVESTING STRATEGY:
- Top 5 trades = 95.3% of profit
- Remaining 17 trades = +0.24% (treading water)
- Must take EVERY signal to catch the big moves

Entry Conditions:
- Detect 5+ consecutive bars with volume > 1.5x average
- Accumulation zone (at local lows) → LONG
- Distribution zone (at local highs) → SHORT
- Asia/EU session ONLY (07:00-14:00 UTC)

Exit Conditions:
- Stop Loss: 1.5x ATR (tighter than overnight session)
- Take Profit: 4.0x ATR (absolute ATR target, not R:R)
- Time Exit: 90 bars (90 minutes) if neither SL/TP hit

Uses MARKET orders (0.1% fees)
Optimized: Dec 9, 2025
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy


class DogeVolumeZonesStrategy(BaseStrategy):
    """
    DOGE Volume Zones strategy (BingX Optimized)
    - Detects sustained high-volume zones (whale accumulation/distribution)
    - Trades breakouts from zones during Asia/EU session (07:00-14:00 UTC)
    - 4.0x ATR take profit with 1.5x ATR stops
    - Outlier-harvesting: Top 5 trades = 95% of profit (requires discipline)
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'DOGE-USDT'):
        super().__init__('doge_volume_zones', config, symbol)

        # Extract strategy parameters
        params = config.get('params', {})
        self.volume_threshold = params.get('volume_threshold', 1.5)
        self.min_zone_bars = params.get('min_zone_bars', 5)
        self.max_zone_bars = params.get('max_zone_bars', 15)
        self.lookback_bars = params.get('lookback_bars', 20)
        self.stop_atr_mult = params.get('stop_atr_mult', 1.5)  # OPTIMIZED: 1.5x (was 2.0x)
        self.tp_type = params.get('tp_type', 'atr_multiple')  # NEW: 'atr_multiple' or 'rr_multiple'
        self.tp_atr_mult = params.get('tp_atr_mult', 4.0)  # NEW: 4.0x ATR target
        self.rr_ratio = params.get('rr_ratio', 2.0)  # Fallback for R:R mode
        self.max_hold_bars = params.get('max_hold_bars', 90)
        self.session_filter = params.get('session_filter', 'asia_eu')  # OPTIMIZED: asia_eu (was overnight)

        # Volume zone tracking
        self.zone_bars = 0
        self.zone_start_idx = None
        self.in_zone = False
        self.zone_highs = []
        self.zone_lows = []

        # Entry tracking
        self.entry_time = None

    def is_overnight_session(self, timestamp: pd.Timestamp) -> bool:
        """Check if timestamp is in overnight session (21:00-07:00 UTC)"""
        hour = timestamp.hour
        return hour >= 21 or hour < 7

    def is_us_session(self, timestamp: pd.Timestamp) -> bool:
        """Check if timestamp is in US session (14:00-21:00 UTC)"""
        hour = timestamp.hour
        return 14 <= hour < 21

    def is_asia_eu_session(self, timestamp: pd.Timestamp) -> bool:
        """Check if timestamp is in Asia/EU session (07:00-14:00 UTC)"""
        hour = timestamp.hour
        return 7 <= hour < 14

    def check_session(self, timestamp: pd.Timestamp) -> bool:
        """Check if current timestamp is in allowed session"""
        if self.session_filter == 'overnight':
            return self.is_overnight_session(timestamp)
        elif self.session_filter == 'us':
            return self.is_us_session(timestamp)
        elif self.session_filter == 'asia_eu':
            return self.is_asia_eu_session(timestamp)
        else:  # 'all'
            return True

    def detect_volume_zone_end(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect when a volume zone ends and classify it as accumulation or distribution.

        Returns zone info if a valid zone just ended, None otherwise.
        """
        if len(df) < self.lookback_bars + self.min_zone_bars + 5:
            return None

        # Calculate volume ratio for current candle
        current = df.iloc[-1]

        # Check if vol_ratio exists, otherwise calculate it
        if 'vol_ratio' in df.columns and not pd.isna(current.get('vol_ratio')):
            vol_ratio = current['vol_ratio']
        else:
            # Calculate manually
            vol_ma = df['volume'].rolling(20).mean().iloc[-1]
            if pd.isna(vol_ma) or vol_ma == 0:
                return None
            vol_ratio = current['volume'] / vol_ma

        is_elevated = vol_ratio >= self.volume_threshold

        # Track zone
        if is_elevated:
            if not self.in_zone:
                # Starting new zone
                self.in_zone = True
                self.zone_start_idx = len(df) - 1
                self.zone_bars = 1
                self.zone_highs = [current['high']]
                self.zone_lows = [current['low']]
            else:
                # Continuing zone
                self.zone_bars += 1
                self.zone_highs.append(current['high'])
                self.zone_lows.append(current['low'])

                # Cap zone length
                if self.zone_bars > self.max_zone_bars:
                    # Zone too long, reset
                    if self.zone_bars >= self.min_zone_bars:
                        # Save current zone before resetting
                        zone_high = max(self.zone_highs)
                        zone_low = min(self.zone_lows)
                        zone_info = self._classify_zone(df, zone_high, zone_low)
                        self._reset_zone()
                        return zone_info
                    self._reset_zone()
        else:
            # Volume dropped - zone ended
            if self.in_zone and self.zone_bars >= self.min_zone_bars:
                # Valid zone ended - classify it
                zone_high = max(self.zone_highs)
                zone_low = min(self.zone_lows)
                zone_info = self._classify_zone(df, zone_high, zone_low)
                self._reset_zone()
                return zone_info
            else:
                # Zone too short, reset
                self._reset_zone()

        return None

    def _reset_zone(self):
        """Reset zone tracking"""
        self.in_zone = False
        self.zone_start_idx = None
        self.zone_bars = 0
        self.zone_highs = []
        self.zone_lows = []

    def _classify_zone(self, df: pd.DataFrame, zone_high: float, zone_low: float) -> Optional[Dict[str, Any]]:
        """
        Classify a volume zone as accumulation (at lows) or distribution (at highs).

        Returns:
            {'type': 'accumulation'/'distribution', 'zone_high': float, 'zone_low': float}
            or None if zone is not at an extreme
        """
        # Get lookback window
        lookback_start = max(0, len(df) - self.lookback_bars - self.zone_bars - 5)
        lookback_end = len(df) - 1

        lookback_data = df.iloc[lookback_start:lookback_end]

        if len(lookback_data) < 10:
            return None

        window_low = lookback_data['low'].min()
        window_high = lookback_data['high'].max()

        # Accumulation: zone is at local low
        if zone_low <= window_low * 1.002:  # Within 0.2% of window low
            return {
                'type': 'accumulation',
                'zone_high': zone_high,
                'zone_low': zone_low,
                'zone_bars': self.zone_bars
            }

        # Distribution: zone is at local high
        if zone_high >= window_high * 0.998:  # Within 0.2% of window high
            return {
                'type': 'distribution',
                'zone_high': zone_high,
                'zone_low': zone_low,
                'zone_bars': self.zone_bars
            }

        return None

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Analyze market and generate signal when volume zone ends"""
        if len(df_1min) < 50:  # Need enough data for lookback
            return None

        # Get current candle
        current = df_1min.iloc[-1]

        # Check required columns
        required_cols = ['close', 'open', 'high', 'low', 'volume', 'atr']
        if any(col not in df_1min.columns or pd.isna(current.get(col)) for col in required_cols):
            return None

        # SESSION FILTER - Critical for profitability
        timestamp = current.get('timestamp')
        if timestamp is not None:
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            if not self.check_session(timestamp):
                return None

        # Detect volume zone ending
        zone_info = self.detect_volume_zone_end(df_1min)

        if zone_info is None:
            return None

        # ZONE DETECTED - Generate signal
        self.signals_generated += 1

        entry_price = current['close']
        atr = current['atr']

        if zone_info['type'] == 'accumulation':
            # LONG signal
            direction = 'LONG'
            stop_loss = entry_price - (self.stop_atr_mult * atr)

            # Calculate TP based on type
            if self.tp_type == 'atr_multiple':
                # OPTIMIZED: ATR-based TP (4.0x ATR absolute target)
                take_profit = entry_price + (self.tp_atr_mult * atr)
            else:
                # Fallback: R:R-based TP
                sl_distance = entry_price - stop_loss
                take_profit = entry_price + (self.rr_ratio * sl_distance)

            pattern = f"Volume Accumulation Zone ({zone_info['zone_bars']} bars)"

        else:  # distribution
            # SHORT signal
            direction = 'SHORT'
            stop_loss = entry_price + (self.stop_atr_mult * atr)

            # Calculate TP based on type
            if self.tp_type == 'atr_multiple':
                # OPTIMIZED: ATR-based TP (4.0x ATR absolute target)
                take_profit = entry_price - (self.tp_atr_mult * atr)
            else:
                # Fallback: R:R-based TP
                sl_distance = stop_loss - entry_price
                take_profit = entry_price - (self.rr_ratio * sl_distance)

            pattern = f"Volume Distribution Zone ({zone_info['zone_bars']} bars)"

        # Store entry time for time-based exit tracking
        self.entry_time = timestamp

        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pattern': pattern,
            'confidence': 0.75,  # 63.6% WR (optimized)
            'atr': atr,
            'zone_bars': zone_info['zone_bars'],
            'zone_high': zone_info['zone_high'],
            'zone_low': zone_info['zone_low'],
            'max_hold_bars': self.max_hold_bars
        }

    def should_exit_time(self, current_bar_index: int, entry_bar_index: int) -> bool:
        """Check if time-based exit should trigger"""
        bars_held = current_bar_index - entry_bar_index
        return bars_held >= self.max_hold_bars

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_statistics()
        stats.update({
            'volume_threshold': self.volume_threshold,
            'min_zone_bars': self.min_zone_bars,
            'session_filter': self.session_filter,
            'tp_type': self.tp_type,
            'tp_atr_mult': f'{self.tp_atr_mult}x ATR' if self.tp_type == 'atr_multiple' else None,
            'r_r_ratio': f'{self.rr_ratio}:1' if self.tp_type == 'rr_multiple' else None,
            'stop_atr_mult': self.stop_atr_mult,
            'max_hold_minutes': self.max_hold_bars,
            'current_zone_bars': self.zone_bars,
            'in_zone': self.in_zone
        })
        return stats
