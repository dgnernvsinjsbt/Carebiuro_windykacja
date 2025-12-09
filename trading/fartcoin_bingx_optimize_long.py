#!/usr/bin/env python3
"""
FARTCOIN BingX LONG Strategy Optimization
Priority: Fix low win rate (20%) by widening stops and relaxing filters
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')


class LongOptimizer:
    """Optimize LONG strategy for BingX"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.df = None
        self.df_5min = None
        self.results = []

    def load_data(self):
        """Load and prepare 1-min and 5-min data"""
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        self.df.set_index('timestamp', inplace=True)

        # Calculate 1-min indicators
        self._calculate_1min_indicators()

        # Resample to 5-min
        self._resample_5min()
        self._calculate_5min_indicators()

        # Merge 5-min data back to 1-min
        df_5min_indicators = self.df_5min[['sma50', 'rsi', 'sma_distance', 'uptrend']].copy()
        df_5min_indicators.columns = [f'{col}_5min' for col in df_5min_indicators.columns]
        self.df = self.df.join(df_5min_indicators, how='left')
        self.df.fillna(method='ffill', inplace=True)

    def _calculate_1min_indicators(self):
        """Calculate 1-minute indicators"""
        df = self.df

        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Candle metrics
        df['body'] = abs(df['close'] - df['open'])
        df['body_pct'] = (df['body'] / df['open']) * 100
        df['upper_wick'] = df['high'] - np.maximum(df['open'], df['close'])
        df['lower_wick'] = np.minimum(df['open'], df['close']) - df['low']
        df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / df['body'].replace(0, np.nan)
        df['is_bullish'] = df['close'] > df['open']

    def _resample_5min(self):
        """Resample to 5-minute candles"""
        ohlc = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        self.df_5min = self.df.resample('5T').agg(ohlc).dropna()

    def _calculate_5min_indicators(self):
        """Calculate 5-minute indicators"""
        df = self.df_5min

        # SMA 50
        df['sma50'] = df['close'].rolling(50).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Distance from SMA
        df['sma_distance'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

        # Uptrend
        df['uptrend'] = df['close'] > df['sma50']

    def backtest(self, config):
        """Run backtest with given configuration"""
        capital = 10000
        fee_rate = 0.001
        trades = []
        position = None
        entry_idx = None

        for i in range(100, len(self.df)):
            row = self.df.iloc[i]

            # Skip if not enough 5-min data
            if pd.isna(row['sma50_5min']):
                continue

            # Entry logic
            if position is None and self.check_entry(i, config):
                entry_price = row['close']
                entry_time = row.name
                atr = row['atr']

                stop_loss = entry_price - (config['stop_atr_mult'] * atr)
                take_profit = entry_price + (config['target_atr_mult'] * atr)

                risk_amount = capital * 0.01
                position_size = risk_amount / (entry_price - stop_loss)

                position = {
                    'entry_price': entry_price,
                    'entry_time': entry_time,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size
                }
                entry_idx = i

            # Exit logic
            elif position is not None:
                current_price = row['close']
                exit_reason = None
                exit_price = None

                if current_price <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'
                elif current_price >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'TP'

                if exit_reason:
                    pnl_gross = (exit_price - position['entry_price']) * position['position_size']
                    fees = (position['entry_price'] + exit_price) * position['position_size'] * fee_rate
                    pnl_net = pnl_gross - fees

                    capital += pnl_net

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row.name,
                        'pnl_net': pnl_net,
                        'exit_reason': exit_reason
                    })

                    position = None
                    entry_idx = None

        return capital, trades

    def check_entry(self, i, config):
        """Check if entry conditions met"""
        row = self.df.iloc[i]

        # 1-min filters
        if not row['is_bullish']:
            return False

        if row['body_pct'] < config['body_threshold']:
            return False

        if row['volume_ratio'] < config['volume_multiplier']:
            return False

        if row['wick_ratio'] > config['wick_threshold']:
            return False

        if row['rsi'] < config['rsi_1min_min'] or row['rsi'] > config['rsi_1min_max']:
            return False

        # 5-min confirmation filters
        if pd.isna(row['uptrend_5min']) or not row['uptrend_5min']:
            return False

        if pd.isna(row['rsi_5min']) or row['rsi_5min'] <= config['rsi_5min_min']:
            return False

        if pd.isna(row['sma_distance_5min']) or row['sma_distance_5min'] < config['sma_distance_min']:
            return False

        return True

    def calculate_metrics(self, initial_capital, final_capital, trades):
        """Calculate performance metrics"""
        if len(trades) == 0:
            return None

        trades_df = pd.DataFrame(trades)

        # Returns
        total_return = ((final_capital - initial_capital) / initial_capital) * 100

        # Drawdown
        equity = initial_capital
        equity_curve = [equity]
        for trade in trades:
            equity += trade['pnl_net']
            equity_curve.append(equity)

        equity_series = pd.Series(equity_curve)
        peak = equity_series.cummax()
        drawdown = ((equity_series - peak) / peak) * 100
        max_drawdown = drawdown.min()

        # Win rate
        winners = trades_df[trades_df['pnl_net'] > 0]
        win_rate = len(winners) / len(trades_df) * 100 if len(trades_df) > 0 else 0

        # R:R ratio
        rr_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

        return {
            'total_trades': len(trades_df),
            'winners': len(winners),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'rr_ratio': rr_ratio
        }

    def optimize(self):
        """Run optimization across parameter grid"""
        print("="*80)
        print("FARTCOIN BINGX LONG STRATEGY OPTIMIZATION")
        print("="*80)
        print("\nTesting systematic parameter variations...")

        # Parameter grid (PRIORITIZED based on baseline analysis)
        param_grid = {
            # PRIORITY 1: Stop loss width (80% SL hit rate at 3x)
            'stop_atr_mult': [3.0, 3.5, 4.0, 4.5, 5.0, 6.0],

            # PRIORITY 2: Take profit distance
            'target_atr_mult': [10.0, 12.0, 15.0, 18.0],

            # PRIORITY 3: Explosive body threshold (0.3% of candles at 1.2%)
            'body_threshold': [0.6, 0.8, 1.0, 1.2],

            # PRIORITY 4: Volume multiplier
            'volume_multiplier': [2.0, 2.5, 3.0],

            # PRIORITY 5: 5-min RSI filter (relaxing from 57)
            'rsi_5min_min': [50, 52, 55, 57],

            # PRIORITY 6: 5-min SMA distance (relaxing from 0.6%)
            'sma_distance_min': [0.3, 0.4, 0.5, 0.6],

            # Keep these fixed
            'wick_threshold': [0.35],
            'rsi_1min_min': [45],
            'rsi_1min_max': [75],
        }

        # Generate all combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        configs = [dict(zip(keys, v)) for v in product(*values)]

        print(f"Testing {len(configs)} configurations...\n")

        for i, config in enumerate(configs):
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(configs)} ({(i+1)/len(configs)*100:.1f}%)")

            final_capital, trades = self.backtest(config)
            metrics = self.calculate_metrics(10000, final_capital, trades)

            if metrics is not None and metrics['total_trades'] >= 5:  # Require minimum 5 trades
                result = {**config, **metrics}
                self.results.append(result)

        print(f"\nCompleted {len(configs)} backtests")
        print(f"Found {len(self.results)} viable configurations (≥5 trades)\n")

    def print_top_configs(self, n=10):
        """Print top N configurations"""
        if len(self.results) == 0:
            print("No viable configurations found!")
            return

        df = pd.DataFrame(self.results)

        # Sort by R:R ratio
        df_sorted = df.sort_values('rr_ratio', ascending=False)

        print("="*80)
        print(f"TOP {n} CONFIGURATIONS (by R:R Ratio)")
        print("="*80)

        for i, (idx, row) in enumerate(df_sorted.head(n).iterrows(), 1):
            print(f"\n#{i}: R:R {row['rr_ratio']:.2f}x | Return {row['total_return']:.2f}% | DD {row['max_drawdown']:.2f}%")
            print(f"  Trades: {row['total_trades']:.0f} | WR: {row['win_rate']:.1f}%")
            print(f"  Body: {row['body_threshold']:.2f}% | Vol: {row['volume_multiplier']:.1f}x")
            print(f"  Stop: {row['stop_atr_mult']:.1f}x ATR | Target: {row['target_atr_mult']:.1f}x ATR")
            print(f"  5min: RSI>{row['rsi_5min_min']:.0f} | Dist>{row['sma_distance_min']:.1f}%")

        # Also show best return
        print(f"\n{'='*80}")
        print("BEST RETURN CONFIGURATION")
        print("="*80)
        best_return = df_sorted.nlargest(1, 'total_return').iloc[0]
        print(f"  Return: {best_return['total_return']:.2f}% | DD: {best_return['max_drawdown']:.2f}% | R:R: {best_return['rr_ratio']:.2f}x")
        print(f"  Trades: {best_return['total_trades']:.0f} | WR: {best_return['win_rate']:.1f}%")
        print(f"  Body: {best_return['body_threshold']:.2f}% | Vol: {best_return['volume_multiplier']:.1f}x")
        print(f"  Stop: {best_return['stop_atr_mult']:.1f}x ATR | Target: {best_return['target_atr_mult']:.1f}x ATR")
        print(f"  5min: RSI>{best_return['rsi_5min_min']:.0f} | Dist>{best_return['sma_distance_min']:.1f}%")

    def save_results(self):
        """Save all results to CSV"""
        if len(self.results) == 0:
            return

        df = pd.DataFrame(self.results)
        df = df.sort_values('rr_ratio', ascending=False)
        output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_long_optimization.csv'
        df.to_csv(output_path, index=False)
        print(f"\n✅ Results saved to {output_path}")


if __name__ == "__main__":
    data_path = "/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv"

    optimizer = LongOptimizer(data_path)
    optimizer.load_data()
    optimizer.optimize()
    optimizer.print_top_configs(10)
    optimizer.save_results()
