"""
TRUMPSOL Contrarian Strategy

**High Win Rate Mean Reversion: 68.8% WR, 5.17x Return/DD (with fees)**
+17.49% return, -3.38% DD (from 32-day BingX backtest with 0.1% fees)

Strategy: Fade violent moves with volume/volatility confirmation

Entry Conditions (CONTRARIAN):
- abs(ret_5m) >= 1.0% (pump or dump in 5 minutes)
- volume_ratio >= 1.0 (current volume >= 30-min average)
- atr_ratio >= 1.1 (current ATR >= 110% of 30-min average)
- hour NOT IN {1, 5, 17} (Europe/Warsaw timezone filter)
- DIRECTION: pump (+1%) → SHORT, dump (-1%) → LONG

Exit Conditions:
- Stop Loss: 1% from entry (fixed)
- Take Profit: 1.5% from entry (fixed)
- Time Exit: 15 bars (15 minutes) if neither SL/TP hit

Key Characteristics:
- 74% of trades hit time exit (not SL/TP) → most profits from small reversals
- LONG 2.7x better than SHORT (+13.94% vs +2.41% in backtest)
- Very selective: 2.4 trades/day average
- Best trades: extreme dumps (ret_5m < -3%) with vol > 5x → instant reversals
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy


class TrumpsolContrarianStrategy(BaseStrategy):
    """
    TRUMPSOL Contrarian Strategy
    - Fades violent moves (buy panic, short euphoria)
    - Requires volume + volatility confirmation
    - 1% SL, 1.5% TP, 15-minute max hold
    - High win rate (68.8%) mean reversion
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'TRUMPSOL-USDT'):
        super().__init__('trumpsol_contrarian', config, symbol)

        # Extract strategy parameters
        params = config.get('params', {})

        # Entry filters
        self.min_ret_5m_pct = params.get('min_ret_5m_pct', 1.0)  # Min 1% move in 5 min
        self.vol_ratio_min = params.get('vol_ratio_min', 1.0)    # Volume >= avg
        self.atr_ratio_min = params.get('atr_ratio_min', 1.1)    # ATR >= 110% avg

        # Time filter (Europe/Warsaw hours to exclude)
        self.excluded_hours = params.get('excluded_hours', [1, 5, 17])

        # Exit parameters (fixed % from entry)
        self.stop_loss_pct = params.get('stop_loss_pct', 1.0)    # 1% SL
        self.take_profit_pct = params.get('take_profit_pct', 1.5) # 1.5% TP
        self.max_hold_bars = params.get('max_hold_bars', 15)      # 15 minutes

        # Lookback periods
        self.vol_ma_period = params.get('vol_ma_period', 30)      # 30-bar volume MA
        self.atr_ma_period = params.get('atr_ma_period', 30)      # 30-bar ATR MA

        # Track entry time
        self.entry_time = None

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze market and generate CONTRARIAN signal on violent moves

        Signal generation:
        1. Calculate 5-minute return (ret_5m)
        2. Check volume_ratio (current / 30-bar MA)
        3. Check atr_ratio (current / 30-bar MA)
        4. Check timezone filter (exclude hours {1, 5, 17} Europe/Warsaw)
        5. If all pass: CONTRARIAN direction (pump → SHORT, dump → LONG)
        """
        if len(df_1min) < 35:  # Need 30 for MA + 5 for ret_5m
            return None

        # Get latest candle
        current = df_1min.iloc[-1]

        # Check if we have timestamp for timezone filter
        timestamp = current.get('timestamp')
        if timestamp is not None and not pd.isna(timestamp):
            # Convert to Europe/Warsaw timezone
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)

            try:
                # Ensure UTC first, then convert to Warsaw
                if timestamp.tz is None:
                    timestamp = timestamp.tz_localize('UTC')
                timestamp_warsaw = timestamp.tz_convert('Europe/Warsaw')
                hour_local = timestamp_warsaw.hour

                # Check hour filter
                if hour_local in self.excluded_hours:
                    return None  # Skip this hour
            except Exception:
                # If timezone conversion fails, proceed without filter
                pass

        # Calculate 5-minute return
        if len(df_1min) < 6:
            return None

        close_current = current['close']
        close_5min_ago = df_1min.iloc[-6]['close']
        ret_5m = (close_current - close_5min_ago) / close_5min_ago
        abs_ret_5m = abs(ret_5m)

        # FILTER 1: Momentum must be >= 1%
        if abs_ret_5m < (self.min_ret_5m_pct / 100):
            return None

        # FILTER 2: Volume ratio
        recent_volumes = df_1min['volume'].tail(self.vol_ma_period)
        vol_ma = recent_volumes.mean()
        vol_ratio = current['volume'] / vol_ma if vol_ma > 0 else 0

        if vol_ratio < self.vol_ratio_min:
            return None

        # FILTER 3: ATR ratio
        # Calculate simplified ATR if not present
        if 'atr' not in df_1min.columns or pd.isna(current.get('atr')):
            # Simplified: TR = high - low
            df_1min['tr_simple'] = df_1min['high'] - df_1min['low']
            df_1min['atr'] = df_1min['tr_simple'].rolling(window=14).mean()
            current = df_1min.iloc[-1]  # Refresh after calculation

        current_atr = current.get('atr', 0)
        if current_atr == 0 or pd.isna(current_atr):
            return None

        recent_atrs = df_1min['atr'].tail(self.atr_ma_period)
        atr_ma = recent_atrs.mean()
        atr_ratio = current_atr / atr_ma if atr_ma > 0 else 0

        if atr_ratio < self.atr_ratio_min:
            return None

        # ALL FILTERS PASSED - DETERMINE DIRECTION (CONTRARIAN)
        if ret_5m >= (self.min_ret_5m_pct / 100):
            # Pump up → FADE IT → SHORT
            direction = 'SHORT'
        elif ret_5m <= -(self.min_ret_5m_pct / 100):
            # Dump down → FADE IT → LONG
            direction = 'LONG'
        else:
            return None

        self.signals_generated += 1

        entry_price = close_current

        # Calculate SL/TP (fixed % from entry)
        if direction == 'LONG':
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit = entry_price * (1 + self.take_profit_pct / 100)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit = entry_price * (1 - self.take_profit_pct / 100)

        # Store entry time for time-based exit
        self.entry_time = timestamp if timestamp else pd.Timestamp.now()

        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pattern': f'Contrarian {direction} (fade {ret_5m*100:+.2f}% move)',
            'confidence': 0.69,  # 68.8% win rate from backtest
            'ret_5m': ret_5m,
            'vol_ratio': vol_ratio,
            'atr_ratio': atr_ratio,
            'atr': current_atr,
            'max_hold_bars': self.max_hold_bars
        }

    def should_exit_time(self, current_bar_index: int, entry_bar_index: int) -> bool:
        """Check if time-based exit should trigger (15 minutes)"""
        bars_held = current_bar_index - entry_bar_index
        return bars_held >= self.max_hold_bars

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_statistics()
        stats.update({
            'min_ret_5m_pct': self.min_ret_5m_pct,
            'vol_ratio_min': self.vol_ratio_min,
            'atr_ratio_min': self.atr_ratio_min,
            'sl_tp_ratio': f'{self.stop_loss_pct}:{self.take_profit_pct}',
            'max_hold_minutes': self.max_hold_bars,
            'excluded_hours': self.excluded_hours
        })
        return stats
