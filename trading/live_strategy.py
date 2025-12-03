"""
Live Implementation Template for EMA50 Pullback + 8-Candle Time Exit

This is a template showing the logic for live trading.
You'll need to adapt it to your exchange's API.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict


class EMA50PullbackStrategy:
    """
    EMA50 Pullback Strategy with 8-Candle Time Exit

    Entry: Price pulls back to EMA50 then closes above it
    Exit: After 8 candles (2 hours on 15m timeframe)
    Stop: Below pullback candle low
    """

    def __init__(self, initial_capital: float = 10000):
        self.capital = initial_capital
        self.starting_daily_capital = initial_capital
        self.position: Optional[Dict] = None
        self.daily_drawdown_limit = 0.05  # 5%
        self.ema_period = 50
        self.exit_candles = 8
        self.pullback_tolerance = 0.002  # 0.2%

    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()

    def check_entry_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Check if current candle generates entry signal

        Args:
            df: DataFrame with OHLC data and 'timestamp' column
                Must have at least 50 candles for EMA calculation

        Returns:
            Dict with entry details if signal, None otherwise
        """
        if len(df) < self.ema_period + 1:
            return None

        # Calculate EMA50
        df = df.copy()
        df['ema50'] = self.calculate_ema(df['close'], self.ema_period)

        # Get last two candles
        prev = df.iloc[-2]
        current = df.iloc[-1]

        # Check conditions:
        # 1. Previous price was above EMA50 (trend confirmation)
        if prev['close'] <= prev['ema50']:
            return None

        # 2. Current candle touched EMA50 (within tolerance)
        if current['low'] > current['ema50'] * (1 + self.pullback_tolerance):
            return None

        # 3. Current candle closes above EMA50
        if current['close'] <= current['ema50']:
            return None

        # Entry signal confirmed
        return {
            'timestamp': current['timestamp'],
            'entry_price': current['close'],
            'stop_loss': current['low'],
            'ema50': current['ema50']
        }

    def calculate_position_size(self, entry_price: float) -> float:
        """
        Calculate position size using 100% of capital

        Returns:
            Number of coins to buy
        """
        return self.capital / entry_price

    def should_trade_today(self) -> bool:
        """
        Check if we should continue trading today
        Returns False if daily drawdown limit hit
        """
        current_daily_return = (self.capital - self.starting_daily_capital) / self.starting_daily_capital
        return current_daily_return > -self.daily_drawdown_limit

    def enter_position(self, entry_signal: Dict) -> Dict:
        """
        Enter a long position

        Returns:
            Position details dict
        """
        position_size = self.calculate_position_size(entry_signal['entry_price'])

        self.position = {
            'entry_timestamp': entry_signal['timestamp'],
            'entry_price': entry_signal['entry_price'],
            'stop_loss': entry_signal['stop_loss'],
            'size': position_size,
            'candles_held': 0,
            'entry_capital': self.capital
        }

        return self.position

    def check_exit(self, current_candle: Dict) -> Optional[Dict]:
        """
        Check if position should be exited

        Args:
            current_candle: Dict with 'timestamp', 'open', 'high', 'low', 'close'

        Returns:
            Exit details if should exit, None otherwise
        """
        if not self.position:
            return None

        self.position['candles_held'] += 1

        # Check stop loss
        if current_candle['low'] <= self.position['stop_loss']:
            return {
                'exit_price': self.position['stop_loss'],
                'exit_reason': 'stop_loss',
                'timestamp': current_candle['timestamp']
            }

        # Check time exit (8 candles)
        if self.position['candles_held'] >= self.exit_candles:
            return {
                'exit_price': current_candle['close'],
                'exit_reason': 'time_exit',
                'timestamp': current_candle['timestamp']
            }

        return None

    def exit_position(self, exit_details: Dict) -> Dict:
        """
        Exit the current position and update capital

        Returns:
            Trade result dict
        """
        if not self.position:
            return {}

        # Calculate P&L
        pnl_per_coin = exit_details['exit_price'] - self.position['entry_price']
        total_pnl = pnl_per_coin * self.position['size']
        pnl_pct = (exit_details['exit_price'] - self.position['entry_price']) / self.position['entry_price']

        # Update capital
        self.capital += total_pnl

        # Create trade record
        trade_result = {
            'entry_timestamp': self.position['entry_timestamp'],
            'entry_price': self.position['entry_price'],
            'exit_timestamp': exit_details['timestamp'],
            'exit_price': exit_details['exit_price'],
            'exit_reason': exit_details['exit_reason'],
            'size': self.position['size'],
            'pnl': total_pnl,
            'pnl_pct': pnl_pct * 100,
            'capital_after': self.capital,
            'candles_held': self.position['candles_held']
        }

        # Clear position
        self.position = None

        return trade_result

    def new_trading_day(self):
        """
        Reset daily tracking at start of new day
        Call this at 00:00 UTC or start of your trading session
        """
        self.starting_daily_capital = self.capital

        # Force close any open positions (no overnight holds)
        if self.position:
            print(f"WARNING: Closing position at end of day")
            # You would implement actual market close here

    def get_status(self) -> Dict:
        """
        Get current strategy status
        """
        daily_pnl = self.capital - self.starting_daily_capital
        daily_pnl_pct = (daily_pnl / self.starting_daily_capital) * 100

        return {
            'capital': self.capital,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl_pct,
            'position_open': self.position is not None,
            'position_details': self.position,
            'can_trade_today': self.should_trade_today()
        }


# =============================================================================
# USAGE EXAMPLE (Pseudo-code - adapt to your exchange API)
# =============================================================================

def example_usage():
    """
    Example of how to use the strategy in a live trading loop
    """

    # Initialize strategy
    strategy = EMA50PullbackStrategy(initial_capital=10000)

    print("EMA50 Pullback Strategy - Live Trading")
    print("=" * 60)
    print(f"Starting Capital: ${strategy.capital:,.2f}")
    print(f"EMA Period: {strategy.ema_period}")
    print(f"Exit After: {strategy.exit_candles} candles (2 hours)")
    print(f"Daily Drawdown Limit: {strategy.daily_drawdown_limit*100}%")
    print("=" * 60)

    # Trading loop (runs every 15 minutes when new candle closes)
    while True:
        # 1. Fetch latest 60 candles of 15-minute data
        # df = fetch_ohlc_data('FARTCOIN/USDT', timeframe='15m', limit=60)
        df = pd.DataFrame()  # Placeholder - replace with actual API call

        # 2. Check if new day started
        current_time = datetime.now()
        if current_time.hour == 0 and current_time.minute == 0:
            strategy.new_trading_day()
            print(f"\n{'='*60}")
            print(f"NEW TRADING DAY - {current_time.date()}")
            print(f"Starting Capital: ${strategy.capital:,.2f}")
            print(f"{'='*60}\n")

        # 3. If we have an open position, check for exit
        if strategy.position:
            current_candle = {
                'timestamp': df.iloc[-1]['timestamp'],
                'open': df.iloc[-1]['open'],
                'high': df.iloc[-1]['high'],
                'low': df.iloc[-1]['low'],
                'close': df.iloc[-1]['close']
            }

            exit_signal = strategy.check_exit(current_candle)

            if exit_signal:
                # Execute exit on exchange
                # exit_order = exchange.create_market_sell_order('FARTCOIN/USDT', strategy.position['size'])

                # Record trade result
                result = strategy.exit_position(exit_signal)

                print(f"\n🔻 EXIT: {result['exit_reason'].upper()}")
                print(f"  Entry: ${result['entry_price']:.4f} @ {result['entry_timestamp']}")
                print(f"  Exit:  ${result['exit_price']:.4f} @ {result['exit_timestamp']}")
                print(f"  P&L: {result['pnl_pct']:+.2f}% (${result['pnl']:+,.2f})")
                print(f"  Capital: ${result['capital_after']:,.2f}")
                print(f"  Duration: {result['candles_held']} candles\n")

        # 4. If no position, check for entry signal
        else:
            # Check if we can trade today
            if not strategy.should_trade_today():
                print("⚠️  Daily drawdown limit hit - no more trades today")
                # Sleep until next day
                continue

            # Check for entry signal
            entry_signal = strategy.check_entry_signal(df)

            if entry_signal:
                # Execute entry on exchange
                # entry_order = exchange.create_market_buy_order('FARTCOIN/USDT', position_size)

                # Record position
                position = strategy.enter_position(entry_signal)

                print(f"\n🔺 ENTRY: EMA50 PULLBACK")
                print(f"  Price: ${position['entry_price']:.4f}")
                print(f"  Stop: ${position['stop_loss']:.4f} ({((position['stop_loss']/position['entry_price'])-1)*100:.2f}%)")
                print(f"  Size: {position['size']:.2f} FARTCOIN")
                print(f"  Time: {position['entry_timestamp']}")
                print(f"  Capital: ${position['entry_capital']:,.2f}\n")

        # 5. Display current status
        status = strategy.get_status()
        print(f"Status: Capital: ${status['capital']:,.2f} | "
              f"Daily P&L: {status['daily_pnl_pct']:+.2f}% | "
              f"Position: {'OPEN' if status['position_open'] else 'CLOSED'}")

        # 6. Wait for next candle (15 minutes)
        # time.sleep(60 * 15)


if __name__ == '__main__':
    print("""
    EMA50 Pullback Strategy - Live Trading Template
    ================================================

    This is a template showing the strategy logic.

    To use for live trading:
    1. Replace 'fetch_ohlc_data()' with your exchange's API
    2. Replace order execution with actual exchange calls
    3. Add proper error handling and logging
    4. Test thoroughly with paper trading first

    Strategy Rules:
    - Entry: Price pullback to EMA50, closes above
    - Exit: After 8 candles (2 hours) or stop loss
    - Stop: Below pullback candle low
    - Size: 100% of capital per trade
    - Risk: 5% daily drawdown limit

    """)

    # Uncomment to run example
    # example_usage()
