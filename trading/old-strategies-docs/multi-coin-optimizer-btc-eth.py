#!/usr/bin/env python3
"""
BTC/ETH Multi-Coin Strategy Optimization
Adapted from V7 explosive strategy for major cryptocurrencies

Key Difference from Memecoins:
- BTC/ETH are MUCH LESS volatile (15% range vs 135% for MELANIA)
- May need lower SMA distance filters (1%, 1.5% vs 2%, 3%)
- Expected R:R targets are lower (2-5x realistic vs 8x for memecoins)
- Pattern parameters may need recalibration for lower volatility
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class ExplosiveTester:
    """
    Simplified V7 tester for parameter optimization
    Based on explosive-v7-advanced.py
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
        self.setup_config()

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

    def setup_config(self):
        """Setup configuration with defaults (adapted for BTC/ETH)"""
        defaults = {
            # Entry filters - MAY NEED ADJUSTMENT for lower volatility
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'wick_threshold': 0.35,

            # Trend filters - CRITICAL: Lower SMA distance for BTC/ETH
            'require_strong_trend': True,
            'sma_distance_min': 1.5,  # Default lower than 2% for less volatile assets

            # RSI filters
            'rsi_short_max': 55,
            'rsi_short_min': 25,
            'rsi_long_min': 45,
            'rsi_long_max': 75,

            # Volatility filters
            'require_high_vol': True,
            'atr_percentile_min': 50,

            # Dynamic TP - May need lower targets for BTC/ETH
            'dynamic_tp': False,
            'tp_atr_mult': 15.0,  # 5:1 R:R baseline
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
            'short_only_in_downtrend': True,
            'long_only_in_uptrend': True,
        }

        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value

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

        # Trend detection
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

        # Check volatility regime
        if cfg['require_high_vol'] and not row['high_vol']:
            return None

        # Check ATR percentile
        if row['atr_percentile'] < cfg['atr_percentile_min']:
            return None

        # === EXPLOSIVE BEARISH BREAKDOWN ===
        if row['is_bearish']:
            if (row['body_pct'] > cfg['body_threshold'] and
                row['vol_ratio'] > cfg['volume_multiplier'] and
                row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
                row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
                row['rsi'] < cfg['rsi_short_max'] and
                row['rsi'] > cfg['rsi_short_min']):

                # Trend filters
                trend_ok = True
                if cfg['require_strong_trend']:
                    trend_ok = row['strong_downtrend']
                elif cfg['short_only_in_downtrend']:
                    trend_ok = row['downtrend_200']

                # SMA distance filter (CRITICAL)
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
            if (row['body_pct'] > cfg['body_threshold'] and
                row['vol_ratio'] > cfg['volume_multiplier'] and
                row['lower_wick'] < row['body'] * cfg['wick_threshold'] and
                row['upper_wick'] < row['body'] * cfg['wick_threshold'] and
                row['rsi'] > cfg['rsi_long_min'] and
                row['rsi'] < cfg['rsi_long_max']):

                # Trend filters
                trend_ok = True
                if cfg['require_strong_trend']:
                    trend_ok = row['strong_uptrend']
                elif cfg['long_only_in_uptrend']:
                    trend_ok = row['uptrend_200']

                # SMA distance filter (CRITICAL)
                if trend_ok and cfg['sma_distance_min'] > 0:
                    trend_ok = abs(row['distance_from_50']) >= cfg['sma_distance_min']

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
        """Adjust position sizing based on win/loss streaks"""
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

                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price + (self.config['tp_atr_mult'] * atr)
                    else:
                        stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price - (self.config['tp_atr_mult'] * atr)

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

        avg_win = df_trades[df_trades['pnl_amount'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_pct'].mean()) if total_trades > wins else 0

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


def optimize_coin(coin_name: str, data_path: str):
    """
    Optimize parameters for a single coin
    Adapted for BTC/ETH (lower volatility assets)
    """
    print(f"\n{'='*80}")
    print(f"OPTIMIZING {coin_name.upper()}")
    print(f"{'='*80}\n")

    all_results = []

    # Phase 1: Baseline Test (V7 config adapted for BTC/ETH)
    print(f"\n{'#'*80}")
    print(f"# PHASE 1: Baseline Test (V7 config)")
    print(f"{'#'*80}\n")

    baseline_config = {
        'body_threshold': 1.0,
        'volume_multiplier': 2.5,
        'wick_threshold': 0.35,
        'require_strong_trend': True,
        'sma_distance_min': 2.0,  # V7 baseline
        'tp_atr_mult': 15.0,      # 5:1 R:R
        'stop_atr_mult': 3.0,
        'base_risk_pct': 1.5,
    }

    result = run_test(coin_name, data_path, "Baseline (V7)", baseline_config)
    if result:
        all_results.append(result)

    # Phase 2: Distance Filter Sweep (CRITICAL for BTC/ETH)
    # Testing LOWER values than memecoins due to lower volatility
    print(f"\n{'#'*80}")
    print(f"# PHASE 2: Distance Filter Sweep (Lower values for BTC/ETH)")
    print(f"{'#'*80}\n")

    for distance in [0.5, 1.0, 1.5, 2.0]:
        config = baseline_config.copy()
        config['sma_distance_min'] = distance

        result = run_test(coin_name, data_path, f"Distance {distance}%", config)
        if result:
            all_results.append(result)

    # Find best distance
    if all_results:
        best_distance = max(
            [r for r in all_results if 'Distance' in r['name']],
            key=lambda x: x['rr_ratio'] if x['total_trades'] >= 5 else 0
        )
        optimal_distance = best_distance['config']['sma_distance_min']
        print(f"\n✓ Best distance: {optimal_distance}%")
    else:
        optimal_distance = 1.5
        print(f"\n⚠ No results, using default: {optimal_distance}%")

    # Phase 3: Entry Threshold Tuning
    print(f"\n{'#'*80}")
    print(f"# PHASE 3: Entry Threshold Tuning")
    print(f"{'#'*80}\n")

    base_config = baseline_config.copy()
    base_config['sma_distance_min'] = optimal_distance

    # Test body thresholds (lower for BTC/ETH's smaller candles)
    for body in [0.6, 0.8, 1.0]:
        config = base_config.copy()
        config['body_threshold'] = body

        result = run_test(coin_name, data_path, f"Body {body}%", config)
        if result:
            all_results.append(result)

    # Test volume multipliers
    for vol_mult in [2.0, 2.5, 3.0]:
        config = base_config.copy()
        config['volume_multiplier'] = vol_mult

        result = run_test(coin_name, data_path, f"Vol {vol_mult}x", config)
        if result:
            all_results.append(result)

    # Find best entry config
    if all_results:
        best_entry = max(
            [r for r in all_results if 'Body' in r['name'] or 'Vol' in r['name']],
            key=lambda x: x['rr_ratio'] if x['total_trades'] >= 5 else 0
        )
        optimal_body = best_entry['config'].get('body_threshold', 1.0)
        optimal_vol = best_entry['config'].get('volume_multiplier', 2.5)
        print(f"\n✓ Best entry: Body={optimal_body}%, Vol={optimal_vol}x")
    else:
        optimal_body = 0.8
        optimal_vol = 2.5
        print(f"\n⚠ No results, using defaults: Body={optimal_body}%, Vol={optimal_vol}x")

    # Phase 4: Risk:Reward Optimization
    # Testing LOWER R:R targets for BTC/ETH (less volatile)
    print(f"\n{'#'*80}")
    print(f"# PHASE 4: Risk:Reward Optimization (Lower targets for BTC/ETH)")
    print(f"{'#'*80}\n")

    optimal_config = baseline_config.copy()
    optimal_config['sma_distance_min'] = optimal_distance
    optimal_config['body_threshold'] = optimal_body
    optimal_config['volume_multiplier'] = optimal_vol

    # Test TP multipliers: 9x (3:1), 12x (4:1), 15x (5:1), 18x (6:1)
    for tp_mult in [9.0, 12.0, 15.0, 18.0]:
        config = optimal_config.copy()
        config['tp_atr_mult'] = tp_mult
        rr_target = tp_mult / 3.0  # Since SL is 3x ATR

        result = run_test(coin_name, data_path, f"TP {tp_mult}x ({rr_target:.1f}:1 R:R)", config)
        if result:
            all_results.append(result)

    # Save results
    if all_results:
        # Sort by R:R ratio
        all_results_sorted = sorted(all_results, key=lambda x: x['rr_ratio'], reverse=True)

        # Save CSV
        df_results = pd.DataFrame(all_results_sorted)
        csv_path = f"/workspaces/Carebiuro_windykacja/strategies/optimization-results-{coin_name.lower()}.csv"
        df_results.to_csv(csv_path, index=False)
        print(f"\n✓ Results saved to: {csv_path}")

        # Save best config as JSON
        best_result = all_results_sorted[0]
        best_config_path = f"/workspaces/Carebiuro_windykacja/strategies/best-config-{coin_name.lower()}.json"

        with open(best_config_path, 'w') as f:
            json.dump({
                'coin': coin_name,
                'config': best_result['config'],
                'performance': {
                    'total_return_pct': best_result['total_return_pct'],
                    'max_drawdown': best_result['max_drawdown'],
                    'rr_ratio': best_result['rr_ratio'],
                    'profit_factor': best_result['profit_factor'],
                    'win_rate': best_result['win_rate'],
                    'total_trades': best_result['total_trades']
                }
            }, f, indent=2)

        print(f"✓ Best config saved to: {best_config_path}")

        return all_results_sorted
    else:
        print(f"\n⚠ No valid results for {coin_name}")
        return []


def run_test(coin_name: str, data_path: str, test_name: str, config: dict):
    """Run a single backtest"""
    try:
        strategy = ExplosiveTester(
            data_path=data_path,
            initial_capital=10000,
            config=config
        )

        strategy.load_data()
        result = strategy.backtest()

        if result and result['total_trades'] > 0:
            result['name'] = test_name
            result['coin'] = coin_name
            result['config'] = config

            print(f"{test_name:35s} | "
                  f"Return: {result['total_return_pct']:>+7.2f}% | "
                  f"DD: {result['max_drawdown']:>6.2f}% | "
                  f"R:R: {result['rr_ratio']:>5.2f}x | "
                  f"PF: {result['profit_factor']:>4.2f} | "
                  f"WR: {result['win_rate']:>5.1f}% | "
                  f"Trades: {result['total_trades']:>3.0f}")

            return result
        else:
            print(f"{test_name:35s} | No trades generated")
            return None

    except Exception as e:
        print(f"{test_name:35s} | ERROR: {str(e)}")
        return None


def generate_analysis_report(btc_results: list, eth_results: list):
    """Generate comprehensive analysis markdown report"""

    report = f"""# BTC/ETH Strategy Optimization Results
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Executive Summary

This analysis tests the V7 "Explosive Momentum" strategy (originally optimized for memecoins) on BTC and ETH.

### Key Findings:

**Data Overview:**
- BTC/USDT: 43,202 candles (30 days, 1-minute)
- ETH/USDT: 43,201 candles (30 days, 1-minute)

**Volatility Comparison:**
- BTC: ~$89k-$103k (15% range)
- ETH: ~$3,031-$3,435 (13% range)
- vs MELANIA memecoin: $0.098-$0.23 (135% range!)

**Hypothesis:** Lower volatility assets may need:
1. Lower SMA distance filters (1%, 1.5% vs 2%, 3%)
2. Lower R:R targets per trade (3:1, 4:1 vs 5:1, 6:1)
3. Different entry thresholds (smaller body%)

---

## BTC/USDT Results

"""

    if btc_results:
        best_btc = btc_results[0]

        report += f"""### Best Configuration:
- **Name:** {best_btc['name']}
- **Total Return:** {best_btc['total_return_pct']:+.2f}%
- **Max Drawdown:** {best_btc['max_drawdown']:.2f}%
- **R:R Ratio:** {best_btc['rr_ratio']:.2f}x
- **Profit Factor:** {best_btc['profit_factor']:.2f}
- **Win Rate:** {best_btc['win_rate']:.1f}%
- **Total Trades:** {best_btc['total_trades']:.0f}

### Key Parameters:
```json
{{
  "body_threshold": {best_btc['config']['body_threshold']},
  "volume_multiplier": {best_btc['config']['volume_multiplier']},
  "sma_distance_min": {best_btc['config']['sma_distance_min']},
  "tp_atr_mult": {best_btc['config']['tp_atr_mult']},
  "stop_atr_mult": {best_btc['config']['stop_atr_mult']}
}}
```

### Top 10 Configurations:
| Rank | Name | Return | MaxDD | R:R | PF | WR | Trades |
|------|------|--------|-------|-----|----|----|--------|
"""

        for i, r in enumerate(btc_results[:10], 1):
            report += f"| {i} | {r['name']} | {r['total_return_pct']:+.2f}% | {r['max_drawdown']:.2f}% | {r['rr_ratio']:.2f}x | {r['profit_factor']:.2f} | {r['win_rate']:.1f}% | {r['total_trades']:.0f} |\n"
    else:
        report += "⚠ **No valid results for BTC**\n\n"

    report += "\n---\n\n## ETH/USDT Results\n\n"

    if eth_results:
        best_eth = eth_results[0]

        report += f"""### Best Configuration:
- **Name:** {best_eth['name']}
- **Total Return:** {best_eth['total_return_pct']:+.2f}%
- **Max Drawdown:** {best_eth['max_drawdown']:.2f}%
- **R:R Ratio:** {best_eth['rr_ratio']:.2f}x
- **Profit Factor:** {best_eth['profit_factor']:.2f}
- **Win Rate:** {best_eth['win_rate']:.1f}%
- **Total Trades:** {best_eth['total_trades']:.0f}

### Key Parameters:
```json
{{
  "body_threshold": {best_eth['config']['body_threshold']},
  "volume_multiplier": {best_eth['config']['volume_multiplier']},
  "sma_distance_min": {best_eth['config']['sma_distance_min']},
  "tp_atr_mult": {best_eth['config']['tp_atr_mult']},
  "stop_atr_mult": {best_eth['config']['stop_atr_mult']}
}}
```

### Top 10 Configurations:
| Rank | Name | Return | MaxDD | R:R | PF | WR | Trades |
|------|------|--------|-------|-----|----|----|--------|
"""

        for i, r in enumerate(eth_results[:10], 1):
            report += f"| {i} | {r['name']} | {r['total_return_pct']:+.2f}% | {r['max_drawdown']:.2f}% | {r['rr_ratio']:.2f}x | {r['profit_factor']:.2f} | {r['win_rate']:.1f}% | {r['total_trades']:.0f} |\n"
    else:
        report += "⚠ **No valid results for ETH**\n\n"

    # Comparative Analysis
    report += "\n---\n\n## Comparative Analysis\n\n"

    if btc_results and eth_results:
        best_btc = btc_results[0]
        best_eth = eth_results[0]

        report += f"""### Head-to-Head Comparison:

| Metric | BTC | ETH | Winner |
|--------|-----|-----|--------|
| R:R Ratio | {best_btc['rr_ratio']:.2f}x | {best_eth['rr_ratio']:.2f}x | {'BTC' if best_btc['rr_ratio'] > best_eth['rr_ratio'] else 'ETH'} |
| Total Return | {best_btc['total_return_pct']:+.2f}% | {best_eth['total_return_pct']:+.2f}% | {'BTC' if best_btc['total_return_pct'] > best_eth['total_return_pct'] else 'ETH'} |
| Max Drawdown | {best_btc['max_drawdown']:.2f}% | {best_eth['max_drawdown']:.2f}% | {'BTC' if abs(best_btc['max_drawdown']) < abs(best_eth['max_drawdown']) else 'ETH'} |
| Profit Factor | {best_btc['profit_factor']:.2f} | {best_eth['profit_factor']:.2f} | {'BTC' if best_btc['profit_factor'] > best_eth['profit_factor'] else 'ETH'} |
| Win Rate | {best_btc['win_rate']:.1f}% | {best_eth['win_rate']:.1f}% | {'BTC' if best_btc['win_rate'] > best_eth['win_rate'] else 'ETH'} |
| Total Trades | {best_btc['total_trades']:.0f} | {best_eth['total_trades']:.0f} | {'BTC' if best_btc['total_trades'] > best_eth['total_trades'] else 'ETH'} |

### Parameter Comparison:

| Parameter | BTC Optimal | ETH Optimal | Difference |
|-----------|-------------|-------------|------------|
| SMA Distance | {best_btc['config']['sma_distance_min']}% | {best_eth['config']['sma_distance_min']}% | {abs(best_btc['config']['sma_distance_min'] - best_eth['config']['sma_distance_min']):.2f}% |
| Body Threshold | {best_btc['config']['body_threshold']}% | {best_eth['config']['body_threshold']}% | {abs(best_btc['config']['body_threshold'] - best_eth['config']['body_threshold']):.2f}% |
| Volume Mult | {best_btc['config']['volume_multiplier']}x | {best_eth['config']['volume_multiplier']}x | {abs(best_btc['config']['volume_multiplier'] - best_eth['config']['volume_multiplier']):.2f}x |
| TP Multiplier | {best_btc['config']['tp_atr_mult']}x | {best_eth['config']['tp_atr_mult']}x | {abs(best_btc['config']['tp_atr_mult'] - best_eth['config']['tp_atr_mult']):.2f}x |

"""

    # Analysis Questions
    report += """
---

## Analysis Questions

### 1. Do major cryptos (BTC/ETH) work with the V7 momentum strategy?

"""

    if btc_results and eth_results:
        best_btc_rr = btc_results[0]['rr_ratio']
        best_eth_rr = eth_results[0]['rr_ratio']

        if best_btc_rr > 2.0 or best_eth_rr > 2.0:
            report += f"✅ **YES** - At least one asset achieved R:R > 2.0x (BTC: {best_btc_rr:.2f}x, ETH: {best_eth_rr:.2f}x)\n\n"
        else:
            report += f"⚠️ **MARGINAL** - Both assets achieved R:R < 2.0x (BTC: {best_btc_rr:.2f}x, ETH: {best_eth_rr:.2f}x)\n\n"
    else:
        report += "❌ **NO DATA** - Unable to determine (insufficient results)\n\n"

    report += """### 2. Are optimal parameters VERY different from memecoins?

"""

    if btc_results and eth_results:
        btc_distance = btc_results[0]['config']['sma_distance_min']
        eth_distance = eth_results[0]['config']['sma_distance_min']
        memecoin_distance = 2.0  # V7 baseline

        if abs(btc_distance - memecoin_distance) > 0.5 or abs(eth_distance - memecoin_distance) > 0.5:
            report += f"✅ **YES** - SMA distance differs significantly (Memecoin: {memecoin_distance}%, BTC: {btc_distance}%, ETH: {eth_distance}%)\n\n"
        else:
            report += f"⚠️ **SIMILAR** - Parameters are comparable (Memecoin: {memecoin_distance}%, BTC: {btc_distance}%, ETH: {eth_distance}%)\n\n"
    else:
        report += "❌ **NO DATA** - Unable to determine\n\n"

    report += """### 3. Is volatility too low for 5:1 R:R targets?

"""

    if btc_results and eth_results:
        # Check if TP 15x (5:1 R:R) performed well
        btc_5to1 = [r for r in btc_results if r['config']['tp_atr_mult'] == 15.0]
        eth_5to1 = [r for r in eth_results if r['config']['tp_atr_mult'] == 15.0]

        if btc_5to1 and eth_5to1:
            btc_5to1_rr = btc_5to1[0]['rr_ratio']
            eth_5to1_rr = eth_5to1[0]['rr_ratio']

            best_btc_tp = btc_results[0]['config']['tp_atr_mult']
            best_eth_tp = eth_results[0]['config']['tp_atr_mult']

            if best_btc_tp < 15.0 or best_eth_tp < 15.0:
                report += f"✅ **YES** - Lower R:R targets performed better (BTC best: {best_btc_tp/3:.1f}:1, ETH best: {best_eth_tp/3:.1f}:1)\n\n"
            else:
                report += f"⚠️ **NO** - 5:1 R:R targets are still viable (BTC: {btc_5to1_rr:.2f}x, ETH: {eth_5to1_rr:.2f}x)\n\n"
        else:
            report += "⚠️ **UNCLEAR** - Insufficient data for 5:1 R:R comparison\n\n"
    else:
        report += "❌ **NO DATA** - Unable to determine\n\n"

    report += """### 4. Should we use different strategy entirely for BTC/ETH?

"""

    if btc_results and eth_results:
        best_btc_rr = btc_results[0]['rr_ratio']
        best_eth_rr = eth_results[0]['rr_ratio']

        if best_btc_rr < 1.5 and best_eth_rr < 1.5:
            report += f"✅ **YES** - Poor R:R ratios suggest trend-following or mean-reversion might work better\n\n"
            report += "**Recommendation:** Test alternative strategies:\n"
            report += "- Trend-following with moving average crossovers\n"
            report += "- Mean-reversion in ranging markets\n"
            report += "- Breakout strategies with volume confirmation\n\n"
        else:
            report += f"⚠️ **NO** - Strategy shows promise (BTC: {best_btc_rr:.2f}x, ETH: {best_eth_rr:.2f}x)\n\n"
    else:
        report += "❌ **NO DATA** - Unable to determine\n\n"

    report += """### 5. Which is better: BTC or ETH for this approach?

"""

    if btc_results and eth_results:
        best_btc = btc_results[0]
        best_eth = eth_results[0]

        if best_btc['rr_ratio'] > best_eth['rr_ratio'] * 1.2:
            report += f"✅ **BTC** - Superior R:R ratio ({best_btc['rr_ratio']:.2f}x vs {best_eth['rr_ratio']:.2f}x)\n\n"
        elif best_eth['rr_ratio'] > best_btc['rr_ratio'] * 1.2:
            report += f"✅ **ETH** - Superior R:R ratio ({best_eth['rr_ratio']:.2f}x vs {best_btc['rr_ratio']:.2f}x)\n\n"
        else:
            report += f"⚠️ **SIMILAR** - Both perform comparably (BTC: {best_btc['rr_ratio']:.2f}x, ETH: {best_eth['rr_ratio']:.2f}x)\n\n"
    else:
        report += "❌ **NO DATA** - Unable to determine\n\n"

    # Recommendations
    report += """
---

## Recommendations

"""

    if btc_results and eth_results:
        best_overall = max([btc_results[0], eth_results[0]], key=lambda x: x['rr_ratio'])

        if best_overall['rr_ratio'] > 3.0:
            report += f"""### ✅ RECOMMENDED FOR LIVE TRADING

**Best Asset:** {best_overall['coin']}
**Expected R:R:** {best_overall['rr_ratio']:.2f}x
**Expected Return:** {best_overall['total_return_pct']:+.2f}% per 30 days

**Next Steps:**
1. Forward test with paper trading for 7 days
2. Start with minimum position sizes (0.5-1% risk)
3. Monitor trade quality and adjust if needed
4. Consider adding the second asset if both perform well

"""
        elif best_overall['rr_ratio'] > 2.0:
            report += f"""### ⚠️ MARGINAL - PAPER TRADE FIRST

**Best Asset:** {best_overall['coin']}
**Expected R:R:** {best_overall['rr_ratio']:.2f}x (marginal)
**Expected Return:** {best_overall['total_return_pct']:+.2f}% per 30 days

**Concerns:**
- R:R ratio is below ideal threshold (3.0x+)
- May not compensate for execution slippage
- Consider longer testing period

**Next Steps:**
1. Paper trade for 14-30 days
2. Test on different market conditions
3. Consider alternative strategies if results don't improve

"""
        else:
            report += f"""### ❌ NOT RECOMMENDED - EXPLORE ALTERNATIVES

**Best Asset:** {best_overall['coin']}
**R:R Ratio:** {best_overall['rr_ratio']:.2f}x (too low)
**Return:** {best_overall['total_return_pct']:+.2f}%

**Why This Strategy Doesn't Fit:**
- BTC/ETH volatility is too low for explosive momentum patterns
- 5:1 R:R targets are unrealistic for major cryptos
- Strategy was optimized for high-volatility memecoins

**Alternative Approaches to Consider:**
1. **Trend Following:** Use longer timeframes (4H, 1D) with moving average systems
2. **Mean Reversion:** Trade range-bound movements with Bollinger Bands
3. **Breakout Trading:** Focus on key support/resistance levels with volume
4. **Grid Trading:** Take advantage of BTC/ETH's ranging behavior

"""
    else:
        report += "❌ **INSUFFICIENT DATA** - Unable to provide recommendations\n\n"

    report += """
---

## Conclusion

"""

    if btc_results and eth_results:
        avg_rr = (btc_results[0]['rr_ratio'] + eth_results[0]['rr_ratio']) / 2

        if avg_rr > 3.0:
            report += f"""The V7 explosive momentum strategy **adapts well** to BTC/ETH despite lower volatility.

Key success factors:
- Lower SMA distance filters (recognizing smaller moves)
- Adjusted R:R targets (more realistic for major cryptos)
- Maintained core logic (trend + momentum + volatility filters)

**Verdict:** Strategy is **robust** and can be applied to major cryptocurrencies with parameter tuning.
"""
        elif avg_rr > 2.0:
            report += f"""The V7 explosive momentum strategy shows **marginal promise** on BTC/ETH.

Mixed results suggest:
- Strategy works but not optimally for major cryptos
- Lower volatility limits upside potential
- May work better during high-volatility periods

**Verdict:** Strategy can work but **requires careful monitoring** and may underperform vs memecoins.
"""
        else:
            report += f"""The V7 explosive momentum strategy **does not translate well** to BTC/ETH.

Fundamental mismatch:
- BTC/ETH volatility too low for explosive patterns
- R:R targets unrealistic for 15% price ranges
- Strategy designed for 100%+ volatility assets

**Verdict:** **Focus on memecoins** or develop alternative BTC/ETH strategies (trend-following, mean-reversion).
"""
    else:
        report += "Insufficient data to draw conclusions.\n"

    report += f"""

---

*Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report


def main():
    """Main execution function"""
    print(f"\n{'='*80}")
    print("BTC/ETH MULTI-COIN STRATEGY OPTIMIZATION")
    print("Adapted V7 Explosive Momentum Strategy for Major Cryptocurrencies")
    print(f"{'='*80}\n")

    # Define data paths
    coins = {
        'BTC': '/workspaces/Carebiuro_windykacja/btc_usdt_1m_lbank.csv',
        'ETH': '/workspaces/Carebiuro_windykacja/eth_usdt_1m_lbank.csv',
    }

    all_coin_results = {}

    # Optimize each coin
    for coin_name, data_path in coins.items():
        results = optimize_coin(coin_name, data_path)
        all_coin_results[coin_name] = results

    # Generate comprehensive analysis report
    print(f"\n{'='*80}")
    print("GENERATING ANALYSIS REPORT")
    print(f"{'='*80}\n")

    report = generate_analysis_report(
        all_coin_results.get('BTC', []),
        all_coin_results.get('ETH', [])
    )

    report_path = "/workspaces/Carebiuro_windykacja/strategies/BTC-ETH-RESULTS.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✓ Analysis report saved to: {report_path}")

    # Summary
    print(f"\n{'='*80}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*80}\n")

    print("Files generated:")
    print(f"  - {report_path}")
    for coin_name in coins.keys():
        print(f"  - /workspaces/Carebiuro_windykacja/strategies/optimization-results-{coin_name.lower()}.csv")
        print(f"  - /workspaces/Carebiuro_windykacja/strategies/best-config-{coin_name.lower()}.json")

    # Display best results
    print(f"\n{'='*80}")
    print("BEST RESULTS BY COIN")
    print(f"{'='*80}\n")

    for coin_name, results in all_coin_results.items():
        if results:
            best = results[0]
            print(f"{coin_name}:")
            print(f"  Config: {best['name']}")
            print(f"  R:R: {best['rr_ratio']:.2f}x | Return: {best['total_return_pct']:+.2f}% | DD: {best['max_drawdown']:.2f}%")
            print(f"  Trades: {best['total_trades']:.0f} | WR: {best['win_rate']:.1f}% | PF: {best['profit_factor']:.2f}")
            print()


if __name__ == "__main__":
    main()
