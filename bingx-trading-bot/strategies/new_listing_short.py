"""
NEW LISTING SHORT STRATEGY

Backtest Results (324 coins listed in 2025, 30 days each):
- 1→1→1% risk: +649% return, 19% DD, 33x R:R
- 5→3→1% risk: +75,150% return, 58% DD, 1304x R:R

Out-of-Sample 2026 (27 coins):
- 75% Win Rate, +77.5% return, 9% DD

Strategy Logic:
1. Wait 24h after listing
2. ARM: Pump ≥25% above listing price
3. ENTRY: Short with pyramid (up to 3 entries)
4. DCA: Next entry when +10% higher
5. SL: 25% from latest entry (moves up with each add)
6. TP: 25% profit from average entry OR return to listing price

Key Insight:
- 63% of 2025 listings dumped >30%
- Pyramid DCA acts as confirmation filter (single entry = 50% WR, pyramid = 66%+ WR)
- Moving SL prevents large losses on runaway pumps
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import logging
import aiohttp


# Risk schedules (% per entry)
RISK_SCHEDULES = {
    'conservative': [1.0, 1.0, 1.0],  # 3% max total
    'moderate':     [2.0, 1.5, 1.0],  # 4.5% max total
    'aggressive':   [5.0, 3.0, 1.0],  # 9% max total (reverse pyramid)
}

# Strategy parameters
WAIT_HOURS = 24           # Wait after listing before trading
PUMP_THRESHOLD = 25.0     # % pump required to enter
MAX_ENTRIES = 3           # Maximum DCA entries
ENTRY_STEP = 10.0         # % between entries
SL_PCT = 25.0             # Stop loss %
TP_PCT = 25.0             # Take profit %
MAX_COIN_AGE_DAYS = 30    # Only trade coins < 30 days old


class NewListingState:
    """Track state for a single coin's position"""
    def __init__(self, symbol: str, listing_price: float, listing_date: datetime):
        self.symbol = symbol
        self.listing_price = listing_price
        self.listing_date = listing_date
        self.entries: List[float] = []
        self.avg_entry: float = 0.0
        self.sl_price: float = 0.0
        self.tp_price: float = 0.0
        self.is_armed: bool = False
        self.total_risk_used: float = 0.0


CACHE_REFRESH_HOURS = 6  # Refresh listing cache every 6 hours


class NewListingShort:
    """
    New Listing Short Strategy

    Shorts newly listed coins that pump >25% above listing price.
    Uses pyramid DCA (up to 3 entries) with moving stop loss.

    Auto-refreshes listing cache every 6 hours to detect new coins.
    """

    def __init__(self, config: Dict[str, Any]):
        self.name = 'new_listing_short'
        self.config = config
        self.enabled = config.get('enabled', True)

        # Risk schedule
        risk_schedule_name = config.get('risk_schedule', 'conservative')
        self.risk_schedule = RISK_SCHEDULES.get(risk_schedule_name, RISK_SCHEDULES['conservative'])

        # State tracking per coin
        self.coin_states: Dict[str, NewListingState] = {}

        # Cache for listing info
        self.listing_cache: Dict[str, Dict] = {}
        self.cache_loaded = False
        self.last_cache_refresh: Optional[datetime] = None

        # Logger
        self.logger = logging.getLogger(f"strategy.{self.name}")

        self.logger.info(f"NewListingShort initialized:")
        self.logger.info(f"  Risk schedule: {risk_schedule_name} = {self.risk_schedule}")
        self.logger.info(f"  Wait: {WAIT_HOURS}h, Pump threshold: {PUMP_THRESHOLD}%")
        self.logger.info(f"  Max entries: {MAX_ENTRIES}, Entry step: {ENTRY_STEP}%")
        self.logger.info(f"  SL: {SL_PCT}%, TP: {TP_PCT}%")

    def needs_cache_refresh(self) -> bool:
        """Check if cache needs refreshing"""
        if not self.cache_loaded or self.last_cache_refresh is None:
            return True

        hours_since_refresh = (datetime.now(timezone.utc) - self.last_cache_refresh).total_seconds() / 3600
        return hours_since_refresh >= CACHE_REFRESH_HOURS

    async def load_listing_cache(self, force: bool = False):
        """Load listing dates and prices from BingX. Auto-refreshes every 6 hours."""
        if not force and self.cache_loaded and not self.needs_cache_refresh():
            return

        action = "Refreshing" if self.cache_loaded else "Loading"
        self.logger.info(f"{action} new listing data from BingX...")

        try:
            # Get all contracts
            url = "https://open-api.bingx.com/openApi/swap/v2/quote/contracts"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    if data.get('code') != 0:
                        self.logger.error(f"Failed to fetch contracts: {data}")
                        return

                    symbols = [c['symbol'] for c in data.get('data', []) if c['symbol'].endswith('-USDT')]

            self.logger.info(f"Found {len(symbols)} USDT perpetuals, checking listing dates...")

            # Check listing date for each (via 1D candles - oldest = listing)
            # This is done at startup, not per-request
            now = datetime.now(timezone.utc)

            for symbol in symbols:
                try:
                    klines_url = f"https://open-api.bingx.com/openApi/swap/v3/quote/klines?symbol={symbol}&interval=1d&limit=60"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(klines_url) as response:
                            data = await response.json()
                            if data.get('code') != 0:
                                continue

                            candles = data.get('data', [])
                            if not candles or len(candles) < 5:
                                continue

                            # BingX returns newest first, last = oldest = listing
                            oldest = candles[-1]
                            listing_ts = int(oldest['time']) / 1000
                            listing_date = datetime.fromtimestamp(listing_ts, tz=timezone.utc)
                            listing_price = float(oldest['open'])

                            days_since_listing = (now - listing_date).days

                            if days_since_listing <= MAX_COIN_AGE_DAYS:
                                self.listing_cache[symbol] = {
                                    'listing_date': listing_date,
                                    'listing_price': listing_price,
                                    'days_listed': days_since_listing
                                }
                                self.logger.info(f"  {symbol}: listed {days_since_listing}d ago @ ${listing_price:.6f}")

                except Exception as e:
                    continue

            self.cache_loaded = True
            self.last_cache_refresh = datetime.now(timezone.utc)
            self.logger.info(f"Loaded {len(self.listing_cache)} coins eligible for trading (< {MAX_COIN_AGE_DAYS} days old)")
            self.logger.info(f"Next refresh in {CACHE_REFRESH_HOURS} hours")

        except Exception as e:
            self.logger.error(f"Failed to load listing cache: {e}")

    def is_eligible(self, symbol: str) -> bool:
        """Check if coin is eligible for this strategy"""
        if symbol not in self.listing_cache:
            return False

        info = self.listing_cache[symbol]
        now = datetime.now(timezone.utc)
        hours_since_listing = (now - info['listing_date']).total_seconds() / 3600

        # Must be > WAIT_HOURS and < MAX_COIN_AGE_DAYS
        return hours_since_listing >= WAIT_HOURS and info['days_listed'] <= MAX_COIN_AGE_DAYS

    def get_listing_price(self, symbol: str) -> Optional[float]:
        """Get listing price for a coin"""
        if symbol in self.listing_cache:
            return self.listing_cache[symbol]['listing_price']
        return None

    async def maybe_refresh_cache(self):
        """Check and refresh cache if needed (call this periodically)"""
        if self.needs_cache_refresh():
            self.logger.info(f"Cache expired ({CACHE_REFRESH_HOURS}h), refreshing...")
            await self.load_listing_cache(force=True)

    def generate_signals(self, symbol: str, df: pd.DataFrame, current_positions: list) -> Optional[Dict[str, Any]]:
        """Generate signals for a specific coin"""

        if not self.is_eligible(symbol):
            return None

        listing_price = self.get_listing_price(symbol)
        if listing_price is None:
            return None

        if len(df) < 2:
            return None

        latest = df.iloc[-1]
        price = float(latest['close'])
        high = float(latest['high'])
        low = float(latest['low'])
        timestamp = latest.get('timestamp', datetime.now(timezone.utc))

        # Initialize state if needed
        if symbol not in self.coin_states:
            listing_info = self.listing_cache[symbol]
            self.coin_states[symbol] = NewListingState(
                symbol=symbol,
                listing_price=listing_price,
                listing_date=listing_info['listing_date']
            )

        state = self.coin_states[symbol]
        pump_pct = (price / listing_price - 1) * 100

        # Check if we have an open position
        has_position = len(current_positions) > 0 or len(state.entries) > 0

        # ===== EXIT LOGIC =====
        if state.entries:
            # Check SL hit (high >= sl_price for short)
            if high >= state.sl_price:
                pnl_pct = -SL_PCT
                self.logger.warning(f"[{symbol}] SL HIT! High ${high:.4f} >= SL ${state.sl_price:.4f}")

                signal = {
                    'action': 'CLOSE',
                    'side': 'CLOSE_SHORT',
                    'direction': 'CLOSE',
                    'type': 'MARKET',
                    'reason': f"SL hit: ${high:.4f} >= ${state.sl_price:.4f}",
                    'pnl_pct': pnl_pct,
                    'metadata': {
                        'avg_entry': state.avg_entry,
                        'num_entries': len(state.entries),
                        'exit_price': state.sl_price
                    }
                }

                # Reset state
                state.entries = []
                state.avg_entry = 0
                state.sl_price = 0
                state.tp_price = 0
                state.total_risk_used = 0

                return signal

            # Check TP hit (low <= tp_price for short) OR return to listing price
            tp_target = state.avg_entry * (1 - TP_PCT / 100)
            listing_target = listing_price * 0.99  # Slightly below listing

            if low <= tp_target or low <= listing_target:
                exit_price = max(tp_target, listing_target)
                pnl_pct = (state.avg_entry - exit_price) / state.avg_entry * 100

                self.logger.info(f"[{symbol}] TP HIT! Low ${low:.4f} <= TP ${tp_target:.4f}")

                signal = {
                    'action': 'CLOSE',
                    'side': 'CLOSE_SHORT',
                    'direction': 'CLOSE',
                    'type': 'MARKET',
                    'reason': f"TP hit: ${low:.4f} <= ${tp_target:.4f}",
                    'pnl_pct': pnl_pct,
                    'metadata': {
                        'avg_entry': state.avg_entry,
                        'num_entries': len(state.entries),
                        'exit_price': exit_price
                    }
                }

                # Reset state
                state.entries = []
                state.avg_entry = 0
                state.sl_price = 0
                state.tp_price = 0
                state.total_risk_used = 0

                return signal

        # ===== ENTRY LOGIC =====

        # Check if pump threshold met
        if pump_pct < PUMP_THRESHOLD:
            self.logger.debug(f"[{symbol}] Pump {pump_pct:.1f}% < threshold {PUMP_THRESHOLD}%")
            return None

        # First entry
        if not state.entries:
            entry_price = price
            sl_price = entry_price * (1 + SL_PCT / 100)
            tp_price = entry_price * (1 - TP_PCT / 100)
            risk_pct = self.risk_schedule[0]

            state.entries = [entry_price]
            state.avg_entry = entry_price
            state.sl_price = sl_price
            state.tp_price = tp_price
            state.total_risk_used = risk_pct

            self.logger.info(f"[{symbol}] ENTRY 1/3 @ ${entry_price:.4f}")
            self.logger.info(f"  Pump: {pump_pct:.1f}%, SL: ${sl_price:.4f}, TP: ${tp_price:.4f}")
            self.logger.info(f"  Risk: {risk_pct}%")

            return {
                'action': 'OPEN',
                'side': 'SHORT',
                'direction': 'SHORT',
                'type': 'MARKET',
                'entry_price': entry_price,
                'stop_loss': sl_price,
                'take_profit': tp_price,
                'risk_pct': risk_pct,
                'reason': f"New listing short: pump {pump_pct:.1f}% (entry 1/{MAX_ENTRIES})",
                'metadata': {
                    'listing_price': listing_price,
                    'pump_pct': pump_pct,
                    'entry_num': 1,
                    'avg_entry': entry_price
                }
            }

        # DCA entries (2nd and 3rd)
        elif len(state.entries) < MAX_ENTRIES:
            last_entry = state.entries[-1]
            required_price = last_entry * (1 + ENTRY_STEP / 100)

            if price >= required_price:
                entry_num = len(state.entries) + 1
                entry_price = price
                risk_pct = self.risk_schedule[entry_num - 1]

                state.entries.append(entry_price)
                state.avg_entry = np.mean(state.entries)
                state.sl_price = entry_price * (1 + SL_PCT / 100)  # SL moves up!
                state.tp_price = state.avg_entry * (1 - TP_PCT / 100)
                state.total_risk_used += risk_pct

                self.logger.info(f"[{symbol}] ENTRY {entry_num}/{MAX_ENTRIES} @ ${entry_price:.4f}")
                self.logger.info(f"  Avg entry: ${state.avg_entry:.4f}, New SL: ${state.sl_price:.4f}")
                self.logger.info(f"  Additional risk: {risk_pct}%, Total: {state.total_risk_used}%")

                return {
                    'action': 'ADD',
                    'side': 'SHORT',
                    'direction': 'SHORT',
                    'type': 'MARKET',
                    'entry_price': entry_price,
                    'stop_loss': state.sl_price,
                    'take_profit': state.tp_price,
                    'risk_pct': risk_pct,
                    'reason': f"DCA add: pump continued (entry {entry_num}/{MAX_ENTRIES})",
                    'metadata': {
                        'listing_price': listing_price,
                        'pump_pct': pump_pct,
                        'entry_num': entry_num,
                        'avg_entry': state.avg_entry,
                        'all_entries': state.entries.copy()
                    }
                }

        return None

    def calculate_position_size(self, risk_pct: float, entry_price: float, stop_price: float, capital: float) -> float:
        """Calculate position size based on risk"""
        sl_distance_pct = abs(entry_price - stop_price) / entry_price * 100

        if sl_distance_pct <= 0:
            return 0

        # Position size = Capital * (Risk% / SL_distance%)
        leverage = risk_pct / sl_distance_pct
        position_size = capital * leverage

        self.logger.info(f"Position sizing: {risk_pct}% risk / {sl_distance_pct:.2f}% SL = {leverage:.2f}x")

        return position_size

    def get_eligible_symbols(self) -> List[str]:
        """Get list of symbols eligible for trading"""
        return [s for s in self.listing_cache.keys() if self.is_eligible(s)]

    async def scan_all_coins(self, get_candles_func, get_positions_func) -> List[Dict[str, Any]]:
        """
        Main entry point - scan all eligible coins for signals.

        Args:
            get_candles_func: async func(symbol) -> pd.DataFrame with 1H candles
            get_positions_func: func(symbol) -> list of current positions

        Returns:
            List of signals to execute
        """
        # Auto-refresh cache if needed
        await self.maybe_refresh_cache()

        if not self.cache_loaded:
            await self.load_listing_cache()

        eligible = self.get_eligible_symbols()
        if not eligible:
            self.logger.debug("No eligible coins found")
            return []

        self.logger.info(f"Scanning {len(eligible)} eligible coins...")

        signals = []
        for symbol in eligible:
            try:
                df = await get_candles_func(symbol)
                if df is None or len(df) < 2:
                    continue

                positions = get_positions_func(symbol)
                signal = self.generate_signals(symbol, df, positions)

                if signal:
                    signal['symbol'] = symbol
                    signals.append(signal)
                    self.logger.info(f"Signal for {symbol}: {signal['action']} {signal.get('side', '')}")

            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {e}")
                continue

        return signals

    def get_state(self, symbol: str) -> Optional[NewListingState]:
        """Get current state for a symbol"""
        return self.coin_states.get(symbol)

    def reset_state(self, symbol: str):
        """Reset state for a symbol"""
        if symbol in self.coin_states:
            del self.coin_states[symbol]


# Factory function
def create_new_listing_strategy(config: Dict[str, Any]) -> NewListingShort:
    """Create the new listing short strategy"""
    return NewListingShort(config)
