"""
Trading Strategies Module

All trading strategies inherit from BaseStrategy

Active Strategies (Dec 2025 - 1H CANDLES):
1. CRV RSI Swing - 22.03x Return/DD 🏆 BEST!
2. MELANIA RSI Swing - 21.36x Return/DD (77% WR!)
3. AIXBT RSI Swing - 20.20x Return/DD
4. TRUMPSOL RSI Swing - 13.28x Return/DD
5. UNI RSI Swing - 12.38x Return/DD
6. DOGE RSI Swing - 10.66x Return/DD
7. XLM RSI Swing - 9.53x Return/DD
8. MOODENG RSI Swing - 8.38x Return/DD
9. FartcoinATRLimit - 8.44x Return/DD
10. PEPE RSI Swing - 7.13x Return/DD

Disabled (insufficient capital):
- BTC RSI Swing - 8.34x Return/DD
- ETH RSI Swing - 15.56x Return/DD
"""

from .base_strategy import BaseStrategy
from .btc_rsi_swing import BTCRSISwingStrategy
from .eth_rsi_swing import ETHRSISwingStrategy
from .pepe_rsi_swing import PEPERSISwingStrategy
from .doge_rsi_swing import DOGERSISwingStrategy
from .moodeng_rsi_swing import MOODENGRSISwingStrategy
from .trumpsol_rsi_swing import TRUMPSOLRSISwingStrategy
from .fartcoin_atr_limit import FartcoinATRLimitStrategy
from .crv_rsi_swing import CRVRSISwingStrategy
from .melania_rsi_swing import MELANIARSISwingStrategy
from .aixbt_rsi_swing import AIXBTRSISwingStrategy
from .uni_rsi_swing import UNIRSISwingStrategy
from .xlm_rsi_swing import XLMRSISwingStrategy

__all__ = [
    'BaseStrategy',
    'BTCRSISwingStrategy',
    'ETHRSISwingStrategy',
    'PEPERSISwingStrategy',
    'DOGERSISwingStrategy',
    'MOODENGRSISwingStrategy',
    'TRUMPSOLRSISwingStrategy',
    'FartcoinATRLimitStrategy',
    'CRVRSISwingStrategy',
    'MELANIARSISwingStrategy',
    'AIXBTRSISwingStrategy',
    'UNIRSISwingStrategy',
    'XLMRSISwingStrategy',
]
