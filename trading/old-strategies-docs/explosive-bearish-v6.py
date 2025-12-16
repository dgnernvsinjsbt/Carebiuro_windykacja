#!/usr/bin/env python3
"""
FARTCOIN/USDT Explosive Bearish Breakdown V6
All improvements combined + multiple configurations tested
Goal: 5-8x Return/Drawdown ratio
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ExplosiveBearishV6:
    """
    Enhanced Explosive Bearish Breakdown strategy with:
    - Relaxed filters (more trades)
    - Aggressive position sizing
    - Wider targets + trailing stops
    - Both long and short patterns
    - Partial profit taking
    """

    def __init__(self, data_path: str, initial_capital: float = 10000,
                 config: dict = None):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Default configuration (can be overridden)
        self.config = config or {
            'body_threshold': 1.0,        # Min body % for entry
            'volume_multiplier': 2.5,     # Min volume surge
            'wick_threshold': 0.35,       # Max wick as % of body
            'rsi_short_max': 55,          # Max RSI for short
            'rsi_long_min': 45,           # Min RSI for long
            'stop_atr_mult': 3.0,         # Stop loss distance (ATR)
            'target_atr_mult': 15.0,      # Take profit distance (ATR)
            'base_risk_pct': 1.5,         # Base risk per trade
            'max_risk_pct': 5.0,          # Max risk on win streaks
            'win_streak_scaling': 0.5,    # Risk increase per win
            'use_trailing_stop': True,    # Enable trailing stops
            'use_partial_exits': True,    # Enable partial profit taking
            'max_hold_hours': 24,         # Max time in trade
            'trade_both_directions': True # Long + Short
        }

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

    def load_data(self):
        """Load and prepare data"""
        print(f"\n{'='*70}")
        print(f"EXPLOSIVE BEARISH BREAKDOWN V6")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  Stop Distance:      {self.config['stop_atr_mult']:.1f}x ATR")
        print(f"  Target Distance:    {self.config['target_atr_mult']:.1f}x ATR")
        print(f"  Risk/Reward:        {self.config['target_atr_mult']/self.config['stop_atr_mult']:.1f}:1")
        print(f"  Base Risk:          {self.config['base_risk_pct']:.1f}%")
        print(f"  Max Risk:           {self.config['max_risk_pct']:.1f}%")
        print(f"  Trailing Stop:      {self.config['use_trailing_stop']}")
        print(f"  Partial Exits:      {self.config['use_partial_exits']}")
        print(f"  Both Directions:    {self.config['trade_both_directions']}")
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

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        return self.df

    def detect_pattern(self, idx: int):
        """Detect Explosive Breakdown patterns (bearish + bullish)"""
        if idx < 200:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # EXPLOSIVE BEARISH BREAKDOWN
        if (row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > cfg['body_threshold'] and
            row['vol_ratio'] > cfg['volume_multiplier'] and
            row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
            row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
            row['rsi'] < cfg['rsi_short_max'] and row['rsi'] > 25 and
            row['high_vol']):
            return {
                'direction': 'short',
                'pattern': 'Explosive Bearish Breakdown'
            }

        # EXPLOSIVE BULLISH BREAKOUT (if enabled)
        if cfg['trade_both_directions']:
            if (row['is_bullish'] and
                row['uptrend'] and
                row['body_pct'] > cfg['body_threshold'] and
                row['vol_ratio'] > cfg['volume_multiplier'] and
                row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
                row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
                row['rsi'] > cfg['rsi_long_min'] and row['rsi'] < 75 and
                row['high_vol']):
                return {
                    'direction': 'long',
                    'pattern': 'Explosive Bullish Breakout'
                }

        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.6  # Increased from 0.4
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Aggressive position sizing on win streaks"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            # Aggressive scaling
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * self.config['win_streak_scaling']),
                self.config['max_risk_pct']
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            # Reset to base on first loss
            self.current_risk_pct = self.base_risk_pct

    def backtest(self):
        """Run backtest"""
        print(f"Running Backtest...\n")

        in_position = False
        position = None
        trade_count = 0
        short_trades = 0
        long_trades = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                # Calculate current P&L and R-multiple
                if position['direction'] == 'long':
                    pnl = current_price - position['entry_price']
                else:
                    pnl = position['entry_price'] - current_price

                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stop logic
                if self.config['use_trailing_stop'] and not position.get('partial_1_taken'):
                    if r_multiple >= 3.0 and position['stop_loss'] != position['entry_price']:
                        # Move stop to breakeven at 3R
                        if position['direction'] == 'long':
                            position['stop_loss'] = position['entry_price']
                        else:
                            position['stop_loss'] = position['entry_price']

                    if r_multiple >= 5.0:
                        # Trail at 2R below current price
                        atr = row['atr']
                        if position['direction'] == 'long':
                            new_stop = current_price - (2 * atr)
                            position['stop_loss'] = max(position['stop_loss'], new_stop)
                        else:
                            new_stop = current_price + (2 * atr)
                            position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Partial profit taking
                if self.config['use_partial_exits']:
                    # 30% at 2R
                    if r_multiple >= 2.0 and not position.get('partial_1_taken'):
                        position['partial_1_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.7
                        # Book 30% profit
                        partial_pnl = position['position_size'] * 0.3 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                    # 40% at 4R (total 70% closed)
                    if r_multiple >= 4.0 and not position.get('partial_2_taken'):
                        position['partial_2_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.3
                        # Book another 40% profit
                        partial_pnl = position['position_size'] * 0.4 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                # Stop loss
                if position['direction'] == 'long' and current_price <= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']
                elif position['direction'] == 'short' and current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']

                # Take profit
                if position['direction'] == 'long' and current_price >= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']
                elif position['direction'] == 'short' and current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']

                # Time stop
                if hours_held >= self.config['max_hold_hours']:
                    exit_triggered, exit_reason = True, f'Time Stop ({self.config["max_hold_hours"]}h)'

                if exit_triggered:
                    # Final P&L on remaining position
                    if position['direction'] == 'long':
                        final_pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else:
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
                        'exit_time': row['timestamp'],
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

                    if position['direction'] == 'short':
                        short_trades += 1
                    else:
                        long_trades += 1

                    if trade_count <= 20 or trade_count % 10 == 0:
                        print(f"Trade {trade_count}: {position['pattern'][:20]:20s} {position['direction'].upper():5s} | "
                              f"{exit_reason:15s} | {total_pnl_pct:+6.2f}% | Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_pattern(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price + (self.config['target_atr_mult'] * atr)
                    else:
                        stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price - (self.config['target_atr_mult'] * atr)

                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        position = {
                            'entry_time': row['timestamp'],
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
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        print(f"\n✓ Total Trades: {trade_count} (Shorts: {short_trades}, Longs: {long_trades})\n")
        return self.analyze_results()

    def analyze_results(self):
        """Analyze results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

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
        print(f"   {'✅ EXCELLENT!' if rr_ratio >= 5.0 else '✅ TARGET MET!' if rr_ratio >= 8.0 else f'Target: 8.0x'}")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*70}")
        print(f"Total:         {total_trades}")
        print(f"Winners:       {wins} ({win_rate:.1f}%)")
        print(f"Losers:        {losses}")
        print(f"Avg Win:       {avg_win:+.2f}%")
        print(f"Avg Loss:      {avg_loss:+.2f}%")
        print(f"Profit Factor: {profit_factor:.2f}")

        # Direction
        shorts = df_trades[df_trades['direction'] == 'short']
        longs = df_trades[df_trades['direction'] == 'long']
        print(f"\n📊 DIRECTION")
        print(f"{'-'*70}")
        print(f"Shorts: {len(shorts):3d} | Return: ${shorts['pnl_amount'].sum():+,.2f}")
        if len(longs) > 0:
            print(f"Longs:  {len(longs):3d} | Return: ${longs['pnl_amount'].sum():+,.2f}")

        # Patterns
        print(f"\n📊 PATTERNS")
        print(f"{'-'*70}")
        for pattern in df_trades['pattern'].unique():
            p = df_trades[df_trades['pattern'] == pattern]
            p_wr = (len(p[p['pnl_amount'] > 0]) / len(p)) * 100
            print(f"{pattern:35s}: {len(p):3d} | WR: {p_wr:5.1f}% | ${p['pnl_amount'].sum():+8.2f}")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades
        }


def test_configurations():
    """Test multiple configurations to find optimal settings"""
    print(f"\n{'='*70}")
    print("TESTING MULTIPLE CONFIGURATIONS")
    print(f"{'='*70}\n")

    configs = [
        # Name, body_thresh, vol_mult, stop_mult, target_mult, base_risk, max_risk, both_directions
        ("Conservative", 1.2, 3.0, 3.0, 12.0, 1.0, 3.0, False),
        ("V4 Baseline", 1.2, 3.0, 3.0, 9.0, 0.8, 2.5, False),
        ("Relaxed", 1.0, 2.5, 3.0, 12.0, 1.5, 4.0, False),
        ("Wide Target", 1.0, 2.5, 3.0, 15.0, 1.5, 5.0, False),
        ("Aggressive", 0.8, 2.0, 2.5, 15.0, 2.0, 5.0, False),
        ("Both Directions", 1.0, 2.5, 3.0, 15.0, 1.5, 5.0, True),
        ("Ultra Aggressive", 0.8, 2.0, 2.5, 20.0, 2.0, 6.0, True),
    ]

    results = []

    for name, body, vol, stop, target, base_risk, max_risk, both_dir in configs:
        print(f"\n{'#'*70}")
        print(f"# CONFIG: {name}")
        print(f"{'#'*70}")

        config = {
            'body_threshold': body,
            'volume_multiplier': vol,
            'wick_threshold': 0.35,
            'rsi_short_max': 55,
            'rsi_long_min': 45,
            'stop_atr_mult': stop,
            'target_atr_mult': target,
            'base_risk_pct': base_risk,
            'max_risk_pct': max_risk,
            'win_streak_scaling': 0.5,
            'use_trailing_stop': True,
            'use_partial_exits': True,
            'max_hold_hours': 24,
            'trade_both_directions': both_dir
        }

        strategy = ExplosiveBearishV6(
            data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
            initial_capital=10000,
            config=config
        )

        strategy.load_data()
        result = strategy.backtest()

        if result:
            result['name'] = name
            results.append(result)

    # Summary
    if results:
        print(f"\n{'='*70}")
        print("CONFIGURATION COMPARISON")
        print(f"{'='*70}\n")
        print(f"{'Config':20s} | {'Return':>8s} | {'MaxDD':>7s} | {'R:R':>6s} | {'PF':>5s} | {'WR':>6s} | {'Trades':>6s}")
        print(f"{'-'*70}")

        for r in results:
            print(f"{r['name']:20s} | "
                  f"{r['total_return_pct']:>+7.2f}% | "
                  f"{r['max_drawdown']:>6.2f}% | "
                  f"{r['rr_ratio']:>5.2f}x | "
                  f"{r['profit_factor']:>4.2f} | "
                  f"{r['win_rate']:>5.1f}% | "
                  f"{r['total_trades']:>6.0f}")

        # Find best
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"\n🏆 BEST R:R RATIO: {best['rr_ratio']:.2f}x")
        print(f"   Config: {best['name']}")
        print(f"   Return: {best['total_return_pct']:+.2f}%")
        print(f"   MaxDD: {best['max_drawdown']:.2f}%")
        print(f"   PF: {best['profit_factor']:.2f}")
        print(f"   Trades: {best['total_trades']:.0f}")


if __name__ == "__main__":
    test_configurations()
