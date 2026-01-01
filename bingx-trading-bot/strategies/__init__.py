"""
Trading Strategies Module

All trading strategies inherit from BaseStrategy

🚀 ACTIVE STRATEGIES (Dec 2025 - 15M CANDLES - SHORT REVERSAL PORTFOLIO):

4-Coin Portfolio Performance (Jun-Dec 2025):
- Starting: $100 → Final: $5,204,573 (+5,204,473%)
- Return/DD: 78,973x ⭐⭐⭐
- Max DD: -65.9%
- Win Rate: 39.9%
- Total Trades: 288

Individual Strategy Performance:
1. MELANIA Short Reversal - 53.96x R/DD, +1330%, 6/7 profitable months 🥇
2. DOGE Short Reversal - 32.53x R/DD, +1167%, 5/7 profitable months (57.5% of portfolio profit!)
3. FARTCOIN Short Reversal - 31.91x R/DD, +3112%, 4/7 profitable months
4. MOODENG Short Reversal - 29.70x R/DD, +844%, 7/7 profitable months ⭐ PERFECT CONSISTENCY

All strategies use:
- RSI reversal setup (overbought → support break → limit order retest)
- 5% risk per trade
- Swing high stop loss
- Fixed % take profit targets
- 15-minute candles
"""

from .base_strategy import BaseStrategy

# SHORT Reversal Strategies (ACTIVE - Dec 2025)
from .fartcoin_short_reversal import FartcoinShortReversal
from .moodeng_short_reversal import MoodengShortReversal
from .melania_short_reversal import MelaniaShortReversal
from .doge_short_reversal import DogeShortReversal

__all__ = [
    'BaseStrategy',
    # Active SHORT Reversal Portfolio
    'FartcoinShortReversal',
    'MoodengShortReversal',
    'MelaniaShortReversal',
    'DogeShortReversal',
]
