"""
Pending Order Manager - Handles TRIGGER_MARKET orders that wait for breakout confirmation

Manages the lifecycle of pending trigger orders:
1. Place TRIGGER_MARKET order with SL/TP attached (atomic - all or nothing)
2. Track order status
3. Check fills every minute
4. Cancel if timeout (3 bars)
5. When filled, SL/TP are automatically active (no separate placement needed)

FIXED Dec 2024:
- Changed LIMIT → TRIGGER_MARKET (LIMIT above price fills instantly, TRIGGER waits)
- SL/TP attached to order (type: STOP_MARKET / TAKE_PROFIT_MARKET, compact JSON)
- Fixed nested response handling (order.get('order', order))
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from execution.bingx_client import BingXClient, BingXAPIError
from monitoring.notifications import get_notifier


class PendingOrder:
    """Represents a pending TRIGGER_MARKET order waiting for breakout fill"""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        strategy: str,
        direction: str,
        trigger_price: float,  # Renamed from limit_price for clarity
        quantity: float,
        stop_loss: float,
        take_profit: float,
        signal_data: Dict[str, Any],
        created_bar: int,
        max_wait_bars: int = 3
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.strategy = strategy
        self.direction = direction
        self.trigger_price = trigger_price  # Price at which order triggers
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.signal_data = signal_data
        self.created_bar = created_bar
        self.max_wait_bars = max_wait_bars
        self.created_at = datetime.now()
        self.bars_waited = 0

    def is_timeout(self, current_bar: int) -> bool:
        """Check if order has waited too long"""
        self.bars_waited = current_bar - self.created_bar
        return self.bars_waited >= self.max_wait_bars

    # Alias for backwards compatibility
    @property
    def limit_price(self):
        return self.trigger_price


class PendingOrderManager:
    """
    Manages pending TRIGGER_MARKET orders that wait for breakout confirmation

    Workflow:
    1. Strategy requests breakout order (1% above/below current price)
    2. We place TRIGGER_MARKET order with SL/TP attached
    3. Every minute we check order status
    4. If filled → SL/TP are already active (attached to order)
    5. If timeout → cancel order

    IMPORTANT: Uses TRIGGER_MARKET (not LIMIT) because:
    - BUY LIMIT above current price fills INSTANTLY (wrong behavior)
    - BUY TRIGGER_MARKET above current price WAITS for breakout (correct)
    """

    def __init__(self, bingx_client: BingXClient):
        self.client = bingx_client
        self.logger = logging.getLogger(__name__)
        self.pending_orders: Dict[str, PendingOrder] = {}  # order_id -> PendingOrder

    async def create_pending_order(
        self,
        symbol: str,
        strategy: str,
        direction: str,
        limit_price: float,  # This is actually trigger_price, kept for backwards compat
        quantity: float,
        stop_loss: float,
        take_profit: float,
        signal_data: Dict[str, Any],
        current_bar: int,
        max_wait_bars: int = 3,
        contract_info: Dict[str, Any] = None
    ) -> Optional[PendingOrder]:
        """
        Place a pending TRIGGER_MARKET order on BingX with SL/TP attached

        Args:
            symbol: Trading symbol (e.g., "FARTCOIN-USDT")
            strategy: Strategy name
            direction: "LONG" or "SHORT"
            limit_price: Trigger price (when price reaches this, order executes)
            quantity: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            signal_data: Original signal data for later use
            current_bar: Current bar index
            max_wait_bars: Max bars to wait before timeout
            contract_info: Contract specifications for precision

        Returns:
            PendingOrder if successful, None if failed
        """
        try:
            trigger_price = limit_price  # Rename for clarity

            # Round prices to contract precision
            if contract_info:
                # Handle contract_info being a list (BingX returns list)
                contract = contract_info[0] if isinstance(contract_info, list) else contract_info
                price_precision = contract.get('pricePrecision', 4)
                trigger_price = round(trigger_price, price_precision)
                stop_loss = round(stop_loss, price_precision)
                if take_profit is not None:
                    take_profit = round(take_profit, price_precision)

            # Determine order side
            side = "BUY" if direction == "LONG" else "SELL"

            self.logger.info(f"📝 Placing TRIGGER_MARKET order with SL/TP:")
            self.logger.info(f"   Strategy: {strategy}")
            self.logger.info(f"   Symbol: {symbol}")
            self.logger.info(f"   Direction: {direction}")
            self.logger.info(f"   Trigger Price: ${trigger_price:.6f}")
            self.logger.info(f"   Stop Loss: ${stop_loss:.6f}")
            self.logger.info(f"   Take Profit: ${take_profit:.6f}" if take_profit else "   Take Profit: None")
            self.logger.info(f"   Quantity: {quantity}")
            self.logger.info(f"   Max wait: {max_wait_bars} bars")

            # Place TRIGGER_MARKET order with SL/TP attached
            # SL/TP use STOP_MARKET and TAKE_PROFIT_MARKET types (not MARK_PRICE!)
            order = await self.client.place_order(
                symbol=symbol,
                side=side,
                position_side=direction,
                order_type="TRIGGER_MARKET",  # CHANGED from LIMIT!
                stop_price=trigger_price,     # Trigger price (not 'price')
                quantity=quantity,
                stop_loss={'type': 'STOP_MARKET', 'stopPrice': stop_loss},
                take_profit={'type': 'TAKE_PROFIT_MARKET', 'stopPrice': take_profit}
            )

            # Handle nested response: BingX returns {'order': {...}} or {...}
            order_data = order.get('order', order)
            order_id = order_data.get('orderId') or order_data.get('orderID')
            status = order_data.get('status')

            if not order_id:
                self.logger.error(f"❌ No order ID returned: {order}")
                # Send notification about failed order
                notifier = get_notifier()
                if notifier:
                    await notifier.notify_order_error(
                        strategy=strategy,
                        symbol=symbol,
                        direction=direction,
                        error_message="No order ID returned from BingX",
                        order_details=str(order)
                    )
                return None

            # Check if order filled immediately (shouldn't happen with TRIGGER, but handle it)
            if status == 'FILLED':
                avg_price = order_data.get('avgPrice', trigger_price)
                self.logger.warning(f"⚡ TRIGGER order filled immediately @ ${avg_price}")
                self.logger.info(f"   SL/TP should be active automatically")
                # Don't track as pending - it's done
                return None

            self.logger.info(f"✅ TRIGGER_MARKET order placed: {order_id}")
            self.logger.info(f"   Status: {status} (waiting for trigger)")

            # Create pending order tracker
            pending = PendingOrder(
                order_id=order_id,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                trigger_price=trigger_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_data=signal_data,
                created_bar=current_bar,
                max_wait_bars=max_wait_bars
            )

            self.pending_orders[order_id] = pending

            return pending

        except BingXAPIError as e:
            self.logger.error(f"❌ Failed to place TRIGGER_MARKET order: {e.msg}")
            # Send notification
            notifier = get_notifier()
            if notifier:
                await notifier.notify_order_error(
                    strategy=strategy,
                    symbol=symbol,
                    direction=direction,
                    error_message=f"BingX API Error: {e.msg}",
                    order_details=f"Trigger: ${limit_price}, SL: ${stop_loss}, TP: ${take_profit if take_profit else 'None'}"
                )
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error placing TRIGGER_MARKET order: {e}", exc_info=True)
            return None

    async def check_pending_orders(
        self,
        current_bar: int
    ) -> List[Dict[str, Any]]:
        """
        Check status of all pending TRIGGER_MARKET orders

        Args:
            current_bar: Current bar index

        Returns:
            List of filled signals (for logging/metrics only - SL/TP already attached!)
        """
        if not self.pending_orders:
            return []

        filled_signals = []
        orders_to_remove = []

        for order_id, pending in self.pending_orders.items():
            try:
                # Check if timeout
                if pending.is_timeout(current_bar):
                    self.logger.warning(f"⏱️  TRIGGER order {order_id} TIMEOUT ({pending.bars_waited} bars)")

                    # Send email notification before cancelling
                    notifier = get_notifier()
                    if notifier:
                        await notifier.notify_limit_order_cancelled(
                            strategy=pending.strategy,
                            symbol=pending.symbol,
                            direction=pending.direction,
                            limit_price=pending.trigger_price,
                            reason=f"Timeout after {pending.bars_waited} bars (no breakout)"
                        )

                    await self._cancel_order(pending)
                    orders_to_remove.append(order_id)
                    continue

                # Check order status
                order_status = await self.client.get_order(
                    symbol=pending.symbol,
                    order_id=order_id
                )

                status = order_status.get('status')

                if status == 'FILLED':
                    # ✅ TRIGGER order filled! SL/TP are already active (attached to order)
                    avg_price = float(order_status.get('avgPrice', pending.trigger_price))
                    filled_qty = float(order_status.get('executedQty', pending.quantity))

                    self.logger.info(f"✅ TRIGGER order FILLED: {order_id}")
                    self.logger.info(f"   Filled @ ${avg_price:.6f} (qty: {filled_qty})")
                    self.logger.info(f"   Waited {pending.bars_waited} bars for breakout")
                    tp_str = f"${pending.take_profit:.6f}" if pending.take_profit else "None"
                    self.logger.info(f"   SL @ ${pending.stop_loss:.6f} | TP @ {tp_str} (auto-active)")

                    # Send email notification
                    notifier = get_notifier()
                    if notifier:
                        await notifier.notify_limit_order_filled(
                            strategy=pending.strategy,
                            symbol=pending.symbol,
                            direction=pending.direction,
                            fill_price=avg_price,
                            quantity=filled_qty,
                            bars_waited=pending.bars_waited
                        )

                    # Return signal for logging/metrics (NO separate SL/TP placement needed!)
                    signal = {
                        'strategy': pending.strategy,
                        'direction': pending.direction,
                        'entry_price': avg_price,
                        'stop_loss': pending.stop_loss,
                        'take_profit': pending.take_profit,
                        'symbol': pending.symbol,
                        'quantity': filled_qty,
                        'entry_order_id': order_id,
                        'pattern': pending.signal_data.get('pattern', 'Breakout Confirmed'),
                        'confidence': pending.signal_data.get('confidence', 0.8),
                        'sl_tp_attached': True,  # Flag: SL/TP already active!
                        **pending.signal_data
                    }

                    filled_signals.append(signal)
                    orders_to_remove.append(order_id)

                elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    # Order cancelled/rejected
                    self.logger.warning(f"❌ Order {order_id} {status}")
                    orders_to_remove.append(order_id)

                else:
                    # Still pending (NEW, PARTIALLY_FILLED)
                    self.logger.debug(f"⏳ TRIGGER {order_id} still {status} (bar {pending.bars_waited}/{pending.max_wait_bars})")

            except BingXAPIError as e:
                self.logger.error(f"❌ Error checking order {order_id}: {e.msg}")
                # Don't remove - might be temporary error
            except Exception as e:
                self.logger.error(f"❌ Unexpected error checking order {order_id}: {e}", exc_info=True)

        # Clean up processed orders
        for order_id in orders_to_remove:
            del self.pending_orders[order_id]

        return filled_signals

    async def _cancel_order(self, pending: PendingOrder) -> bool:
        """Cancel a pending order"""
        try:
            self.logger.info(f"🚫 Canceling order {pending.order_id}...")

            await self.client.cancel_order(
                symbol=pending.symbol,
                order_id=pending.order_id
            )

            self.logger.info(f"✅ Order {pending.order_id} cancelled")
            return True

        except BingXAPIError as e:
            # Order might already be filled/cancelled
            self.logger.warning(f"⚠️  Cancel failed: {e.msg}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error canceling order: {e}", exc_info=True)
            return False

    async def cancel_all_pending_orders(self) -> int:
        """
        Cancel all pending orders (emergency shutdown)

        Returns:
            Number of orders cancelled
        """
        if not self.pending_orders:
            return 0

        cancelled = 0

        for order_id, pending in list(self.pending_orders.items()):
            if await self._cancel_order(pending):
                cancelled += 1
            del self.pending_orders[order_id]

        return cancelled

    def get_pending_count(self) -> int:
        """Get number of pending orders"""
        return len(self.pending_orders)

    def get_pending_orders_for_strategy(self, strategy: str) -> List[PendingOrder]:
        """Get all pending orders for a specific strategy"""
        return [p for p in self.pending_orders.values() if p.strategy == strategy]
