"""
Pending Order Manager - Handles limit orders that wait for confirmation

Manages the lifecycle of pending limit orders:
1. Place limit order on exchange
2. Track order status
3. Check fills every minute
4. Cancel if timeout (3 bars)
5. Convert filled orders to trading signals
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from execution.bingx_client import BingXClient, BingXAPIError
from monitoring.notifications import get_notifier


class PendingOrder:
    """Represents a pending limit order waiting for fill"""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        strategy: str,
        direction: str,
        limit_price: float,
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
        self.limit_price = limit_price
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


class PendingOrderManager:
    """
    Manages pending limit orders that wait for market confirmation

    Workflow:
    1. Strategy requests limit order
    2. We place limit order on BingX
    3. Every minute we check order status
    4. If filled → convert to signal for SL/TP placement
    5. If timeout → cancel order
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
        limit_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        signal_data: Dict[str, Any],
        current_bar: int,
        max_wait_bars: int = 3,
        contract_info: Dict[str, Any] = None
    ) -> Optional[PendingOrder]:
        """
        Place a pending limit order on BingX

        Args:
            symbol: Trading symbol (e.g., "FARTCOIN-USDT")
            strategy: Strategy name
            direction: "LONG" or "SHORT"
            limit_price: Limit order price
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
            # Round price to contract precision
            if contract_info:
                price_precision = contract_info.get('pricePrecision', 4)
                limit_price = round(limit_price, price_precision)

            # Determine order side
            side = "BUY" if direction == "LONG" else "SELL"

            self.logger.info(f"📝 Placing PENDING LIMIT order:")
            self.logger.info(f"   Strategy: {strategy}")
            self.logger.info(f"   Symbol: {symbol}")
            self.logger.info(f"   Direction: {direction}")
            self.logger.info(f"   Limit Price: ${limit_price:.6f}")
            self.logger.info(f"   Quantity: {quantity}")
            self.logger.info(f"   Max wait: {max_wait_bars} bars")

            # Place limit order on BingX
            order = await self.client.place_order(
                symbol=symbol,
                side=side,
                position_side=direction,  # Use LONG or SHORT (Hedge mode compatible)
                order_type="LIMIT",
                price=limit_price,
                quantity=quantity
            )

            order_id = order.get('orderId')

            if not order_id:
                self.logger.error(f"❌ No order ID returned: {order}")
                return None

            self.logger.info(f"✅ Limit order placed: {order_id}")

            # Create pending order tracker
            pending = PendingOrder(
                order_id=order_id,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                limit_price=limit_price,
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
            self.logger.error(f"❌ Failed to place limit order: {e.msg}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error placing limit order: {e}", exc_info=True)
            return None

    async def check_pending_orders(
        self,
        current_bar: int
    ) -> List[Dict[str, Any]]:
        """
        Check status of all pending orders

        Args:
            current_bar: Current bar index

        Returns:
            List of filled signals ready for SL/TP placement
        """
        if not self.pending_orders:
            return []

        filled_signals = []
        orders_to_remove = []

        for order_id, pending in self.pending_orders.items():
            try:
                # Check if timeout
                if pending.is_timeout(current_bar):
                    self.logger.warning(f"⏱️  Pending order {order_id} TIMEOUT ({pending.bars_waited} bars)")

                    # Send email notification before cancelling
                    notifier = get_notifier()
                    if notifier:
                        await notifier.notify_limit_order_cancelled(
                            strategy=pending.strategy,
                            symbol=pending.symbol,
                            direction=pending.direction,
                            limit_price=pending.limit_price,
                            reason=f"Timeout after {pending.bars_waited} bars"
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
                    # ✅ Order filled! Convert to signal
                    avg_price = float(order_status.get('avgPrice', pending.limit_price))
                    filled_qty = float(order_status.get('executedQty', pending.quantity))

                    self.logger.info(f"✅ Limit order FILLED: {order_id}")
                    self.logger.info(f"   Filled @ ${avg_price:.6f} (qty: {filled_qty})")
                    self.logger.info(f"   Waited {pending.bars_waited} bars")

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

                    # Create signal for SL/TP placement
                    signal = {
                        'strategy': pending.strategy,
                        'direction': pending.direction,
                        'entry_price': avg_price,
                        'stop_loss': pending.stop_loss,
                        'take_profit': pending.take_profit,
                        'symbol': pending.symbol,
                        'quantity': filled_qty,
                        'entry_order_id': order_id,
                        'pattern': pending.signal_data.get('pattern', 'Limit Confirmed'),
                        'confidence': pending.signal_data.get('confidence', 0.8),
                        **pending.signal_data  # Include all original signal data
                    }

                    filled_signals.append(signal)
                    orders_to_remove.append(order_id)

                elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    # Order cancelled/rejected
                    self.logger.warning(f"❌ Order {order_id} {status}")
                    orders_to_remove.append(order_id)

                else:
                    # Still pending (NEW, PARTIALLY_FILLED)
                    self.logger.debug(f"⏳ Order {order_id} still {status} (bar {pending.bars_waited}/{pending.max_wait_bars})")

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
