"""
Trading Engine Main Entry Point

Orchestrates all components and runs the main event loop
"""

import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from monitoring.logger import setup_logging, get_logger
from monitoring.metrics import PerformanceTracker
from monitoring.notifications import EmailNotifier, init_notifier, get_notifier
from monitoring.status_reporter import get_reporter
from database.trade_logger import TradeLogger
from data.candle_builder import MultiTimeframeCandleManager
from data.indicators import IndicatorCalculator
from strategies.multi_timeframe_long import MultiTimeframeLongStrategy
from strategies.trend_distance_short import TrendDistanceShortStrategy
from strategies.moodeng_rsi_momentum import MoodengRSIMomentumStrategy
from strategies.doge_volume_zones import DogeVolumeZonesStrategy
from strategies.pepe_volume_zones import PepeVolumeZonesStrategy
from strategies.trump_volume_zones import TrumpVolumeZonesStrategy
from strategies.uni_volume_zones import UniVolumeZonesStrategy
from execution.signal_generator import SignalGenerator
from execution.position_manager import PositionManager, PositionStatus
from execution.risk_manager import RiskManager
from execution.bingx_client import BingXClient
from execution.order_executor import OrderExecutor
# NOTE: WebSocket removed - using pure REST API polling for reliability


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

        if self.config.is_strategy_enabled('moodeng_rsi_momentum'):
            strategy_config = self.config.get_strategy_config('moodeng_rsi_momentum')
            self.strategies.append(MoodengRSIMomentumStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('moodeng_rsi_momentum')

        if self.config.is_strategy_enabled('doge_volume_zones'):
            strategy_config = self.config.get_strategy_config('doge_volume_zones')
            self.strategies.append(DogeVolumeZonesStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('doge_volume_zones')

        if self.config.is_strategy_enabled('pepe_volume_zones'):
            strategy_config = self.config.get_strategy_config('pepe_volume_zones')
            self.strategies.append(PepeVolumeZonesStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('pepe_volume_zones')

        if self.config.is_strategy_enabled('trump_volume_zones'):
            strategy_config = self.config.get_strategy_config('trump_volume_zones')
            self.strategies.append(TrumpVolumeZonesStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('trump_volume_zones')

        if self.config.is_strategy_enabled('uni_volume_zones'):
            strategy_config = self.config.get_strategy_config('uni_volume_zones')
            self.strategies.append(UniVolumeZonesStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('uni_volume_zones')

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

        # Order executor
        self.executor = OrderExecutor(self.bingx)

        # Candle management
        self.candle_manager = MultiTimeframeCandleManager(
            base_interval=1,
            timeframes=[1, 5],
            buffer_size=self.config.data.buffer_size
        )

        # NOTE: WebSocket removed - using pure REST API polling instead
        # This eliminates data corruption issues from WebSocket

        # Account state
        self.account_balance = 0.0
        self.symbols = self.config.trading.symbols

        self.running = False

        # Initialize email notifier
        if self.config.notifications and self.config.notifications.enabled:
            self.notifier = init_notifier(
                api_key=self.config.notifications.resend_api_key,
                to_email=self.config.notifications.to_email,
                enabled=True
            )
            self.logger.info("Email notifications enabled")
        else:
            self.notifier = None
            self.logger.info("Email notifications disabled")

        # Initialize status reporter (for remote monitoring)
        self.status = get_reporter()
        self.status.update(
            strategies_active=[s.name for s in self.strategies],
            message='Initialized, starting pre-flight checks...'
        )

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

            # Get account balance
            balance_data = await self.bingx.get_balance()
            if isinstance(balance_data, list):
                for asset in balance_data:
                    if asset.get('asset') == 'USDT':
                        self.account_balance = float(asset.get('availableMargin', 0))
                        self.logger.info(f"Account balance: ${self.account_balance:.2f} USDT")

            # Check minimum balance
            if self.account_balance < self.config.safety.min_account_balance:
                self.logger.error(f"Balance ${self.account_balance:.2f} below minimum ${self.config.safety.min_account_balance}")
                return False

        self.logger.info("Pre-flight checks passed")

        # Update status for remote monitoring
        self.status.update(
            running=True,
            balance=self.account_balance,
            message='Pre-flight checks passed, starting...'
        )
        await self.status.report()

        # Send bot started notification
        if self.notifier:
            strategies_enabled = [s.name for s in self.strategies]
            await self.notifier.notify_bot_started(self.account_balance, strategies_enabled)

        return True

    async def _process_signal(self, symbol: str, candle: dict) -> None:
        """Process candle and generate signals"""
        try:
            # Get dataframes
            df_1min = self.candle_manager.get_dataframe(1)
            df_5min = self.candle_manager.get_dataframe(5)

            if len(df_1min) < 250:
                self.logger.debug(f"Not enough data: {len(df_1min)} candles (need 250)")
                return

            # Calculate indicators
            calc_1min = IndicatorCalculator(df_1min)
            df_1min = calc_1min.add_all_indicators()

            calc_5min = IndicatorCalculator(df_5min)
            df_5min = calc_5min.add_all_indicators()

            # Generate signals
            signals = self.signal_generator.generate_signals(df_1min, df_5min)

            if signals:
                signal = self.signal_generator.resolve_conflicts(signals)
                self.logger.info(f"Signal generated: {signal['strategy']} {signal['direction']}")

                # Check risk management
                can_trade, reason = self.risk_manager.validate_trade(signal, self.metrics.current_capital)
                if not can_trade:
                    self.logger.warning(f"Trade rejected: {reason}")
                    return

                # Check position limits
                if not self.position_manager.can_open_position(signal['strategy']):
                    self.logger.warning(f"Position limit reached for {signal['strategy']}")
                    return

                # Execute trade
                await self.execute_trade(signal)

        except Exception as e:
            self.logger.error(f"Error processing signal: {e}", exc_info=True)

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
            self.logger.info(f"[DRY RUN]   Entry: ${signal['entry_price']:.4f}")
            self.logger.info(f"[DRY RUN]   Stop-Loss: ${signal['stop_loss']:.4f}")
            self.logger.info(f"[DRY RUN]   Take-Profit: ${signal['take_profit']:.4f}")
            return

        # Get symbol (first symbol from config for now)
        # TODO: Multi-symbol support
        symbol = self.symbols[0] if self.symbols else "FARTCOIN-USDT"

        # Add symbol to signal if not present
        if 'symbol' not in signal:
            signal['symbol'] = symbol

        # Get strategy config for risk percentage
        strategy_config = self.config.get_strategy_config(signal['strategy'])
        risk_pct = strategy_config.base_risk_pct

        # Execute trade with automatic SL/TP
        result = await self.executor.execute_trade(
            signal=signal,
            symbol=symbol,
            account_balance=self.account_balance,
            risk_pct=risk_pct,
            use_market_order=True,  # Use market orders for faster execution
            leverage=self.config.bingx.default_leverage,
            leverage_mode=self.config.bingx.leverage_mode
        )

        if result['success']:
            # Register position with manager
            position = self.position_manager.open_position(
                signal=signal,
                quantity=result['quantity']
            )

            # Update position with order IDs
            position.entry_order_id = result['entry_order_id']
            position.sl_order_id = result['sl_order_id']
            position.tp_order_id = result['tp_order_id']
            position.status = PositionStatus.OPEN

            # Log to database
            self.db.log_trade_open(
                strategy=signal['strategy'],
                symbol=symbol,
                side=signal['direction'],
                entry_price=result['entry_price'],
                quantity=result['quantity'],
                stop_loss=result['stop_loss'],
                take_profit=result['take_profit']
            )

            # Update metrics
            self.metrics.record_trade_opened(signal['strategy'], result['quantity'] * result['entry_price'])

            self.logger.info(f"✅ Trade executed successfully! Position ID: {position.id}")

            # Update remote status
            self.status.update(
                today_trades=self.status.status.get('today_trades', 0) + 1,
                last_signal=f"{signal['direction']} @ ${result['entry_price']:.4f}",
                message=f"Trade executed: {signal['direction']} {symbol}"
            )
            await self.status.report()

            # Send email notification
            if self.notifier:
                await self.notifier.notify_trade_opened(
                    strategy=signal['strategy'],
                    symbol=symbol,
                    direction=signal['direction'],
                    entry_price=result['entry_price'],
                    quantity=result['quantity'],
                    stop_loss=result['stop_loss'],
                    take_profit=result['take_profit'],
                    leverage=self.config.bingx.default_leverage
                )

        else:
            self.logger.error(f"❌ Trade execution failed: {result.get('error')}")
            self.db.log_event('TRADE_FAILED', 'ERROR',
                            f"Failed to execute {signal['strategy']}: {result.get('error')}",
                            component='executor')

            # Send error notification
            if self.notifier:
                await self.notifier.notify_error(
                    error_type='TRADE_FAILED',
                    message=f"Failed to execute {signal['direction']} on {symbol}",
                    details=str(result.get('error', 'Unknown error'))
                )

    async def _poll_and_process_candles(self, symbol: str, expected_candle_time: datetime) -> bool:
        """
        Poll REST API for the latest candles and process signals.

        Args:
            symbol: Trading symbol
            expected_candle_time: The timestamp we expect the closed candle to have

        Returns:
            True if we got the correct candle, False if stale data
        """
        try:
            # Fetch last 5 candles from REST API
            klines = await self.bingx.get_klines(
                symbol=symbol,
                interval='1m',
                limit=5
            )

            if not klines or len(klines) < 2:
                self.logger.warning(f"No klines returned from REST API for {symbol}")
                return False

            # BingX returns newest first, so klines[1] is the last CLOSED candle
            # klines[0] is the current (still forming) candle
            latest_closed = klines[1] if len(klines) > 1 else klines[0]

            # Verify we got the expected candle (not stale data)
            candle_timestamp = datetime.fromtimestamp(latest_closed['time'] / 1000)

            # Compare hour and minute to handle hour boundaries correctly
            if (candle_timestamp.hour != expected_candle_time.hour or
                candle_timestamp.minute != expected_candle_time.minute):
                self.logger.debug(f"Stale candle: got {candle_timestamp.strftime('%H:%M')}, "
                                f"expected {expected_candle_time.strftime('%H:%M')}")
                return False  # Signal to retry

            # Build candle dict from REST API data
            candle = {
                'timestamp': candle_timestamp,
                'open': float(latest_closed['open']),
                'high': float(latest_closed['high']),
                'low': float(latest_closed['low']),
                'close': float(latest_closed['close']),
                'volume': float(latest_closed['volume'])
            }

            # Log the candle we're processing
            self.logger.info(f"✓ {symbol} candle {candle_timestamp.strftime('%H:%M')} | "
                           f"O={candle['open']:.5f} H={candle['high']:.5f} "
                           f"L={candle['low']:.5f} C={candle['close']:.5f}")

            # Check if we have enough data
            candle_count = len(self.candle_manager.get_dataframe(1))
            if candle_count < 250:
                self.logger.debug(f"Not enough candles for signals: {candle_count}/250")
                return True  # Candle was correct, just not enough history

            # Process signal with REST API data
            await self._process_signal(symbol, candle)
            return True

        except Exception as e:
            self.logger.error(f"Error polling {symbol}: {e}")
            return False

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

        # Pre-load historical candles to avoid 4-hour warmup wait
        self.logger.info("=" * 70)
        self.logger.info("HISTORICAL DATA WARMUP")
        self.logger.info("=" * 70)
        for symbol in self.symbols:
            try:
                await self.candle_manager.warmup_from_history(
                    bingx_client=self.bingx,
                    symbol=symbol,
                    candles_count=300
                )
            except Exception as e:
                self.logger.error(f"Failed to warmup historical data for {symbol}: {e}")
                # Continue with other symbols even if one fails

        candle_count = len(self.candle_manager.get_dataframe(1))
        self.logger.info(f"✅ Historical warmup complete: {candle_count} candles ready")
        self.logger.info("=" * 70)

        try:
            # ============================================================
            # PURE REST API POLLING - Aligned to minute boundaries
            # Polls at :00 each minute with retry until correct candle received
            # ============================================================
            self.logger.info("Starting REST API polling mode (aligned to :00 each minute)")

            while self.running:
                # Check for stop file
                if Path(self.config.safety.stop_file).exists():
                    self.logger.warning("Stop file detected, shutting down")
                    break

                # Wait until exactly :00 of next minute
                now = datetime.now()
                seconds_until_next_minute = 60 - now.second - (now.microsecond / 1_000_000)
                if seconds_until_next_minute <= 0:
                    seconds_until_next_minute += 60
                self.logger.debug(f"Waiting {seconds_until_next_minute:.1f}s until :00")
                await asyncio.sleep(seconds_until_next_minute)

                # Now it's :00 - the previous minute's candle should be closed
                now = datetime.now()
                # Expected candle timestamp is the start of the PREVIOUS minute
                expected_candle_time = (now - timedelta(minutes=1)).replace(second=0, microsecond=0)
                self.logger.info(f"Polling at {now.strftime('%H:%M:%S')} for candle {expected_candle_time.strftime('%H:%M')}")

                # Check daily reset
                self.metrics.check_daily_reset()

                # Poll each symbol with retry logic (max 10 retries = 10 seconds)
                max_retries = 10
                for symbol in self.symbols:
                    success = False
                    for attempt in range(max_retries):
                        try:
                            success = await self._poll_and_process_candles(symbol, expected_candle_time)
                            if success:
                                break  # Got correct candle
                            # Stale data - wait 1 second and retry
                            self.logger.debug(f"Retry {attempt + 1}/{max_retries} for {symbol}...")
                            await asyncio.sleep(1)
                        except Exception as e:
                            self.logger.error(f"Error polling {symbol}: {e}")
                            await asyncio.sleep(1)

                    if not success:
                        self.logger.warning(f"⚠️ Failed to get correct candle for {symbol} after {max_retries} retries")

                candle_count = len(self.candle_manager.get_dataframe(1))
                self.logger.info(f"Poll complete | Candles: {candle_count} | Balance: ${self.account_balance:.2f}")

                # Update remote status
                self.status.update(
                    candles=candle_count,
                    balance=self.account_balance,
                    open_positions=len(self.position_manager.get_open_positions()),
                    message=f'Running OK - {candle_count} candles'
                )
                await self.status.report()

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)

            # Update remote status with error
            self.status.update(
                last_error=str(e),
                message=f'ERROR: {str(e)[:50]}'
            )
            await self.status.report()

            # Send critical error notification
            if self.notifier:
                await self.notifier.notify_error(
                    error_type='MAIN_LOOP_CRASH',
                    message='Trading engine main loop crashed',
                    details=str(e)
                )
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        self.logger.info("Shutting down trading engine...")

        self.running = False

        # Update remote status
        self.status.update(running=False, message='Shutting down...')
        await self.status.report()

        # Stop WebSocket feed
        await self.ws_feed.stop()
        self.logger.info("WebSocket feed stopped")

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
