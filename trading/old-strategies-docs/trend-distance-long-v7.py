#!/usr/bin/env python3
"""
FARTCOIN/USDT Trend + Distance 2% LONG Strategy V7
Implements WINNING configuration for LONG trades (inverted from SHORT)

Goal: Replicate 8.88x R:R success from SHORT version
Expected: +18-25% return, -2 to -3% max DD, 8-12x R:R ratio

Key Filters:
1. Explosive bullish breakout (body > 1.2%, vol > 3x, clean candles)
2. Strong uptrend (price ABOVE both 50 & 200 SMA)
3. 2% distance filter (price must be 2%+ ABOVE 50 SMA)
4. RSI confirmation (48-75 range)

SHORT Baseline: +20.08% return, -2.26% DD = 8.88x R:R with 12 trades
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class TrendDistanceLongV7:
    """
    LONG version of the 8.88x R:R winning strategy.
    Ultra-selective entries using strong uptrend + 2% distance filters.
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # WINNING Configuration (inverted for LONGS)
        self.config = {
            # Entry Pattern
            'body_threshold': 1.2,           # Min body % for explosive breakout
            'volume_multiplier': 3.0,        # Min volume surge (3x average)
            'wick_threshold': 0.35,          # Max wick size (35% of body)

            # CRITICAL FILTERS (The Secret Sauce)
            'require_strong_trend': True,    # Must be ABOVE both 50 AND 200 SMA
            'sma_distance_min': 2.0,         # Price must be 2%+ ABOVE 50 SMA

            # RSI Filters (for LONGS)
            'rsi_long_min': 48,              # Bullish but not overbought
            'rsi_long_max': 75,              # Avoid extreme overbought

            # Risk:Reward (Fixed, not dynamic - this is what worked!)
            'stop_atr_mult': 3.0,            # 3x ATR stop
            'target_atr_mult': 15.0,         # 15x ATR target (5:1 R:R per trade)

            # Position Sizing
            'base_risk_pct': 1.5,            # Starting risk per trade
            'max_risk_pct': 4.0,             # Max risk on win streaks
            'win_streak_scaling': 0.5,       # Risk increase per win

            # Trade Management
            'use_trailing_stop': True,       # Move to BE at 3R, trail at 5R
            'use_partial_exits': True,       # 30% at 2R, 40% at 4R, 30% rides
            'max_hold_hours': 24,            # Max hold time

            # Volatility Filter
            'require_high_vol': True,        # Only trade in high volatility
            'atr_percentile_min': 50,        # ATR must be above median
        }

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

        # Tracking stats
        self.patterns_detected = 0
        self.passed_trend_filter = 0
        self.passed_distance_filter = 0

    def load_data(self):
        """Load and prepare data"""
        print(f"\n{'='*70}")
        print(f"TREND + DISTANCE 2% LONG STRATEGY V7")
        print(f"{'='*70}")
        print(f"Configuration (LONG Inverted from WINNING SHORT):")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  Strong Trend:       {self.config['require_strong_trend']} (ABOVE 50 & 200 SMA)")
        print(f"  Distance Filter:    {self.config['sma_distance_min']:.1f}% ABOVE 50 SMA ⭐")
        print(f"  RSI Range:          {self.config['rsi_long_min']}-{self.config['rsi_long_max']}")
        print(f"  Stop Distance:      {self.config['stop_atr_mult']:.1f}x ATR")
        print(f"  Target Distance:    {self.config['target_atr_mult']:.1f}x ATR (5:1 R:R)")
        print(f"  Trailing Stop:      {self.config['use_trailing_stop']}")
        print(f"  Partial Exits:      {self.config['use_partial_exits']}")
        print(f"{'='*70}\n")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # ATR
        self.df['tr'] = np.maximum(
            self.df['high'] - self.df['low'],
            np.maximum(
                abs(self.df['high'] - self.df['close'].shift(1)),
                abs(self.df['low'] - self.df['close'].shift(1))
            )
        )
        self.df['atr'] = self.df['tr'].rolling(14).mean()

        # ATR percentile for volatility filter
        self.df['atr_50'] = self.df['atr'].rolling(50).mean()
        self.df['atr_percentile'] = self.df['atr'].rolling(100).rank(pct=True) * 100

        # Volume
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Price characteristics
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Trend indicators (CRITICAL for LONG)
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()

        # Strong uptrend: price above BOTH SMAs
        self.df['uptrend'] = (self.df['close'] > self.df['sma_50']) & (self.df['close'] > self.df['sma_200'])

        # SMA slope (trend confirmation)
        self.df['sma_50_slope'] = self.df['sma_50'].diff(5)
        self.df['sma_200_slope'] = self.df['sma_200'].diff(10)
        self.df['smas_sloping_up'] = (self.df['sma_50_slope'] > 0) & (self.df['sma_200_slope'] > 0)

        # Distance from 50 SMA (CRITICAL 2% filter)
        self.df['dist_from_50_pct'] = ((self.df['close'] - self.df['sma_50']) / self.df['sma_50']) * 100

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        return self.df

    def detect_explosive_bullish_breakout(self, idx: int):
        """Detect explosive BULLISH breakout pattern"""
        if idx < 200:
            return False

        row = self.df.loc[idx]
        cfg = self.config

        # EXPLOSIVE BULLISH BREAKOUT
        if not row['is_bullish']:
            return False

        self.patterns_detected += 1

        # Clean candle structure
        if row['lower_wick'] >= row['body'] * cfg['wick_threshold']:
            return False
        if row['upper_wick'] >= row['body'] * cfg['wick_threshold']:
            return False

        # Explosive characteristics
        if row['body_pct'] <= cfg['body_threshold']:
            return False
        if row['vol_ratio'] <= cfg['volume_multiplier']:
            return False

        # Strong uptrend filter (CRITICAL!)
        if cfg['require_strong_trend']:
            if not row['uptrend']:
                return False
            # Optional: require SMAs sloping up for extra confirmation
            if not row['smas_sloping_up']:
                return False

        self.passed_trend_filter += 1

        # 2% distance filter (THE SECRET WEAPON!)
        if row['dist_from_50_pct'] < cfg['sma_distance_min']:
            return False

        self.passed_distance_filter += 1

        # RSI confirmation (bullish but not overbought)
        if row['rsi'] < cfg['rsi_long_min'] or row['rsi'] > cfg['rsi_long_max']:
            return False

        # Volatility filter
        if cfg['require_high_vol']:
            if row['atr_percentile'] < cfg['atr_percentile_min']:
                return False

        return True

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing based on win streaks"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.6
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Increase position sizing on win streaks"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * self.config['win_streak_scaling']),
                self.config['max_risk_pct']
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            self.current_risk_pct = self.base_risk_pct

    def backtest(self):
        """Run backtest with ultra-selective LONG entries"""
        print(f"Running Backtest...\n")

        in_position = False
        position = None
        trade_count = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                # Calculate current P&L and R-multiple
                pnl = current_price - position['entry_price']
                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None

                # 1. Stop loss
                if current_price <= position['stop_loss']:
                    exit_triggered = True
                    exit_reason = 'stop_loss'
                    exit_price = position['stop_loss']

                # 2. Take profit
                elif current_price >= position['take_profit']:
                    exit_triggered = True
                    exit_reason = 'take_profit'
                    exit_price = position['take_profit']

                # 3. Trailing stop (move to BE at 3R, trail at 5R)
                elif self.config['use_trailing_stop'] and r_multiple >= 3.0:
                    # Move stop to breakeven at 3R
                    if position['stop_loss'] < position['entry_price']:
                        position['stop_loss'] = position['entry_price']

                    # Trail stop at 5R
                    if r_multiple >= 5.0:
                        trail_stop = position['entry_price'] + (initial_risk * 4.0)
                        position['stop_loss'] = max(position['stop_loss'], trail_stop)

                # 4. Partial exits
                elif self.config['use_partial_exits'] and not position.get('partial_exit_done', False):
                    # 30% at 2R
                    if r_multiple >= 2.0 and not position.get('exit_2r_done', False):
                        partial_size = position['size'] * 0.3
                        partial_pnl = partial_size * pnl
                        self.capital += partial_pnl * (1 - self.fee_rate)
                        position['size'] -= partial_size
                        position['exit_2r_done'] = True
                        position['partial_profits'] = position.get('partial_profits', 0) + partial_pnl

                    # 40% at 4R
                    if r_multiple >= 4.0 and not position.get('exit_4r_done', False):
                        partial_size = position['original_size'] * 0.4
                        partial_pnl = partial_size * pnl
                        self.capital += partial_pnl * (1 - self.fee_rate)
                        position['size'] -= partial_size
                        position['exit_4r_done'] = True
                        position['partial_profits'] = position.get('partial_profits', 0) + partial_pnl
                        # Only 30% left riding

                # 5. Max hold time
                elif hours_held >= self.config['max_hold_hours']:
                    exit_triggered = True
                    exit_reason = 'max_hold'
                    exit_price = current_price

                # Execute exit
                if exit_triggered:
                    final_pnl = position['size'] * (exit_price - position['entry_price'])
                    final_pnl += position.get('partial_profits', 0)

                    self.capital += final_pnl * (1 - self.fee_rate)

                    trade_won = final_pnl > 0
                    self.update_risk_sizing(trade_won)

                    self.trades.append({
                        'trade_num': trade_count,
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'LONG',
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['initial_stop'],
                        'take_profit': position['take_profit'],
                        'size': position['original_size'],
                        'pnl': final_pnl,
                        'pnl_pct': (final_pnl / (position['original_size'] * position['entry_price'])) * 100,
                        'r_multiple': r_multiple,
                        'exit_reason': exit_reason,
                        'hours_held': hours_held,
                        'capital_after': self.capital,
                        'dist_from_50_pct': position['dist_from_50_pct'],
                        'rsi': position['rsi']
                    })

                    in_position = False
                    position = None

            # Entry logic (LONG only)
            if not in_position:
                if self.detect_explosive_bullish_breakout(idx):
                    entry_price = row['close']
                    atr = row['atr']

                    # Fixed 5:1 R:R targets (what worked best!)
                    stop_loss = entry_price - (atr * self.config['stop_atr_mult'])
                    take_profit = entry_price + (atr * self.config['target_atr_mult'])

                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        trade_count += 1
                        in_position = True

                        position = {
                            'entry_time': row['timestamp'],
                            'entry_price': entry_price,
                            'initial_stop': stop_loss,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'size': position_size,
                            'original_size': position_size,
                            'atr': atr,
                            'dist_from_50_pct': row['dist_from_50_pct'],
                            'rsi': row['rsi'],
                            'partial_profits': 0,
                            'exit_2r_done': False,
                            'exit_4r_done': False
                        }

            # Track equity
            if in_position and position:
                unrealized_pnl = position['size'] * (row['close'] - position['entry_price'])
                unrealized_pnl += position.get('partial_profits', 0)
                current_equity = self.capital + unrealized_pnl * (1 - self.fee_rate)
            else:
                current_equity = self.capital

            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'equity': current_equity,
                'in_position': in_position
            })

        print(f"Backtest Complete!\n")

    def calculate_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            print("No trades executed!")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Basic metrics
        total_trades = len(df_trades)
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] < 0]

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        # Drawdown
        df_equity['peak'] = df_equity['equity'].cummax()
        df_equity['drawdown'] = ((df_equity['equity'] - df_equity['peak']) / df_equity['peak']) * 100
        max_drawdown = df_equity['drawdown'].min()

        # R:R Ratio (THE KEY METRIC!)
        rr_ratio = abs(total_return_pct / max_drawdown) if max_drawdown != 0 else 0

        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

        # Average metrics
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
        avg_r = df_trades['r_multiple'].mean()

        # Annualized return
        days = (df_equity['timestamp'].max() - df_equity['timestamp'].min()).days
        annualized_return = (total_return_pct / days) * 365 if days > 0 else 0

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return_pct': total_return_pct,
            'max_drawdown': max_drawdown,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_r': avg_r,
            'annualized_return': annualized_return,
            'patterns_detected': self.patterns_detected,
            'passed_trend_filter': self.passed_trend_filter,
            'passed_distance_filter': self.passed_distance_filter
        }

    def print_results(self, metrics):
        """Print comprehensive results"""
        print(f"\n{'='*70}")
        print(f"FILTER FUNNEL ANALYSIS")
        print(f"{'='*70}")
        print(f"Explosive Bullish Patterns Detected:   {metrics['patterns_detected']}")
        print(f"Passed Strong Uptrend Filter:          {metrics['passed_trend_filter']} ({metrics['passed_trend_filter']/metrics['patterns_detected']*100:.1f}%)")
        print(f"Passed 2% Distance Filter:             {metrics['passed_distance_filter']} ({metrics['passed_distance_filter']/metrics['patterns_detected']*100:.1f}%)")
        print(f"Final Trades Executed:                 {metrics['total_trades']}")
        print(f"\n{'='*70}")
        print(f"PERFORMANCE METRICS")
        print(f"{'='*70}")
        print(f"Total Return:        {metrics['total_return_pct']:>8.2f}%")
        print(f"Max Drawdown:        {metrics['max_drawdown']:>8.2f}%")
        print(f"R:R Ratio:           {metrics['rr_ratio']:>8.2f}x {'⭐' if metrics['rr_ratio'] >= 8.0 else ''}")
        print(f"Profit Factor:       {metrics['profit_factor']:>8.2f}")
        print(f"Win Rate:            {metrics['win_rate']:>8.1f}%")
        print(f"Avg R-Multiple:      {metrics['avg_r']:>8.2f}R")
        print(f"Annualized Return:   {metrics['annualized_return']:>8.1f}%")
        print(f"\n{'='*70}")
        print(f"COMPARISON TO SHORT BASELINE")
        print(f"{'='*70}")
        short_baseline_rr = 8.88
        print(f"SHORT Baseline R:R:  {short_baseline_rr:>8.2f}x (12 trades, +20.08%, -2.26% DD)")
        print(f"LONG Strategy R:R:   {metrics['rr_ratio']:>8.2f}x ({metrics['total_trades']} trades)")
        print(f"Difference:          {metrics['rr_ratio'] - short_baseline_rr:>+8.2f}x")

        if metrics['rr_ratio'] >= 8.0:
            print(f"\n✅ SUCCESS! Achieved 8+ R:R ratio target!")
        elif metrics['rr_ratio'] >= 6.0:
            print(f"\n🔶 GOOD! Strong R:R ratio (6-8x range)")
        else:
            print(f"\n⚠️  Below target. SHORT version outperformed.")

        print(f"{'='*70}\n")

    def save_results(self):
        """Save trade log and equity curve"""
        if self.trades:
            df_trades = pd.DataFrame(self.trades)
            df_trades.to_csv('./strategies/trend-distance-long-trades.csv', index=False)
            print(f"✅ Saved: ./strategies/trend-distance-long-trades.csv")

        if self.equity_curve:
            df_equity = pd.DataFrame(self.equity_curve)
            df_equity.to_csv('./strategies/trend-distance-long-equity.csv', index=False)
            print(f"✅ Saved: ./strategies/trend-distance-long-equity.csv\n")

    def print_trade_breakdown(self):
        """Print detailed trade-by-trade breakdown"""
        if not self.trades:
            return

        print(f"\n{'='*70}")
        print(f"TRADE-BY-TRADE BREAKDOWN")
        print(f"{'='*70}")
        print(f"{'#':<4} {'Entry':<11} {'Exit':<11} {'Dir':<5} {'R':>6} {'P&L%':>8} {'Reason':<12} {'Hrs':>5}")
        print(f"{'-'*70}")

        for trade in self.trades:
            print(f"{trade['trade_num']:<4} "
                  f"{trade['entry_time'].strftime('%m/%d %H:%M'):<11} "
                  f"{trade['exit_time'].strftime('%m/%d %H:%M'):<11} "
                  f"{trade['direction']:<5} "
                  f"{trade['r_multiple']:>6.2f} "
                  f"{trade['pnl_pct']:>8.2f}% "
                  f"{trade['exit_reason']:<12} "
                  f"{trade['hours_held']:>5.1f}")
        print(f"{'='*70}\n")


def main():
    """Main execution"""
    strategy = TrendDistanceLongV7(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    strategy.backtest()

    metrics = strategy.calculate_metrics()

    if metrics:
        strategy.print_results(metrics)
        strategy.print_trade_breakdown()
        strategy.save_results()

        return metrics
    else:
        print("No trades to analyze!")
        return None


if __name__ == "__main__":
    main()
