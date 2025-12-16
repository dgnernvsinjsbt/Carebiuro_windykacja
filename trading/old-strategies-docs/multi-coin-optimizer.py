#!/usr/bin/env python3
"""
Multi-Coin Strategy Optimizer
Test V7 "Trend + Distance 2%" winning strategy across all 4 coin pairs.

Goal: Find optimal parameters for each coin individually and validate if the 8.88x R:R
achieved on FARTCOIN is robust across different assets.

Coins: FARTCOIN, PI, MELANIA, PENGU
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class ExplosiveBacktestEngine:
    """
    Backtest engine for explosive pattern strategy
    Optimized for parameter testing across multiple coins
    """

    def __init__(self, data_path: str, initial_capital: float = 10000, config: dict = None):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []
        self.config = config or {}

        # Position sizing
        self.base_risk_pct = self.config.get('base_risk_pct', 1.5)
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

    def load_data(self):
        """Load and prepare data with indicators"""
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

        # ATR percentile
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

        # SMAs for trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()

        # Trend identification
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
        """Detect explosive patterns with filters"""
        if idx < 250:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # Volatility filter
        if cfg.get('require_high_vol', True) and not row['high_vol']:
            return None

        # ATR percentile filter
        if row['atr_percentile'] < cfg.get('atr_percentile_min', 50):
            return None

        # === EXPLOSIVE BEARISH BREAKDOWN ===
        if row['is_bearish']:
            if (row['body_pct'] > cfg.get('body_threshold', 1.0) and
                row['vol_ratio'] > cfg.get('volume_multiplier', 2.5) and
                row['lower_wick'] < row['body'] * cfg.get('wick_threshold', 0.35) and
                row['upper_wick'] < row['body'] * cfg.get('wick_threshold', 0.35) and
                cfg.get('rsi_short_min', 25) < row['rsi'] < cfg.get('rsi_short_max', 55)):

                # Trend filters
                trend_ok = True

                if cfg.get('require_strong_trend', True):
                    trend_ok = row['strong_downtrend']

                # SMA distance filter (THE CRITICAL ONE from V7)
                if trend_ok and cfg.get('sma_distance_min', 0.0) > 0:
                    trend_ok = abs(row['distance_from_50']) >= cfg.get('sma_distance_min', 0.0)

                if trend_ok:
                    return {
                        'direction': 'short',
                        'pattern': 'Explosive Bearish Breakdown',
                        'atr_percentile': row['atr_percentile']
                    }

        # === EXPLOSIVE BULLISH BREAKOUT ===
        if cfg.get('trade_both_directions', True) and row['is_bullish']:
            if (row['body_pct'] > cfg.get('body_threshold', 1.0) and
                row['vol_ratio'] > cfg.get('volume_multiplier', 2.5) and
                row['lower_wick'] < row['body'] * cfg.get('wick_threshold', 0.35) and
                row['upper_wick'] < row['body'] * cfg.get('wick_threshold', 0.35) and
                cfg.get('rsi_long_min', 45) < row['rsi'] < cfg.get('rsi_long_max', 75)):

                # Trend filters
                trend_ok = True

                if cfg.get('require_strong_trend', True):
                    trend_ok = row['strong_uptrend']

                # SMA distance filter
                if trend_ok and cfg.get('sma_distance_min', 0.0) > 0:
                    trend_ok = abs(row['distance_from_50']) >= cfg.get('sma_distance_min', 0.0)

                if trend_ok:
                    return {
                        'direction': 'long',
                        'pattern': 'Explosive Bullish Breakout',
                        'atr_percentile': row['atr_percentile']
                    }

        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0 or stop_distance > 0.1:
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
                self.base_risk_pct + (self.win_streak * self.config.get('win_streak_scaling', 0.5)),
                self.config.get('max_risk_pct', 5.0)
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            self.current_risk_pct = self.base_risk_pct

    def backtest(self):
        """Run backtest"""
        in_position = False
        position = None

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
                if self.config.get('use_trailing_stop', True) and not position.get('partial_1_taken'):
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
                if self.config.get('use_partial_exits', True):
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
                if hours_held >= self.config.get('max_hold_hours', 24):
                    exit_triggered, exit_reason = True, 'Time Stop'

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

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_pattern(idx)

                if signal:
                    entry_price = row['close']
                    atr = row['atr']

                    # TP multiplier (configurable for testing different R:R ratios)
                    tp_mult = self.config.get('tp_atr_mult', 15.0)
                    sl_mult = self.config.get('stop_atr_mult', 3.0)

                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (sl_mult * atr)
                        take_profit = entry_price + (tp_mult * atr)
                    else:
                        stop_loss = entry_price + (sl_mult * atr)
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
        """Analyze backtest results"""
        if not self.trades:
            return {
                'total_return_pct': 0,
                'max_drawdown': 0,
                'rr_ratio': 0,
                'profit_factor': 0,
                'win_rate': 0,
                'total_trades': 0,
                'avg_win': 0,
                'avg_loss': 0
            }

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl_amount'] > 0])
        losses = len(df_trades[df_trades['pnl_amount'] <= 0])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = ((df_equity['capital'] - df_equity['peak']) / df_equity['peak']) * 100
        max_dd = df_equity['drawdown'].min()

        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        avg_win = df_trades[df_trades['pnl_amount'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = df_trades[df_trades['pnl_amount'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }


class MultiCoinOptimizer:
    """
    Optimize strategy parameters across multiple coins
    Smart phased approach to find best config per coin
    """

    def __init__(self):
        self.base_path = Path('/workspaces/Carebiuro_windykacja')
        self.coins = {
            'FARTCOIN': 'fartcoin_usdt_1m_lbank.csv',
            'PI': 'pi_usdt_1m_lbank.csv',
            'MELANIA': 'melania_usdt_1m_lbank.csv',
            'PENGU': 'pengu_usdt_1m_lbank.csv'
        }
        self.results = {}

    def get_v7_baseline_config(self):
        """V7 winning configuration from FARTCOIN"""
        return {
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'wick_threshold': 0.35,
            'require_strong_trend': True,
            'sma_distance_min': 2.0,  # THE CRITICAL FILTER
            'rsi_short_max': 55,
            'rsi_short_min': 25,
            'rsi_long_min': 45,
            'rsi_long_max': 75,
            'require_high_vol': True,
            'atr_percentile_min': 50,
            'tp_atr_mult': 15.0,  # 5:1 R:R
            'stop_atr_mult': 3.0,
            'base_risk_pct': 1.5,
            'max_risk_pct': 5.0,
            'win_streak_scaling': 0.5,
            'use_trailing_stop': True,
            'use_partial_exits': True,
            'max_hold_hours': 24,
            'trade_both_directions': True
        }

    def generate_test_configs(self, coin_name: str):
        """
        Generate smart test configurations
        Phased approach: baseline -> distance -> entry -> R:R
        """
        configs = []
        base = self.get_v7_baseline_config()

        # === PHASE 1: BASELINE TEST ===
        configs.append({
            'name': f'{coin_name}_Baseline_V7',
            'config': base.copy()
        })

        # === PHASE 2: DISTANCE FILTER SWEEP ===
        # Test different SMA distance thresholds (most impactful from V7)
        for distance in [1.5, 2.0, 2.5, 3.0]:
            cfg = base.copy()
            cfg['sma_distance_min'] = distance
            configs.append({
                'name': f'{coin_name}_Distance_{distance}%',
                'config': cfg
            })

        # === PHASE 3: ENTRY THRESHOLD TUNING ===
        # Test different body thresholds
        for body in [0.8, 1.0, 1.2]:
            cfg = base.copy()
            cfg['body_threshold'] = body
            configs.append({
                'name': f'{coin_name}_Body_{body}%',
                'config': cfg
            })

        # Test different volume multipliers
        for vol_mult in [2.0, 2.5, 3.0]:
            cfg = base.copy()
            cfg['volume_multiplier'] = vol_mult
            configs.append({
                'name': f'{coin_name}_Vol_{vol_mult}x',
                'config': cfg
            })

        # === PHASE 4: R:R OPTIMIZATION ===
        # Test different TP multipliers (4:1, 5:1, 6:1, 7:1)
        for tp_mult in [12.0, 15.0, 18.0, 21.0]:
            rr_ratio = tp_mult / 3.0
            cfg = base.copy()
            cfg['tp_atr_mult'] = tp_mult
            configs.append({
                'name': f'{coin_name}_RR_{rr_ratio:.0f}to1',
                'config': cfg
            })

        # === COMBINED OPTIMIZATION ===
        # Best distance + tighter filters
        cfg = base.copy()
        cfg['sma_distance_min'] = 2.5
        cfg['body_threshold'] = 1.2
        cfg['volume_multiplier'] = 3.0
        configs.append({
            'name': f'{coin_name}_Conservative',
            'config': cfg
        })

        # Best distance + wider TP
        cfg = base.copy()
        cfg['sma_distance_min'] = 2.5
        cfg['tp_atr_mult'] = 18.0
        configs.append({
            'name': f'{coin_name}_Aggressive_TP',
            'config': cfg
        })

        # Looser distance + stricter entry
        cfg = base.copy()
        cfg['sma_distance_min'] = 1.5
        cfg['body_threshold'] = 1.2
        cfg['volume_multiplier'] = 3.0
        configs.append({
            'name': f'{coin_name}_Selective',
            'config': cfg
        })

        return configs

    def run_single_test(self, coin_name: str, data_path: str, test_name: str, config: dict):
        """Run a single backtest"""
        try:
            engine = ExplosiveBacktestEngine(
                data_path=str(data_path),
                initial_capital=10000,
                config=config
            )
            engine.load_data()
            result = engine.backtest()

            result['coin'] = coin_name
            result['test_name'] = test_name
            result['config'] = config

            return result
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            return None

    def optimize_coin(self, coin_name: str):
        """Run full optimization for a single coin"""
        print(f"\n{'='*80}")
        print(f"OPTIMIZING: {coin_name}")
        print(f"{'='*80}\n")

        data_path = self.base_path / self.coins[coin_name]
        configs = self.generate_test_configs(coin_name)

        results = []

        for i, test in enumerate(configs, 1):
            print(f"[{i}/{len(configs)}] Testing: {test['name']}...", end=' ')

            result = self.run_single_test(
                coin_name=coin_name,
                data_path=data_path,
                test_name=test['name'],
                config=test['config']
            )

            if result and result['total_trades'] > 0:
                print(f"Return: {result['total_return_pct']:+.2f}% | "
                      f"DD: {result['max_drawdown']:.2f}% | "
                      f"R:R: {result['rr_ratio']:.2f}x | "
                      f"Trades: {result['total_trades']}")
                results.append(result)
            else:
                print(f"No trades")

        self.results[coin_name] = results
        return results

    def save_results(self, coin_name: str, results: list):
        """Save results to CSV"""
        if not results:
            return

        df = pd.DataFrame([{
            'test_name': r['test_name'],
            'total_return_pct': r['total_return_pct'],
            'max_drawdown': r['max_drawdown'],
            'rr_ratio': r['rr_ratio'],
            'profit_factor': r['profit_factor'],
            'win_rate': r['win_rate'],
            'total_trades': r['total_trades'],
            'avg_win': r['avg_win'],
            'avg_loss': r['avg_loss']
        } for r in results])

        output_path = self.base_path / 'strategies' / f'optimization-results-{coin_name.lower()}.csv'
        df.to_csv(output_path, index=False)
        print(f"\nResults saved to: {output_path}")

    def save_best_config(self, coin_name: str, results: list):
        """Save best configuration as JSON"""
        if not results:
            return

        # Find best by R:R ratio
        best = max(results, key=lambda x: x['rr_ratio'])

        output_path = self.base_path / 'strategies' / f'best-config-{coin_name.lower()}.json'

        with open(output_path, 'w') as f:
            json.dump({
                'coin': coin_name,
                'test_name': best['test_name'],
                'metrics': {
                    'total_return_pct': best['total_return_pct'],
                    'max_drawdown': best['max_drawdown'],
                    'rr_ratio': best['rr_ratio'],
                    'profit_factor': best['profit_factor'],
                    'win_rate': best['win_rate'],
                    'total_trades': best['total_trades'],
                    'avg_win': best['avg_win'],
                    'avg_loss': best['avg_loss']
                },
                'config': best['config']
            }, f, indent=2)

        print(f"Best config saved to: {output_path}")

    def generate_summary_report(self):
        """Generate comprehensive multi-coin analysis report"""
        report_lines = []

        report_lines.append("# Multi-Coin Strategy Optimization Results\n")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"\n## Overview\n")
        report_lines.append("Testing V7 'Trend + Distance 2%' strategy across 4 memecoins:\n")
        report_lines.append("- FARTCOIN/USDT (baseline: 8.88x R:R)\n")
        report_lines.append("- PI/USDT\n")
        report_lines.append("- MELANIA/USDT\n")
        report_lines.append("- PENGU/USDT\n")

        report_lines.append(f"\n## Best Configuration Per Coin\n")
        report_lines.append("| Coin | Best R:R | Return | Max DD | Trades | Win Rate | PF | Config |\n")
        report_lines.append("|------|----------|--------|--------|--------|----------|----|---------|\n")

        best_by_coin = {}

        for coin_name, results in self.results.items():
            if not results:
                continue

            best = max(results, key=lambda x: x['rr_ratio'])
            best_by_coin[coin_name] = best

            report_lines.append(
                f"| {coin_name} | "
                f"{best['rr_ratio']:.2f}x | "
                f"{best['total_return_pct']:+.2f}% | "
                f"{best['max_drawdown']:.2f}% | "
                f"{best['total_trades']} | "
                f"{best['win_rate']:.1f}% | "
                f"{best['profit_factor']:.2f} | "
                f"{best['test_name']} |\n"
            )

        # Ranking
        report_lines.append(f"\n## Coin Rankings by R:R Ratio\n")
        sorted_coins = sorted(best_by_coin.items(), key=lambda x: x[1]['rr_ratio'], reverse=True)

        for i, (coin_name, best) in enumerate(sorted_coins, 1):
            report_lines.append(
                f"{i}. **{coin_name}**: {best['rr_ratio']:.2f}x R:R "
                f"({best['total_return_pct']:+.2f}% return, {best['max_drawdown']:.2f}% DD, "
                f"{best['total_trades']} trades)\n"
            )

        # Parameter sensitivity analysis
        report_lines.append(f"\n## Parameter Sensitivity Analysis\n")

        for coin_name in self.coins.keys():
            if coin_name not in self.results or not self.results[coin_name]:
                continue

            report_lines.append(f"\n### {coin_name}\n")

            results = self.results[coin_name]

            # Distance filter impact
            distance_tests = [r for r in results if 'Distance_' in r['test_name']]
            if distance_tests:
                report_lines.append("\n**Distance Filter Impact:**\n")
                for r in sorted(distance_tests, key=lambda x: x['config']['sma_distance_min']):
                    dist = r['config']['sma_distance_min']
                    report_lines.append(
                        f"- {dist}%: {r['rr_ratio']:.2f}x R:R, "
                        f"{r['total_return_pct']:+.2f}% return, "
                        f"{r['total_trades']} trades\n"
                    )

            # R:R ratio impact
            rr_tests = [r for r in results if 'RR_' in r['test_name']]
            if rr_tests:
                report_lines.append("\n**TP Multiplier Impact:**\n")
                for r in sorted(rr_tests, key=lambda x: x['config']['tp_atr_mult']):
                    tp = r['config']['tp_atr_mult']
                    ratio = tp / 3.0
                    report_lines.append(
                        f"- {ratio:.0f}:1 ({tp:.0f}x ATR): {r['rr_ratio']:.2f}x R:R, "
                        f"{r['total_return_pct']:+.2f}% return, "
                        f"{r['total_trades']} trades\n"
                    )

        # Analysis questions
        report_lines.append(f"\n## Analysis & Insights\n")

        # Question 1: Which coin has best R:R?
        if sorted_coins:
            best_coin_name, best_coin_result = sorted_coins[0]
            report_lines.append(f"\n### 1. Which coin has the best R:R potential?\n")
            report_lines.append(
                f"**{best_coin_name}** shows the best risk:reward ratio of **{best_coin_result['rr_ratio']:.2f}x** "
                f"with {best_coin_result['test_name']} configuration.\n"
            )

        # Question 2: Parameter similarity
        report_lines.append(f"\n### 2. Are optimal parameters similar across coins?\n")
        distance_settings = {coin: best['config']['sma_distance_min'] for coin, best in best_by_coin.items()}
        tp_settings = {coin: best['config']['tp_atr_mult'] for coin, best in best_by_coin.items()}

        if len(set(distance_settings.values())) == 1:
            report_lines.append("**YES - Strategy is ROBUST**: All coins share the same optimal distance filter.\n")
        else:
            report_lines.append("**NO - Each coin needs CUSTOM tuning**: Optimal distance filters vary:\n")
            for coin, dist in distance_settings.items():
                report_lines.append(f"- {coin}: {dist}%\n")

        # Question 3: 2% distance filter universality
        report_lines.append(f"\n### 3. Does the 2% distance filter work universally?\n")
        baseline_results = {}
        for coin_name, results in self.results.items():
            baseline = [r for r in results if 'Baseline_V7' in r['test_name']]
            if baseline:
                baseline_results[coin_name] = baseline[0]

        if baseline_results:
            report_lines.append("**Baseline V7 (2% distance) results across all coins:**\n")
            for coin, r in baseline_results.items():
                report_lines.append(
                    f"- {coin}: {r['rr_ratio']:.2f}x R:R, "
                    f"{r['total_return_pct']:+.2f}% return, "
                    f"{r['total_trades']} trades\n"
                )

        # Question 4: Typical R:R range
        report_lines.append(f"\n### 4. What's the typical R:R range we can expect?\n")
        all_rr = [best['rr_ratio'] for best in best_by_coin.values()]
        if all_rr:
            min_rr = min(all_rr)
            max_rr = max(all_rr)
            avg_rr = sum(all_rr) / len(all_rr)
            report_lines.append(
                f"Across all coins, R:R ranges from **{min_rr:.2f}x to {max_rr:.2f}x** "
                f"with an average of **{avg_rr:.2f}x**.\n"
            )

        # Question 5: Portfolio approach
        report_lines.append(f"\n### 5. Should we run a portfolio approach?\n")
        good_coins = [coin for coin, best in best_by_coin.items() if best['rr_ratio'] >= 3.0]
        if len(good_coins) >= 2:
            report_lines.append(
                f"**YES**: {len(good_coins)} coins ({', '.join(good_coins)}) show R:R >= 3.0x. "
                f"Trading multiple coins simultaneously could:\n"
                f"- Diversify risk across different volatility patterns\n"
                f"- Increase trade frequency\n"
                f"- Smooth equity curve\n"
            )
        else:
            report_lines.append(
                f"**NO**: Only {len(good_coins)} coin(s) show R:R >= 3.0x. "
                f"Focus on the single best performer.\n"
            )

        # Question 6: Coins to avoid
        report_lines.append(f"\n### 6. Which coins should be avoided?\n")
        poor_coins = [coin for coin, best in best_by_coin.items() if best['rr_ratio'] < 2.0]
        if poor_coins:
            report_lines.append(f"**Avoid these coins** (R:R < 2.0x):\n")
            for coin in poor_coins:
                best = best_by_coin[coin]
                report_lines.append(
                    f"- {coin}: {best['rr_ratio']:.2f}x R:R, "
                    f"{best['total_return_pct']:+.2f}% return\n"
                )
        else:
            report_lines.append("All coins show acceptable R:R ratios (>= 2.0x).\n")

        # Question 7: Evidence of overfitting
        report_lines.append(f"\n### 7. Is there evidence of overfitting?\n")

        # Check variance in results
        for coin_name, results in self.results.items():
            if len(results) > 3:
                rr_values = [r['rr_ratio'] for r in results if r['total_trades'] >= 10]
                if rr_values:
                    std = np.std(rr_values)
                    mean = np.mean(rr_values)
                    cv = (std / mean) * 100 if mean > 0 else 0

                    if cv > 50:
                        report_lines.append(
                            f"- {coin_name}: **HIGH VARIANCE** (CV={cv:.1f}%) - "
                            f"Results highly sensitive to parameters, possible overfitting.\n"
                        )
                    else:
                        report_lines.append(
                            f"- {coin_name}: Stable results (CV={cv:.1f}%) - "
                            f"Strategy appears robust.\n"
                        )

        # Recommendations
        report_lines.append(f"\n## Recommendations\n")

        if sorted_coins:
            top_coin_name, top_coin = sorted_coins[0]
            report_lines.append(f"\n### Primary Trading Recommendation\n")
            report_lines.append(f"**Trade {top_coin_name}** using the **{top_coin['test_name']}** configuration:\n")
            report_lines.append(f"- Expected R:R: {top_coin['rr_ratio']:.2f}x\n")
            report_lines.append(f"- Win rate: {top_coin['win_rate']:.1f}%\n")
            report_lines.append(f"- Profit factor: {top_coin['profit_factor']:.2f}\n")

            if len(good_coins) > 1:
                report_lines.append(f"\n### Portfolio Approach\n")
                report_lines.append(f"Consider trading {', '.join(good_coins)} simultaneously with:\n")
                report_lines.append(f"- Equal allocation per coin (diversification)\n")
                report_lines.append(f"- Individual configs optimized per coin\n")
                report_lines.append(f"- Total capital split across {len(good_coins)} positions\n")

        # Validation of 8.88x R:R
        report_lines.append(f"\n### Validation of FARTCOIN's 8.88x R:R\n")
        if 'FARTCOIN' in baseline_results:
            fartcoin_baseline = baseline_results['FARTCOIN']
            if fartcoin_baseline['rr_ratio'] >= 7.0:
                report_lines.append(
                    f"**VALIDATED**: FARTCOIN maintains exceptional R:R of {fartcoin_baseline['rr_ratio']:.2f}x "
                    f"with V7 baseline config.\n"
                )
            else:
                report_lines.append(
                    f"**PARTIAL**: FARTCOIN shows {fartcoin_baseline['rr_ratio']:.2f}x R:R "
                    f"(lower than original 8.88x, may be data period dependent).\n"
                )

        # Save report
        report_path = self.base_path / 'strategies' / 'MULTI-COIN-RESULTS.md'
        with open(report_path, 'w') as f:
            f.writelines(report_lines)

        print(f"\n{'='*80}")
        print(f"Comprehensive analysis saved to: {report_path}")
        print(f"{'='*80}\n")

        return report_path

    def run_all(self):
        """Run optimization for all coins"""
        print(f"\n{'#'*80}")
        print("# MULTI-COIN STRATEGY OPTIMIZATION")
        print(f"# Testing V7 across {len(self.coins)} coins")
        print(f"{'#'*80}\n")

        for coin_name in self.coins.keys():
            results = self.optimize_coin(coin_name)
            self.save_results(coin_name, results)
            self.save_best_config(coin_name, results)
            print()

        # Generate comprehensive report
        self.generate_summary_report()

        print("\n✓ Optimization complete!")
        print(f"\nFiles generated:")
        print(f"- optimization-results-[coin].csv (4 files)")
        print(f"- best-config-[coin].json (4 files)")
        print(f"- MULTI-COIN-RESULTS.md (comprehensive analysis)")


if __name__ == "__main__":
    optimizer = MultiCoinOptimizer()
    optimizer.run_all()
