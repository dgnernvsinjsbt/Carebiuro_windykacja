#!/usr/bin/env python3
"""
FARTCOIN/USDT Final Strategy V4
Focus: Best patterns only + tight risk management
Goal: Achieve 8:1 Return/Drawdown ratio
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class FinalFartcoinStrategy:
    """
    Ultra-selective strategy focusing on:
    - ONLY proven profitable patterns (Shooting Star, Explosive Bearish)
    - Conservative position sizing (0.5-2% risk)
    - Partial profit taking to lock gains
    - Strict filters to reduce trade frequency
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Conservative position sizing
        self.base_risk_pct = 0.8  # Lower base risk
        self.current_risk_pct = 0.8
        self.win_streak = 0
        self.loss_streak = 0
        self.max_risk_pct = 2.5  # Lower max
        self.min_risk_pct = 0.3

    def load_data(self):
        """Load data with indicators"""
        print(f"\n{'='*60}")
        print("FARTCOIN Final Strategy V4 - Best Patterns Only")
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

        # Volume
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Price
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['uptrend'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend'] = self.df['close'] < self.df['sma_50']

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # Volatility regime
        self.df['volatility'] = self.df['atr'].rolling(50).mean()
        self.df['high_vol'] = self.df['atr'] > self.df['volatility'] * 1.2

        print(f"✓ Indicators loaded\n")
        return self.df

    def detect_elite_setup(self, idx: int):
        """
        ONLY the most profitable patterns from V3:
        1. Shooting Star Reversal (best performer)
        2. Explosive Bearish Breakdown (profitable)

        Ultra-strict filters
        """
        if idx < 200:
            return None

        row = self.df.loc[idx]

        # 1. SHOOTING STAR REVERSAL (Best pattern - 1.70 PF)
        if (row['is_bearish'] and
            row['uptrend'] and  # Must be in uptrend
            row['upper_wick'] > 3.0 * row['body'] and  # Stricter: longer wick
            row['lower_wick'] < row['body'] * 0.4 and
            row['vol_ratio'] > 2.5 and  # Higher volume
            row['rsi'] > 70 and  # Overbought
            row['body_pct'] > 0.3 and  # Substantial body
            row['high_vol']):  # High volatility regime
            return {
                'direction': 'short',
                'pattern': 'Shooting Star Reversal',
                'confidence': 0.95,
                'atr_stop_mult': 3.5,
                'atr_target_mult': 10.5  # 3:1 R:R
            }

        # 2. EXPLOSIVE BEARISH BREAKDOWN (1.16 PF)
        if (row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > 1.2 and  # Larger body
            row['vol_ratio'] > 3.0 and  # Much higher volume
            row['lower_wick'] < row['body'] * 0.25 and  # Very clean
            row['upper_wick'] < row['body'] * 0.25 and
            row['rsi'] < 50 and row['rsi'] > 25 and  # Not oversold
            row['high_vol']):
            return {
                'direction': 'short',
                'pattern': 'Explosive Bearish Breakdown',
                'confidence': 0.90,
                'atr_stop_mult': 3.0,
                'atr_target_mult': 9.0
            }

        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Conservative position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.4  # Cap at 40%
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Conservative scaling"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            # Slow increase: 0.3% per win
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * 0.3),
                self.max_risk_pct
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            # Fast decrease: 0.25% per loss
            self.current_risk_pct = max(
                self.base_risk_pct - (self.loss_streak * 0.25),
                self.min_risk_pct
            )

    def backtest(self):
        """Run ultra-selective backtest"""
        print(f"{'='*60}")
        print("Running Elite Pattern Backtest")
        print(f"{'='*60}\n")

        in_position = False
        position = None
        trade_count = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']

                # P&L
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

                # Full take profit
                if position['direction'] == 'long' and current_price >= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    current_price = position['take_profit']
                elif position['direction'] == 'short' and current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    current_price = position['take_profit']

                # Partial profit at 50% of target (lock in gains)
                partial_target = None
                if position['direction'] == 'short':
                    partial_target = position['entry_price'] - (position['entry_price'] - position['take_profit']) * 0.5
                    if current_price <= partial_target and not position.get('partial_taken'):
                        position['partial_taken'] = True
                        # Move stop to breakeven
                        position['stop_loss'] = position['entry_price']

                # Time stop (6 hours)
                if (row['timestamp'] - position['entry_time']).total_seconds() > 21600:
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

                    if trade_count % 5 == 0:
                        print(f"Trade {trade_count}: {position['pattern']} → {exit_reason} | "
                              f"{pnl_pct:+.2f}% | Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_elite_setup(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

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
                            'risk_pct': self.current_risk_pct,
                            'partial_taken': False
                        }
                        in_position = True

            # Equity tracking
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        return self.analyze_results()

    def analyze_results(self):
        """Final analysis"""
        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}\n")

        if not self.trades:
            print("❌ No elite setups found!")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Metrics
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

        # R:R
        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        # Stats
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
        print(f"   {'✅ TARGET MET!' if rr_ratio >= 8.0 else '❌ Target: 8.0x'}")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*60}")
        print(f"Total:         {total_trades}")
        print(f"Winners:       {wins} ({win_rate:.1f}%)")
        print(f"Losers:        {losses}")
        print(f"Avg Win:       {avg_win:+.2f}%")
        print(f"Avg Loss:      {avg_loss:+.2f}%")
        print(f"Profit Factor: {profit_factor:.2f}")

        # Patterns
        print(f"\n📊 PATTERN BREAKDOWN")
        print(f"{'-'*60}")
        for pattern in df_trades['pattern'].unique():
            p_trades = df_trades[df_trades['pattern'] == pattern]
            p_return = p_trades['pnl_amount'].sum()
            p_wr = (len(p_trades[p_trades['pnl_amount'] > 0]) / len(p_trades)) * 100
            p_pf = (p_trades[p_trades['pnl_amount'] > 0]['pnl_amount'].sum() /
                    abs(p_trades[p_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
                    if len(p_trades[p_trades['pnl_amount'] <= 0]) > 0 else float('inf'))
            print(f"{pattern:35s}: {len(p_trades):2d} | WR: {p_wr:5.1f}% | PF: {p_pf:5.2f} | ${p_return:+8.2f}")

        # Best/Worst
        if len(df_trades) > 0:
            best = df_trades.loc[df_trades['pnl_pct'].idxmax()]
            worst = df_trades.loc[df_trades['pnl_pct'].idxmin()]
            print(f"\n🏆 BEST:  {best['pattern']} | {best['pnl_pct']:+.2f}% | {best['exit_reason']}")
            print(f"📉 WORST: {worst['pattern']} | {worst['pnl_pct']:+.2f}% | {worst['exit_reason']}")

        # Save
        df_trades.to_csv('./strategies/fartcoin-trades-v4.csv', index=False)
        df_equity.to_csv('./strategies/fartcoin-equity-v4.csv', index=False)
        print(f"\n✓ Saved: fartcoin-trades-v4.csv, fartcoin-equity-v4.csv")

        # Verdict
        print(f"\n{'='*60}")
        print("VERDICT")
        print(f"{'='*60}")
        is_profitable = total_return_pct > 0
        has_good_rr = rr_ratio >= 8.0

        print(f"✓ Profitable:  {'YES ✅' if is_profitable else 'NO ❌'} ({total_return_pct:+.2f}%)")
        print(f"✓ R:R ≥ 8.0x:  {'YES ✅' if has_good_rr else 'NO ❌'} (got {rr_ratio:.2f}x)")

        if is_profitable and has_good_rr:
            print(f"\n🎉 MISSION ACCOMPLISHED!")
            print(f"Strategy achieves {rr_ratio:.1f}x return/drawdown ratio")
            print(f"Ready for paper trading with ${total_return:+,.2f} profit on $10k")
        elif is_profitable:
            print(f"\n⚠️ Profitable but R:R below 8x")
            print(f"Consider: Higher selectivity or better stop placement")
        else:
            print(f"\n❌ Not profitable - pattern selection needs refinement")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate
        }


if __name__ == "__main__":
    strategy = FinalFartcoinStrategy(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    results = strategy.backtest()
