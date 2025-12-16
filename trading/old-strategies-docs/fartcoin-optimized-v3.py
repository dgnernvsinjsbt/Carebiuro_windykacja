#!/usr/bin/env python3
"""
FARTCOIN/USDT Optimized Pattern Strategy V3
Focus: Return/Drawdown ratio with selective high-quality patterns
Dynamic position sizing and wider ATR-based stops
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class OptimizedFartcoinStrategy:
    """
    Highly selective pattern strategy focusing on:
    - Quality over quantity (fewer, better trades)
    - Wider stops (3-4x ATR) for breathing room
    - Aggressive position sizing on winning streaks
    - Both long and short patterns
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Dynamic position sizing
        self.base_risk_pct = 1.5  # Higher base risk
        self.current_risk_pct = 1.5
        self.win_streak = 0
        self.loss_streak = 0
        self.max_risk_pct = 5.0  # More aggressive max
        self.min_risk_pct = 0.5

    def load_data(self):
        """Load and calculate indicators"""
        print(f"\n{'='*60}")
        print("FARTCOIN Optimized Strategy V3")
        print(f"{'='*60}")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)")

        # ATR
        self.df['tr'] = np.maximum(
            self.df['high'] - self.df['low'],
            np.maximum(
                abs(self.df['high'] - self.df['close'].shift(1)),
                abs(self.df['low'] - self.df['close'].shift(1))
            )
        )
        self.df['atr'] = self.df['tr'].rolling(14).mean()
        self.df['atr_pct'] = (self.df['atr'] / self.df['close']) * 100

        # Volume
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Price structure
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Moving averages for trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()
        self.df['uptrend'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend'] = self.df['close'] < self.df['sma_50']

        # RSI for extremes
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        print(f"✓ Indicators loaded\n")
        return self.df

    def detect_high_quality_setup(self, idx: int):
        """
        Detect ONLY high-quality, high-confidence setups
        Much more selective than V2
        """
        if idx < 200:
            return None

        row = self.df.loc[idx]
        setups = []

        # === LONG SETUPS ===

        # 1. Explosive Bullish Breakout (BEST pattern from V1)
        if (row['is_bullish'] and
            row['uptrend'] and  # Trend filter
            row['body_pct'] > 1.0 and  # Larger body
            row['vol_ratio'] > 2.5 and  # Higher volume threshold
            row['lower_wick'] < row['body'] * 0.3 and  # Clean candle
            row['upper_wick'] < row['body'] * 0.3 and
            row['rsi'] > 45 and row['rsi'] < 70):  # Not overbought
            setups.append({
                'direction': 'long',
                'pattern': 'Explosive Bullish Breakout',
                'confidence': 0.90,
                'atr_stop_mult': 3.0,  # Wider stop
                'atr_target_mult': 9.0  # Larger target (3:1 R:R)
            })

        # 2. Hammer Reversal (showed profit in V2)
        if (row['is_bullish'] and
            row['lower_wick'] > 2.5 * row['body'] and
            row['upper_wick'] < row['body'] * 0.5 and
            row['vol_ratio'] > 2.0 and
            row['rsi'] < 35 and  # Oversold
            row['downtrend']):  # In downtrend
            setups.append({
                'direction': 'long',
                'pattern': 'Hammer Reversal',
                'confidence': 0.80,
                'atr_stop_mult': 2.5,
                'atr_target_mult': 7.5
            })

        # 3. Bullish Volume Climax
        if (row['is_bullish'] and
            row['vol_ratio'] > 4.0 and  # Massive volume
            row['body_pct'] > 0.8 and
            row['rsi'] < 40):
            setups.append({
                'direction': 'long',
                'pattern': 'Bullish Volume Climax',
                'confidence': 0.85,
                'atr_stop_mult': 3.0,
                'atr_target_mult': 9.0
            })

        # === SHORT SETUPS ===

        # 4. Explosive Bearish Breakdown
        if (row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > 1.0 and
            row['vol_ratio'] > 2.5 and
            row['lower_wick'] < row['body'] * 0.3 and
            row['upper_wick'] < row['body'] * 0.3 and
            row['rsi'] < 55 and row['rsi'] > 30):
            setups.append({
                'direction': 'short',
                'pattern': 'Explosive Bearish Breakdown',
                'confidence': 0.90,
                'atr_stop_mult': 3.0,
                'atr_target_mult': 9.0
            })

        # 5. Shooting Star Reversal
        if (row['is_bearish'] and
            row['upper_wick'] > 2.5 * row['body'] and
            row['lower_wick'] < row['body'] * 0.5 and
            row['vol_ratio'] > 2.0 and
            row['rsi'] > 65 and  # Overbought
            row['uptrend']):
            setups.append({
                'direction': 'short',
                'pattern': 'Shooting Star Reversal',
                'confidence': 0.80,
                'atr_stop_mult': 2.5,
                'atr_target_mult': 7.5
            })

        # 6. Bearish Volume Climax
        if (row['is_bearish'] and
            row['vol_ratio'] > 4.0 and
            row['body_pct'] > 0.8 and
            row['rsi'] > 60):
            setups.append({
                'direction': 'short',
                'pattern': 'Bearish Volume Climax',
                'confidence': 0.85,
                'atr_stop_mult': 3.0,
                'atr_target_mult': 9.0
            })

        if setups:
            return max(setups, key=lambda x: x['confidence'])
        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing with streak-based scaling"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.8  # More aggressive max
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """More aggressive scaling on wins, slower reduction on losses"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            # Increase 0.5% per win (faster scaling)
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * 0.5),
                self.max_risk_pct
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            # Decrease 0.3% per loss (slower reduction)
            self.current_risk_pct = max(
                self.base_risk_pct - (self.loss_streak * 0.3),
                self.min_risk_pct
            )

    def backtest(self):
        """Run selective, high-quality backtest"""
        print(f"{'='*60}")
        print("Running Backtest (Selective Mode)")
        print(f"{'='*60}\n")

        in_position = False
        position = None
        trade_count = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']

                # Calculate current P&L
                if position['direction'] == 'long':
                    pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                else:
                    pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100

                exit_triggered = False
                exit_reason = None

                # Stop loss
                if position['direction'] == 'long' and current_price <= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    current_price = position['stop_loss']
                elif position['direction'] == 'short' and current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    current_price = position['stop_loss']

                # Take profit
                if position['direction'] == 'long' and current_price >= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    current_price = position['take_profit']
                elif position['direction'] == 'short' and current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    current_price = position['take_profit']

                # Time stop (4 hours - longer hold)
                if (row['timestamp'] - position['entry_time']).total_seconds() > 14400:
                    exit_triggered, exit_reason = True, 'Time Stop'

                if exit_triggered:
                    # Final P&L
                    if position['direction'] == 'long':
                        pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100

                    pnl_pct -= (self.fee_rate * 2 * 100)
                    pnl_amount = position['position_size'] * (pnl_pct / 100)
                    self.capital += pnl_amount

                    self.trades.append({
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
                        'risk_pct': position['risk_pct']
                    })

                    self.update_risk_sizing(pnl_amount > 0)
                    trade_count += 1

                    if trade_count % 10 == 0:
                        print(f"Trade {trade_count}: {position['pattern']} {position['direction'].upper()} → "
                              f"{exit_reason} | P&L: {pnl_pct:+.2f}% | Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_high_quality_setup(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    # Use signal-specific ATR multipliers
                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (signal['atr_stop_mult'] * atr)
                        take_profit = entry_price + (signal['atr_target_mult'] * atr)
                    else:
                        stop_loss = entry_price + (signal['atr_stop_mult'] * atr)
                        take_profit = entry_price - (signal['atr_target_mult'] * atr)

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

            # Track equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        return self.analyze_results()

    def analyze_results(self):
        """Analyze with Return/Drawdown focus"""
        print(f"\n{'='*60}")
        print("RESULTS")
        print(f"{'='*60}\n")

        if not self.trades:
            print("❌ No trades generated!")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Core metrics
        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl_amount'] > 0])
        losses = len(df_trades[df_trades['pnl_amount'] <= 0])
        win_rate = (wins / total_trades) * 100

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        total_return = self.capital - self.initial_capital

        # Drawdown
        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = ((df_equity['capital'] - df_equity['peak']) / df_equity['peak']) * 100
        max_dd = df_equity['drawdown'].min()

        # R:R Ratio
        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        # Trade stats
        avg_win = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Print
        print(f"📊 PERFORMANCE")
        print(f"{'-'*60}")
        print(f"Initial Capital:     ${self.initial_capital:,.2f}")
        print(f"Final Capital:       ${self.capital:,.2f}")
        print(f"Total Return:        ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:        {max_dd:.2f}%")
        print(f"")
        print(f"🎯 RETURN/DRAWDOWN:  {rr_ratio:.2f}x")
        print(f"   Target: >8x (total return should be 8x the max drawdown)")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*60}")
        print(f"Total:       {total_trades}")
        print(f"Winners:     {wins} ({win_rate:.1f}%)")
        print(f"Losers:      {losses}")
        print(f"Avg Win:     {avg_win:+.2f}%")
        print(f"Avg Loss:    {avg_loss:+.2f}%")
        print(f"Profit Factor: {profit_factor:.2f}")

        # Direction
        longs = df_trades[df_trades['direction'] == 'long']
        shorts = df_trades[df_trades['direction'] == 'short']
        print(f"\n📊 DIRECTION")
        print(f"{'-'*60}")
        print(f"Longs:   {len(longs):3d} trades | Return: ${longs['pnl_amount'].sum():+,.2f}")
        print(f"Shorts:  {len(shorts):3d} trades | Return: ${shorts['pnl_amount'].sum():+,.2f}")

        # Patterns
        print(f"\n📊 PATTERNS")
        print(f"{'-'*60}")
        for pattern in df_trades['pattern'].unique():
            p_trades = df_trades[df_trades['pattern'] == pattern]
            p_return = p_trades['pnl_amount'].sum()
            p_wr = (len(p_trades[p_trades['pnl_amount'] > 0]) / len(p_trades)) * 100
            p_pf = (p_trades[p_trades['pnl_amount'] > 0]['pnl_amount'].sum() /
                    abs(p_trades[p_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
                    if len(p_trades[p_trades['pnl_amount'] <= 0]) > 0 else float('inf'))
            print(f"{pattern:35s}: {len(p_trades):3d} | WR: {p_wr:5.1f}% | PF: {p_pf:5.2f} | ${p_return:+9.2f}")

        # Best/worst
        best = df_trades.loc[df_trades['pnl_pct'].idxmax()]
        worst = df_trades.loc[df_trades['pnl_pct'].idxmin()]

        print(f"\n🏆 BEST: {best['pattern']} {best['direction'].upper()} | {best['pnl_pct']:+.2f}% | {best['exit_reason']}")
        print(f"📉 WORST: {worst['pattern']} {worst['direction'].upper()} | {worst['pnl_pct']:+.2f}% | {worst['exit_reason']}")

        # Save
        df_trades.to_csv('./strategies/fartcoin-trades-v3.csv', index=False)
        df_equity.to_csv('./strategies/fartcoin-equity-v3.csv', index=False)
        print(f"\n✓ Saved: fartcoin-trades-v3.csv, fartcoin-equity-v3.csv")

        # Verdict
        print(f"\n{'='*60}")
        print("VERDICT")
        print(f"{'='*60}")
        is_profitable = total_return_pct > 0
        has_good_rr = rr_ratio >= 8.0

        print(f"✓ Profitable: {'YES ✅' if is_profitable else 'NO ❌'}")
        print(f"✓ R:R ≥ 8x: {'YES ✅' if has_good_rr else 'NO ❌'} (got {rr_ratio:.2f}x)")

        if is_profitable and has_good_rr:
            print(f"\n🎉 EXCELLENT! Strategy is viable with great risk:reward!")
        elif is_profitable:
            print(f"\n⚠️ Profitable but needs improvement on drawdown control")
        else:
            print(f"\n❌ Not profitable yet - continue optimization")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate
        }


if __name__ == "__main__":
    strategy = OptimizedFartcoinStrategy(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    results = strategy.backtest()
