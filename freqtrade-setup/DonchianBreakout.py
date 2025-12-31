"""
Donchian Channel Breakout Strategy for Freqtrade

10-Coin Portfolio Performance (Jun-Dec 2025, 1H candles, 3% risk/trade):
- Total Return: +118,787%
- Max Drawdown: -36.7%
- R:R Ratio: 3,237x
- Win Rate: 60.7%
- Total Trades: 849

Strategy Logic:
1. ENTRY LONG: Close breaks above Donchian upper channel (highest high of N bars)
2. ENTRY SHORT: Close breaks below Donchian lower channel (lowest low of N bars)
3. SL: ATR-based stop loss
4. TP: ATR-based take profit
"""
import numpy as np
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
from datetime import datetime


# Optimal parameters per coin (from backtest optimization)
COIN_PARAMS = {
    'DOGE/USDT:USDT':     {'period': 15, 'tp_atr': 4.0,  'sl_atr': 4},
    'PENGU/USDT:USDT':    {'period': 25, 'tp_atr': 7.0,  'sl_atr': 5},
    'FARTCOIN/USDT:USDT': {'period': 15, 'tp_atr': 7.5,  'sl_atr': 2},
    'ETH/USDT:USDT':      {'period': 20, 'tp_atr': 1.5,  'sl_atr': 4},
    'UNI/USDT:USDT':      {'period': 30, 'tp_atr': 10.5, 'sl_atr': 2},
    'PI/USDT:USDT':       {'period': 15, 'tp_atr': 3.0,  'sl_atr': 2},
    'CRV/USDT:USDT':      {'period': 15, 'tp_atr': 9.0,  'sl_atr': 5},
    'AIXBT/USDT:USDT':    {'period': 15, 'tp_atr': 12.0, 'sl_atr': 2},
    'TRUMP/USDT:USDT':    {'period': 25, 'tp_atr': 3.0,  'sl_atr': 3},
    'BTC/USDT:USDT':      {'period': 30, 'tp_atr': 4.0,  'sl_atr': 4},
}

# Default parameters for unknown pairs
DEFAULT_PARAMS = {'period': 20, 'tp_atr': 4.0, 'sl_atr': 3}


class DonchianBreakout(IStrategy):
    """
    Donchian Channel Breakout with ATR-based SL/TP
    """

    INTERFACE_VERSION = 3

    # Enable shorting
    can_short: bool = True

    # Timeframe
    timeframe = '1h'

    # Disable ROI - we use custom TP
    minimal_roi = {"0": 100}

    # Initial stoploss (will be overridden by custom_stoploss)
    stoploss = -0.25

    # Use custom stoploss
    use_custom_stoploss = True

    # Required candles before trading
    startup_candle_count: int = 35

    # Process only new candles
    process_only_new_candles = True

    # Order types
    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }

    def get_params(self, pair: str) -> dict:
        """Get parameters for a specific pair"""
        return COIN_PARAMS.get(pair, DEFAULT_PARAMS)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate Donchian channels and ATR"""
        pair = metadata['pair']
        params = self.get_params(pair)
        period = params['period']

        # ATR (simple: high - low average over 14 bars)
        dataframe['atr'] = (dataframe['high'] - dataframe['low']).rolling(14).mean()

        # Donchian channels (shifted by 1 to avoid look-ahead)
        dataframe['donchian_upper'] = dataframe['high'].rolling(period).max().shift(1)
        dataframe['donchian_lower'] = dataframe['low'].rolling(period).min().shift(1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signals:
        - LONG: close > donchian_upper (breakout above)
        - SHORT: close < donchian_lower (breakout below)
        """

        # Long entry: breakout above upper channel
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['donchian_upper']) &
                (dataframe['atr'] > 0) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1

        # Short entry: breakout below lower channel
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['donchian_lower']) &
                (dataframe['atr'] > 0) &
                (dataframe['volume'] > 0)
            ),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signals - we use custom_exit for TP"""
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """
        ATR-based stoploss
        SL = entry +/- (sl_atr * ATR at entry)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stoploss

        # Get ATR at trade open time
        trade_candles = dataframe.loc[dataframe['date'] <= trade.open_date_utc]
        if len(trade_candles) < 1:
            return self.stoploss

        atr_at_entry = trade_candles.iloc[-1]['atr']

        if atr_at_entry <= 0 or np.isnan(atr_at_entry):
            return self.stoploss

        # Get SL multiplier for this pair
        params = self.get_params(pair)
        sl_atr = params['sl_atr']

        # Calculate SL distance as percentage
        sl_distance_pct = (sl_atr * atr_at_entry) / trade.open_rate

        # Return negative value (freqtrade convention)
        return -sl_distance_pct

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> str | bool:
        """
        ATR-based take profit
        TP = entry +/- (tp_atr * ATR at entry)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return False

        # Get ATR at trade open time
        trade_candles = dataframe.loc[dataframe['date'] <= trade.open_date_utc]
        if len(trade_candles) < 1:
            return False

        atr_at_entry = trade_candles.iloc[-1]['atr']

        if atr_at_entry <= 0 or np.isnan(atr_at_entry):
            return False

        # Get TP multiplier for this pair
        params = self.get_params(pair)
        tp_atr = params['tp_atr']

        # Calculate TP distance as percentage
        tp_distance_pct = (tp_atr * atr_at_entry) / trade.open_rate

        # Check if TP hit
        if current_profit >= tp_distance_pct:
            return 'tp_hit'

        return False
