"""
DONCHIAN CHANNEL BREAKOUT STRATEGY

8-Coin Portfolio Performance (Jun-Dec 2025, 1H candles, 3% risk/trade):
- Total Return: +35,902%
- Max Drawdown: -39.9%
- R:R Ratio: 899x
- Win Rate: 60.6%
- Total Trades: 619

Strategy Logic:
1. ENTRY LONG: Close breaks above Donchian upper channel (highest high of N bars)
2. ENTRY SHORT: Close breaks below Donchian lower channel (lowest low of N bars)
3. SL: ATR-based stop loss
4. TP: ATR-based take profit

Each coin has individually optimized parameters from backtesting.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


# Optimal parameters per coin (from backtest optimization)
COIN_PARAMS = {
    'PENGU-USDT':    {'tp_atr': 7.0,  'period': 25, 'sl_atr': 5},
    'DOGE-USDT':     {'tp_atr': 4.0,  'period': 15, 'sl_atr': 4},
    'FARTCOIN-USDT': {'tp_atr': 7.5,  'period': 15, 'sl_atr': 2},
    'ETH-USDT':      {'tp_atr': 1.5,  'period': 20, 'sl_atr': 4},
    'UNI-USDT':      {'tp_atr': 10.5, 'period': 30, 'sl_atr': 2},
    'PI-USDT':       {'tp_atr': 3.0,  'period': 15, 'sl_atr': 2},
    'CRV-USDT':      {'tp_atr': 9.0,  'period': 15, 'sl_atr': 5},
    'AIXBT-USDT':    {'tp_atr': 12.0, 'period': 15, 'sl_atr': 2},
}


class DonchianBreakout(BaseStrategy):
    """Donchian Channel Breakout Strategy for multiple coins"""

    def __init__(self, config: Dict[str, Any], symbol: str):
        super().__init__(f'donchian_{symbol.split("-")[0].lower()}', config, symbol)

        # Get coin-specific parameters
        if symbol in COIN_PARAMS:
            params = COIN_PARAMS[symbol]
            self.tp_atr = params['tp_atr']
            self.period = params['period']
            self.sl_atr = params['sl_atr']
        else:
            # Default parameters for unknown coins
            self.tp_atr = 4.0
            self.period = 20
            self.sl_atr = 3
            self.logger.warning(f"[{symbol}] No optimized params - using defaults")

        # Risk settings
        self.risk_pct = config.get('risk_pct', 3.0)
        self.max_leverage = config.get('max_leverage', 5.0)

        # State tracking
        self.last_signal_bar = None

        self.logger.info(f"[{symbol}] Donchian Breakout initialized:")
        self.logger.info(f"  Period: {self.period}, TP: {self.tp_atr} ATR, SL: {self.sl_atr} ATR")

    def generate_signals(self, df: pd.DataFrame, current_positions: list) -> Optional[Dict[str, Any]]:
        """Generate Donchian breakout signals"""

        # Don't generate new signals if we already have a position
        if current_positions:
            self.logger.debug(f"[{self.symbol}] Skipping - already have position")
            return None

        # Need enough data for Donchian channel
        min_bars = max(self.period, 14) + 1
        if len(df) < min_bars:
            self.logger.debug(f"[{self.symbol}] Insufficient data - need {min_bars}, have {len(df)}")
            return None

        # Calculate indicators if not present
        if 'atr' not in df.columns:
            df['atr'] = (df['high'] - df['low']).rolling(14).mean()

        if 'donchian_upper' not in df.columns:
            df['donchian_upper'] = df['high'].rolling(self.period).max().shift(1)
            df['donchian_lower'] = df['low'].rolling(self.period).min().shift(1)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        current_bar_idx = len(df) - 1
        timestamp = latest.get('timestamp', 'N/A')

        # Skip if indicators not ready
        if pd.isna(latest['atr']) or pd.isna(latest['donchian_upper']) or latest['atr'] <= 0:
            self.logger.debug(f"[{self.symbol}] Indicators not ready")
            return None

        # Avoid duplicate signals on same bar
        if self.last_signal_bar == current_bar_idx:
            return None

        price = latest['close']
        upper = latest['donchian_upper']
        lower = latest['donchian_lower']
        atr = latest['atr']

        # Log current state
        self.logger.info(f"[{self.symbol}] Poll {timestamp} | Price: ${price:.4f} | Upper: ${upper:.4f} | Lower: ${lower:.4f} | ATR: ${atr:.4f}")

        signal = None

        # LONG: Close breaks above upper channel
        if price > upper:
            entry = price
            sl = entry - (self.sl_atr * atr)
            tp = entry + (self.tp_atr * atr)
            sl_dist_pct = (entry - sl) / entry * 100

            self.logger.info(f"[{self.symbol}] LONG BREAKOUT! Price ${price:.4f} > Upper ${upper:.4f}")
            self.logger.info(f"  Entry: ${entry:.4f}, SL: ${sl:.4f} ({sl_dist_pct:.2f}%), TP: ${tp:.4f}")

            signal = {
                'side': 'LONG',
                'direction': 'LONG',
                'type': 'MARKET',
                'entry_price': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'reason': f"Donchian breakout: ${price:.4f} > ${upper:.4f} (period={self.period})",
                'metadata': {
                    'atr': atr,
                    'donchian_upper': upper,
                    'donchian_lower': lower,
                    'sl_dist_pct': sl_dist_pct,
                    'tp_atr': self.tp_atr,
                    'sl_atr': self.sl_atr
                }
            }

        # SHORT: Close breaks below lower channel
        elif price < lower:
            entry = price
            sl = entry + (self.sl_atr * atr)
            tp = entry - (self.tp_atr * atr)
            sl_dist_pct = (sl - entry) / entry * 100

            self.logger.info(f"[{self.symbol}] SHORT BREAKOUT! Price ${price:.4f} < Lower ${lower:.4f}")
            self.logger.info(f"  Entry: ${entry:.4f}, SL: ${sl:.4f} ({sl_dist_pct:.2f}%), TP: ${tp:.4f}")

            signal = {
                'side': 'SHORT',
                'direction': 'SHORT',
                'type': 'MARKET',
                'entry_price': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'reason': f"Donchian breakout: ${price:.4f} < ${lower:.4f} (period={self.period})",
                'metadata': {
                    'atr': atr,
                    'donchian_upper': upper,
                    'donchian_lower': lower,
                    'sl_dist_pct': sl_dist_pct,
                    'tp_atr': self.tp_atr,
                    'sl_atr': self.sl_atr
                }
            }

        if signal:
            self.last_signal_bar = current_bar_idx
            self.signals_generated += 1

        return signal

    def calculate_position_size(self, entry_price: float, stop_price: float, capital: float) -> float:
        """Calculate position size based on risk percentage"""
        sl_distance_pct = abs(entry_price - stop_price) / entry_price * 100

        if sl_distance_pct <= 0:
            return 0

        # Position size = (Capital * Risk%) / SL_distance%
        # Capped at max_leverage
        leverage = min(self.risk_pct / sl_distance_pct, self.max_leverage)
        position_size = capital * leverage

        self.logger.info(f"[{self.symbol}] Position sizing: {self.risk_pct}% risk / {sl_distance_pct:.2f}% SL = {leverage:.2f}x leverage")

        return position_size

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Wrapper for generate_signals to match BaseStrategy interface"""
        return self.generate_signals(df_1min, [])


# Factory function to create strategies for all coins
def create_donchian_strategies(config: Dict[str, Any]) -> Dict[str, DonchianBreakout]:
    """Create Donchian breakout strategies for all supported coins"""
    strategies = {}
    for symbol in COIN_PARAMS.keys():
        strategies[symbol] = DonchianBreakout(config, symbol)
    return strategies
