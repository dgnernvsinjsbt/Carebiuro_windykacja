"""
Email Notifications Module

Sends important notifications via Resend API.
Only critical events - not spammy.
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Email notifications for critical trading events.

    Events that trigger emails:
    - Trade executed successfully
    - Trade execution failed
    - Critical errors
    - Daily summary (optional)
    - Emergency stop triggered

    Anti-spam:
    - Rate limiting (max 1 email per type per 5 minutes)
    - Batching similar errors
    """

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        api_key: str = None,
        from_email: str = "trading-bot@resend.dev",
        to_email: str = None,
        enabled: bool = True
    ):
        """
        Initialize email notifier.

        Args:
            api_key: Resend API key (or set RESEND_API_KEY env var)
            from_email: Sender email (default: trading-bot@resend.dev)
            to_email: Recipient email (required)
            enabled: Enable/disable notifications
        """
        self.api_key = api_key or os.environ.get('RESEND_API_KEY', '')
        self.from_email = from_email
        self.to_email = to_email or os.environ.get('NOTIFICATION_EMAIL', '')
        self.enabled = enabled and bool(self.api_key) and bool(self.to_email)

        # Rate limiting - track last send time per event type
        self._last_sent: dict = {}
        self._rate_limit_minutes = 5

        if self.enabled:
            logger.info(f"Email notifications enabled -> {self.to_email}")
        else:
            if not self.api_key:
                logger.warning("Email notifications disabled: No RESEND_API_KEY")
            elif not self.to_email:
                logger.warning("Email notifications disabled: No recipient email")

    def _can_send(self, event_type: str) -> bool:
        """Check if we can send (rate limiting)"""
        now = datetime.utcnow()
        last_sent = self._last_sent.get(event_type)

        if last_sent and (now - last_sent) < timedelta(minutes=self._rate_limit_minutes):
            return False

        self._last_sent[event_type] = now
        return True

    async def _send_email(self, subject: str, html_body: str) -> bool:
        """Send email via Resend API"""
        if not self.enabled:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "from": self.from_email,
                "to": [self.to_email],
                "subject": subject,
                "html": html_body
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.RESEND_API_URL,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info(f"Email sent: {subject}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Email failed ({response.status}): {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    async def notify_trade_opened(
        self,
        strategy: str,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        leverage: int = 1
    ) -> bool:
        """Notify when trade is successfully opened"""
        if not self._can_send('trade_opened'):
            return False

        risk_pct = abs(entry_price - stop_loss) / entry_price * 100
        reward_pct = abs(take_profit - entry_price) / entry_price * 100
        position_value = quantity * entry_price

        subject = f"✅ Trade Opened: {direction} {symbol}"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2 style="color: {'#22c55e' if direction == 'LONG' else '#ef4444'};">
                {direction} Position Opened
            </h2>

            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Symbol:</strong></td><td>{symbol}</td></tr>
                <tr><td><strong>Strategy:</strong></td><td>{strategy}</td></tr>
                <tr><td><strong>Entry Price:</strong></td><td>${entry_price:.6f}</td></tr>
                <tr><td><strong>Quantity:</strong></td><td>{quantity:.4f}</td></tr>
                <tr><td><strong>Position Value:</strong></td><td>${position_value:.2f}</td></tr>
                <tr><td><strong>Leverage:</strong></td><td>{leverage}x</td></tr>
                <tr><td><strong>Stop Loss:</strong></td><td>${stop_loss:.6f} ({risk_pct:.2f}%)</td></tr>
                <tr><td><strong>Take Profit:</strong></td><td>${take_profit:.6f} ({reward_pct:.2f}%)</td></tr>
            </table>

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)

    async def notify_trade_closed(
        self,
        strategy: str,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        exit_reason: str
    ) -> bool:
        """Notify when trade is closed"""
        if not self._can_send('trade_closed'):
            return False

        is_win = pnl > 0
        emoji = "🎉" if is_win else "📉"
        color = "#22c55e" if is_win else "#ef4444"

        subject = f"{emoji} Trade Closed: {'+' if is_win else ''}{pnl_pct:.2f}% on {symbol}"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2 style="color: {color};">
                Trade Closed - {'PROFIT' if is_win else 'LOSS'}
            </h2>

            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Symbol:</strong></td><td>{symbol}</td></tr>
                <tr><td><strong>Strategy:</strong></td><td>{strategy}</td></tr>
                <tr><td><strong>Direction:</strong></td><td>{direction}</td></tr>
                <tr><td><strong>Entry:</strong></td><td>${entry_price:.6f}</td></tr>
                <tr><td><strong>Exit:</strong></td><td>${exit_price:.6f}</td></tr>
                <tr><td><strong>P&L:</strong></td><td style="color: {color}; font-weight: bold;">${pnl:+.2f} ({pnl_pct:+.2f}%)</td></tr>
                <tr><td><strong>Exit Reason:</strong></td><td>{exit_reason}</td></tr>
            </table>

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)

    async def notify_error(self, error_type: str, message: str, details: str = "") -> bool:
        """Notify on critical error"""
        if not self._can_send(f'error_{error_type}'):
            return False

        subject = f"🚨 Trading Bot Error: {error_type}"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2 style="color: #ef4444;">⚠️ Critical Error</h2>

            <p><strong>Type:</strong> {error_type}</p>
            <p><strong>Message:</strong> {message}</p>

            {f'<pre style="background: #f3f4f6; padding: 10px; overflow-x: auto;">{details}</pre>' if details else ''}

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)

    async def notify_emergency_stop(self, reason: str, account_balance: float) -> bool:
        """Notify when emergency stop is triggered"""
        # Always send emergency stop (no rate limit)
        self._last_sent['emergency_stop'] = None

        subject = "🛑 EMERGENCY STOP - Trading Halted"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2 style="color: #ef4444;">🛑 TRADING HALTED</h2>

            <p style="font-size: 18px;"><strong>Reason:</strong> {reason}</p>
            <p><strong>Account Balance:</strong> ${account_balance:.2f}</p>

            <p style="background: #fef2f2; padding: 15px; border-left: 4px solid #ef4444;">
                All trading has been stopped. Manual intervention required.
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)

    async def notify_daily_summary(
        self,
        trades_today: int,
        wins: int,
        losses: int,
        daily_pnl: float,
        total_capital: float,
        drawdown_pct: float
    ) -> bool:
        """Send daily performance summary"""
        if not self._can_send('daily_summary'):
            return False

        win_rate = (wins / trades_today * 100) if trades_today > 0 else 0
        is_profitable = daily_pnl >= 0

        subject = f"📊 Daily Summary: {'+'if is_profitable else ''}{daily_pnl:.2f} USDT"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2>📊 Daily Trading Summary</h2>

            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><strong>Trades:</strong></td><td>{trades_today} ({wins}W / {losses}L)</td></tr>
                <tr><td><strong>Win Rate:</strong></td><td>{win_rate:.1f}%</td></tr>
                <tr><td><strong>Daily P&L:</strong></td><td style="color: {'#22c55e' if is_profitable else '#ef4444'};">${daily_pnl:+.2f}</td></tr>
                <tr><td><strong>Total Capital:</strong></td><td>${total_capital:.2f}</td></tr>
                <tr><td><strong>Drawdown:</strong></td><td>{drawdown_pct:.2f}%</td></tr>
            </table>

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)

    async def notify_bot_started(self, account_balance: float, strategies: list) -> bool:
        """Notify when bot starts"""
        subject = "🤖 Trading Bot Started"

        strategies_html = "".join([f"<li>{s}</li>" for s in strategies])

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px;">
            <h2 style="color: #22c55e;">🤖 Bot Started Successfully</h2>

            <p><strong>Account Balance:</strong> ${account_balance:.2f}</p>

            <p><strong>Active Strategies:</strong></p>
            <ul>{strategies_html}</ul>

            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        """

        return await self._send_email(subject, html)


# Global notifier instance
_notifier: Optional[EmailNotifier] = None


def init_notifier(
    api_key: str = None,
    to_email: str = None,
    enabled: bool = True
) -> EmailNotifier:
    """Initialize global notifier"""
    global _notifier
    _notifier = EmailNotifier(
        api_key=api_key,
        to_email=to_email,
        enabled=enabled
    )
    return _notifier


def get_notifier() -> Optional[EmailNotifier]:
    """Get global notifier instance"""
    return _notifier
