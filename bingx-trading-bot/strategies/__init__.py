"""
Trading Strategies Module

All trading strategies inherit from BaseStrategy

Active Strategies (Dec 2025):
1. PippinFreshCrossesStrategy - 12.71x Return/DD (BEST RISK-ADJUSTED!)
2. DogeVolumeZonesStrategy - 10.75x Return/DD (BingX optimized)
3. FartcoinATRLimitStrategy - 8.44x Return/DD
4. TrumpsolContrarianStrategy - 5.17x Return/DD (mean reversion)
"""

from .base_strategy import BaseStrategy
from .doge_volume_zones import DogeVolumeZonesStrategy
from .fartcoin_atr_limit import FartcoinATRLimitStrategy
from .trumpsol_contrarian import TrumpsolContrarianStrategy
from .pippin_fresh_crosses import PippinFreshCrossesStrategy

__all__ = [
    'BaseStrategy',
    'DogeVolumeZonesStrategy',
    'FartcoinATRLimitStrategy',
    'TrumpsolContrarianStrategy',
    'PippinFreshCrossesStrategy',
]
