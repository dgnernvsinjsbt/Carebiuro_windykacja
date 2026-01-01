"""
Order Executor - Handles automatic order placement with SL/TP
Implements the 3-order pattern: Entry -> Stop-Loss -> Take-Profit
"""

import asyncio
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
import logging

from execution.bingx_client import BingXClient, BingXAPIError


class OrderExecutor:
    """
    Executes trades with automatic stop-loss and take-profit

    Workflow:
    1. Calculate position size based on risk
    2. Place entry order (market or limit)
    3. Immediately place stop-loss order
    4. Immediately place take-profit order
    5. Return order IDs for tracking
    """

    def __init__(self, bingx_client: BingXClient):
        self.client = bingx_client
        self.logger = logging.getLogger(__name__)

    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        account_balance: float,
        risk_pct: float,  # Kept for API compatibility but NOT used
        contract_info: Dict[str, Any],
        leverage: int = 1,
        leverage_mode: str = 'conservative',  # Kept for API compatibility but NOT used
        fixed_position_value_usdt: float = 0.0  # If set, uses fixed USDT value per trade
    ) -> float:
        """
        Calculate position size - Position = (Equity × Risk% × Leverage) OR Fixed USDT Value

        Examples (percentage-based with NO leverage):
        - 10% risk + $100 equity + 1x leverage → $10 position (10% of equity)
        - 20% risk + $100 equity + 1x leverage → $20 position (20% of equity)

        Examples (percentage-based WITH leverage):
        - 10% risk + $100 equity + 5x leverage → $50 position (50% of equity)
        - 10% risk + $100 equity + 10x leverage → $100 position (100% of equity)

        Examples (fixed value):
        - fixed_position_value_usdt=6 → $6 position (regardless of equity)
        - With 5x leverage: $6 position requires $1.2 margin
        - With $100 balance: 16 simultaneous positions possible

        Args:
            signal: Trading signal with entry price
            account_balance: Current USDT balance (equity)
            risk_pct: Position size as % of equity (e.g., 10.0 = 10% of equity)
            contract_info: Contract specifications
            leverage: Leverage multiplier for BingX (1x = no leverage, 5x/10x = leveraged)
            leverage_mode: NOT USED - kept for API compatibility
            fixed_position_value_usdt: If > 0, uses fixed USDT value instead of % based

        Returns:
            Position size in base currency (e.g., FARTCOIN)
        """
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']

        # Position value: Fixed USDT or Kelly sizing (risk-adjusted)
        if fixed_position_value_usdt > 0:
            position_value = fixed_position_value_usdt
            self.logger.info(f"Using fixed position value: ${position_value:.2f} USDT")
        else:
            # Kelly sizing: Position size based on risk amount / SL distance
            # Each trade risks exactly risk_pct% of equity, regardless of SL width
            risk_amount = account_balance * (risk_pct / 100)  # e.g., $100 * 3% = $3
            sl_distance_pct = abs(entry_price - stop_loss) / entry_price * 100

            if sl_distance_pct <= 0:
                self.logger.error(f"Invalid SL distance: {sl_distance_pct}%")
                return 0

            # Position value = Risk amount / SL distance %
            # Wide SL (5%) → smaller position, Narrow SL (1%) → larger position
            # But SL hit always = -risk_amount (e.g., -$3)
            position_value = risk_amount / (sl_distance_pct / 100)

            self.logger.info(f"Using Kelly sizing:")
            self.logger.info(f"  Risk amount: ${risk_amount:.2f} ({risk_pct}% of equity)")
            self.logger.info(f"  SL distance: {sl_distance_pct:.2f}%")
            self.logger.info(f"  Position value: ${position_value:.2f} USDT")

        position_size = position_value / entry_price

        # Get precision from contract info
        quantity_precision = contract_info.get('quantityPrecision', 3)

        # Round down to contract precision
        precision_factor = Decimal(10) ** quantity_precision
        position_size = float(Decimal(str(position_size)).quantize(
            Decimal('1') / precision_factor,
            rounding=ROUND_DOWN
        ))

        # Check minimum quantity
        min_qty = contract_info.get('minQty')
        if min_qty and position_size < float(min_qty):
            self.logger.warning(f"Calculated size {position_size} below minimum {min_qty}, using minimum")
            position_size = float(min_qty)

        # Recalculate actual position value after rounding
        actual_position_value = position_size * entry_price

        # Calculate risk based on stop-loss distance
        sl_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
        risk_if_stopped = actual_position_value * (sl_distance_pct / 100)

        self.logger.info(f"Position size: {position_size}")
        if fixed_position_value_usdt > 0:
            margin_required = actual_position_value / leverage
            self.logger.info(f"Position value: ${actual_position_value:.2f} USDT (fixed)")
            self.logger.info(f"Leverage: {leverage}x → Margin required: ${margin_required:.2f}")
        else:
            equity_pct = (risk_pct * leverage)
            self.logger.info(f"Position value: ${actual_position_value:.2f} ({risk_pct}% × {leverage}x = {equity_pct}% of equity)")
            self.logger.info(f"Leverage: {leverage}x")
        self.logger.info(f"SL distance: {sl_distance_pct:.2f}% → Risk if stopped: ${risk_if_stopped:.2f}")

        return position_size

    async def execute_trade(
        self,
        signal: Dict[str, Any],
        symbol: str,
        account_balance: float,
        risk_pct: float = 1.0,
        use_market_order: bool = True,
        leverage: int = 1,
        leverage_mode: str = 'conservative',
        fixed_position_value_usdt: float = 0.0
    ) -> Dict[str, Any]:
        """
        Execute complete trade with entry, SL, and TP

        Args:
            signal: Trading signal from strategy
            symbol: Trading symbol (e.g., "FARTCOIN-USDT")
            account_balance: Current account balance
            risk_pct: Risk percentage per trade
            use_market_order: Use market order for entry (vs limit)
            leverage: Leverage to use (1, 5, 10, 20, etc.)
            leverage_mode: 'conservative' or 'aggressive'
            fixed_position_value_usdt: If > 0, uses fixed USDT value per trade

        Returns:
            Dict with entry_order_id, sl_order_id, tp_order_id, quantity
        """
        # Track state for safety cleanup
        entry_placed = False
        quantity = None
        direction = None
        exit_side = None

        try:
            # Get contract info
            contracts = await self.client.get_contract_info(symbol)
            contract = contracts[0] if isinstance(contracts, list) else contracts

            # Extract direction early (needed for hedge mode)
            direction = signal['direction']

            # Set leverage on BingX (if > 1x)
            if leverage > 1:
                try:
                    self.logger.info(f"Setting leverage to {leverage}x for {symbol}...")
                    await self.client.set_leverage(
                        symbol=symbol,
                        side=direction,  # Hedge mode: use actual direction
                        leverage=leverage
                    )
                    self.logger.info(f"✓ Leverage set to {leverage}x")
                except BingXAPIError as e:
                    self.logger.warning(f"Leverage setting: {e.msg} (might already be set)")

            # Calculate position size
            quantity = self.calculate_position_size(
                signal,
                account_balance,
                risk_pct,
                contract,
                leverage,
                leverage_mode,
                fixed_position_value_usdt
            )
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']

            # Determine order side
            entry_side = "BUY" if direction == "LONG" else "SELL"
            exit_side = "SELL" if direction == "LONG" else "BUY"

            self.logger.info("="*70)
            self.logger.info(f"EXECUTING TRADE: {signal['strategy']}")
            self.logger.info("="*70)
            self.logger.info(f"Direction: {direction}")
            self.logger.info(f"Symbol: {symbol}")
            self.logger.info(f"Quantity: {quantity}")
            self.logger.info(f"Entry: ${entry_price}")
            self.logger.info(f"Stop-Loss: ${stop_loss}")
            self.logger.info(f"Take-Profit: ${take_profit}")
            self.logger.info(f"Risk: {risk_pct}% (${account_balance * risk_pct / 100:.2f})")

            # STEP 1: Place entry order
            self.logger.info("\nSTEP 1: Placing entry order...")

            if use_market_order:
                entry_order = await self.client.place_order(
                    symbol=symbol,
                    side=entry_side,
                    position_side=direction,  # Hedge mode: use actual direction
                    order_type="MARKET",
                    quantity=quantity
                )
            else:
                # Use limit order with attached SL/TP
                price_precision = contract.get('pricePrecision', 4)
                entry_price_rounded = round(entry_price, price_precision)
                sl_price_rounded = round(stop_loss, price_precision)
                tp_price_rounded = round(take_profit, price_precision)

                # Prepare SL/TP configs (attached to entry order)
                stop_loss_config = {
                    "type": "STOP_MARKET",
                    "stopPrice": sl_price_rounded,
                    "workingType": "MARK_PRICE"
                }

                take_profit_config = {
                    "type": "TAKE_PROFIT_MARKET",
                    "stopPrice": tp_price_rounded,
                    "workingType": "MARK_PRICE"
                }

                entry_order = await self.client.place_order(
                    symbol=symbol,
                    side=entry_side,
                    position_side=direction,  # Hedge mode: use actual direction
                    order_type="LIMIT",
                    quantity=quantity,
                    price=entry_price_rounded,
                    stop_loss=stop_loss_config,
                    take_profit=take_profit_config
                )

            # Extract order ID
            entry_order_id = None
            if isinstance(entry_order, dict) and 'order' in entry_order:
                entry_order_id = entry_order['order'].get('orderId')
                status = entry_order['order'].get('status')
                self.logger.info(f"✓ Entry order placed! ID: {entry_order_id}, Status: {status}")
            else:
                entry_order_id = entry_order.get('orderId')
                self.logger.info(f"✓ Entry order placed! ID: {entry_order_id}")

            # Mark entry as placed for safety cleanup
            entry_placed = True

            # Wait for market order to fill
            if use_market_order:
                await asyncio.sleep(1)

            # For limit orders, SL/TP are already attached - skip separate placement
            if not use_market_order:
                self.logger.info("✓ Limit order placed with attached SL/TP")
                self.logger.info(f"   Entry will fill at: ${entry_price_rounded}")
                self.logger.info(f"   Stop-loss trigger: ${sl_price_rounded}")
                self.logger.info(f"   Take-profit trigger: ${tp_price_rounded}")

                return {
                    'success': True,
                    'entry_order_id': entry_order_id,
                    'sl_order_id': 'attached',
                    'tp_order_id': 'attached',
                    'position_size': quantity,
                    'entry_price': entry_price_rounded,
                    'stop_loss': sl_price_rounded,
                    'take_profit': tp_price_rounded,
                    'entry_status': 'PENDING',
                    'note': 'Limit order with attached SL/TP - will activate when entry fills'
                }

            # STEP 2: Place stop-loss order (with retry logic) - MARKET ORDERS ONLY
            self.logger.info("\nSTEP 2: Placing stop-loss order...")

            price_precision = contract.get('pricePrecision', 4)
            sl_price = round(stop_loss, price_precision)

            sl_order_id = None
            max_retries = 3

            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(f"SL attempt {attempt}/{max_retries}...")
                    sl_order = await self.client.place_order(
                        symbol=symbol,
                        side=exit_side,
                        position_side=direction,  # Hedge mode: use actual direction
                        order_type="STOP_MARKET",
                        quantity=quantity,
                        stop_price=sl_price
                        # Note: reduce_only not supported in hedge mode (position_side handles this)
                    )

                    if isinstance(sl_order, dict) and 'order' in sl_order:
                        sl_order_id = sl_order['order'].get('orderId')
                        self.logger.info(f"✓ Stop-loss placed! ID: {sl_order_id}, Trigger: ${sl_price}")
                    else:
                        sl_order_id = sl_order.get('orderId')
                        self.logger.info(f"✓ Stop-loss placed! ID: {sl_order_id}")
                    break  # Success, exit retry loop

                except BingXAPIError as e:
                    self.logger.error(f"❌ Stop-loss attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        # All retries failed - CLOSE POSITION IMMEDIATELY
                        self.logger.critical("🚨 ALL SL RETRIES FAILED - CLOSING POSITION FOR SAFETY!")
                        try:
                            await self.client.place_order(
                                symbol=symbol,
                                side=exit_side,
                                position_side=direction,  # Hedge mode: use actual direction
                                order_type="MARKET",
                                quantity=quantity
                            )
                            self.logger.info("✓ Position closed due to SL failure")
                        except Exception as close_err:
                            self.logger.critical(f"🚨 FAILED TO CLOSE POSITION: {close_err}")

                        return {
                            'success': False,
                            'error': f'Stop-loss placement failed after {max_retries} retries - position closed',
                            'error_code': e.code
                        }

            # STEP 3: Place take-profit order (with retry logic)
            self.logger.info("\nSTEP 3: Placing take-profit order...")

            tp_price = round(take_profit, price_precision)

            tp_order_id = None

            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(f"TP attempt {attempt}/{max_retries}...")
                    tp_order = await self.client.place_order(
                        symbol=symbol,
                        side=exit_side,
                        position_side=direction,  # Hedge mode: use actual direction
                        order_type="TAKE_PROFIT_MARKET",
                        quantity=quantity,
                        stop_price=tp_price
                        # Note: reduce_only not supported in hedge mode (position_side handles this)
                    )

                    if isinstance(tp_order, dict) and 'order' in tp_order:
                        tp_order_id = tp_order['order'].get('orderId')
                        self.logger.info(f"✓ Take-profit placed! ID: {tp_order_id}, Trigger: ${tp_price}")
                    else:
                        tp_order_id = tp_order.get('orderId')
                        self.logger.info(f"✓ Take-profit placed! ID: {tp_order_id}")
                    break  # Success, exit retry loop

                except BingXAPIError as e:
                    self.logger.error(f"❌ Take-profit attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        # All retries failed - CLOSE POSITION AND CANCEL SL
                        self.logger.critical("🚨 ALL TP RETRIES FAILED - CLOSING POSITION FOR SAFETY!")
                        try:
                            # Cancel SL order first
                            if sl_order_id:
                                await self.client.cancel_all_orders(symbol)
                                self.logger.info("✓ Cancelled pending SL order")

                            # Close position
                            await self.client.place_order(
                                symbol=symbol,
                                side=exit_side,
                                position_side=direction,  # Hedge mode: use actual direction
                                order_type="MARKET",
                                quantity=quantity
                            )
                            self.logger.info("✓ Position closed due to TP failure")
                        except Exception as close_err:
                            self.logger.critical(f"🚨 FAILED TO CLOSE POSITION: {close_err}")

                        return {
                            'success': False,
                            'error': f'Take-profit placement failed after {max_retries} retries - position closed',
                            'error_code': e.code
                        }

            self.logger.info("\n" + "="*70)
            self.logger.info("✅ TRADE EXECUTION COMPLETE")
            self.logger.info("="*70)
            self.logger.info(f"Entry Order ID: {entry_order_id}")
            self.logger.info(f"Stop-Loss Order ID: {sl_order_id}")
            self.logger.info(f"Take-Profit Order ID: {tp_order_id}")

            return {
                'success': True,
                'entry_order_id': entry_order_id,
                'sl_order_id': sl_order_id,
                'tp_order_id': tp_order_id,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'symbol': symbol,
                'direction': direction
            }

        except BingXAPIError as e:
            self.logger.error(f"❌ BingX API Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': e.code
            }

        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            # SAFETY: If entry was placed but we're exiting due to exception,
            # close the position to prevent unprotected exposure
            if entry_placed and quantity and exit_side:
                # Check if we returned successfully (sl_order_id and tp_order_id would be set)
                # This runs after return, so we check via locals
                try:
                    # If this finally block runs after an exception, close position
                    import sys
                    if sys.exc_info()[0] is not None:
                        self.logger.critical("🚨 SAFETY CLEANUP: Closing position due to unexpected error!")
                        await self.client.cancel_all_orders(symbol)
                        await self.client.place_order(
                            symbol=symbol,
                            side=exit_side,
                            position_side=direction,  # Hedge mode: use actual direction
                            order_type="MARKET",
                            quantity=quantity
                        )
                        self.logger.info("✓ Position closed via safety cleanup")
                except Exception as cleanup_err:
                    self.logger.critical(f"🚨 SAFETY CLEANUP FAILED: {cleanup_err}")

    async def close_position(
        self,
        symbol: str,
        quantity: float,
        side: str = "LONG"
    ) -> Dict[str, Any]:
        """
        Manually close a position (emergency exit)

        Args:
            symbol: Trading symbol
            quantity: Position size to close
            side: Position side (LONG or SHORT)

        Returns:
            Order result
        """
        try:
            # Determine exit side
            exit_side = "SELL" if side == "LONG" else "BUY"

            self.logger.warning(f"EMERGENCY CLOSE: {side} position of {quantity} {symbol}")

            # Cancel all pending orders for this symbol first
            await self.client.cancel_all_orders(symbol)
            self.logger.info("✓ All pending orders cancelled")

            # Close with market order
            close_order = await self.client.place_order(
                symbol=symbol,
                side=exit_side,
                position_side=side,  # Hedge mode: use actual position side (LONG/SHORT)
                order_type="MARKET",
                quantity=quantity
            )

            self.logger.info(f"✓ Position closed via market order")

            return {
                'success': True,
                'close_order': close_order
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to close position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
