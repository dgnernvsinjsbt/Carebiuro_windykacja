"""
Trading Engine Main Entry Point

Orchestrates all components and runs the main event loop
"""

import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from monitoring.logger import setup_logging, get_logger
from monitoring.metrics import PerformanceTracker
from database.trade_logger import TradeLogger
from data.candle_builder import MultiTimeframeCandleManager
from data.indicators import IndicatorCalculator
from strategies.multi_timeframe_long import MultiTimeframeLongStrategy
from strategies.trend_distance_short import TrendDistanceShortStrategy
from execution.signal_generator import SignalGenerator
from execution.position_manager import PositionManager
from execution.risk_manager import RiskManager
from execution.bingx_client import BingXClient


class TradingEngine:
    """Main trading engine orchestrator"""

    def __init__(self, config_path: str = 'config.yaml'):
        # Load configuration
        self.config = load_config(config_path)

        # Setup logging
        setup_logging(
            level=self.config.logging.level,
            console_output=self.config.logging.console_output,
            file_output=self.config.logging.file_output,
            file_path=self.config.logging.file_path,
            max_size_mb=self.config.logging.max_size_mb,
            backup_count=self.config.logging.backup_count,
            json_format=self.config.logging.json_format
        )

        self.logger = get_logger(__name__)
        self.logger.info("=" * 70)
        self.logger.info("TRADING ENGINE STARTING")
        self.logger.info("=" * 70)

        # Initialize components
        self.db = TradeLogger(self.config.get_database_url(), self.config.database.echo)
        self.metrics = PerformanceTracker(initial_capital=10000)  # TODO: Get from BingX

        # Initialize strategies
        self.strategies = []
        if self.config.is_strategy_enabled('multi_timeframe_long'):
            strategy_config = self.config.get_strategy_config('multi_timeframe_long')
            self.strategies.append(MultiTimeframeLongStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('multi_timeframe_long')

        if self.config.is_strategy_enabled('trend_distance_short'):
            strategy_config = self.config.get_strategy_config('trend_distance_short')
            self.strategies.append(TrendDistanceShortStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('trend_distance_short')

        # Initialize execution components
        self.signal_generator = SignalGenerator(self.strategies)

        max_positions = {s.name: self.config.get_strategy_config(s.name).max_positions 
                        for s in self.strategies}
        self.position_manager = PositionManager(max_positions)
        self.risk_manager = RiskManager(self.config.trading.risk_management)

        # BingX client
        self.bingx = BingXClient(
            self.config.bingx.api_key,
            self.config.bingx.api_secret,
            self.config.bingx.testnet,
            self.config.bingx.base_url
        )

        # Candle management
        self.candle_manager = MultiTimeframeCandleManager(
            base_interval=1,
            timeframes=[1, 5],
            buffer_size=self.config.data.buffer_size
        )

        self.running = False
        self.logger.info("Trading engine initialized successfully")

    async def pre_flight_checks(self) -> bool:
        """Run pre-flight checks before starting"""
        self.logger.info("Running pre-flight checks...")

        # Check stop file
        if Path(self.config.safety.stop_file).exists():
            self.logger.error(f"Stop file exists: {self.config.safety.stop_file}")
            return False

        # Test BingX connectivity
        if not self.config.safety.dry_run:
            if not await self.bingx.ping():
                self.logger.error("Failed to connect to BingX")
                return False

        self.logger.info("Pre-flight checks passed")
        return True

    async def on_candle_closed(self, timeframe: int, candle) -> None:
        """Handle closed candle event"""
        if timeframe != 1:  # Only process 1-min candles
            return

        # Get dataframes
        df_1min = self.candle_manager.get_dataframe(1)
        df_5min = self.candle_manager.get_dataframe(5)

        if len(df_1min) < 250:
            return  # Not enough data

        # Calculate indicators
        calc_1min = IndicatorCalculator(df_1min)
        df_1min = calc_1min.add_all_indicators()

        calc_5min = IndicatorCalculator(df_5min)
        df_5min = calc_5min.add_all_indicators()

        # Generate signals
        signals = self.signal_generator.generate_signals(df_1min, df_5min)

        if signals:
            # Resolve conflicts if multiple signals
            signal = self.signal_generator.resolve_conflicts(signals)

            # Check risk management
            can_trade, reason = self.risk_manager.validate_trade(signal, self.metrics.current_capital)

            if not can_trade:
                self.logger.warning(f"Trade rejected: {reason}")
                return

            # Check position limits
            if not self.position_manager.can_open_position(signal['strategy']):
                self.logger.warning(f"Position limit reached for {signal['strategy']}")
                return

            # Execute trade (dry run or live)
            await self.execute_trade(signal)

    async def execute_trade(self, signal: dict) -> None:
        """Execute a trade based on signal"""
        if self.config.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: {signal['strategy']} {signal['direction']} @ {signal['entry_price']}")
            return

        # TODO: Implement actual trade execution via BingX
        self.logger.info(f"[PLACEHOLDER] Executing trade: {signal}")

    async def run(self) -> None:
        """Main event loop"""
        # Pre-flight checks
        if not await self.pre_flight_checks():
            self.logger.error("Pre-flight checks failed, exiting")
            return

        self.running = True
        self.logger.info("Trading engine running")

        # Log system startup
        self.db.log_event('START', 'INFO', 'Trading engine started', component='main')

        # TODO: Connect to data feed and process ticks
        # For now, just keep running
        try:
            while self.running:
                # Check for stop file
                if Path(self.config.safety.stop_file).exists():
                    self.logger.warning("Stop file detected, shutting down")
                    break

                # Check daily reset
                self.metrics.check_daily_reset()

                # Print dashboard periodically
                # await asyncio.sleep(self.config.logging.dashboard_interval_minutes * 60)
                # self.metrics.print_dashboard()

                await asyncio.sleep(1)  # Main loop

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        self.logger.info("Shutting down trading engine...")

        self.running = False

        # Close positions if configured
        if self.config.safety.close_positions_on_shutdown:
            self.logger.info("Closing all open positions...")
            # TODO: Implement position closing

        # Close BingX client
        await self.bingx.close()

        # Log shutdown
        self.db.log_event('STOP', 'INFO', 'Trading engine stopped', component='main')

        # Print final stats
        self.metrics.print_dashboard()

        self.logger.info("Trading engine stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nShutdown signal received")
    sys.exit(0)


async def main():
    """Entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run engine
    engine = TradingEngine()
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
