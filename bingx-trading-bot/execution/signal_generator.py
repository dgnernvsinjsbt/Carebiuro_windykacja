"""Signal Generator - Aggregates signals from all strategies"""
from typing import List, Optional, Dict, Any
import pandas as pd
import logging

class SignalGenerator:
    """Aggregates signals from multiple strategies"""
    def __init__(self, strategies: List):
        self.strategies = strategies
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate signals from enabled strategies that match the given symbol"""
        signals = []
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            # Filter: only run strategy if it matches this symbol
            # Handle both 'MOODENG' and 'MOODENG-USDT' formats
            if symbol and strategy.symbol:
                symbol_base = symbol.split('-')[0]  # Extract base symbol (e.g., '1000PEPE' from '1000PEPE-USDT')
                if strategy.symbol != symbol and strategy.symbol != symbol_base:
                    continue
            signal = strategy.analyze(df_1min, df_5min)
            if signal:
                signal['strategy'] = strategy.name

                # Normalize field names for compatibility
                # Fix #1: Convert 'side' to 'direction' (main.py expects 'direction')
                if 'side' in signal and 'direction' not in signal:
                    signal['direction'] = signal['side']

                # Fix #2: Convert 'LIMIT' type to 'PENDING_LIMIT_REQUEST' (main.py expects this)
                if signal.get('type') == 'LIMIT':
                    signal['type'] = 'PENDING_LIMIT_REQUEST'

                signals.append(signal)
                # Log signal with appropriate price field
                price = signal.get('entry_price') or signal.get('limit_price') or signal.get('signal_price', 0.0)
                signal_type = signal.get('type', 'SIGNAL')
                direction = signal.get('direction', 'UNKNOWN')
                self.logger.info(f"Signal: {strategy.name} {direction} @ ${price:.6f} ({signal_type})")
        return signals

    def resolve_conflicts(self, signals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve conflicting signals - highest confidence wins"""
        if not signals:
            return None
        if len(signals) == 1:
            return signals[0]
        return max(signals, key=lambda s: s.get('confidence', 0.5))
