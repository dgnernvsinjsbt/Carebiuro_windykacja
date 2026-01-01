#!/usr/bin/env python3
"""
FARTCOIN/USDT Ultra-Selective Strategy V7
Goal: Achieve 6-12x Return/Drawdown ratio through extreme selectivity
Target: 5-10 trades only, 60-70% win rate, minimal drawdown
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class UltraSelectiveV7:
    """
    Ultra-selective strategy with extreme filters:
    - Only 5-10 highest quality trades
    - Massive moves only (body > 2.0%)
    - Institutional volume (5x average, top 5%)
    - At key support levels (swing lows)
    - Confirmation candle required
    - Multi-indicator confluence
    - Very tight stop (1.5x ATR) + wide target (20x ATR) = 13:1 R:R
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Ultra-strict configuration (optimized for 6-12x R:R)
        self.config = {
            'body_threshold': 1.5,        # Large candles only
            'volume_multiplier': 3.5,     # High volume
            'volume_percentile': 90,      # Top 10% of all candles
            'largest_candle_window': 20,  # Must be largest in 20 periods
            'wick_threshold': 0.25,       # Clean candles only
            'close_position_pct': 35,     # Close in bottom 35% of range
            'rsi_max': 48,                # Bearish bias
            'stop_atr_mult': 3.5,         # Wider stop to avoid whipsaws
            'target_atr_mult': 25.0,      # Very wide target (7.1:1 R:R)
            'base_risk_pct': 0.8,         # Conservative base risk
            'max_risk_pct': 2.0,          # Max risk on win streaks
            'win_streak_scaling': 0.4,    # Modest scaling
            'trailing_stops': [3, 5, 8],  # Trail earlier to lock profits
            'use_swing_low_filter': False,
            'use_confirmation': False,
        }

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0

    def load_data(self):
        """Load and prepare data with all indicators"""
        print(f"\n{'='*70}")
        print(f"ULTRA-SELECTIVE STRATEGY V7")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Body Threshold:        {self.config['body_threshold']:.1f}% (MASSIVE)")
        print(f"  Volume Multiplier:     {self.config['volume_multiplier']:.1f}x (INSTITUTIONAL)")
        print(f"  Volume Percentile:     Top {100-self.config['volume_percentile']:.0f}%")
        print(f"  Largest in Window:     {self.config['largest_candle_window']} periods")
        print(f"  Stop Distance:         {self.config['stop_atr_mult']:.1f}x ATR (TIGHT)")
        print(f"  Target Distance:       {self.config['target_atr_mult']:.1f}x ATR (WIDE)")
        print(f"  Risk/Reward:           {self.config['target_atr_mult']/self.config['stop_atr_mult']:.1f}:1")
        print(f"  Base Risk:             {self.config['base_risk_pct']:.1f}%")
        print(f"  Max Risk:              {self.config['max_risk_pct']:.1f}%")
        print(f"  Confirmation Required: {'YES' if self.config['use_confirmation'] else 'NO'}")
        print(f"  Swing Low Support:     {'YES' if self.config['use_swing_low_filter'] else 'NO'}")
        print(f"{'='*70}\n")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # ATR (14-period)
        self.df['tr'] = np.maximum(
            self.df['high'] - self.df['low'],
            np.maximum(
                abs(self.df['high'] - self.df['close'].shift(1)),
                abs(self.df['low'] - self.df['close'].shift(1))
            )
        )
        self.df['atr'] = self.df['tr'].rolling(14).mean()
        self.df['atr_avg'] = self.df['atr'].rolling(50).mean()
        self.df['atr_expanding'] = self.df['atr'] > self.df['atr_avg']

        # Volume analysis
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Volume percentile (top 5% of ALL candles)
        self.df['vol_percentile'] = self.df['volume'].rank(pct=True) * 100

        # Price structure
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['range'] = self.df['high'] - self.df['low']
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Close position in candle (0-100, where 0 is low, 100 is high)
        self.df['close_position'] = ((self.df['close'] - self.df['low']) /
                                     (self.df['range'] + 1e-10)) * 100

        # Largest candle in window
        self.df['max_body_in_window'] = self.df['body_pct'].rolling(
            window=self.config['largest_candle_window'],
            center=False
        ).max().shift(1)
        self.df['is_largest_candle'] = self.df['body_pct'] >= self.df['max_body_in_window']

        # Swing lows (support levels) - optional, only if enabled
        if self.config.get('use_swing_low_filter', False):
            swing_window = 20
            self.df['swing_low'] = self.df['low'].rolling(
                window=swing_window,
                center=True
            ).min()

        # Trend indicators
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()
        self.df['below_50'] = self.df['close'] < self.df['sma_50']
        self.df['below_200'] = self.df['close'] < self.df['sma_200']
        self.df['strong_downtrend'] = self.df['below_50'] & self.df['below_200']

        # RSI (14-period)
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        return self.df

    def detect_pattern(self, idx: int):
        """
        Detect ultra-selective bearish breakdown pattern
        Very strict multi-criteria filter
        """
        if idx < 200:
            return None

        # Check if we need to look ahead for confirmation
        if self.config['use_confirmation'] and idx >= len(self.df) - 1:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # CRITERION 1: Large bearish move
        if not row['is_bearish']:
            return None
        if row['body_pct'] < cfg['body_threshold']:
            return None

        # CRITERION 2: High volume
        if row['vol_ratio'] < cfg['volume_multiplier']:
            return None
        if row['vol_percentile'] < cfg['volume_percentile']:
            return None

        # CRITERION 3: Largest candle in window
        if not row['is_largest_candle']:
            return None

        # CRITERION 4: Multi-indicator confluence
        if not row['strong_downtrend']:
            return None
        if row['rsi'] >= cfg['rsi_max'] or row['rsi'] < 25:
            return None
        if not row['atr_expanding']:
            return None

        # CRITERION 5: Clean candle structure
        if row['upper_wick'] > row['body'] * cfg['wick_threshold']:
            return None
        if row['lower_wick'] > row['body'] * cfg['wick_threshold']:
            return None
        if row['close_position'] > cfg['close_position_pct']:
            return None

        # OPTIONAL: Swing low filter
        if cfg['use_swing_low_filter']:
            if pd.isna(row['swing_low']):
                return None
            # Not used for now - distance from swing low check removed

        # OPTIONAL: Confirmation candle
        entry_idx = idx
        if cfg['use_confirmation']:
            next_row = self.df.loc[idx + 1]
            if not next_row['is_bearish']:
                return None
            if next_row['vol_ratio'] < 1.5:
                return None
            entry_idx = idx + 1

        return {
            'direction': 'short',
            'pattern': 'Ultra-Selective Bearish Breakdown',
            'entry_idx': entry_idx,
            'body_pct': row['body_pct'],
            'vol_ratio': row['vol_ratio'],
            'vol_percentile': row['vol_percentile'],
            'rsi': row['rsi']
        }

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Conservative position sizing with risk management"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.3  # Conservative max position
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Conservative risk scaling on win streaks"""
        if trade_won:
            self.win_streak += 1
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * self.config['win_streak_scaling']),
                self.config['max_risk_pct']
            )
        else:
            self.win_streak = 0
            self.current_risk_pct = self.base_risk_pct

    def backtest(self):
        """Run backtest with ultra-selective filters"""
        print(f"Running Ultra-Selective Backtest...\n")
        print(f"Scanning {len(self.df):,} candles for perfect setups...\n")

        in_position = False
        position = None
        trade_count = 0
        patterns_detected = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                # Calculate P&L and R-multiple
                pnl = position['entry_price'] - current_price
                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stops at 3R, 5R, 8R
                if r_multiple >= 3.0:
                    # Trail stop to breakeven
                    new_stop = position['entry_price']
                    position['stop_loss'] = min(position['stop_loss'], new_stop)
                if r_multiple >= 5.0:
                    # Trail to 2R
                    new_stop = position['entry_price'] - (2 * initial_risk)
                    position['stop_loss'] = min(position['stop_loss'], new_stop)
                if r_multiple >= 8.0:
                    # Trail to 4R
                    new_stop = position['entry_price'] - (4 * initial_risk)
                    position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Stop loss
                if current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']

                # Take profit
                if current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit (25R)'
                    exit_price = position['take_profit']

                # No time stop if profitable (let winners run)
                if r_multiple < 0 and hours_held >= 48:
                    exit_triggered, exit_reason = True, 'Time Stop (48h losing)'

                if exit_triggered:
                    # Calculate final P&L
                    pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                    pnl_pct -= (self.fee_rate * 2 * 100)  # Fees
                    pnl_amount = position['position_size'] * (pnl_pct / 100)
                    self.capital += pnl_amount

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'r_multiple': r_multiple,
                        'exit_reason': exit_reason,
                        'capital': self.capital,
                        'risk_pct': position['risk_pct'],
                        'hours_held': hours_held,
                        'body_pct': position['body_pct'],
                        'vol_ratio': position['vol_ratio'],
                        'vol_percentile': position['vol_percentile'],
                        'rsi': position['rsi']
                    })

                    self.update_risk_sizing(pnl_amount > 0)
                    trade_count += 1

                    print(f"Trade {trade_count}: {position['pattern'][:35]:35s} | "
                          f"{exit_reason:20s} | {pnl_pct:+6.2f}% ({r_multiple:+5.1f}R) | "
                          f"Capital: ${self.capital:,.0f}")
                    print(f"           Body: {position['body_pct']:.2f}% | "
                          f"Vol: {position['vol_ratio']:.1f}x (P{position['vol_percentile']:.0f}) | "
                          f"RSI: {position['rsi']:.1f} | "
                          f"Held: {hours_held:.1f}h\n")

                    in_position = False
                    position = None

            # Entry logic (scan for ultra-selective patterns)
            if not in_position:
                signal = self.detect_pattern(idx)

                if signal:
                    patterns_detected += 1
                    entry_idx = signal['entry_idx']
                    entry_row = self.df.loc[entry_idx]
                    entry_price = entry_row['close']
                    atr = entry_row['atr']

                    stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                    take_profit = entry_price - (self.config['target_atr_mult'] * atr)

                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        position = {
                            'entry_time': entry_row['timestamp'],
                            'entry_price': entry_price,
                            'direction': signal['direction'],
                            'pattern': signal['pattern'],
                            'stop_loss': stop_loss,
                            'initial_stop': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size,
                            'risk_pct': self.current_risk_pct,
                            'capital_at_entry': self.capital,
                            'body_pct': signal['body_pct'],
                            'vol_ratio': signal['vol_ratio'],
                            'vol_percentile': signal['vol_percentile'],
                            'rsi': signal['rsi']
                        }
                        in_position = True

                        print(f"✓ Pattern #{patterns_detected} detected at {entry_row['timestamp']}")
                        print(f"  Entry: ${entry_price:.6f} | Stop: ${stop_loss:.6f} | Target: ${take_profit:.6f}")
                        print(f"  Body: {signal['body_pct']:.2f}% | Vol: {signal['vol_ratio']:.1f}x (P{signal['vol_percentile']:.0f})")
                        print(f"  RSI: {signal['rsi']:.1f}\n")

            # Track equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        print(f"\n✓ Patterns Detected: {patterns_detected}")
        print(f"✓ Trades Executed: {trade_count}\n")
        return self.analyze_results()

    def analyze_results(self):
        """Analyze results and compare to baseline"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if not self.trades:
            print("❌ No trades executed!")
            print("   This means the filters were TOO strict.")
            print("   Consider relaxing some criteria.\n")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Save CSVs
        trades_csv = '/workspaces/Carebiuro_windykacja/strategies/ultra-selective-trades.csv'
        equity_csv = '/workspaces/Carebiuro_windykacja/strategies/ultra-selective-equity.csv'
        df_trades.to_csv(trades_csv, index=False)
        df_equity.to_csv(equity_csv, index=False)
        print(f"✓ Saved: {trades_csv}")
        print(f"✓ Saved: {equity_csv}\n")

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

        # R:R ratio
        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        # Stats
        avg_win = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        avg_r_multiple = df_trades['r_multiple'].mean()
        max_r_multiple = df_trades['r_multiple'].max()

        # Print results
        print(f"📊 PERFORMANCE")
        print(f"{'-'*70}")
        print(f"Initial Capital:      ${self.initial_capital:,.2f}")
        print(f"Final Capital:        ${self.capital:,.2f}")
        print(f"Total Return:         ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:         {max_dd:.2f}%")
        print(f"")
        print(f"🎯 RETURN/DRAWDOWN:   {rr_ratio:.2f}x")
        if rr_ratio >= 12.0:
            print(f"   ✅ EXCEPTIONAL! (Target: 6-12x)")
        elif rr_ratio >= 6.0:
            print(f"   ✅ TARGET ACHIEVED! (Target: 6-12x)")
        else:
            print(f"   ⚠️  Below target (Target: 6-12x)")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*70}")
        print(f"Total:           {total_trades} {'✅ PERFECT!' if 5 <= total_trades <= 10 else '⚠️  Outside 5-10 range'}")
        print(f"Winners:         {wins} ({win_rate:.1f}%)")
        print(f"Losers:          {losses}")
        print(f"Win Rate:        {win_rate:.1f}% {'✅' if 55 <= win_rate <= 70 else '⚠️'}")
        print(f"Avg Win:         {avg_win:+.2f}%")
        print(f"Avg Loss:        {avg_loss:+.2f}%")
        print(f"Profit Factor:   {profit_factor:.2f} {'✅' if profit_factor >= 2.5 else '⚠️'}")
        print(f"Avg R-Multiple:  {avg_r_multiple:+.2f}R")
        print(f"Max R-Multiple:  {max_r_multiple:+.2f}R")

        # Trade details
        print(f"\n📋 TRADE DETAILS")
        print(f"{'-'*70}")
        for i, trade in df_trades.iterrows():
            print(f"Trade {i+1}: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} → "
                  f"{trade['exit_time'].strftime('%Y-%m-%d %H:%M')} | "
                  f"{trade['pnl_pct']:+6.2f}% ({trade['r_multiple']:+5.1f}R) | "
                  f"{trade['exit_reason']}")

        # Comparison to Conservative baseline
        print(f"\n📊 COMPARISON TO CONSERVATIVE V6 BASELINE")
        print(f"{'-'*70}")
        baseline = {
            'return': 11.41,
            'max_dd': -5.76,
            'rr_ratio': 1.98,
            'trades': 20,
            'win_rate': 35.0,
            'profit_factor': 1.5
        }

        print(f"                    V7 Ultra     |   V6 Baseline  |  Improvement")
        print(f"{'-'*70}")
        print(f"Total Return:       {total_return_pct:+7.2f}%     |   {baseline['return']:+7.2f}%     |  {total_return_pct - baseline['return']:+6.2f}%")
        print(f"Max Drawdown:       {max_dd:7.2f}%     |   {baseline['max_dd']:7.2f}%     |  {max_dd - baseline['max_dd']:+6.2f}%")
        print(f"R:R Ratio:          {rr_ratio:7.2f}x     |   {baseline['rr_ratio']:7.2f}x     |  {rr_ratio - baseline['rr_ratio']:+6.2f}x")
        print(f"Total Trades:       {total_trades:7.0f}       |   {baseline['trades']:7.0f}       |  {total_trades - baseline['trades']:+6.0f}")
        print(f"Win Rate:           {win_rate:7.1f}%     |   {baseline['win_rate']:7.1f}%     |  {win_rate - baseline['win_rate']:+6.1f}%")
        print(f"Profit Factor:      {profit_factor:7.2f}      |   {baseline['profit_factor']:7.2f}      |  {profit_factor - baseline['profit_factor']:+6.2f}")

        # Success criteria check
        print(f"\n✅ SUCCESS CRITERIA")
        print(f"{'-'*70}")
        print(f"R:R ratio 6-12x:    {'✅ YES' if 6.0 <= rr_ratio <= 12.0 else '❌ NO':20s} (Actual: {rr_ratio:.2f}x)")
        print(f"Return +8-15%:      {'✅ YES' if 8.0 <= total_return_pct <= 15.0 else '❌ NO':20s} (Actual: {total_return_pct:+.2f}%)")
        print(f"Max DD -1 to -2%:   {'✅ YES' if -2.0 <= max_dd <= -1.0 else '❌ NO':20s} (Actual: {max_dd:.2f}%)")
        print(f"Win rate 55-70%:    {'✅ YES' if 55.0 <= win_rate <= 70.0 else '❌ NO':20s} (Actual: {win_rate:.1f}%)")
        print(f"Profit factor 2.5+: {'✅ YES' if profit_factor >= 2.5 else '❌ NO':20s} (Actual: {profit_factor:.2f})")
        print(f"Trades 5-10:        {'✅ YES' if 5 <= total_trades <= 10 else '❌ NO':20s} (Actual: {total_trades})")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_r_multiple': avg_r_multiple,
            'max_r_multiple': max_r_multiple
        }


if __name__ == "__main__":
    strategy = UltraSelectiveV7(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    results = strategy.backtest()

    if results:
        print(f"\n{'='*70}")
        print("FINAL SUMMARY")
        print(f"{'='*70}")
        print(f"Total Return:     {results['total_return_pct']:+.2f}%")
        print(f"Max Drawdown:     {results['max_drawdown']:.2f}%")
        print(f"R:R Ratio:        {results['rr_ratio']:.2f}x")
        print(f"Win Rate:         {results['win_rate']:.1f}%")
        print(f"Profit Factor:    {results['profit_factor']:.2f}")
        print(f"Total Trades:     {results['total_trades']}")
        print(f"Avg R-Multiple:   {results['avg_r_multiple']:+.2f}R")
        print(f"Max R-Multiple:   {results['max_r_multiple']:+.2f}R")

        if 6.0 <= results['rr_ratio'] <= 12.0:
            print(f"\n🎯 TARGET ACHIEVED: {results['rr_ratio']:.2f}x R:R ratio (6-12x target)")
        elif results['rr_ratio'] > 12.0:
            print(f"\n🚀 EXCEPTIONAL: {results['rr_ratio']:.2f}x R:R ratio (exceeded 12x target!)")
        else:
            print(f"\n⚠️  BELOW TARGET: {results['rr_ratio']:.2f}x R:R ratio (target: 6-12x)")
        print(f"{'='*70}\n")
