"""
Trading Engine Main Entry Point

SIMPLIFIED ARCHITECTURE (Dec 2025):
- Every hour: Fetch 300 1h candles with start_time/end_time
- Build DataFrame from scratch (identical to backtests)
- Calculate indicators
- Log all values for verification
- Run strategies

NO MORE:
- Incremental candle building
- Candle managers
- Data corruption risks
"""

import asyncio
import signal
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from monitoring.logger import setup_logging, get_logger
from monitoring.metrics import PerformanceTracker
from monitoring.notifications import EmailNotifier, init_notifier, get_notifier
from monitoring.status_reporter import get_reporter
from database.trade_logger import TradeLogger
from data.indicators import IndicatorCalculator
from strategies.fartcoin_atr_limit import FartcoinATRLimitStrategy
from strategies.btc_rsi_swing import BTCRSISwingStrategy
from strategies.eth_rsi_swing import ETHRSISwingStrategy
from strategies.pepe_rsi_swing import PEPERSISwingStrategy
from strategies.doge_rsi_swing import DOGERSISwingStrategy
from strategies.moodeng_rsi_swing import MOODENGRSISwingStrategy
from strategies.trumpsol_rsi_swing import TRUMPSOLRSISwingStrategy
from strategies.crv_rsi_swing import CRVRSISwingStrategy
from strategies.melania_rsi_swing import MELANIARSISwingStrategy
from strategies.melania_rsi_optimized import MelaniaRSIOptimized
from strategies.aixbt_rsi_swing import AIXBTRSISwingStrategy
from strategies.uni_rsi_swing import UNIRSISwingStrategy
from strategies.xlm_rsi_swing import XLMRSISwingStrategy
from execution.signal_generator import SignalGenerator
from execution.position_manager import PositionManager, PositionStatus
from execution.risk_manager import RiskManager
from execution.bingx_client import BingXClient
from execution.order_executor import OrderExecutor
from execution.pending_order_manager import PendingOrderManager


class TradingEngine:
    """Main trading engine orchestrator - SIMPLIFIED ARCHITECTURE"""

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
        self.logger.info("TRADING ENGINE STARTING - SIMPLIFIED ARCHITECTURE")
        self.logger.info("=" * 70)

        # Initialize components
        self.db = TradeLogger(self.config.get_database_url(), self.config.database.echo)
        self.metrics = PerformanceTracker(initial_capital=10000)

        # Initialize strategies (Active: BTC, ETH, PEPE, DOGE RSI Swing + FARTCOIN ATR)
        self.strategies = []

        if self.config.is_strategy_enabled('btc_rsi_swing'):
            strategy_config = self.config.get_strategy_config('btc_rsi_swing')
            self.strategies.append(BTCRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('btc_rsi_swing')

        if self.config.is_strategy_enabled('eth_rsi_swing'):
            strategy_config = self.config.get_strategy_config('eth_rsi_swing')
            self.strategies.append(ETHRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('eth_rsi_swing')

        if self.config.is_strategy_enabled('pepe_rsi_swing'):
            strategy_config = self.config.get_strategy_config('pepe_rsi_swing')
            self.strategies.append(PEPERSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('pepe_rsi_swing')

        if self.config.is_strategy_enabled('doge_rsi_swing'):
            strategy_config = self.config.get_strategy_config('doge_rsi_swing')
            self.strategies.append(DOGERSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('doge_rsi_swing')

        if self.config.is_strategy_enabled('moodeng_rsi_swing'):
            strategy_config = self.config.get_strategy_config('moodeng_rsi_swing')
            self.strategies.append(MOODENGRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('moodeng_rsi_swing')

        if self.config.is_strategy_enabled('trumpsol_rsi_swing'):
            strategy_config = self.config.get_strategy_config('trumpsol_rsi_swing')
            self.strategies.append(TRUMPSOLRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('trumpsol_rsi_swing')

        if self.config.is_strategy_enabled('fartcoin_atr_limit'):
            strategy_config = self.config.get_strategy_config('fartcoin_atr_limit')
            self.strategies.append(FartcoinATRLimitStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('fartcoin_atr_limit')

        if self.config.is_strategy_enabled('crv_rsi_swing'):
            strategy_config = self.config.get_strategy_config('crv_rsi_swing')
            self.strategies.append(CRVRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('crv_rsi_swing')

        if self.config.is_strategy_enabled('melania_rsi_swing'):
            strategy_config = self.config.get_strategy_config('melania_rsi_swing')
            self.strategies.append(MELANIARSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('melania_rsi_swing')

        if self.config.is_strategy_enabled('aixbt_rsi_swing'):
            strategy_config = self.config.get_strategy_config('aixbt_rsi_swing')
            self.strategies.append(AIXBTRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('aixbt_rsi_swing')

        if self.config.is_strategy_enabled('uni_rsi_swing'):
            strategy_config = self.config.get_strategy_config('uni_rsi_swing')
            self.strategies.append(UNIRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('uni_rsi_swing')

        if self.config.is_strategy_enabled('xlm_rsi_swing'):
            strategy_config = self.config.get_strategy_config('xlm_rsi_swing')
            self.strategies.append(XLMRSISwingStrategy(strategy_config.__dict__))
            self.metrics.register_strategy('xlm_rsi_swing')

        if self.config.is_strategy_enabled('melania_rsi_optimized'):
            self.strategies.append(MelaniaRSIOptimized())
            self.metrics.register_strategy('melania_rsi_optimized')
            self.logger.info("✅ MELANIA RSI OPTIMIZED STRATEGY LOADED (+3,441% return, 53.43x R/DD)")

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

        # Pending order manager (for limit orders waiting for fill)
        self.pending_order_manager = PendingOrderManager(self.bingx)

        # Symbols to trade
        self.symbols = self.config.trading.symbols

        # Account state
        self.account_balance = 0.0
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

        # Initialize status reporter
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

    async def _fetch_and_analyze(self, symbol: str) -> tuple:
        """
        Fetch 300 1-hour candles and calculate indicators (identical to backtests)

        Returns:
            (df_1h, df_4h, latest_candle_data) or (None, None, None) on error
        """
        try:
            # Fetch last 300 hours with explicit time range
            now = datetime.now(timezone.utc)
            end_time = int(now.timestamp() * 1000)
            start_time = end_time - (300 * 60 * 60 * 1000)  # 300 hours ago

            klines = await self.bingx.get_klines(
                symbol=symbol,
                interval='1h',
                start_time=start_time,
                end_time=end_time,
                limit=300
            )

            if not klines or len(klines) < 250:
                self.logger.warning(f"{symbol}: Insufficient data ({len(klines) if klines else 0} candles)")
                return None, None, None

            # Build DataFrame (identical to backtests)
            df = pd.DataFrame(klines)
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            df = df.sort_values('timestamp')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # Calculate indicators
            calc = IndicatorCalculator(df)
            df_1h = calc.add_all_indicators()

            # Build 4-hour candles (for multi-timeframe strategies)
            df_4h = df_1h.resample('4h', on='timestamp').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            df_4h = df_4h.reset_index()

            # Calculate indicators for 4h
            calc_4h = IndicatorCalculator(df_4h)
            df_4h = calc_4h.add_all_indicators()

            # Get latest closed candle (second to last, since last might be forming)
            if len(df_1h) >= 2:
                latest = df_1h.iloc[-2]
            else:
                latest = df_1h.iloc[-1]

            return df_1h, df_4h, latest

        except Exception as e:
            self.logger.error(f"Error fetching/analyzing {symbol}: {e}", exc_info=True)
            return None, None, None

    async def _process_symbol(self, symbol: str) -> None:
        """Fetch data, log indicators, run strategies"""
        try:
            # ============================================================
            # CHECK PENDING LIMIT ORDERS (FIRST!)
            # ============================================================
            current_bar = int(pd.Timestamp.now().timestamp() // 3600)  # Hour-level bar index
            filled_signals = await self.pending_order_manager.check_pending_orders(current_bar)

            if filled_signals:
                self.logger.info(f"🎉 {len(filled_signals)} pending limit order(s) FILLED!")
                for filled_signal in filled_signals:
                    # Place SL/TP for filled limit order
                    await self._place_sl_tp_for_filled_order(filled_signal)

            # Fetch and analyze (same as backtests!)
            df_1h, df_4h, latest = await self._fetch_and_analyze(symbol)

            if df_1h is None:
                return

            # ============================================================
            # LOG ALL CALCULATED VALUES FOR VERIFICATION
            # ============================================================
            self.logger.info("=" * 70)
            self.logger.info(f"{symbol} - {latest['timestamp']}")
            self.logger.info("=" * 70)
            self.logger.info(f"  Open:   ${latest['open']:.6f}")
            self.logger.info(f"  High:   ${latest['high']:.6f}")
            self.logger.info(f"  Low:    ${latest['low']:.6f}")
            self.logger.info(f"  Close:  ${latest['close']:.6f}")
            self.logger.info(f"  Volume: {latest['volume']:,.0f}")

            # Log indicators (if available)
            if 'rsi' in latest and pd.notna(latest['rsi']):
                self.logger.info(f"  RSI(14): {latest['rsi']:.2f}")
            if 'sma_20' in latest and pd.notna(latest['sma_20']):
                self.logger.info(f"  SMA(20): ${latest['sma_20']:.6f}")
            if 'sma_50' in latest and pd.notna(latest['sma_50']):
                self.logger.info(f"  SMA(50): ${latest['sma_50']:.6f}")
            if 'sma_200' in latest and pd.notna(latest['sma_200']):
                self.logger.info(f"  SMA(200): ${latest['sma_200']:.6f}")
            if 'vol_ratio' in latest and pd.notna(latest['vol_ratio']):
                self.logger.info(f"  Vol Ratio: {latest['vol_ratio']:.2f}x")
            if 'atr' in latest and pd.notna(latest['atr']):
                self.logger.info(f"  ATR(14): ${latest['atr']:.6f}")

            # Log candle characteristics
            body = abs(latest['close'] - latest['open'])
            body_pct = (body / latest['open']) * 100 if latest['open'] != 0 else 0
            is_bullish = latest['close'] > latest['open']
            self.logger.info(f"  Body: {body_pct:.2f}% ({'BULLISH' if is_bullish else 'BEARISH' if latest['close'] < latest['open'] else 'DOJI'})")

            # ============================================================
            # GENERATE SIGNALS
            # ============================================================
            signals = self.signal_generator.generate_signals(df_1h, df_4h, symbol)

            if signals:
                signal = self.signal_generator.resolve_conflicts(signals)
                signal['symbol'] = symbol

                # Check if this is a pending limit order request
                if signal.get('type') == 'PENDING_LIMIT_REQUEST':
                    self.logger.info(f"  📝 PENDING LIMIT REQUEST: {signal['strategy']} {signal['direction']} @ ${signal['limit_price']:.6f}")

                    # Send email notification for signal generation
                    if self.notifier:
                        await self.notifier.notify_signal_generated(
                            strategy=signal['strategy'],
                            symbol=symbol,
                            direction=signal['direction'],
                            signal_price=signal.get('signal_price', signal['limit_price']),
                            limit_price=signal['limit_price'],
                            confidence=signal.get('confidence')
                        )

                    # Check risk management before placing limit order
                    can_trade, reason = self.risk_manager.validate_trade(signal, self.metrics.current_capital)
                    if not can_trade:
                        self.logger.warning(f"  ❌ Request rejected: {reason}")
                        return

                    # Check position limits
                    if not self.position_manager.can_open_position(signal['strategy']):
                        self.logger.warning(f"  ❌ Position limit reached for {signal['strategy']}")
                        return

                    # REMOVED: Blocking for duplicate pending orders
                    # Now allows multiple pending orders (matches backtest behavior)
                    # existing_pending = self.pending_order_manager.get_pending_orders_for_strategy(signal['strategy'])
                    # if existing_pending:
                    #     self.logger.warning(f"  ❌ Already have {len(existing_pending)} pending order(s) for {signal['strategy']} - skipping")
                    #     return

                    # Place pending limit order
                    await self._place_pending_limit_order(signal)

                else:
                    # Regular signal - execute immediately
                    self.logger.info(f"  🎯 SIGNAL: {signal['strategy']} {signal['direction']} @ ${signal['entry_price']:.6f}")

                    # Check risk management
                    can_trade, reason = self.risk_manager.validate_trade(signal, self.metrics.current_capital)
                    if not can_trade:
                        self.logger.warning(f"  ❌ Trade rejected: {reason}")
                        return

                    # Check position limits
                    if not self.position_manager.can_open_position(signal['strategy']):
                        self.logger.warning(f"  ❌ Position limit reached for {signal['strategy']}")
                        return

                    # REMOVED: Blocking for duplicate pending orders
                    # Now allows multiple pending orders (matches backtest behavior)
                    # existing_pending = self.pending_order_manager.get_pending_orders_for_strategy(signal['strategy'])
                    # if existing_pending:
                    #     self.logger.warning(f"  ❌ Already have {len(existing_pending)} pending order(s) for {signal['strategy']} - skipping")
                    #     return

                    # Execute trade
                    await self.execute_trade(signal)
            else:
                self.logger.info(f"  No signals found")

        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}", exc_info=True)

    async def execute_trade(self, signal: dict) -> None:
        """Execute a trade based on signal"""
        # Extract symbol from signal (added by _process_symbol)
        symbol = signal.get('symbol', self.symbols[0] if self.symbols else "FARTCOIN-USDT")

        if self.config.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: {symbol} {signal['strategy']} {signal['direction']} @ {signal['entry_price']}")
            self.logger.info(f"[DRY RUN]   Entry: ${signal['entry_price']:.4f}")
            self.logger.info(f"[DRY RUN]   Stop-Loss: ${signal['stop_loss']:.4f}")
            self.logger.info(f"[DRY RUN]   Take-Profit: ${signal['take_profit']:.4f}")
            return

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
            leverage_mode=self.config.bingx.leverage_mode,
            fixed_position_value_usdt=self.config.bingx.fixed_position_value_usdt
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

    async def _place_pending_limit_order(self, signal: dict) -> None:
        """
        Place a pending limit order on exchange

        Args:
            signal: PENDING_LIMIT_REQUEST signal from strategy
        """
        symbol = signal['symbol']
        strategy = signal['strategy']

        try:
            # Get contract info for precision
            contracts = await self.bingx.get_contract_info(symbol)
            contract = contracts[0] if isinstance(contracts, list) else contracts

            # Calculate position size based on limit price
            strategy_config = self.config.get_strategy_config(strategy)
            risk_pct = strategy_config.base_risk_pct

            # Use fixed position value (e.g., $6 USDT per trade) or fallback to % based
            fixed_value = self.config.bingx.fixed_position_value_usdt
            if fixed_value and fixed_value > 0:
                position_value = fixed_value
                self.logger.info(f"Using fixed position value: ${position_value:.2f} USDT")
            else:
                # Use risk_pct for position sizing (e.g., 10% = 0.10 of equity)
                position_value = self.account_balance * (risk_pct / 100) * self.config.bingx.default_leverage
                self.logger.info(f"Using %-based sizing: ${position_value:.2f} USDT ({risk_pct}% × {self.config.bingx.default_leverage}x leverage)")
            quantity = position_value / signal['limit_price']

            # Round to contract precision
            from decimal import Decimal, ROUND_DOWN
            quantity_precision = contract.get('quantityPrecision', 3)
            precision_factor = Decimal(10) ** quantity_precision
            quantity = float(Decimal(str(quantity)).quantize(
                Decimal('1') / precision_factor,
                rounding=ROUND_DOWN
            ))

            # Check minimum quantity
            min_qty = contract.get('minQty')
            if min_qty and quantity < float(min_qty):
                quantity = float(min_qty)

            self.logger.info(f"📝 Creating pending limit order:")
            self.logger.info(f"   Calculated quantity: {quantity}")

            # Create pending order through manager
            pending = await self.pending_order_manager.create_pending_order(
                symbol=symbol,
                strategy=strategy,
                direction=signal['direction'],
                limit_price=signal['limit_price'],
                quantity=quantity,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                signal_data=signal,
                current_bar=signal['current_bar'],
                max_wait_bars=signal['max_wait_bars'],
                contract_info=contract
            )

            if pending:
                self.logger.info(f"✅ Pending limit order created: {pending.order_id}")
                self.logger.info(f"   Limit: ${pending.limit_price:.6f}")
                self.logger.info(f"   Qty: {pending.quantity}")
                self.logger.info(f"   Max wait: {pending.max_wait_bars} bars")

                # Send email notification
                if self.notifier:
                    await self.notifier.notify_limit_order_placed(
                        strategy=strategy,
                        symbol=symbol,
                        direction=signal['direction'],
                        limit_price=pending.limit_price,
                        quantity=pending.quantity,
                        order_id=pending.order_id
                    )
            else:
                self.logger.error(f"❌ Failed to create pending limit order")

                # Send error email
                if self.notifier:
                    await self.notifier.notify_order_error(
                        strategy=strategy,
                        symbol=symbol,
                        direction=signal['direction'],
                        error_message="Failed to create pending limit order"
                    )

        except Exception as e:
            self.logger.error(f"❌ Error placing pending limit order: {e}", exc_info=True)

            # Send error email
            if self.notifier:
                await self.notifier.notify_order_error(
                    strategy=strategy,
                    symbol=symbol,
                    direction=signal.get('direction', 'UNKNOWN'),
                    error_message=str(e),
                    order_details=f"Limit price: {signal.get('limit_price', 'N/A')}"
                )

    async def _place_sl_tp_for_filled_order(self, signal: dict) -> None:
        """
        Place SL/TP for a limit order that has filled

        Args:
            signal: Filled signal from PendingOrderManager (includes entry_order_id)
        """
        symbol = signal['symbol']
        strategy = signal['strategy']

        try:
            self.logger.info(f"📊 Placing SL/TP for filled limit order:")
            self.logger.info(f"   Entry: ${signal['entry_price']:.6f}")
            self.logger.info(f"   SL: ${signal['stop_loss']:.6f}")
            self.logger.info(f"   TP: ${signal['take_profit']:.6f}")

            # Get contract info for precision
            contracts = await self.bingx.get_contract_info(symbol)
            contract = contracts[0] if isinstance(contracts, list) else contracts

            quantity = signal['quantity']
            direction = signal['direction']
            entry_side = "BUY" if direction == "LONG" else "SELL"
            exit_side = "SELL" if direction == "LONG" else "BUY"

            # Round prices to precision
            price_precision = contract.get('pricePrecision', 4)
            stop_loss = round(signal['stop_loss'], price_precision)
            take_profit = round(signal['take_profit'], price_precision)

            # Place stop-loss order
            self.logger.info("  Placing stop-loss...")
            sl_order = await self.bingx.place_order(
                symbol=symbol,
                side=exit_side,
                position_side="BOTH",
                order_type="STOP_MARKET",
                quantity=quantity,
                stop_price=stop_loss,
                close_position=True
            )
            sl_order_id = sl_order.get('orderId')
            self.logger.info(f"  ✅ Stop-loss placed: {sl_order_id}")

            # Place take-profit order
            self.logger.info("  Placing take-profit...")
            tp_order = await self.bingx.place_order(
                symbol=symbol,
                side=exit_side,
                position_side="BOTH",
                order_type="TAKE_PROFIT_MARKET",
                quantity=quantity,
                stop_price=take_profit,
                close_position=True
            )
            tp_order_id = tp_order.get('orderId')
            self.logger.info(f"  ✅ Take-profit placed: {tp_order_id}")

            # Register position with manager
            position = self.position_manager.open_position(
                signal=signal,
                quantity=quantity
            )

            # Update position with order IDs
            position.entry_order_id = signal['entry_order_id']
            position.sl_order_id = sl_order_id
            position.tp_order_id = tp_order_id
            position.status = PositionStatus.OPEN

            # Log to database
            self.db.log_trade_open(
                strategy=strategy,
                symbol=symbol,
                side=direction,
                entry_price=signal['entry_price'],
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            # Update metrics
            self.metrics.record_trade_opened(strategy, quantity * signal['entry_price'])

            self.logger.info(f"✅ SL/TP placed successfully! Position ID: {position.id}")

            # Update remote status
            self.status.update(
                today_trades=self.status.status.get('today_trades', 0) + 1,
                last_signal=f"{direction} @ ${signal['entry_price']:.4f}",
                message=f"Limit order filled: {direction} {symbol}"
            )
            await self.status.report()

            # Send email notification
            if self.notifier:
                await self.notifier.notify_trade_opened(
                    strategy=strategy,
                    symbol=symbol,
                    direction=direction,
                    entry_price=signal['entry_price'],
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=self.config.bingx.default_leverage
                )

        except Exception as e:
            self.logger.error(f"❌ Error placing SL/TP for filled order: {e}", exc_info=True)

    async def run(self) -> None:
        """Main event loop"""
        # Pre-flight checks
        if not await self.pre_flight_checks():
            self.logger.error("Pre-flight checks failed, exiting")
            return

        self.running = True
        self.logger.info("Trading engine running")

        # Log system startup
        self.db.log_event('START', 'INFO', 'Trading engine started (simplified architecture)', component='main')

        try:
            self.logger.info("=" * 70)
            self.logger.info("SIMPLIFIED POLLING MODE - 1H CANDLES")
            self.logger.info("Every hour: Fetch 300 1h candles → Calculate → Log → Trade")
            self.logger.info("=" * 70)

            while self.running:
                # Check for stop file
                if Path(self.config.safety.stop_file).exists():
                    self.logger.warning("Stop file detected, shutting down")
                    break

                # Wait until exactly :01 of next hour (candle fully settled)
                now = datetime.now(timezone.utc)
                next_hour = (now + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0)
                wait_seconds = (next_hour - now).total_seconds()
                if wait_seconds > 0:
                    self.logger.info(f"⏰ Waiting {wait_seconds/60:.0f} minutes until {next_hour.strftime('%H:%M:%S UTC')}")
                    await asyncio.sleep(wait_seconds)

                # Now it's top of the hour - process all symbols
                poll_time = datetime.now(timezone.utc)
                self.logger.info(f"\n{'=' * 70}")
                self.logger.info(f"POLL START: {poll_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                self.logger.info(f"{'=' * 70}")

                # Check daily reset
                self.metrics.check_daily_reset()

                # Process each symbol
                for symbol in self.symbols:
                    await self._process_symbol(symbol)

                # Update remote status
                self.status.update(
                    balance=self.account_balance,
                    open_positions=len(self.position_manager.get_open_positions()),
                    message=f'Running OK'
                )
                await self.status.report()

                self.logger.info(f"{'=' * 70}")
                self.logger.info(f"POLL COMPLETE | Balance: ${self.account_balance:.2f}")
                self.logger.info(f"{'=' * 70}\n")

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Clean shutdown"""
        self.logger.info("Shutting down trading engine...")
        self.running = False

        # Cancel all pending limit orders
        pending_count = self.pending_order_manager.get_pending_count()
        if pending_count > 0:
            self.logger.info(f"Canceling {pending_count} pending limit order(s)...")
            cancelled = await self.pending_order_manager.cancel_all_pending_orders()
            self.logger.info(f"✅ Cancelled {cancelled} pending order(s)")

        # Close all open positions (if enabled)
        if self.config.safety.close_positions_on_shutdown:
            open_positions = self.position_manager.get_open_positions()
            if open_positions:
                self.logger.info(f"Closing {len(open_positions)} open positions...")
                for position_id, position in open_positions.items():
                    try:
                        await self.executor.close_position(position)
                    except Exception as e:
                        self.logger.error(f"Error closing position {position_id}: {e}")

        # Close BingX client
        await self.bingx.close()

        # Log shutdown
        self.db.log_event('STOP', 'INFO', 'Trading engine stopped', component='main')

        # Send notification
        if self.notifier:
            await self.notifier.notify_bot_stopped()

        self.logger.info("Shutdown complete")


def main():
    """Entry point"""
    engine = TradingEngine()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\nShutdown signal received")
        asyncio.create_task(engine.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the engine
    asyncio.run(engine.run())


if __name__ == "__main__":
    main()
