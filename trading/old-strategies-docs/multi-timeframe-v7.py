#!/usr/bin/env python3
"""
FARTCOIN/USDT Multi-Timeframe Approach V7
Combines 1-min explosive patterns with 5-min trend confirmation
Goal: 3-5x Return/Drawdown ratio through higher timeframe alignment
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class MultiTimeframeV7:
    """
    Multi-timeframe strategy:
    - Detects Explosive Bearish Breakdown on 1-min
    - Confirms with 5-min downtrend filter
    - Only trades when both timeframes align
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.df_5min = None
        self.trades = []
        self.equity_curve = []

        # Conservative configuration from V6
        self.config = {
            'body_threshold': 1.2,        # Min body % for entry
            'volume_multiplier': 3.0,     # Min volume surge
            'wick_threshold': 0.35,       # Max wick as % of body
            'rsi_short_max': 55,          # Max RSI for short
            'stop_atr_mult': 3.0,         # Stop loss distance (ATR)
            'target_atr_mult': 12.0,      # Take profit distance (ATR)
            'base_risk_pct': 1.0,         # Base risk per trade
            'max_risk_pct': 3.0,          # Max risk on win streaks
            'win_streak_scaling': 0.5,    # Risk increase per win
            'use_trailing_stop': True,    # Enable trailing stops
            'use_partial_exits': True,    # Enable partial profit taking
            'max_hold_hours': 24,         # Max time in trade
        }

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

        # Pattern detection tracking
        self.total_1min_patterns = 0
        self.patterns_passed_5min_filter = 0

    def load_data(self):
        """Load and prepare 1-min and 5-min data"""
        print(f"\n{'='*70}")
        print(f"MULTI-TIMEFRAME APPROACH V7")
        print(f"{'='*70}")
        print(f"Configuration: Conservative Base")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  Stop Distance:      {self.config['stop_atr_mult']:.1f}x ATR")
        print(f"  Target Distance:    {self.config['target_atr_mult']:.1f}x ATR")
        print(f"  Risk/Reward:        {self.config['target_atr_mult']/self.config['stop_atr_mult']:.1f}:1")
        print(f"  Base Risk:          {self.config['base_risk_pct']:.1f}%")
        print(f"{'='*70}\n")

        # Load 1-min data
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        self.df.set_index('timestamp', inplace=True)

        print(f"Loading 1-minute data...")
        print(f"  Period: {self.df.index.min()} to {self.df.index.max()}")
        print(f"  Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        # Calculate 1-min indicators
        self._calculate_1min_indicators()

        # Resample to 5-min and calculate indicators
        print(f"Resampling to 5-minute timeframe...")
        self._resample_5min()
        self._calculate_5min_indicators()

        print(f"  5-min candles: {len(self.df_5min):,}")
        print(f"  First 5-min candle: {self.df_5min.index[0]}")
        print(f"  Last 5-min candle: {self.df_5min.index[-1]}\n")

        # Merge 5-min data back to 1-min (forward fill)
        self.df = self.df.join(self.df_5min, rsuffix='_5min', how='left')
        self.df.fillna(method='ffill', inplace=True)

        return self.df

    def _calculate_1min_indicators(self):
        """Calculate 1-minute indicators"""
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

        # Volatility
        self.df['volatility'] = self.df['atr'].rolling(50).mean()
        self.df['high_vol'] = self.df['atr'] > self.df['volatility'] * 1.1

    def _resample_5min(self):
        """Resample 1-min data to 5-min candles"""
        # Resample OHLCV
        self.df_5min = pd.DataFrame()
        self.df_5min['open'] = self.df['open'].resample('5T').first()
        self.df_5min['high'] = self.df['high'].resample('5T').max()
        self.df_5min['low'] = self.df['low'].resample('5T').min()
        self.df_5min['close'] = self.df['close'].resample('5T').last()
        self.df_5min['volume'] = self.df['volume'].resample('5T').sum()

        # Drop NaN rows
        self.df_5min.dropna(inplace=True)

    def _calculate_5min_indicators(self):
        """Calculate 5-minute indicators"""
        # 50-period SMA (on 5-min = 250 min = 4+ hours)
        self.df_5min['sma_50'] = self.df_5min['close'].rolling(50).mean()

        # 14-period RSI (on 5-min)
        delta = self.df_5min['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df_5min['rsi'] = 100 - (100 / (1 + rs))

        # 20-period ATR (on 5-min)
        self.df_5min['tr'] = np.maximum(
            self.df_5min['high'] - self.df_5min['low'],
            np.maximum(
                abs(self.df_5min['high'] - self.df_5min['close'].shift(1)),
                abs(self.df_5min['low'] - self.df_5min['close'].shift(1))
            )
        )
        self.df_5min['atr'] = self.df_5min['tr'].rolling(20).mean()

        # Downtrend
        self.df_5min['downtrend_5min'] = self.df_5min['close'] < self.df_5min['sma_50']

        # Last 3 candles showing lower lows (momentum continuing)
        self.df_5min['lower_low_1'] = self.df_5min['low'] < self.df_5min['low'].shift(1)
        self.df_5min['lower_low_2'] = self.df_5min['low'].shift(1) < self.df_5min['low'].shift(2)
        self.df_5min['lower_low_3'] = self.df_5min['low'].shift(2) < self.df_5min['low'].shift(3)
        self.df_5min['momentum_down'] = (
            self.df_5min['lower_low_1'] &
            self.df_5min['lower_low_2'] &
            self.df_5min['lower_low_3']
        )

    def check_5min_filter(self, timestamp):
        """Check if 5-min timeframe confirms downtrend"""
        if timestamp not in self.df.index:
            return False

        row = self.df.loc[timestamp]

        # Check all 5-min conditions exist
        conditions = [
            pd.notna(row.get('close_5min')),
            pd.notna(row.get('sma_50_5min')),
            pd.notna(row.get('rsi_5min')),
        ]

        if not all(conditions):
            return False

        # 5-min downtrend conditions - balanced for 3x R:R target
        close_below_sma = row['close_5min'] < row['sma_50_5min']
        rsi_very_bearish = row['rsi_5min'] < 43  # Selective but not too strict

        # Distance from SMA (at least 0.6% below for quality)
        distance_from_sma = ((row['sma_50_5min'] - row['close_5min']) / row['sma_50_5min']) * 100
        strong_distance = distance_from_sma > 0.6

        # Require all three conditions for high-quality setup
        return close_below_sma and rsi_very_bearish and strong_distance

    def detect_pattern(self, timestamp):
        """Detect Explosive Bearish Breakdown on 1-min with 5-min confirmation"""
        if timestamp not in self.df.index:
            return None

        row = self.df.loc[timestamp]
        cfg = self.config

        # Check if we have enough data
        if pd.isna(row.get('atr')) or pd.isna(row.get('rsi')):
            return None

        # 1-MIN EXPLOSIVE BEARISH BREAKDOWN
        pattern_detected = (
            row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > cfg['body_threshold'] and
            row['vol_ratio'] > cfg['volume_multiplier'] and
            row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
            row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
            row['rsi'] < cfg['rsi_short_max'] and row['rsi'] > 25 and
            row['high_vol']
        )

        if pattern_detected:
            self.total_1min_patterns += 1

            # Check 5-min filter
            if self.check_5min_filter(timestamp):
                self.patterns_passed_5min_filter += 1
                return {
                    'direction': 'short',
                    'pattern': 'Explosive Bearish Breakdown'
                }

        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.4
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Position sizing on win streaks"""
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
        """Run backtest"""
        print(f"Running Backtest...\n")

        in_position = False
        position = None
        trade_count = 0

        timestamps = self.df.index[200:]  # Skip first 200 for indicator warmup

        for timestamp in timestamps:
            row = self.df.loc[timestamp]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (timestamp - position['entry_time']).total_seconds() / 3600

                # Calculate current P&L and R-multiple
                pnl = position['entry_price'] - current_price
                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stop logic
                if self.config['use_trailing_stop'] and not position.get('partial_1_taken'):
                    if r_multiple >= 3.0 and position['stop_loss'] != position['entry_price']:
                        position['stop_loss'] = position['entry_price']

                    if r_multiple >= 5.0:
                        atr = row['atr']
                        new_stop = current_price + (2 * atr)
                        position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Partial profit taking
                if self.config['use_partial_exits']:
                    # 30% at 2R
                    if r_multiple >= 2.0 and not position.get('partial_1_taken'):
                        position['partial_1_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.7
                        partial_pnl = position['position_size'] * 0.3 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                    # 40% at 4R (total 70% closed)
                    if r_multiple >= 4.0 and not position.get('partial_2_taken'):
                        position['partial_2_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.3
                        partial_pnl = position['position_size'] * 0.4 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                # Stop loss
                if current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']

                # Take profit
                if current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']

                # Time stop
                if hours_held >= self.config['max_hold_hours']:
                    exit_triggered, exit_reason = True, f'Time Stop ({self.config["max_hold_hours"]}h)'

                if exit_triggered:
                    # Final P&L on remaining position
                    final_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    # Account for what's still open
                    remaining_size = position.get('remaining_size', position['position_size'])
                    final_pnl_pct -= (self.fee_rate * 2 * 100)  # Fees
                    pnl_amount = remaining_size * (final_pnl_pct / 100)
                    self.capital += pnl_amount

                    # Total P&L for trade (including partials already booked)
                    total_pnl_pct = ((self.capital - position['capital_at_entry']) / position['capital_at_entry']) * 100

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_pct': total_pnl_pct,
                        'pnl_amount': self.capital - position['capital_at_entry'],
                        'exit_reason': exit_reason,
                        'capital': self.capital,
                        'risk_pct': position['risk_pct'],
                        'hours_held': hours_held,
                        'partial_exits': position.get('partial_1_taken', False) or position.get('partial_2_taken', False)
                    })

                    self.update_risk_sizing(self.capital > position['capital_at_entry'])
                    trade_count += 1

                    if trade_count <= 20 or trade_count % 10 == 0:
                        print(f"Trade {trade_count}: {position['pattern'][:20]:20s} {position['direction'].upper():5s} | "
                              f"{exit_reason:15s} | {total_pnl_pct:+6.2f}% | Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_pattern(timestamp)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                    take_profit = entry_price - (self.config['target_atr_mult'] * atr)

                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        position = {
                            'entry_time': timestamp,
                            'entry_price': entry_price,
                            'direction': signal['direction'],
                            'pattern': signal['pattern'],
                            'stop_loss': stop_loss,
                            'initial_stop': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size,
                            'remaining_size': position_size,
                            'risk_pct': self.current_risk_pct,
                            'capital_at_entry': self.capital
                        }
                        in_position = True

            # Track equity
            self.equity_curve.append({
                'timestamp': timestamp,
                'capital': self.capital,
                'in_position': in_position
            })

        print(f"\n✓ Total Trades: {trade_count}\n")
        return self.analyze_results()

    def analyze_results(self):
        """Analyze results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        # Pattern filtering stats
        print(f"📊 PATTERN FILTERING")
        print(f"{'-'*70}")
        print(f"Total 1-min patterns detected:       {self.total_1min_patterns}")
        print(f"Passed 5-min trend filter:           {self.patterns_passed_5min_filter}")
        if self.total_1min_patterns > 0:
            filter_rate = (self.patterns_passed_5min_filter / self.total_1min_patterns) * 100
            print(f"Filter pass rate:                    {filter_rate:.1f}%")
            filtered_out = self.total_1min_patterns - self.patterns_passed_5min_filter
            print(f"Filtered out by 5-min:               {filtered_out}")
        print()

        if not self.trades:
            print("❌ No trades!")
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
        print(f"{'-'*70}")
        print(f"Initial Capital:      ${self.initial_capital:,.2f}")
        print(f"Final Capital:        ${self.capital:,.2f}")
        print(f"Total Return:         ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:         {max_dd:.2f}%")
        print(f"")
        print(f"🎯 RETURN/DRAWDOWN:   {rr_ratio:.2f}x")
        if rr_ratio >= 3.0 and rr_ratio <= 5.0:
            print(f"   ✅ TARGET MET! (Goal: 3-5x)")
        elif rr_ratio > 5.0:
            print(f"   ✅ EXCEEDED TARGET! (Goal: 3-5x)")
        else:
            print(f"   Target: 3-5x")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*70}")
        print(f"Total:         {total_trades}")
        print(f"Winners:       {wins} ({win_rate:.1f}%)")
        print(f"Losers:        {losses}")
        print(f"Avg Win:       {avg_win:+.2f}%")
        print(f"Avg Loss:      {avg_loss:+.2f}%")
        print(f"Profit Factor: {profit_factor:.2f}")

        # Save outputs
        df_trades.to_csv('/workspaces/Carebiuro_windykacja/strategies/multi-timeframe-trades.csv', index=False)
        df_equity.to_csv('/workspaces/Carebiuro_windykacja/strategies/multi-timeframe-equity.csv', index=False)
        print(f"\n✓ Trades saved to: ./strategies/multi-timeframe-trades.csv")
        print(f"✓ Equity saved to: ./strategies/multi-timeframe-equity.csv")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'total_1min_patterns': self.total_1min_patterns,
            'patterns_passed_5min': self.patterns_passed_5min_filter
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTI-TIMEFRAME V7: 1-MIN + 5-MIN CONFIRMATION")
    print("="*70 + "\n")

    strategy = MultiTimeframeV7(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    result = strategy.backtest()

    if result:
        print(f"\n{'='*70}")
        print("COMPARISON TO CONSERVATIVE (V6)")
        print(f"{'='*70}")
        print(f"Conservative V6 Results:")
        print(f"  Return:        +11.41%")
        print(f"  Max Drawdown:  -5.76%")
        print(f"  R:R Ratio:     1.98x")
        print(f"  Total Trades:  20")
        print()
        print(f"Multi-Timeframe V7 Results:")
        print(f"  Return:        {result['total_return_pct']:+.2f}%")
        print(f"  Max Drawdown:  {result['max_drawdown']:.2f}%")
        print(f"  R:R Ratio:     {result['rr_ratio']:.2f}x")
        print(f"  Total Trades:  {result['total_trades']}")
        print()
        print(f"Improvement:")
        if result['max_drawdown'] < 0:
            dd_improvement = ((-5.76 - result['max_drawdown']) / -5.76) * 100
            print(f"  Drawdown:      {dd_improvement:+.1f}%")
        rr_improvement = ((result['rr_ratio'] - 1.98) / 1.98) * 100
        print(f"  R:R Ratio:     {rr_improvement:+.1f}%")
        print(f"  Trades:        {result['total_trades'] - 20:+d}")
        print(f"{'='*70}")
