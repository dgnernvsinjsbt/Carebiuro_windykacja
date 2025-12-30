"""
Trading Strategies Module

All trading strategies inherit from BaseStrategy

ACTIVE STRATEGY (Dec 2025 - 1H CANDLES - DONCHIAN BREAKOUT):

8-Coin Portfolio Performance (Jun-Dec 2025, 3% risk/trade):
- Total Return: +35,902%
- Max Drawdown: -39.9%
- R:R Ratio: 899x
- Win Rate: 60.6%
- Total Trades: 619

Individual Coin Performance (by R:R ratio):
1. PENGU   - 34.05x R:R (TP=7.0, SL=5, Period=25)
2. DOGE    - 16.72x R:R (TP=4.0, SL=4, Period=15)
3. FARTCOIN- 12.57x R:R (TP=7.5, SL=2, Period=15)
4. ETH     - 10.12x R:R (TP=1.5, SL=4, Period=20)
5. UNI     -  9.95x R:R (TP=10.5, SL=2, Period=30)
6. PI      -  7.79x R:R (TP=3.0, SL=2, Period=15)
7. CRV     -  7.43x R:R (TP=9.0, SL=5, Period=15)
8. AIXBT   -  5.86x R:R (TP=12.0, SL=2, Period=15)

Strategy Logic:
- Entry LONG: Close > Donchian Upper (highest high of N bars)
- Entry SHORT: Close < Donchian Lower (lowest low of N bars)
- ATR-based TP/SL with coin-specific multipliers
- 1-hour candles
"""

from .base_strategy import BaseStrategy
from .donchian_breakout import DonchianBreakout, create_donchian_strategies, COIN_PARAMS

__all__ = [
    'BaseStrategy',
    'DonchianBreakout',
    'create_donchian_strategies',
    'COIN_PARAMS',
]
