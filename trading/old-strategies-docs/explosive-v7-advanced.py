#!/usr/bin/env python3
"""
FARTCOIN/USDT Explosive Strategy V7 - Advanced Testing
Focus: Filters, dynamic TP based on volatility, trend strength, market conditions
Goal: Find optimal 8:1 R:R configuration
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ExplosiveV7Advanced:
    """
    Advanced testing with:
    - Stronger trend filters (50, 200 SMA)
    - Dynamic TP based on ATR percentile
    - Volatility regime filters
    - RSI strength filters
    - Volume quality filters
    - Time-of-day filters (optional)
    """

    def __init__(self, data_path: str, initial_capital: float = 10000, config: dict = None):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Configuration
        self.config = config or {}
        self.setup_config()

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

    def setup_config(self):
        """Setup configuration with defaults"""
        defaults = {
            # Entry filters
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'wick_threshold': 0.35,

            # Trend filters
            'require_strong_trend': True,      # Must be below/above BOTH 50 and 200 SMA
            'sma_distance_min': 0.0,           # Min % distance from SMA (0 = any)
            'trend_strength_min': 0,           # Min candles in trend (0 = any)

            # RSI filters
            'rsi_short_max': 55,
            'rsi_short_min': 25,
            'rsi_long_min': 45,
            'rsi_long_max': 75,

            # Volatility filters
            'require_high_vol': True,          # Only trade in high vol regime
            'atr_percentile_min': 50,          # Min ATR percentile (50 = median+)

            # Dynamic TP based on volatility
            'dynamic_tp': True,                # Adjust TP based on ATR
            'tp_atr_low_vol': 12.0,           # TP multiplier when ATR is low
            'tp_atr_high_vol': 18.0,          # TP multiplier when ATR is high
            'tp_atr_threshold': 70,            # ATR percentile for "high vol"

            # Stop loss
            'stop_atr_mult': 3.0,

            # Position sizing
            'base_risk_pct': 1.5,
            'max_risk_pct': 5.0,
            'win_streak_scaling': 0.5,

            # Trade management
            'use_trailing_stop': True,
            'use_partial_exits': True,
            'max_hold_hours': 24,

            # Direction
            'trade_both_directions': True,
            'short_only_in_downtrend': True,  # Only short if below 200 SMA
            'long_only_in_uptrend': True,     # Only long if above 200 SMA
        }

        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value

    def load_data(self):
        """Load and prepare data with advanced indicators"""
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
        self.df['atr_pct'] = (self.df['atr'] / self.df['close']) * 100

        # ATR percentile (for dynamic TP)
        self.df['atr_percentile'] = self.df['atr'].rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) * 100 if len(x) > 0 else 50
        )

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

        # Multiple SMAs for trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()

        # Trend strength (consecutive candles in same direction)
        self.df['uptrend_50'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend_50'] = self.df['close'] < self.df['sma_50']
        self.df['uptrend_200'] = self.df['close'] > self.df['sma_200']
        self.df['downtrend_200'] = self.df['close'] < self.df['sma_200']

        # Strong trend (both SMAs aligned)
        self.df['strong_uptrend'] = self.df['uptrend_50'] & self.df['uptrend_200']
        self.df['strong_downtrend'] = self.df['downtrend_50'] & self.df['downtrend_200']

        # Distance from SMA
        self.df['distance_from_50'] = ((self.df['close'] - self.df['sma_50']) / self.df['sma_50']) * 100
        self.df['distance_from_200'] = ((self.df['close'] - self.df['sma_200']) / self.df['sma_200']) * 100

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # Volatility regime
        self.df['volatility'] = self.df['atr'].rolling(50).mean()
        self.df['high_vol'] = self.df['atr'] > self.df['volatility'] * 1.1

        return self.df

    def detect_pattern(self, idx: int):
        """Detect patterns with advanced filters"""
        if idx < 250:  # Need more history for 200 SMA
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # Check volatility regime
        if cfg['require_high_vol'] and not row['high_vol']:
            return None

        # Check ATR percentile
        if row['atr_percentile'] < cfg['atr_percentile_min']:
            return None

        # === EXPLOSIVE BEARISH BREAKDOWN ===
        if row['is_bearish']:
            # Basic pattern
            if not (row['body_pct'] > cfg['body_threshold'] and
                    row['vol_ratio'] > cfg['volume_multiplier'] and
                    row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
                    row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
                    row['rsi'] < cfg['rsi_short_max'] and
                    row['rsi'] > cfg['rsi_short_min']):
                pass  # Check next pattern
            else:
                # Trend filters
                trend_ok = True

                if cfg['require_strong_trend']:
                    trend_ok = row['strong_downtrend']
                elif cfg['short_only_in_downtrend']:
                    trend_ok = row['downtrend_200']

                # SMA distance filter
                if trend_ok and cfg['sma_distance_min'] > 0:
                    trend_ok = abs(row['distance_from_50']) >= cfg['sma_distance_min']

                if trend_ok:
                    return {
                        'direction': 'short',
                        'pattern': 'Explosive Bearish Breakdown',
                        'atr_percentile': row['atr_percentile']
                    }

        # === EXPLOSIVE BULLISH BREAKOUT ===
        if cfg['trade_both_directions'] and row['is_bullish']:
            # Basic pattern
            if not (row['body_pct'] > cfg['body_threshold'] and
                    row['vol_ratio'] > cfg['volume_multiplier'] and
                    row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
                    row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
                    row['rsi'] > cfg['rsi_long_min'] and
                    row['rsi'] < cfg['rsi_long_max']):
                pass
            else:
                # Trend filters
                trend_ok = True

                if cfg['require_strong_trend']:
                    trend_ok = row['strong_uptrend']
                elif cfg['long_only_in_uptrend']:
                    trend_ok = row['uptrend_200']

                # SMA distance filter
                if trend_ok and cfg['sma_distance_min'] > 0:
                    trend_ok = abs(row['distance_from_50']) >= cfg['sma_distance_min']

                if trend_ok:
                    return {
                        'direction': 'long',
                        'pattern': 'Explosive Bullish Breakout',
                        'atr_percentile': row['atr_percentile']
                    }

        return None

    def calculate_dynamic_tp(self, atr_percentile: float):
        """Calculate TP multiplier based on volatility"""
        if not self.config['dynamic_tp']:
            return self.config.get('tp_atr_high_vol', 15.0)

        # High volatility = wider targets
        if atr_percentile >= self.config['tp_atr_threshold']:
            return self.config['tp_atr_high_vol']
        else:
            return self.config['tp_atr_low_vol']

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0 or stop_distance > 0.1:  # Reject if stop > 10%
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.6
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Aggressive scaling on wins"""
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
        in_position = False
        position = None
        trade_count = 0

        for idx in range(250, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                if position['direction'] == 'long':
                    pnl = current_price - position['entry_price']
                else:
                    pnl = position['entry_price'] - current_price

                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stop
                if self.config['use_trailing_stop'] and not position.get('partial_1_taken'):
                    if r_multiple >= 3.0:
                        position['stop_loss'] = position['entry_price']

                    if r_multiple >= 5.0:
                        atr = row['atr']
                        if position['direction'] == 'long':
                            new_stop = current_price - (2 * atr)
                            position['stop_loss'] = max(position['stop_loss'], new_stop)
                        else:
                            new_stop = current_price + (2 * atr)
                            position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Partial exits
                if self.config['use_partial_exits']:
                    if r_multiple >= 2.0 and not position.get('partial_1_taken'):
                        position['partial_1_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.7
                        partial_pnl = position['position_size'] * 0.3 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                    if r_multiple >= 4.0 and not position.get('partial_2_taken'):
                        position['partial_2_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.3
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
                    exit_triggered, exit_reason = True, f'Time Stop'

                if exit_triggered:
                    if position['direction'] == 'long':
                        final_pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        final_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    remaining_size = position.get('remaining_size', position['position_size'])
                    final_pnl_pct -= (self.fee_rate * 2 * 100)
                    pnl_amount = remaining_size * (final_pnl_pct / 100)
                    self.capital += pnl_amount

                    total_pnl_pct = ((self.capital - position['capital_at_entry']) / position['capital_at_entry']) * 100

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'pnl_pct': total_pnl_pct,
                        'pnl_amount': self.capital - position['capital_at_entry'],
                        'exit_reason': exit_reason,
                        'capital': self.capital
                    })

                    self.update_risk_sizing(self.capital > position['capital_at_entry'])
                    trade_count += 1

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_pattern(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    # Dynamic TP based on volatility
                    tp_mult = self.calculate_dynamic_tp(signal['atr_percentile'])

                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price + (tp_mult * atr)
                    else:
                        stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price - (tp_mult * atr)

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
                            'capital_at_entry': self.capital
                        }
                        in_position = True

            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital
            })

        return self.analyze_results()

    def analyze_results(self):
        """Analyze results"""
        if not self.trades:
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl_amount'] > 0])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = ((df_equity['capital'] - df_equity['peak']) / df_equity['peak']) * 100
        max_dd = df_equity['drawdown'].min()

        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades
        }


def run_comprehensive_tests():
    """Run comprehensive testing suite"""
    print(f"\n{'='*80}")
    print("COMPREHENSIVE STRATEGY TESTING - V7 Advanced")
    print(f"{'='*80}\n")

    test_scenarios = [
        # (Name, config_overrides)

        # === BASELINE ===
        ("Baseline (V6 Best)", {
            'require_strong_trend': False,
            'short_only_in_downtrend': False,
            'long_only_in_uptrend': False,
            'dynamic_tp': False,
            'tp_atr_high_vol': 15.0
        }),

        # === TREND FILTERS ===
        ("Strong Trend Only", {
            'require_strong_trend': True,  # Both 50 and 200 SMA
            'dynamic_tp': False,
            'tp_atr_high_vol': 15.0
        }),

        ("200 SMA Trend Filter", {
            'require_strong_trend': False,
            'short_only_in_downtrend': True,
            'long_only_in_uptrend': True,
            'dynamic_tp': False,
            'tp_atr_high_vol': 15.0
        }),

        ("Trend + Distance 2%", {
            'require_strong_trend': True,
            'sma_distance_min': 2.0,  # Must be 2%+ from SMA
            'dynamic_tp': False,
            'tp_atr_high_vol': 15.0
        }),

        # === DYNAMIC TP TESTS ===
        ("Dynamic TP (12-18x)", {
            'require_strong_trend': False,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 18.0,
            'tp_atr_threshold': 70
        }),

        ("Dynamic TP (10-20x)", {
            'require_strong_trend': False,
            'dynamic_tp': True,
            'tp_atr_low_vol': 10.0,
            'tp_atr_high_vol': 20.0,
            'tp_atr_threshold': 70
        }),

        ("Dynamic TP + Trend", {
            'require_strong_trend': True,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 18.0,
            'tp_atr_threshold': 70
        }),

        # === VOLATILITY FILTERS ===
        ("High Vol Only (70%ile+)", {
            'atr_percentile_min': 70,
            'require_high_vol': True,
            'dynamic_tp': True,
            'tp_atr_low_vol': 15.0,
            'tp_atr_high_vol': 20.0
        }),

        ("Medium Vol (50%ile+)", {
            'atr_percentile_min': 50,
            'require_high_vol': True,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 18.0
        }),

        # === TIGHTER FILTERS ===
        ("Ultra Selective", {
            'body_threshold': 1.5,
            'volume_multiplier': 3.5,
            'require_strong_trend': True,
            'atr_percentile_min': 60,
            'dynamic_tp': True,
            'tp_atr_low_vol': 15.0,
            'tp_atr_high_vol': 22.0
        }),

        # === AGGRESSIVE SIZING ===
        ("Aggressive Sizing", {
            'base_risk_pct': 2.0,
            'max_risk_pct': 7.0,
            'win_streak_scaling': 0.75,
            'require_strong_trend': True,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 18.0
        }),

        # === CONSERVATIVE ===
        ("Conservative", {
            'body_threshold': 1.2,
            'volume_multiplier': 3.0,
            'require_strong_trend': True,
            'base_risk_pct': 1.0,
            'max_risk_pct': 3.0,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 16.0
        }),

        # === COMBINED BEST FEATURES ===
        ("Best Combined", {
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'require_strong_trend': True,
            'sma_distance_min': 1.0,
            'atr_percentile_min': 60,
            'dynamic_tp': True,
            'tp_atr_low_vol': 12.0,
            'tp_atr_high_vol': 20.0,
            'tp_atr_threshold': 65,
            'base_risk_pct': 1.5,
            'max_risk_pct': 5.0
        }),
    ]

    results = []

    for name, config_overrides in test_scenarios:
        print(f"\n{'#'*80}")
        print(f"# {name}")
        print(f"{'#'*80}")

        strategy = ExplosiveV7Advanced(
            data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
            initial_capital=10000,
            config=config_overrides
        )

        strategy.load_data()
        result = strategy.backtest()

        if result:
            result['name'] = name
            results.append(result)

            print(f"Return: {result['total_return_pct']:+.2f}% | "
                  f"DD: {result['max_drawdown']:.2f}% | "
                  f"R:R: {result['rr_ratio']:.2f}x | "
                  f"PF: {result['profit_factor']:.2f} | "
                  f"Trades: {result['total_trades']}")
        else:
            print(f"❌ No trades generated")

    # Summary
    if results:
        print(f"\n{'='*80}")
        print("COMPREHENSIVE RESULTS COMPARISON")
        print(f"{'='*80}\n")
        print(f"{'Scenario':30s} | {'Return':>8s} | {'MaxDD':>7s} | {'R:R':>6s} | {'PF':>5s} | {'WR':>6s} | {'Trades':>6s}")
        print(f"{'-'*80}")

        for r in sorted(results, key=lambda x: x['rr_ratio'], reverse=True):
            print(f"{r['name']:30s} | "
                  f"{r['total_return_pct']:>+7.2f}% | "
                  f"{r['max_drawdown']:>6.2f}% | "
                  f"{r['rr_ratio']:>5.2f}x | "
                  f"{r['profit_factor']:>4.2f} | "
                  f"{r['win_rate']:>5.1f}% | "
                  f"{r['total_trades']:>6.0f}")

        # Best by different metrics
        print(f"\n{'='*80}")
        print("TOP PERFORMERS")
        print(f"{'='*80}")

        best_rr = max(results, key=lambda x: x['rr_ratio'])
        print(f"\n🏆 BEST R:R RATIO: {best_rr['rr_ratio']:.2f}x - {best_rr['name']}")
        print(f"   Return: {best_rr['total_return_pct']:+.2f}% | DD: {best_rr['max_drawdown']:.2f}% | Trades: {best_rr['total_trades']:.0f}")

        best_return = max(results, key=lambda x: x['total_return_pct'])
        print(f"\n💰 BEST RETURN: {best_return['total_return_pct']:+.2f}% - {best_return['name']}")
        print(f"   R:R: {best_return['rr_ratio']:.2f}x | DD: {best_return['max_drawdown']:.2f}% | Trades: {best_return['total_trades']:.0f}")

        best_pf = max(results, key=lambda x: x['profit_factor'])
        print(f"\n📊 BEST PROFIT FACTOR: {best_pf['profit_factor']:.2f} - {best_pf['name']}")
        print(f"   Return: {best_pf['total_return_pct']:+.2f}% | R:R: {best_pf['rr_ratio']:.2f}x | Trades: {best_pf['total_trades']:.0f}")


if __name__ == "__main__":
    run_comprehensive_tests()
