"""
Candle Builder

Constructs OHLCV candles from tick data and handles resampling
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import deque
import logging


class Candle:
    """Represents a single OHLCV candle"""

    def __init__(self, timestamp: datetime, open_price: float):
        self.timestamp = timestamp
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0.0
        self.trades = 0
        self.is_closed = False

    def update(self, price: float, volume: float) -> None:
        """Update candle with new tick"""
        if self.is_closed:
            raise ValueError("Cannot update closed candle")

        self.close = price
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.volume += volume
        self.trades += 1

    def close_candle(self) -> None:
        """Mark candle as closed"""
        self.is_closed = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'trades': self.trades
        }

    def __repr__(self) -> str:
        return (f"Candle(ts={self.timestamp}, O={self.open:.8f}, "
                f"H={self.high:.8f}, L={self.low:.8f}, C={self.close:.8f}, "
                f"V={self.volume:.2f})")


class CandleBuilder:
    """
    Builds OHLCV candles from real-time tick data

    Manages candle construction and provides history buffer
    """

    def __init__(self, interval_minutes: int = 1, buffer_size: int = 300):
        """
        Initialize candle builder

        Args:
            interval_minutes: Candle interval in minutes
            buffer_size: Number of historical candles to keep
        """
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.buffer_size = buffer_size

        # Current candle being built
        self.current_candle: Optional[Candle] = None

        # Historical candles
        self.candles: deque = deque(maxlen=buffer_size)

        # Statistics
        self.total_ticks = 0
        self.total_candles = 0

        self.logger = logging.getLogger(__name__)

    def _get_candle_timestamp(self, tick_time: datetime) -> datetime:
        """
        Get candle timestamp for a given tick time

        Aligns to interval boundaries (e.g., :00, :01, :02 for 1-min candles)
        """
        # Round down to interval boundary
        minutes = (tick_time.minute // self.interval_minutes) * self.interval_minutes
        return tick_time.replace(minute=minutes, second=0, microsecond=0)

    def process_tick(self, timestamp: datetime, price: float, volume: float) -> Optional[Candle]:
        """
        Process a new tick and build candles

        Args:
            timestamp: Tick timestamp
            price: Tick price
            volume: Tick volume

        Returns:
            Closed candle if interval completed, None otherwise
        """
        self.total_ticks += 1

        candle_ts = self._get_candle_timestamp(timestamp)

        # Initialize first candle
        if self.current_candle is None:
            self.current_candle = Candle(candle_ts, price)
            self.current_candle.update(price, volume)
            self.logger.debug(f"Initialized first candle at {candle_ts}")
            return None

        # Check if we need to close current candle and start new one
        if candle_ts > self.current_candle.timestamp:
            # Close current candle
            self.current_candle.close_candle()
            closed_candle = self.current_candle

            # Add to history
            self.candles.append(closed_candle)
            self.total_candles += 1

            self.logger.info(f"Candle closed: {closed_candle}")

            # Start new candle
            self.current_candle = Candle(candle_ts, price)
            self.current_candle.update(price, volume)

            return closed_candle

        # Update current candle
        self.current_candle.update(price, volume)
        return None

    def get_dataframe(self, last_n: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical candles as DataFrame

        Args:
            last_n: Number of most recent candles to include (None = all)

        Returns:
            DataFrame with OHLCV data
        """
        if not self.candles:
            return pd.DataFrame()

        candles_list = list(self.candles)
        if last_n:
            candles_list = candles_list[-last_n:]

        df = pd.DataFrame([c.to_dict() for c in candles_list])
        df.set_index('timestamp', inplace=True)

        return df

    def get_latest_candle(self) -> Optional[Candle]:
        """Get the most recent completed candle"""
        if self.candles:
            return self.candles[-1]
        return None

    def get_current_candle(self) -> Optional[Candle]:
        """Get the current candle being built"""
        return self.current_candle

    def resample(self, target_interval_minutes: int) -> pd.DataFrame:
        """
        Resample candles to a different interval

        Args:
            target_interval_minutes: Target interval in minutes

        Returns:
            Resampled DataFrame
        """
        df = self.get_dataframe()

        if df.empty:
            return pd.DataFrame()

        # Resample using pandas
        resampled = pd.DataFrame()
        resampled['open'] = df['open'].resample(f'{target_interval_minutes}T').first()
        resampled['high'] = df['high'].resample(f'{target_interval_minutes}T').max()
        resampled['low'] = df['low'].resample(f'{target_interval_minutes}T').min()
        resampled['close'] = df['close'].resample(f'{target_interval_minutes}T').last()
        resampled['volume'] = df['volume'].resample(f'{target_interval_minutes}T').sum()

        resampled.dropna(inplace=True)

        return resampled

    def clear_history(self) -> None:
        """Clear historical candles"""
        self.candles.clear()
        self.logger.info("Candle history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get builder statistics"""
        return {
            'interval_minutes': self.interval_minutes,
            'buffer_size': self.buffer_size,
            'total_ticks': self.total_ticks,
            'total_candles': self.total_candles,
            'history_size': len(self.candles),
            'current_candle': self.current_candle.to_dict() if self.current_candle else None
        }


class MultiTimeframeCandleManager:
    """
    Manages candles for multiple timeframes

    Efficiently builds 1-min candles and resamples to higher timeframes
    """

    def __init__(self, base_interval: int = 1, timeframes: List[int] = None,
                 buffer_size: int = 300):
        """
        Initialize multi-timeframe manager

        Args:
            base_interval: Base interval in minutes (default: 1)
            timeframes: List of timeframes to maintain (e.g., [1, 5, 15])
            buffer_size: Buffer size for each timeframe
        """
        self.base_interval = base_interval
        self.timeframes = timeframes or [1, 5, 15]
        self.buffer_size = buffer_size

        # Create builder for base interval
        self.base_builder = CandleBuilder(base_interval, buffer_size)

        # Builders for higher timeframes
        self.builders: Dict[int, CandleBuilder] = {
            tf: CandleBuilder(tf, buffer_size)
            for tf in self.timeframes if tf != base_interval
        }

        self.logger = logging.getLogger(__name__)

    def process_tick(self, timestamp: datetime, price: float,
                    volume: float) -> Dict[int, Optional[Candle]]:
        """
        Process tick for all timeframes

        Args:
            timestamp: Tick timestamp
            price: Tick price
            volume: Tick volume

        Returns:
            Dictionary mapping timeframe to closed candle (if any)
        """
        closed_candles = {}

        # Process base interval
        base_candle = self.base_builder.process_tick(timestamp, price, volume)
        closed_candles[self.base_interval] = base_candle

        # If base candle closed, update higher timeframes
        if base_candle:
            for tf, builder in self.builders.items():
                # Get candle timestamp for this timeframe
                candle_ts = builder._get_candle_timestamp(timestamp)

                # Initialize or update candle
                if builder.current_candle is None:
                    builder.current_candle = Candle(candle_ts, base_candle.open)

                # Check if we need to close this timeframe's candle
                if candle_ts > builder.current_candle.timestamp:
                    builder.current_candle.close_candle()
                    closed_candles[tf] = builder.current_candle
                    builder.candles.append(builder.current_candle)
                    builder.total_candles += 1

                    # Start new candle
                    builder.current_candle = Candle(candle_ts, base_candle.close)

                # Update with base candle data
                builder.current_candle.high = max(builder.current_candle.high, base_candle.high)
                builder.current_candle.low = min(builder.current_candle.low, base_candle.low)
                builder.current_candle.close = base_candle.close
                builder.current_candle.volume += base_candle.volume
                builder.current_candle.trades += base_candle.trades

        return closed_candles

    def get_dataframe(self, timeframe: int) -> pd.DataFrame:
        """Get DataFrame for specific timeframe"""
        if timeframe == self.base_interval:
            return self.base_builder.get_dataframe()
        elif timeframe in self.builders:
            return self.builders[timeframe].get_dataframe()
        else:
            raise ValueError(f"Timeframe {timeframe} not configured")

    def get_all_dataframes(self) -> Dict[int, pd.DataFrame]:
        """Get DataFrames for all timeframes"""
        dfs = {self.base_interval: self.base_builder.get_dataframe()}

        for tf, builder in self.builders.items():
            dfs[tf] = builder.get_dataframe()

        return dfs

    async def warmup_from_history(self, bingx_client, symbol: str, candles_count: int = 300) -> None:
        """
        Pre-load historical candles on startup to avoid 4-hour warmup wait

        Args:
            bingx_client: BingXClient instance
            symbol: Trading symbol (e.g., "FARTCOIN-USDT")
            candles_count: Number of historical candles to fetch (default: 300)
        """
        self.logger.info(f"Starting historical warmup for {symbol}: fetching {candles_count} candles...")

        try:
            # Fetch historical 1-minute klines from BingX
            klines = await bingx_client.get_klines(
                symbol=symbol,
                interval='1m',
                limit=candles_count
            )

            if not klines:
                self.logger.warning(f"No historical data returned for {symbol}")
                return

            self.logger.info(f"Received {len(klines)} historical candles from BingX")

            # Reverse klines to process in chronological order (BingX returns newest first)
            klines = list(reversed(klines))

            # Process each historical candle
            for kline in klines:
                # BingX kline format: {'time': 1234567890000, 'open': '0.1', 'high': '0.11', ...}
                timestamp = datetime.fromtimestamp(kline['time'] / 1000)

                # Create candle object
                candle = Candle(
                    timestamp=self.base_builder._get_candle_timestamp(timestamp),
                    open_price=float(kline['open'])
                )
                candle.high = float(kline['high'])
                candle.low = float(kline['low'])
                candle.close = float(kline['close'])
                candle.volume = float(kline['volume'])
                candle.close_candle()

                # Add to base builder
                self.base_builder.candles.append(candle)
                self.base_builder.total_candles += 1

                # Build higher timeframe candles
                for tf, builder in self.builders.items():
                    candle_ts = builder._get_candle_timestamp(timestamp)

                    # Initialize or update higher timeframe candle
                    if builder.current_candle is None:
                        builder.current_candle = Candle(candle_ts, candle.open)

                    # Check if we need to close and start new candle
                    if candle_ts > builder.current_candle.timestamp:
                        builder.current_candle.close_candle()
                        builder.candles.append(builder.current_candle)
                        builder.total_candles += 1
                        builder.current_candle = Candle(candle_ts, candle.open)

                    # Update with base candle data
                    builder.current_candle.high = max(builder.current_candle.high, candle.high)
                    builder.current_candle.low = min(builder.current_candle.low, candle.low)
                    builder.current_candle.close = candle.close
                    builder.current_candle.volume += candle.volume
                    builder.current_candle.trades += 1

            # Close any remaining open candles in higher timeframes
            for tf, builder in self.builders.items():
                if builder.current_candle and not builder.current_candle.is_closed:
                    builder.current_candle.close_candle()
                    builder.candles.append(builder.current_candle)
                    builder.total_candles += 1
                    builder.current_candle = None

            self.logger.info(f"✅ Warmup complete for {symbol}:")
            self.logger.info(f"   1-min candles: {len(self.base_builder.candles)}")
            for tf, builder in self.builders.items():
                self.logger.info(f"   {tf}-min candles: {len(builder.candles)}")

        except Exception as e:
            self.logger.error(f"Error during historical warmup for {symbol}: {e}", exc_info=True)
            raise

    def add_completed_candle(self, candle_data: dict) -> None:
        """
        Add a single completed candle to the manager

        Args:
            candle_data: Dict with keys: time, open, high, low, close, volume
        """
        timestamp = datetime.fromtimestamp(candle_data['time'] / 1000)

        # Create completed 1-min candle
        candle = Candle(
            timestamp=self.base_builder._get_candle_timestamp(timestamp),
            open_price=float(candle_data['open'])
        )
        candle.high = float(candle_data['high'])
        candle.low = float(candle_data['low'])
        candle.close = float(candle_data['close'])
        candle.volume = float(candle_data['volume'])
        candle.close_candle()

        # Add to base builder
        self.base_builder.candles.append(candle)
        self.base_builder.total_candles += 1

        # Update higher timeframe candles
        for tf, builder in self.builders.items():
            candle_ts = builder._get_candle_timestamp(timestamp)

            # Initialize or update higher timeframe candle
            if builder.current_candle is None:
                builder.current_candle = Candle(candle_ts, candle.open)

            # Check if we need to close and start new candle
            if candle_ts > builder.current_candle.timestamp:
                builder.current_candle.close_candle()
                builder.candles.append(builder.current_candle)
                builder.total_candles += 1
                builder.current_candle = Candle(candle_ts, candle.open)

            # Update with base candle data
            builder.current_candle.high = max(builder.current_candle.high, candle.high)
            builder.current_candle.low = min(builder.current_candle.low, candle.low)
            builder.current_candle.close = candle.close
            builder.current_candle.volume += candle.volume
            builder.current_candle.trades += 1
