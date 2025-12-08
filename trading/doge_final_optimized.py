"""
DOGE/USDT FINAL OPTIMIZED STRATEGY - Production Ready
Combines best optimization findings for maximum R:R ratio
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class DOGEOptimizedStrategy:
    """Final optimized DOGE/USDT trading strategy"""

    def __init__(self, data_path: str, initial_capital: float = 10000):
        """Initialize with DOGE data"""
        self.data = pd.read_csv(data_path)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data['date'] = self.data['timestamp'].dt.date
        self.data['hour'] = self.data['timestamp'].dt.hour
        self.data['time'] = self.data['timestamp'].dt.time
        self.initial_capital = initial_capital

        # Calculate indicators
        self._calculate_indicators()

        print(f"Loaded {len(self.data)} candles")
        print(f"Period: {self.data['timestamp'].iloc[0]} to {self.data['timestamp'].iloc[-1]}")

    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        df = self.data

        # SMA
        df['sma_20'] = df['close'].rolling(20).mean()

        # ATR for dynamic stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr_14'] = df['tr'].rolling(14).mean()

        # Consecutive down bars
        df['down_bar'] = (df['close'] < df['open']).astype(int)
        df['consec_down'] = 0

        for i in range(4, len(df)):
            if all(df['down_bar'].iloc[i-j] == 1 for j in range(1, 5)):
                df.loc[df.index[i], 'consec_down'] = 4

        self.data = df

    def run_optimized_strategy(self, config: str = 'best_rr') -> pd.DataFrame:
        """
        Run optimized strategy based on selected configuration

        Configs:
        - 'best_rr': Best R:R ratio (SL:1x, TP:6x, limit orders)
        - 'best_return': Best total return (SL:2x, TP:6x, limit orders)
        - 'best_winrate': Best win rate (Afternoon session, baseline SL/TP)
        - 'balanced': Balanced approach (SL:1.5x, TP:6x, limit orders)
        """
        df = self.data.copy()
        trades = []
        capital = self.initial_capital
        position = None

        # Configuration settings
        configs = {
            'best_rr': {
                'sl_mult': 1.0,
                'tp_mult': 6.0,
                'use_limit': True,
                'session': None,
                'name': 'Best R:R Ratio (3.90x)'
            },
            'best_return': {
                'sl_mult': 2.0,
                'tp_mult': 6.0,
                'use_limit': True,
                'session': None,
                'name': 'Best Return (9.10%)'
            },
            'best_winrate': {
                'sl_mult': 1.5,
                'tp_mult': 3.0,
                'use_limit': True,
                'session': (12, 18),
                'name': 'Best Win Rate (71.4%)'
            },
            'balanced': {
                'sl_mult': 1.5,
                'tp_mult': 6.0,
                'use_limit': True,
                'session': None,
                'name': 'Balanced (R:R 2.84x)'
            }
        }

        selected = configs[config]
        fee_pct = 0.0007 if selected['use_limit'] else 0.001

        print(f"\n{'='*80}")
        print(f"Running Configuration: {selected['name']}")
        print(f"{'='*80}")
        print(f"SL: {selected['sl_mult']}x ATR, TP: {selected['tp_mult']}x ATR")
        print(f"Order Type: {'Limit (0.07% fees)' if selected['use_limit'] else 'Market (0.1% fees)'}")
        if selected['session']:
            print(f"Session: {selected['session'][0]}-{selected['session'][1]} UTC")
        print()

        for idx in range(20, len(df)):
            row = df.iloc[idx]

            # Session filter
            if selected['session']:
                start_h, end_h = selected['session']
                if not (start_h <= row['hour'] < end_h):
                    continue

            # Manage open position
            if position:
                # Check stop loss
                if row['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'

                    gross_pnl = (exit_price - position['entry_price']) * position['size']
                    fees = (position['entry_price'] * position['size'] * fee_pct +
                           exit_price * position['size'] * fee_pct)
                    net_pnl = gross_pnl - fees
                    pnl_pct = net_pnl / (position['entry_price'] * position['size'])

                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_date': row['date'],
                        'exit_time': row['time'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'gross_pnl': gross_pnl,
                        'fees': fees,
                        'net_pnl': net_pnl,
                        'pnl_pct': pnl_pct,
                        'duration_minutes': idx - position['entry_idx'],
                        'r_multiple': (exit_price - position['entry_price']) / (position['entry_price'] - position['stop_loss'])
                    })

                    capital += net_pnl
                    position = None

                # Check take profit
                elif row['high'] >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'take_profit'

                    gross_pnl = (exit_price - position['entry_price']) * position['size']
                    fees = (position['entry_price'] * position['size'] * fee_pct +
                           exit_price * position['size'] * fee_pct)
                    net_pnl = gross_pnl - fees
                    pnl_pct = net_pnl / (position['entry_price'] * position['size'])

                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_date': row['date'],
                        'exit_time': row['time'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'gross_pnl': gross_pnl,
                        'fees': fees,
                        'net_pnl': net_pnl,
                        'pnl_pct': pnl_pct,
                        'duration_minutes': idx - position['entry_idx'],
                        'r_multiple': (exit_price - position['entry_price']) / (position['entry_price'] - position['stop_loss'])
                    })

                    capital += net_pnl
                    position = None

            # Check for entry signal
            if not position and not pd.isna(row['sma_20']) and not pd.isna(row['atr_14']):
                # Entry conditions
                price_below_sma = row['close'] < row['sma_20'] * 0.99
                consec_down_bars = row['consec_down'] >= 4

                if price_below_sma and consec_down_bars:
                    # Entry logic
                    if selected['use_limit']:
                        entry_price = row['close'] * 0.99965  # 0.035% below
                    else:
                        entry_price = row['close']

                    # Calculate stops
                    stop_loss = entry_price - (row['atr_14'] * selected['sl_mult'])
                    take_profit = entry_price + (row['atr_14'] * selected['tp_mult'])

                    # Position size
                    position_size = capital / entry_price

                    position = {
                        'entry_date': row['date'],
                        'entry_time': row['time'],
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'size': position_size,
                        'entry_idx': idx
                    }

        # Create trades DataFrame
        trades_df = pd.DataFrame(trades)

        # Calculate metrics
        if len(trades_df) > 0:
            trades_df['cumulative_capital'] = self.initial_capital + trades_df['net_pnl'].cumsum()

            self._print_metrics(trades_df, selected['name'])
            self._save_results(trades_df, config)

        return trades_df

    def _print_metrics(self, trades_df: pd.DataFrame, config_name: str):
        """Print comprehensive performance metrics"""
        final_capital = trades_df['cumulative_capital'].iloc[-1]
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        winners = trades_df[trades_df['net_pnl'] > 0]
        losers = trades_df[trades_df['net_pnl'] < 0]

        win_rate = len(winners) / len(trades_df) * 100

        gross_wins = winners['net_pnl'].sum() if len(winners) > 0 else 0
        gross_losses = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else np.inf

        running_max = trades_df['cumulative_capital'].cummax()
        drawdown = (trades_df['cumulative_capital'] - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100

        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
        rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

        avg_r = trades_df['r_multiple'].mean()
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        print(f"\n{'='*80}")
        print(f"PERFORMANCE METRICS: {config_name}")
        print(f"{'='*80}\n")

        print(f"OVERALL PERFORMANCE:")
        print(f"  Total Trades: {len(trades_df)}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Total Return: {total_return_pct:.2f}%")
        print(f"  Final Capital: ${final_capital:,.2f}")
        print(f"  Max Drawdown: {max_drawdown:.2f}%")
        print()

        print(f"RISK/REWARD:")
        print(f"  R:R Ratio: {rr_ratio:.2f}")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Average R Multiple: {avg_r:.2f}")
        print(f"  Expectancy: {expectancy * 100:.2f}%")
        print()

        print(f"TRADE STATISTICS:")
        print(f"  Average Win: {avg_win * 100:.2f}%")
        print(f"  Average Loss: {avg_loss * 100:.2f}%")
        print(f"  Largest Win: {winners['pnl_pct'].max() * 100 if len(winners) > 0 else 0:.2f}%")
        print(f"  Largest Loss: {losers['pnl_pct'].min() * 100 if len(losers) > 0 else 0:.2f}%")
        print(f"  Avg Duration: {trades_df['duration_minutes'].mean():.1f} minutes")
        print()

        print(f"EXIT BREAKDOWN:")
        print(f"  Take Profits: {len(trades_df[trades_df['exit_reason'] == 'take_profit'])} ({len(trades_df[trades_df['exit_reason'] == 'take_profit']) / len(trades_df) * 100:.1f}%)")
        print(f"  Stop Losses: {len(trades_df[trades_df['exit_reason'] == 'stop_loss'])} ({len(trades_df[trades_df['exit_reason'] == 'stop_loss']) / len(trades_df) * 100:.1f}%)")
        print()

    def _save_results(self, trades_df: pd.DataFrame, config_name: str):
        """Save results and create equity curve"""
        output_dir = '/workspaces/Carebiuro_windykacja/trading/results'

        # Save trades
        trades_df.to_csv(f'{output_dir}/doge_{config_name}_trades.csv', index=False)
        print(f"✓ Trades saved to {output_dir}/doge_{config_name}_trades.csv")

        # Create equity curve
        plt.figure(figsize=(14, 6))
        plt.plot(trades_df['cumulative_capital'], linewidth=2, color='#2E86AB')
        plt.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
        plt.fill_between(range(len(trades_df)), self.initial_capital, trades_df['cumulative_capital'],
                        where=(trades_df['cumulative_capital'] >= self.initial_capital),
                        color='green', alpha=0.2, interpolate=True)
        plt.fill_between(range(len(trades_df)), self.initial_capital, trades_df['cumulative_capital'],
                        where=(trades_df['cumulative_capital'] < self.initial_capital),
                        color='red', alpha=0.2, interpolate=True)

        final_return = ((trades_df['cumulative_capital'].iloc[-1] - self.initial_capital) / self.initial_capital) * 100
        plt.title(f'DOGE/USDT {config_name.upper()} - Equity Curve\nFinal Return: {final_return:.2f}%',
                 fontsize=14, fontweight='bold')
        plt.xlabel('Trade Number', fontsize=12)
        plt.ylabel('Capital ($)', fontsize=12)
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f'{output_dir}/doge_{config_name}_equity.png', dpi=150)
        print(f"✓ Equity curve saved to {output_dir}/doge_{config_name}_equity.png")

    def compare_all_configs(self):
        """Run and compare all optimized configurations"""
        print("\n" + "#"*80)
        print("# COMPARING ALL OPTIMIZED CONFIGURATIONS")
        print("#"*80)

        configs = ['best_rr', 'best_return', 'best_winrate', 'balanced']
        all_results = []

        for config in configs:
            trades = self.run_optimized_strategy(config)
            if len(trades) > 0:
                metrics = {
                    'config': config,
                    'trades': len(trades),
                    'win_rate': len(trades[trades['net_pnl'] > 0]) / len(trades) * 100,
                    'total_return': ((trades['cumulative_capital'].iloc[-1] - self.initial_capital) / self.initial_capital) * 100,
                    'max_dd': abs((trades['cumulative_capital'] - trades['cumulative_capital'].cummax()).min() / trades['cumulative_capital'].cummax().max()) * 100,
                    'rr_ratio': abs(trades[trades['net_pnl'] > 0]['pnl_pct'].mean() / trades[trades['net_pnl'] < 0]['pnl_pct'].mean()) if len(trades[trades['net_pnl'] < 0]) > 0 else np.inf
                }
                all_results.append(metrics)

        # Save comparison
        comparison_df = pd.DataFrame(all_results)
        comparison_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/doge_all_configs_comparison.csv', index=False)
        print(f"\n✓ Full comparison saved to results/doge_all_configs_comparison.csv")

        return comparison_df


if __name__ == '__main__':
    # Initialize strategy
    strategy = DOGEOptimizedStrategy('/workspaces/Carebiuro_windykacja/trading/doge_usdt_1m_lbank.csv')

    # Run all configurations and compare
    comparison = strategy.compare_all_configs()

    print("\n" + "="*80)
    print("FINAL COMPARISON")
    print("="*80)
    print(comparison.to_string(index=False))

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE - All results saved to ./results/")
    print("="*80)
