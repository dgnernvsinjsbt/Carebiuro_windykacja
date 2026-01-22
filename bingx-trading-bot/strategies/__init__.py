"""
Trading Strategies Module

All trading strategies inherit from BaseStrategy

=== STRATEGY 1: DONCHIAN BREAKOUT (1H CANDLES) ===

8-Coin Portfolio Performance (Jun-Dec 2025, 3% risk/trade):
- Total Return: +35,902%
- Max Drawdown: -39.9%
- R:R Ratio: 899x
- Win Rate: 60.6%
- Total Trades: 619

Individual Coin Performance (by R:R ratio, 3% risk, compounded):
1. UNI      - 19.35x R:R (TP=10.5, SL=2, Period=30)
2. PI       - 12.68x R:R (TP=3.0, SL=2, Period=15)
3. DOGE     -  7.81x R:R (TP=4.0, SL=4, Period=15)
4. PENGU    -  7.24x R:R (TP=7.0, SL=5, Period=25)
5. ETH      -  6.64x R:R (TP=1.5, SL=4, Period=20)
6. AIXBT    -  4.73x R:R (TP=12.0, SL=2, Period=15)
7. FARTCOIN -  4.61x R:R (TP=7.5, SL=2, Period=15)
8. CRV      -  2.92x R:R (TP=9.0, SL=5, Period=15)

=== STRATEGY 2: NEW LISTING SHORT (1H CANDLES) ===

Backtest Results (324 coins listed in 2025, first 30 days):
- Conservative (1-1-1%): +649% return, 19% DD, 33x R:R
- Aggressive (5-3-1%):   +75,150% return, 58% DD, 1304x R:R

Out-of-Sample 2026 (27 coins): 75% WR, +77.5% return, 9% DD

Logic:
- Wait 24h after listing
- Short when pump ≥25% above listing price
- Pyramid up to 3 entries (DCA on +10% moves)
- SL 25%, TP 25% or return to listing price
- Moving SL (moves up with each DCA entry)
"""

from .base_strategy import BaseStrategy
from .donchian_breakout import DonchianBreakout, create_donchian_strategies, COIN_PARAMS
from .new_listing_short import NewListingShort, create_new_listing_strategy

__all__ = [
    'BaseStrategy',
    'DonchianBreakout',
    'create_donchian_strategies',
    'COIN_PARAMS',
    'NewListingShort',
    'create_new_listing_strategy',
]
