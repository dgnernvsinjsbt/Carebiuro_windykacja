"""
Comprehensive Backtesting Engine for FARTCOIN/USDT Trading Strategies

Features:
- Daily compounding
- 5% daily drawdown limit
- Session-based analysis
- Multiple exit methods
- Realistic trade simulation
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from strategies import calculate_indicators, STRATEGIES, EXIT_CONFIGS, fixed_rr_exit


class BacktestEngine:
    """Core backtesting engine with daily compounding and drawdown limits"""

    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.daily_drawdown_limit = 0.05  # 5%

        # Prepare data
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data['date'] = self.data['timestamp'].dt.date
        self.data['hour'] = self.data['timestamp'].dt.hour
        self.data['time'] = self.data['timestamp'].dt.time

        # Calculate all indicators
        print("Calculating technical indicators...")
        self.data = calculate_indicators(self.data)

    def run_strategy(self, strategy_name: str, strategy_func,
                     exit_config: Dict, session_hours: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Run a single strategy with specified exit method

        Args:
            strategy_name: Name of the strategy
            strategy_func: Function that generates entry signals
            exit_config: Exit method configuration
            session_hours: Optional tuple (start_hour, end_hour) to restrict trading

        Returns:
            Dictionary with performance metrics
        """
        # Generate entry signals
        signals = strategy_func(self.data)

        # Merge signals with data
        trade_data = self.data.copy()
        trade_data['entry_signal'] = signals['entry']
        trade_data['stop_loss'] = signals['stop_loss']

        # Filter by session hours if specified
        if session_hours:
            start_hour, end_hour = session_hours
            if start_hour < end_hour:
                session_mask = (trade_data['hour'] >= start_hour) & (trade_data['hour'] < end_hour)
            else:  # Wraps midnight
                session_mask = (trade_data['hour'] >= start_hour) | (trade_data['hour'] < end_hour)
            trade_data.loc[~session_mask, 'entry_signal'] = 0

        # Simulate trading
        results = self._simulate_trading(trade_data, exit_config)

        # Calculate metrics
        metrics = self._calculate_metrics(results, strategy_name, exit_config, session_hours)

        return metrics

    def _simulate_trading(self, data: pd.DataFrame, exit_config: Dict) -> pd.DataFrame:
        """
        Simulate actual trading with daily compounding and drawdown limits
        """
        capital = self.initial_capital
        position = None  # Current position: {'entry_price', 'stop_loss', 'target', 'entry_idx', 'size', 'highest'}
        trades = []

        # Track daily performance
        daily_start_capital = {}
        daily_trades = {}
        daily_halted = set()

        for idx in range(len(data)):
            row = data.iloc[idx]
            current_date = row['date']

            # Initialize daily tracking
            if current_date not in daily_start_capital:
                daily_start_capital[current_date] = capital
                daily_trades[current_date] = []

            # Check if trading is halted for the day
            if current_date in daily_halted:
                # Close any open position at end of day
                if position and idx == len(data) - 1 or (idx < len(data) - 1 and data.iloc[idx + 1]['date'] != current_date):
                    # Exit at close
                    pnl = (row['close'] - position['entry_price']) * position['size']
                    pnl_pct = (row['close'] - position['entry_price']) / position['entry_price']

                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_date': row['date'],
                        'exit_time': row['time'],
                        'exit_price': row['close'],
                        'exit_reason': 'end_of_day',
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration_candles': idx - position['entry_idx']
                    })

                    capital += pnl
                    position = None
                continue

            # Check daily drawdown limit
            current_daily_return = (capital - daily_start_capital[current_date]) / daily_start_capital[current_date]
            if current_daily_return <= -self.daily_drawdown_limit:
                daily_halted.add(current_date)
                # Close position if open
                if position:
                    pnl = (row['close'] - position['entry_price']) * position['size']
                    pnl_pct = (row['close'] - position['entry_price']) / position['entry_price']

                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_date': row['date'],
                        'exit_time': row['time'],
                        'exit_price': row['close'],
                        'exit_reason': 'daily_limit_hit',
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration_candles': idx - position['entry_idx']
                    })

                    capital += pnl
                    position = None
                continue

            # Manage open position
            if position:
                exit_price = None
                exit_reason = None

                # Check stop loss (use low of candle)
                if row['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'

                # Check target based on exit method
                elif exit_config['type'] == 'fixed_rr':
                    if row['high'] >= position['target']:
                        exit_price = position['target']
                        exit_reason = 'target'

                elif exit_config['type'] == 'trail_atr':
                    # Update highest price
                    position['highest'] = max(position['highest'], row['high'])

                    # Calculate trailing stop
                    atr = row['atr_14'] if not pd.isna(row['atr_14']) else 0.01
                    trail_stop = position['highest'] - (atr * exit_config['multiplier'])

                    # Update stop if trail is higher
                    if trail_stop > position['stop_loss']:
                        position['stop_loss'] = trail_stop

                    # Check if stopped out
                    if row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'trailing_stop'

                elif exit_config['type'] == 'time_based':
                    # Exit after N candles
                    if idx - position['entry_idx'] >= exit_config['candles']:
                        exit_price = row['close']
                        exit_reason = 'time_exit'

                # Check end of day
                if idx < len(data) - 1 and data.iloc[idx + 1]['date'] != current_date:
                    if exit_price is None:
                        exit_price = row['close']
                        exit_reason = 'end_of_day'

                # Execute exit
                if exit_price:
                    pnl = (exit_price - position['entry_price']) * position['size']
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']

                    trade_record = {
                        'entry_date': position['entry_date'],
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_date': row['date'],
                        'exit_time': row['time'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration_candles': idx - position['entry_idx']
                    }

                    trades.append(trade_record)
                    daily_trades[current_date].append(trade_record)

                    capital += pnl
                    position = None

            # Check for entry signal (only if no position)
            if not position and row['entry_signal'] == 1 and not pd.isna(row['stop_loss']):
                # Validate stop loss
                if row['stop_loss'] >= row['close']:
                    continue  # Invalid stop loss

                # Calculate position size (use 100% of capital)
                position_size = capital / row['close']

                # Calculate target based on exit method
                if exit_config['type'] == 'fixed_rr':
                    target = fixed_rr_exit(row['close'], row['stop_loss'], exit_config['ratio'])
                else:
                    target = None

                position = {
                    'entry_date': row['date'],
                    'entry_time': row['time'],
                    'entry_price': row['close'],
                    'stop_loss': row['stop_loss'],
                    'target': target,
                    'entry_idx': idx,
                    'size': position_size,
                    'highest': row['high']
                }

            # Compound to next day
            if idx < len(data) - 1 and data.iloc[idx + 1]['date'] != current_date:
                # Day is over, capital is compounded automatically
                pass

        return pd.DataFrame(trades)

    def _calculate_metrics(self, trades_df: pd.DataFrame, strategy_name: str,
                          exit_config: Dict, session_hours: Optional[Tuple[int, int]]) -> Dict:
        """
        Calculate comprehensive performance metrics
        """
        if len(trades_df) == 0:
            return {
                'strategy': strategy_name,
                'exit_method': f"{exit_config['type']}_{exit_config.get('ratio', exit_config.get('multiplier', exit_config.get('candles', '')))}",
                'session': f"{session_hours[0]}-{session_hours[1]}" if session_hours else "all",
                'total_trades': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_duration': 0,
                'largest_win': 0,
                'largest_loss': 0
            }

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else 0)

        # Calculate cumulative returns
        trades_df['cumulative_capital'] = self.initial_capital + trades_df['pnl'].cumsum()
        final_capital = trades_df['cumulative_capital'].iloc[-1]
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # Drawdown calculation
        running_max = trades_df['cumulative_capital'].cummax()
        drawdown = (trades_df['cumulative_capital'] - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100

        # Average win/loss
        avg_win = winning_trades['pnl_pct'].mean() * 100 if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() * 100 if len(losing_trades) > 0 else 0

        # Sharpe ratio (simplified - using trade returns)
        if len(trades_df) > 1:
            returns = trades_df['pnl_pct']
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0

        # Other metrics
        avg_duration = trades_df['duration_candles'].mean()
        largest_win = winning_trades['pnl_pct'].max() * 100 if len(winning_trades) > 0 else 0
        largest_loss = losing_trades['pnl_pct'].min() * 100 if len(losing_trades) > 0 else 0

        return {
            'strategy': strategy_name,
            'exit_method': f"{exit_config['type']}_{exit_config.get('ratio', exit_config.get('multiplier', exit_config.get('candles', '')))}",
            'session': f"{session_hours[0]}-{session_hours[1]}" if session_hours else "all",
            'total_trades': total_trades,
            'total_return_pct': round(total_return_pct, 2),
            'win_rate': round(win_rate * 100, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != np.inf else 999,
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'avg_duration': round(avg_duration, 1),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2)
        }

    def analyze_session_performance(self, strategy_name: str, strategy_func,
                                   exit_config: Dict) -> pd.DataFrame:
        """
        Analyze performance by hour of day to find optimal trading hours
        """
        hourly_results = []

        # Test different session windows
        sessions = {
            'asian': (0, 8),
            'european': (8, 16),
            'us': (16, 24),
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 24),
            'night': (0, 6)
        }

        for session_name, hours in sessions.items():
            metrics = self.run_strategy(strategy_name, strategy_func, exit_config, session_hours=hours)
            metrics['session_name'] = session_name
            hourly_results.append(metrics)

        return pd.DataFrame(hourly_results)


def run_comprehensive_backtest(data_path: str, output_dir: str):
    """
    Run comprehensive backtest on all strategies and variations
    """
    print("=" * 80)
    print("FARTCOIN/USDT COMPREHENSIVE STRATEGY BACKTEST")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data = pd.read_csv(data_path)
    print(f"Loaded {len(data)} candles from {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")

    # Initialize backtest engine
    engine = BacktestEngine(data)

    # Test all strategy combinations
    all_results = []
    total_combinations = len(STRATEGIES) * len(EXIT_CONFIGS)

    print(f"\nTesting {len(STRATEGIES)} strategies with {len(EXIT_CONFIGS)} exit methods")
    print(f"Total combinations: {total_combinations}")
    print("-" * 80)

    counter = 0
    for strategy_name, strategy_func in STRATEGIES.items():
        for exit_name, exit_config in EXIT_CONFIGS.items():
            counter += 1
            print(f"[{counter}/{total_combinations}] Testing: {strategy_name} + {exit_name}...", end=' ')

            try:
                metrics = engine.run_strategy(strategy_name, strategy_func, exit_config)
                all_results.append(metrics)
                print(f"✓ Return: {metrics['total_return_pct']:.1f}%, Trades: {metrics['total_trades']}")
            except Exception as e:
                print(f"✗ Error: {str(e)}")

    # Create results DataFrame
    results_df = pd.DataFrame(all_results)

    # Sort by total return
    results_df = results_df.sort_values('total_return_pct', ascending=False)

    # Save detailed results
    results_df.to_csv(f'{output_dir}/detailed_results.csv', index=False)
    print(f"\n✓ Saved detailed results to {output_dir}/detailed_results.csv")

    # Analyze top 3 strategies
    print("\n" + "=" * 80)
    print("TOP 3 STRATEGIES")
    print("=" * 80)

    top_3 = results_df.head(3)

    for idx, row in top_3.iterrows():
        print(f"\n#{top_3.index.get_loc(idx) + 1}: {row['strategy']} + {row['exit_method']}")
        print(f"  Total Return: {row['total_return_pct']:.2f}%")
        print(f"  Win Rate: {row['win_rate']:.2f}%")
        print(f"  Profit Factor: {row['profit_factor']:.2f}")
        print(f"  Total Trades: {row['total_trades']}")
        print(f"  Max Drawdown: {row['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio: {row['sharpe_ratio']:.2f}")

    # Session analysis for top strategy
    if len(results_df) > 0:
        print("\n" + "=" * 80)
        print("SESSION ANALYSIS FOR TOP STRATEGY")
        print("=" * 80)

        top_strategy = results_df.iloc[0]
        strategy_func = STRATEGIES[top_strategy['strategy']]
        exit_config = None

        # Reconstruct exit config
        for exit_name, ec in EXIT_CONFIGS.items():
            if exit_name in top_strategy['exit_method']:
                exit_config = ec
                break

        if exit_config:
            session_df = engine.analyze_session_performance(
                top_strategy['strategy'], strategy_func, exit_config
            )
            session_df = session_df.sort_values('total_return_pct', ascending=False)

            print("\nPerformance by session:")
            for _, session in session_df.iterrows():
                print(f"  {session['session_name']:12s}: {session['total_return_pct']:7.2f}% "
                      f"(Trades: {session['total_trades']:3d}, WR: {session['win_rate']:5.1f}%)")

    # Generate summary report
    generate_summary_report(results_df, top_3, output_dir, engine, data)

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)

    return results_df


def generate_summary_report(results_df: pd.DataFrame, top_3: pd.DataFrame,
                           output_dir: str, engine: BacktestEngine, data: pd.DataFrame):
    """
    Generate human-readable summary report
    """
    report = []
    report.append("# FARTCOIN/USDT Trading Strategy Backtest Results")
    report.append("")
    report.append(f"**Backtest Period**: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")
    report.append(f"**Total Candles**: {len(data)} (15-minute intervals)")
    report.append(f"**Initial Capital**: $10,000")
    report.append(f"**Trading Fees**: 0% (zero-fee spot exchange)")
    report.append("")
    report.append("---")
    report.append("")

    # Top 10 ranking
    report.append("## Strategy Rankings - Top 10")
    report.append("")
    report.append("| Rank | Strategy | Exit Method | Return (%) | Trades | Win Rate (%) | Profit Factor | Max DD (%) | Sharpe |")
    report.append("|------|----------|-------------|-----------|--------|-------------|---------------|-----------|--------|")

    for i, (_, row) in enumerate(results_df.head(10).iterrows()):
        report.append(f"| {i+1} | {row['strategy']} | {row['exit_method']} | "
                     f"{row['total_return_pct']:.2f} | {row['total_trades']} | "
                     f"{row['win_rate']:.1f} | {row['profit_factor']:.2f} | "
                     f"{row['max_drawdown']:.2f} | {row['sharpe_ratio']:.2f} |")

    report.append("")
    report.append("---")
    report.append("")

    # Top 3 Deep Dive
    report.append("## Top 3 Strategies - Detailed Analysis")
    report.append("")

    for i, (_, row) in enumerate(top_3.iterrows()):
        report.append(f"### #{i+1}: {row['strategy']} + {row['exit_method']}")
        report.append("")
        report.append("**Performance Metrics:**")
        report.append(f"- **Total Return**: {row['total_return_pct']:.2f}%")
        report.append(f"- **Final Capital**: ${10000 * (1 + row['total_return_pct']/100):,.2f}")
        report.append(f"- **Total Trades**: {row['total_trades']}")
        report.append(f"- **Win Rate**: {row['win_rate']:.2f}%")
        report.append(f"- **Profit Factor**: {row['profit_factor']:.2f}")
        report.append(f"- **Average Win**: {row['avg_win']:.2f}%")
        report.append(f"- **Average Loss**: {row['avg_loss']:.2f}%")
        report.append(f"- **Max Drawdown**: {row['max_drawdown']:.2f}%")
        report.append(f"- **Sharpe Ratio**: {row['sharpe_ratio']:.2f}")
        report.append(f"- **Average Trade Duration**: {row['avg_duration']:.1f} candles ({row['avg_duration'] * 15:.0f} minutes)")
        report.append(f"- **Largest Win**: {row['largest_win']:.2f}%")
        report.append(f"- **Largest Loss**: {row['largest_loss']:.2f}%")
        report.append("")

    # Recommended Strategy
    report.append("---")
    report.append("")
    report.append("## Recommended Trading Strategy")
    report.append("")

    if len(results_df) > 0:
        best = results_df.iloc[0]
        report.append(f"**Strategy**: {best['strategy']}")
        report.append(f"**Exit Method**: {best['exit_method']}")
        report.append("")
        report.append("### Entry Rules")

        # Get entry description based on strategy name
        if 'green_candle' in best['strategy']:
            report.append("- Enter LONG when candle closes green (close > open)")
            if 'min_size' in best['strategy']:
                report.append("- Candle must have minimum size of 0.1% of price")
            if 'consec' in best['strategy']:
                report.append("- Require 2 consecutive green candles")
            report.append("- Stop loss: Below the entry candle's low")
        elif 'price_cross' in best['strategy']:
            report.append(f"- Enter LONG when price crosses above {best['strategy'].split('_')[-1].upper()}")
            report.append("- Stop loss: 2 ATR below entry or recent swing low")
        elif 'ema_' in best['strategy'] and '_cross' in best['strategy']:
            parts = best['strategy'].split('_')
            report.append(f"- Enter LONG when EMA{parts[1]} crosses above EMA{parts[2]}")
            report.append("- Stop loss: Below slow EMA or 2 ATR")
        elif 'rsi' in best['strategy']:
            if 'oversold' in best['strategy']:
                report.append("- Enter LONG when RSI crosses back above 30 from oversold")
            else:
                report.append("- Enter LONG when RSI crosses above 50 (momentum)")
            report.append("- Stop loss: Below recent swing low")
        elif 'breakout' in best['strategy']:
            report.append("- Enter LONG on breakout above period high")
            report.append("- Stop loss: Below period low")
        elif 'above_' in best['strategy']:
            report.append("- Hybrid strategy combining multiple conditions")
            report.append("- Must be above EMA for trend confirmation")

        report.append("")
        report.append("### Exit Rules")

        if 'rr_' in best['exit_method']:
            ratio = best['exit_method'].split('_')[1]
            report.append(f"- Fixed risk:reward ratio of 1:{ratio}")
            report.append(f"- Target = Entry + (Risk × {ratio})")
        elif 'trail_atr' in best['exit_method']:
            mult = best['exit_method'].split('_')[1]
            report.append(f"- Trailing stop based on ATR × {mult}")
            report.append("- Stop trails below highest price since entry")
        elif 'time_' in best['exit_method']:
            candles = best['exit_method'].split('_')[1]
            report.append(f"- Time-based exit after {candles} candles")

        report.append("- Stop loss if price hits stop level")
        report.append("- Close all positions at end of day (no overnight holds)")

        report.append("")
        report.append("### Position Sizing")
        report.append("- Use 100% of available capital per trade (long only, no leverage)")
        report.append("- No overlapping positions")
        report.append("- Daily compounding: Profits/losses affect next trade size")

        report.append("")
        report.append("### Risk Management")
        report.append("- **Daily Drawdown Limit**: 5% - Stop trading for the day if hit")
        report.append("- **No Overnight Positions**: Close all trades by end of session")
        report.append("- **Stop Loss**: Always use stop loss on every trade")

        report.append("")
        report.append(f"### Expected Performance")
        report.append(f"- Total Return: {best['total_return_pct']:.2f}% over 3 months")
        report.append(f"- Win Rate: {best['win_rate']:.2f}%")
        report.append(f"- Average Trade: ~{best['avg_duration'] * 15:.0f} minutes")
        report.append(f"- Trades per day: ~{best['total_trades'] / 90:.1f}")

    # Save report
    with open(f'{output_dir}/summary.md', 'w') as f:
        f.write('\n'.join(report))

    print(f"✓ Saved summary report to {output_dir}/summary.md")


if __name__ == '__main__':
    import sys

    data_path = './fartcoin_15m_3months.csv'
    output_dir = './trading/results'

    results = run_comprehensive_backtest(data_path, output_dir)

    print(f"\nAll results saved to {output_dir}/")
    print("- detailed_results.csv: Full metrics for all strategies")
    print("- summary.md: Human-readable analysis and recommendations")
