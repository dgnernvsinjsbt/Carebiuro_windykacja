#!/usr/bin/env python3
"""
FARTCOIN/USDT Pattern Recognition Strategy V2
Focus: Total Return / Max Drawdown Ratio (Portfolio R:R)
With dynamic position sizing and ATR-based exits
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class FartcoinPatternStrategy:
    """
    Pattern recognition with focus on portfolio-level risk:reward.
    Goal: Maximize (Total Return / Max Drawdown) ratio
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001  # 0.1% per side
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Position sizing parameters
        self.base_risk_pct = 1.0  # Base risk per trade (%)
        self.current_risk_pct = 1.0
        self.win_streak = 0
        self.loss_streak = 0

    def load_data(self):
        """Load and prepare OHLCV data with technical indicators"""
        print(f"\n{'='*60}")
        print("Loading FARTCOIN/USDT Data")
        print(f"{'='*60}")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,}")
        print(f"Duration: {len(self.df) / 60 / 24:.1f} days")

        # Calculate ATR for dynamic stops
        self.df['tr'] = np.maximum(
            self.df['high'] - self.df['low'],
            np.maximum(
                abs(self.df['high'] - self.df['close'].shift(1)),
                abs(self.df['low'] - self.df['close'].shift(1))
            )
        )
        self.df['atr'] = self.df['tr'].rolling(14).mean()
        self.df['atr_pct'] = (self.df['atr'] / self.df['close']) * 100

        # Volume indicators
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Price features
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['total_wick'] = self.df['upper_wick'] + self.df['lower_wick']
        self.df['wick_to_body'] = self.df['total_wick'] / (self.df['body'] + 0.0001)

        # Candle direction
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Momentum
        self.df['sma_20'] = self.df['close'].rolling(20).mean()
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['price_to_sma20'] = ((self.df['close'] - self.df['sma_20']) / self.df['sma_20']) * 100

        # Range
        self.df['range_pct'] = ((self.df['high'] - self.df['low']) / self.df['low']) * 100
        self.df['avg_range_20'] = self.df['range_pct'].rolling(20).mean()

        print(f"\n✓ Technical indicators calculated")
        return self.df

    def detect_patterns(self, idx: int):
        """
        Detect profitable patterns - both long and short
        Returns: {'direction': 'long'/'short', 'pattern': str, 'confidence': float}
        """
        if idx < 100:  # Need history for indicators
            return None

        row = self.df.loc[idx]

        patterns = []

        # === LONG PATTERNS ===

        # 1. Strong Bullish Momentum Breakout
        if (row['is_bullish'] and
            row['body_pct'] > 0.6 and
            row['vol_ratio'] > 2.0 and
            row['wick_to_body'] < 0.5 and
            row['close'] > row['sma_20']):
            patterns.append({
                'direction': 'long',
                'pattern': 'Bullish Momentum Breakout',
                'confidence': 0.85
            })

        # 2. Hammer at Support
        if (row['is_bullish'] and
            row['lower_wick'] > 2 * row['body'] and
            row['upper_wick'] < row['body'] and
            row['vol_ratio'] > 1.5 and
            row['close'] < row['sma_20'] and
            row['price_to_sma20'] < -2):
            patterns.append({
                'direction': 'long',
                'pattern': 'Hammer Reversal',
                'confidence': 0.75
            })

        # 3. Bullish Engulfing
        if idx > 0:
            prev = self.df.loc[idx-1]
            if (prev['is_bearish'] and row['is_bullish'] and
                row['open'] < prev['close'] and
                row['close'] > prev['open'] and
                row['vol_ratio'] > 1.3):
                patterns.append({
                    'direction': 'long',
                    'pattern': 'Bullish Engulfing',
                    'confidence': 0.70
                })

        # === SHORT PATTERNS ===

        # 4. Strong Bearish Momentum Breakdown
        if (row['is_bearish'] and
            row['body_pct'] > 0.6 and
            row['vol_ratio'] > 2.0 and
            row['wick_to_body'] < 0.5 and
            row['close'] < row['sma_20']):
            patterns.append({
                'direction': 'short',
                'pattern': 'Bearish Momentum Breakdown',
                'confidence': 0.85
            })

        # 5. Shooting Star at Resistance
        if (row['is_bearish'] and
            row['upper_wick'] > 2 * row['body'] and
            row['lower_wick'] < row['body'] and
            row['vol_ratio'] > 1.5 and
            row['close'] > row['sma_20'] and
            row['price_to_sma20'] > 2):
            patterns.append({
                'direction': 'short',
                'pattern': 'Shooting Star Reversal',
                'confidence': 0.75
            })

        # 6. Bearish Engulfing
        if idx > 0:
            prev = self.df.loc[idx-1]
            if (prev['is_bullish'] and row['is_bearish'] and
                row['open'] > prev['close'] and
                row['close'] < prev['open'] and
                row['vol_ratio'] > 1.3):
                patterns.append({
                    'direction': 'short',
                    'pattern': 'Bearish Engulfing',
                    'confidence': 0.70
                })

        # Return highest confidence pattern
        if patterns:
            return max(patterns, key=lambda x: x['confidence'])
        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """
        Calculate position size based on:
        - Current risk percentage (dynamic based on win/loss streak)
        - Stop loss distance
        - Available capital
        """
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance

        # Cap at 50% of capital (conservative)
        max_position = self.capital * 0.5
        position_size = min(position_size, max_position)

        return position_size

    def update_risk_sizing(self, trade_won: bool):
        """
        Dynamically adjust position sizing based on performance
        - Increase size on winning streaks (confidence building)
        - Decrease size on losing streaks (risk reduction)
        """
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0

            # Increase risk by 0.25% per win (max 2.5%)
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * 0.25),
                2.5
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0

            # Decrease risk by 0.2% per loss (min 0.5%)
            self.current_risk_pct = max(
                self.base_risk_pct - (self.loss_streak * 0.2),
                0.5
            )

    def backtest(self):
        """Run backtest with pattern detection and dynamic position sizing"""
        print(f"\n{'='*60}")
        print("Running Backtest")
        print(f"{'='*60}")

        in_position = False
        entry_idx = None
        position = None

        for idx in range(100, len(self.df)):
            row = self.df.loc[idx]

            # Check for exit if in position
            if in_position and position:
                current_price = row['close']

                # Calculate P&L
                if position['direction'] == 'long':
                    pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                else:  # short
                    pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100

                exit_triggered = False
                exit_reason = None

                # Stop loss
                if position['direction'] == 'long' and current_price <= position['stop_loss']:
                    exit_triggered = True
                    exit_reason = 'Stop Loss'
                    current_price = position['stop_loss']
                elif position['direction'] == 'short' and current_price >= position['stop_loss']:
                    exit_triggered = True
                    exit_reason = 'Stop Loss'
                    current_price = position['stop_loss']

                # Take profit
                if position['direction'] == 'long' and current_price >= position['take_profit']:
                    exit_triggered = True
                    exit_reason = 'Take Profit'
                    current_price = position['take_profit']
                elif position['direction'] == 'short' and current_price <= position['take_profit']:
                    exit_triggered = True
                    exit_reason = 'Take Profit'
                    current_price = position['take_profit']

                # Time stop (max 2 hours)
                if (row['timestamp'] - position['entry_time']).total_seconds() > 7200:
                    exit_triggered = True
                    exit_reason = 'Time Stop'

                # Exit position
                if exit_triggered:
                    # Calculate final P&L
                    if position['direction'] == 'long':
                        pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100

                    # Apply fees
                    pnl_pct -= (self.fee_rate * 2 * 100)  # Entry + exit fees

                    # Update capital
                    pnl_amount = position['position_size'] * (pnl_pct / 100)
                    self.capital += pnl_amount

                    # Record trade
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'exit_reason': exit_reason,
                        'capital': self.capital,
                        'risk_pct_used': position['risk_pct']
                    }
                    self.trades.append(trade)

                    # Update risk sizing based on result
                    self.update_risk_sizing(pnl_amount > 0)

                    in_position = False
                    position = None

            # Look for entry if not in position
            if not in_position:
                signal = self.detect_patterns(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    # ATR-based stops and targets
                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (2 * atr)
                        take_profit = entry_price + (4 * atr)  # 2:1 R:R
                    else:  # short
                        stop_loss = entry_price + (2 * atr)
                        take_profit = entry_price - (4 * atr)

                    # Calculate position size
                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        position = {
                            'entry_time': row['timestamp'],
                            'entry_price': entry_price,
                            'direction': signal['direction'],
                            'pattern': signal['pattern'],
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size,
                            'risk_pct': self.current_risk_pct
                        }
                        in_position = True

            # Record equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        return self.analyze_results()

    def analyze_results(self):
        """Analyze backtest performance with focus on Return/Drawdown ratio"""
        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")

        if not self.trades:
            print("No trades generated!")
            return

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Calculate metrics
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl_amount'] > 0])
        losing_trades = len(df_trades[df_trades['pnl_amount'] <= 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        total_return_amount = self.capital - self.initial_capital

        # Calculate drawdown
        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = ((df_equity['capital'] - df_equity['peak']) / df_equity['peak']) * 100
        max_drawdown_pct = df_equity['drawdown'].min()

        # Risk:Reward ratio (Total Return / Max Drawdown)
        if max_drawdown_pct < 0:
            risk_reward_ratio = abs(total_return_pct / max_drawdown_pct)
        else:
            risk_reward_ratio = float('inf') if total_return_pct > 0 else 0

        # Trade statistics
        avg_win = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losing_trades > 0 else 0

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Print results
        print(f"\n📊 PERFORMANCE SUMMARY")
        print(f"{'-'*60}")
        print(f"Initial Capital:        ${self.initial_capital:,.2f}")
        print(f"Final Capital:          ${self.capital:,.2f}")
        print(f"Total Return:           ${total_return_amount:,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:           {max_drawdown_pct:.2f}%")
        print(f"")
        print(f"🎯 RISK:REWARD RATIO:   {risk_reward_ratio:.2f}x")
        print(f"   (Total Return / Max Drawdown)")
        print(f"")
        print(f"📈 TRADE STATISTICS")
        print(f"{'-'*60}")
        print(f"Total Trades:           {total_trades}")
        print(f"Winning Trades:         {winning_trades} ({win_rate:.1f}%)")
        print(f"Losing Trades:          {losing_trades}")
        print(f"Average Win:            {avg_win:+.2f}%")
        print(f"Average Loss:           {avg_loss:+.2f}%")
        print(f"Profit Factor:          {profit_factor:.2f}")
        print(f"")

        # Direction breakdown
        long_trades = df_trades[df_trades['direction'] == 'long']
        short_trades = df_trades[df_trades['direction'] == 'short']

        print(f"📊 DIRECTION BREAKDOWN")
        print(f"{'-'*60}")
        print(f"Long Trades:   {len(long_trades)} (Return: {long_trades['pnl_amount'].sum():+.2f})")
        print(f"Short Trades:  {len(short_trades)} (Return: {short_trades['pnl_amount'].sum():+.2f})")

        # Pattern breakdown
        print(f"\n📊 PATTERN PERFORMANCE")
        print(f"{'-'*60}")
        for pattern in df_trades['pattern'].unique():
            pattern_trades = df_trades[df_trades['pattern'] == pattern]
            pattern_return = pattern_trades['pnl_amount'].sum()
            pattern_win_rate = (len(pattern_trades[pattern_trades['pnl_amount'] > 0]) / len(pattern_trades)) * 100
            print(f"{pattern:30s}: {len(pattern_trades):3d} trades, {pattern_win_rate:5.1f}% WR, ${pattern_return:+8.2f}")

        # Best and worst trades
        best_trade = df_trades.loc[df_trades['pnl_pct'].idxmax()]
        worst_trade = df_trades.loc[df_trades['pnl_pct'].idxmin()]

        print(f"\n🏆 BEST TRADE")
        print(f"{'-'*60}")
        print(f"Pattern: {best_trade['pattern']}")
        print(f"Direction: {best_trade['direction'].upper()}")
        print(f"Entry: ${best_trade['entry_price']:.5f} @ {best_trade['entry_time']}")
        print(f"Exit: ${best_trade['exit_price']:.5f} @ {best_trade['exit_time']}")
        print(f"Return: {best_trade['pnl_pct']:+.2f}% (${best_trade['pnl_amount']:+.2f})")
        print(f"Exit: {best_trade['exit_reason']}")

        print(f"\n📉 WORST TRADE")
        print(f"{'-'*60}")
        print(f"Pattern: {worst_trade['pattern']}")
        print(f"Direction: {worst_trade['direction'].upper()}")
        print(f"Entry: ${worst_trade['entry_price']:.5f} @ {worst_trade['entry_time']}")
        print(f"Exit: ${worst_trade['exit_price']:.5f} @ {worst_trade['exit_time']}")
        print(f"Return: {worst_trade['pnl_pct']:+.2f}% (${worst_trade['pnl_amount']:+.2f})")
        print(f"Exit: {worst_trade['exit_reason']}")

        # Save results
        df_trades.to_csv('./strategies/fartcoin-trades-v2.csv', index=False)
        df_equity.to_csv('./strategies/fartcoin-equity-v2.csv', index=False)

        print(f"\n✓ Results saved:")
        print(f"  - ./strategies/fartcoin-trades-v2.csv")
        print(f"  - ./strategies/fartcoin-equity-v2.csv")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'risk_reward_ratio': risk_reward_ratio,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor
        }


if __name__ == "__main__":
    # Run strategy
    strategy = FartcoinPatternStrategy(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    results = strategy.backtest()

    print(f"\n{'='*60}")
    print("STRATEGY COMPLETE")
    print(f"{'='*60}")

    if results:
        is_profitable = results['total_return_pct'] > 0
        has_good_rr = results['risk_reward_ratio'] > 3.0

        print(f"\n✓ Profitable: {'YES' if is_profitable else 'NO'}")
        print(f"✓ Good Risk:Reward: {'YES' if has_good_rr else 'NO'} (target: >3x)")

        if is_profitable and has_good_rr:
            print(f"\n🎉 STRATEGY IS VIABLE!")
            print(f"Next step: Optimize position sizing and ATR multipliers")
        elif is_profitable:
            print(f"\n⚠️ PROFITABLE but high drawdown")
            print(f"Next step: Reduce position sizes or improve exits")
        else:
            print(f"\n❌ NOT PROFITABLE")
            print(f"Next step: Filter to best patterns only")
