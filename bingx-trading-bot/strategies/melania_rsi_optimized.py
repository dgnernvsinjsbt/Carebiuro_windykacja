"""
MELANIA RSI Mean Reversion - OPTIMIZED
Config: +50%/-50% Dynamic Sizing | 2% Floor | 0.8% Surgical Filter

Performance (Jun-Dec 2025):
- Return: +3,441%
- Max DD: -64.40%
- R/DD: 53.43x
- Win Rate: 38.1%
- Trades: 139
"""
import pandas as pd
import numpy as np

class MelaniaRSIOptimized:
    def __init__(self):
        self.name = "MELANIA RSI Optimized"
        self.symbol = "MELANIA-USDT"
        self.timeframe = "15m"

        # RSI levels
        self.rsi_oversold = 35
        self.rsi_overbought = 65

        # Entry/Exit
        self.limit_offset_atr = 0.1
        self.stop_loss_atr = 1.2
        self.take_profit_atr = 3.0
        self.max_wait_bars = 8

        # Dynamic position sizing
        self.initial_risk = 0.12
        self.current_risk = 0.12
        self.min_risk = 0.02  # 2% floor - THE SECRET WEAPON
        self.max_risk = 0.30  # 30% cap
        self.win_multiplier = 1.5  # +50% after win
        self.loss_multiplier = 0.5  # -50% after loss

        # Surgical filter
        self.min_move_size = 0.8  # Skip SHORT if avg move < 0.8%

        # State
        self.pending_order = None
        self.last_trade_won = None

    def calculate_indicators(self, candles):
        """Calculate RSI, ATR, momentum filter, move size filter"""
        df = pd.DataFrame(candles)

        # RSI (Wilder's EMA)
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()

        # Momentum filter (20-bar return)
        df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

        # Move size filter (avg absolute 4-hour return)
        df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
        df['ret_4h_abs'] = abs(df['ret_4h'])
        df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

        return df

    def update_risk_after_trade(self, won):
        """Dynamic position sizing: +50% after win, -50% after loss"""
        if won:
            self.current_risk = min(self.current_risk * self.win_multiplier, self.max_risk)
        else:
            self.current_risk = max(self.current_risk * self.loss_multiplier, self.min_risk)

        self.last_trade_won = won

    def generate_signal(self, candles, current_price, account_balance):
        """Generate trading signals with dynamic sizing and surgical filter"""

        if len(candles) < 100:
            return None

        df = self.calculate_indicators(candles)

        if df.empty or len(df) < 2:
            return None

        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Check required indicators
        if pd.isna(current['rsi']) or pd.isna(current['atr']) or pd.isna(current['ret_20']):
            return None
        if pd.isna(current['avg_move_size']):
            return None

        # Momentum filter: only trade when ret_20 > 0
        if current['ret_20'] <= 0:
            return None

        atr = current['atr']

        # LONG signal: RSI crosses above 35
        if previous['rsi'] < self.rsi_oversold and current['rsi'] >= self.rsi_oversold:
            limit_price = current_price - (atr * self.limit_offset_atr)
            sl_price = limit_price - (atr * self.stop_loss_atr)
            tp_price = limit_price + (atr * self.take_profit_atr)

            # Calculate position size based on current risk
            sl_distance_pct = abs((limit_price - sl_price) / limit_price)
            risk_amount = account_balance * self.current_risk
            position_size = risk_amount / sl_distance_pct

            return {
                'type': 'LIMIT',
                'side': 'LONG',
                'symbol': self.symbol,
                'entry_price': limit_price,
                'stop_loss': sl_price,
                'take_profit': tp_price,
                'position_size_usd': position_size,
                'max_wait_bars': self.max_wait_bars,
                'reason': f'RSI cross above {self.rsi_oversold}, Risk: {self.current_risk*100:.1f}%'
            }

        # SHORT signal: RSI crosses below 65
        elif previous['rsi'] > self.rsi_overbought and current['rsi'] <= self.rsi_overbought:

            # SURGICAL FILTER: Skip SHORT if move size < 0.8%
            if current['avg_move_size'] < self.min_move_size:
                return None

            limit_price = current_price + (atr * self.limit_offset_atr)
            sl_price = limit_price + (atr * self.stop_loss_atr)
            tp_price = limit_price - (atr * self.take_profit_atr)

            # Calculate position size based on current risk
            sl_distance_pct = abs((sl_price - limit_price) / limit_price)
            risk_amount = account_balance * self.current_risk
            position_size = risk_amount / sl_distance_pct

            return {
                'type': 'LIMIT',
                'side': 'SHORT',
                'symbol': self.symbol,
                'entry_price': limit_price,
                'stop_loss': sl_price,
                'take_profit': tp_price,
                'position_size_usd': position_size,
                'max_wait_bars': self.max_wait_bars,
                'reason': f'RSI cross below {self.rsi_overbought}, Risk: {self.current_risk*100:.1f}%, MoveSize: {current["avg_move_size"]:.2f}%'
            }

        return None

    def on_trade_closed(self, pnl_pct):
        """Called when a trade closes - update risk for next trade"""
        won = pnl_pct > 0
        self.update_risk_after_trade(won)

        status = "WIN" if won else "LOSS"
        print(f"[{self.name}] Trade closed: {status} ({pnl_pct:+.2f}%) | Next risk: {self.current_risk*100:.1f}%")
