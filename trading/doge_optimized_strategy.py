"""
DOGE/USDT Strategy Optimization Engine
Systematically tests all optimization variables for the baseline strategy
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt


class DOGEStrategyOptimizer:
    """Systematic optimization engine for DOGE/USDT trading strategy"""

    def __init__(self, data_path: str, initial_capital: float = 10000):
        """Initialize optimizer with DOGE data"""
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
        print(f"Days: {(self.data['timestamp'].iloc[-1] - self.data['timestamp'].iloc[0]).days}")

    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        df = self.data

        # SMA
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()

        # EMA for higher TF filter
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

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

        # Volume indicators
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']

        # Volatility (for filters)
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100

        # 1H trend (resample to hourly)
        hourly = df.set_index('timestamp').resample('1H').agg({
            'close': 'last',
            'high': 'max',
            'low': 'min',
            'open': 'first'
        }).dropna()
        hourly['sma_50_1h'] = hourly['close'].rolling(50).mean()
        hourly['ema_50_1h'] = hourly['close'].ewm(span=50, adjust=False).mean()

        # Merge hourly trend back to 1m data
        df['hour_start'] = df['timestamp'].dt.floor('1H')
        df = df.merge(
            hourly[['sma_50_1h', 'ema_50_1h']].reset_index().rename(columns={'timestamp': 'hour_start'}),
            on='hour_start',
            how='left'
        )
        df['above_1h_sma'] = (df['close'] > df['sma_50_1h']).astype(int)
        df['above_1h_ema'] = (df['close'] > df['ema_50_1h']).astype(int)

        self.data = df

    def baseline_strategy(self, sl_atr_mult: float = 1.5, tp_atr_mult: float = 3.0,
                         session_hours: Optional[Tuple[int, int]] = None,
                         use_limit_orders: bool = False,
                         volume_filter: Optional[float] = None,
                         volatility_filter: Optional[Tuple[float, float]] = None,
                         higher_tf_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Run baseline strategy with configurable parameters

        Args:
            sl_atr_mult: Stop loss ATR multiplier
            tp_atr_mult: Take profit ATR multiplier
            session_hours: Trading session (start_hour, end_hour)
            use_limit_orders: Use limit orders instead of market
            volume_filter: Minimum volume ratio (vs 20-period SMA)
            volatility_filter: (min_vol, max_vol) volatility range
            higher_tf_filter: '1h_sma' or '1h_ema' for trend alignment
        """
        df = self.data.copy()
        trades = []
        capital = self.initial_capital
        position = None

        # Fee structure
        fee_pct = 0.0007 if use_limit_orders else 0.001  # 0.07% limit, 0.1% market

        for idx in range(20, len(df)):  # Start after SMA warmup
            row = df.iloc[idx]

            # Session filter
            if session_hours:
                start_h, end_h = session_hours
                if start_h < end_h:
                    if not (start_h <= row['hour'] < end_h):
                        continue
                else:  # Overnight session
                    if not (row['hour'] >= start_h or row['hour'] < end_h):
                        continue

            # Manage open position
            if position:
                # Check stop loss
                if row['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'

                    # Calculate P&L
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
                        'duration_minutes': idx - position['entry_idx']
                    })

                    capital += net_pnl
                    position = None

                # Check take profit
                elif row['high'] >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'take_profit'

                    # Calculate P&L
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
                        'duration_minutes': idx - position['entry_idx']
                    })

                    capital += net_pnl
                    position = None

            # Check for entry signal
            if not position and not pd.isna(row['sma_20']) and not pd.isna(row['atr_14']):
                # Baseline entry conditions
                price_below_sma = row['close'] < row['sma_20'] * 0.99  # 1% below SMA
                consec_down_bars = row['consec_down'] >= 4

                # Additional filters
                volume_ok = True
                if volume_filter and not pd.isna(row['volume_ratio']):
                    volume_ok = row['volume_ratio'] >= volume_filter

                volatility_ok = True
                if volatility_filter and not pd.isna(row['volatility']):
                    min_vol, max_vol = volatility_filter
                    volatility_ok = min_vol <= row['volatility'] <= max_vol

                higher_tf_ok = True
                if higher_tf_filter == '1h_sma' and not pd.isna(row['above_1h_sma']):
                    higher_tf_ok = row['above_1h_sma'] == 1
                elif higher_tf_filter == '1h_ema' and not pd.isna(row['above_1h_ema']):
                    higher_tf_ok = row['above_1h_ema'] == 1

                if price_below_sma and consec_down_bars and volume_ok and volatility_ok and higher_tf_ok:
                    # Entry logic
                    if use_limit_orders:
                        # Limit order at 0.035% below current price
                        entry_price = row['close'] * 0.99965
                    else:
                        # Market order at close
                        entry_price = row['close']

                    # Calculate stops
                    stop_loss = entry_price - (row['atr_14'] * sl_atr_mult)
                    take_profit = entry_price + (row['atr_14'] * tp_atr_mult)

                    # Position size (100% capital)
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
            final_capital = trades_df['cumulative_capital'].iloc[-1]
            total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

            # Win rate
            winners = trades_df[trades_df['net_pnl'] > 0]
            win_rate = len(winners) / len(trades_df) * 100

            # Profit factor
            gross_wins = winners['net_pnl'].sum() if len(winners) > 0 else 0
            losers = trades_df[trades_df['net_pnl'] < 0]
            gross_losses = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
            profit_factor = gross_wins / gross_losses if gross_losses > 0 else np.inf

            # Max drawdown
            running_max = trades_df['cumulative_capital'].cummax()
            drawdown = (trades_df['cumulative_capital'] - running_max) / running_max
            max_drawdown = abs(drawdown.min()) * 100

            # R:R ratio
            avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
            avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
            rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

            trades_df.attrs['metrics'] = {
                'total_trades': len(trades_df),
                'win_rate': win_rate,
                'total_return_pct': total_return_pct,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'rr_ratio': rr_ratio,
                'avg_win_pct': avg_win * 100,
                'avg_loss_pct': avg_loss * 100,
                'final_capital': final_capital
            }
        else:
            trades_df.attrs['metrics'] = {
                'total_trades': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'rr_ratio': 0,
                'avg_win_pct': 0,
                'avg_loss_pct': 0,
                'final_capital': self.initial_capital
            }

        return trades_df

    def optimize_sessions(self) -> pd.DataFrame:
        """Test different trading sessions"""
        print("\n" + "="*80)
        print("OPTIMIZATION 1: SESSION ANALYSIS")
        print("="*80)

        sessions = {
            'All Hours': None,
            'Asia (0-8 UTC)': (0, 8),
            'Europe (8-14 UTC)': (8, 14),
            'US (14-17 UTC)': (14, 17),
            'Overnight (17-24 UTC)': (17, 24),
            'Morning (6-12 UTC)': (6, 12),
            'Afternoon (12-18 UTC)': (12, 18)
        }

        results = []
        for name, hours in sessions.items():
            print(f"Testing {name}...", end=' ')
            trades = self.baseline_strategy(session_hours=hours)
            metrics = trades.attrs['metrics']
            metrics['session'] = name
            results.append(metrics)
            print(f"Return: {metrics['total_return_pct']:.2f}%, Trades: {metrics['total_trades']}, R:R: {metrics['rr_ratio']:.2f}")

        return pd.DataFrame(results)

    def optimize_sl_tp(self) -> pd.DataFrame:
        """Test dynamic SL/TP combinations"""
        print("\n" + "="*80)
        print("OPTIMIZATION 2: DYNAMIC SL/TP")
        print("="*80)

        sl_multipliers = [1.0, 1.5, 2.0]
        tp_multipliers = [2.0, 3.0, 4.0, 6.0]

        results = []
        for sl in sl_multipliers:
            for tp in tp_multipliers:
                print(f"Testing SL:{sl}x ATR, TP:{tp}x ATR...", end=' ')
                trades = self.baseline_strategy(sl_atr_mult=sl, tp_atr_mult=tp)
                metrics = trades.attrs['metrics']
                metrics['sl_mult'] = sl
                metrics['tp_mult'] = tp
                metrics['config'] = f"SL:{sl}x_TP:{tp}x"
                results.append(metrics)
                print(f"Return: {metrics['total_return_pct']:.2f}%, R:R: {metrics['rr_ratio']:.2f}")

        return pd.DataFrame(results)

    def optimize_higher_tf_filter(self) -> pd.DataFrame:
        """Test 1H trend filters"""
        print("\n" + "="*80)
        print("OPTIMIZATION 3: HIGHER TIMEFRAME FILTERS")
        print("="*80)

        filters = {
            'No Filter': None,
            '1H SMA50 Aligned': '1h_sma',
            '1H EMA50 Aligned': '1h_ema'
        }

        results = []
        for name, filter_type in filters.items():
            print(f"Testing {name}...", end=' ')
            trades = self.baseline_strategy(higher_tf_filter=filter_type)
            metrics = trades.attrs['metrics']
            metrics['filter'] = name
            results.append(metrics)
            print(f"Return: {metrics['total_return_pct']:.2f}%, Trades: {metrics['total_trades']}, R:R: {metrics['rr_ratio']:.2f}")

        return pd.DataFrame(results)

    def optimize_limit_orders(self) -> pd.DataFrame:
        """Test limit order entries"""
        print("\n" + "="*80)
        print("OPTIMIZATION 4: LIMIT ORDER ENTRIES")
        print("="*80)

        configs = [
            {'use_limit': False, 'name': 'Market Orders (0.1% fees)'},
            {'use_limit': True, 'name': 'Limit Orders (0.07% fees)'}
        ]

        results = []
        for config in configs:
            print(f"Testing {config['name']}...", end=' ')
            trades = self.baseline_strategy(use_limit_orders=config['use_limit'])
            metrics = trades.attrs['metrics']
            metrics['order_type'] = config['name']
            results.append(metrics)
            print(f"Return: {metrics['total_return_pct']:.2f}%, Trades: {metrics['total_trades']}")

        return pd.DataFrame(results)

    def optimize_filters(self) -> pd.DataFrame:
        """Test additional filters"""
        print("\n" + "="*80)
        print("OPTIMIZATION 5: ADDITIONAL FILTERS")
        print("="*80)

        filters = [
            {'name': 'No Filters', 'volume': None, 'volatility': None},
            {'name': 'Volume > 1.2x avg', 'volume': 1.2, 'volatility': None},
            {'name': 'Volume > 1.5x avg', 'volume': 1.5, 'volatility': None},
            {'name': 'Low volatility (0.1-0.5%)', 'volume': None, 'volatility': (0.1, 0.5)},
            {'name': 'Medium volatility (0.3-1.0%)', 'volume': None, 'volatility': (0.3, 1.0)},
            {'name': 'Combined: Vol>1.2x + Med Vol', 'volume': 1.2, 'volatility': (0.3, 1.0)}
        ]

        results = []
        for f in filters:
            print(f"Testing {f['name']}...", end=' ')
            trades = self.baseline_strategy(volume_filter=f['volume'], volatility_filter=f['volatility'])
            metrics = trades.attrs['metrics']
            metrics['filter_name'] = f['name']
            results.append(metrics)
            print(f"Return: {metrics['total_return_pct']:.2f}%, Trades: {metrics['total_trades']}, R:R: {metrics['rr_ratio']:.2f}")

        return pd.DataFrame(results)

    def run_comprehensive_optimization(self) -> Dict[str, pd.DataFrame]:
        """Run all optimizations and generate report"""
        print("\n" + "#"*80)
        print("# DOGE/USDT COMPREHENSIVE STRATEGY OPTIMIZATION")
        print("#"*80)

        # Run baseline first
        print("\n" + "="*80)
        print("BASELINE STRATEGY")
        print("="*80)
        baseline = self.baseline_strategy()
        baseline_metrics = baseline.attrs['metrics']

        print(f"\nBaseline Performance:")
        print(f"  Trades: {baseline_metrics['total_trades']}")
        print(f"  Win Rate: {baseline_metrics['win_rate']:.2f}%")
        print(f"  Net P&L: {baseline_metrics['total_return_pct']:.2f}%")
        print(f"  Max Drawdown: {baseline_metrics['max_drawdown']:.2f}%")
        print(f"  R:R Ratio: {baseline_metrics['rr_ratio']:.2f}")

        # Run all optimizations
        results = {
            'baseline': baseline_metrics,
            'sessions': self.optimize_sessions(),
            'sl_tp': self.optimize_sl_tp(),
            'higher_tf': self.optimize_higher_tf_filter(),
            'limit_orders': self.optimize_limit_orders(),
            'filters': self.optimize_filters()
        }

        return results


def generate_optimization_report(results: Dict, output_dir: str):
    """Generate comprehensive optimization report"""
    report = []

    report.append("# DOGE/USDT Strategy Optimization Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n---\n")

    # Baseline
    report.append("## Baseline Strategy Performance")
    report.append("\n**Entry Signal:**")
    report.append("- Price < 1.0% below 20-period SMA")
    report.append("- Previous 4 consecutive down bars completed")
    report.append("\n**Exit Rules:**")
    report.append("- Stop Loss: 1.5x ATR below entry")
    report.append("- Take Profit: 3.0x ATR above entry")
    report.append("\n**Baseline Metrics:**")

    baseline = results['baseline']
    report.append(f"- Total Trades: {baseline['total_trades']}")
    report.append(f"- Win Rate: {baseline['win_rate']:.2f}%")
    report.append(f"- Net P&L: {baseline['total_return_pct']:.2f}%")
    report.append(f"- Max Drawdown: {baseline['max_drawdown']:.2f}%")
    report.append(f"- R:R Ratio: {baseline['rr_ratio']:.2f}")
    report.append(f"- Profit Factor: {baseline['profit_factor']:.2f}")

    # Session optimization
    report.append("\n---\n")
    report.append("## 1. Session Optimization")
    report.append("\n| Session | Trades | Win Rate | Return % | R:R | Max DD |")
    report.append("|---------|--------|----------|----------|-----|--------|")

    sessions = results['sessions'].sort_values('total_return_pct', ascending=False)
    for _, row in sessions.iterrows():
        report.append(f"| {row['session']} | {row['total_trades']} | {row['win_rate']:.1f}% | "
                     f"{row['total_return_pct']:.2f}% | {row['rr_ratio']:.2f} | {row['max_drawdown']:.2f}% |")

    best_session = sessions.iloc[0]
    report.append(f"\n**Best Session:** {best_session['session']}")
    report.append(f"- Improvement: {best_session['total_return_pct'] - baseline['total_return_pct']:.2f}% vs baseline")

    # SL/TP optimization
    report.append("\n---\n")
    report.append("## 2. Dynamic SL/TP Optimization")
    report.append("\n| Config | Trades | Win Rate | Return % | R:R | Max DD |")
    report.append("|--------|--------|----------|----------|-----|--------|")

    sl_tp = results['sl_tp'].sort_values('rr_ratio', ascending=False).head(10)
    for _, row in sl_tp.iterrows():
        report.append(f"| {row['config']} | {row['total_trades']} | {row['win_rate']:.1f}% | "
                     f"{row['total_return_pct']:.2f}% | {row['rr_ratio']:.2f} | {row['max_drawdown']:.2f}% |")

    best_sl_tp = results['sl_tp'].sort_values('rr_ratio', ascending=False).iloc[0]
    report.append(f"\n**Best SL/TP:** {best_sl_tp['config']}")
    report.append(f"- R:R Ratio: {best_sl_tp['rr_ratio']:.2f} (baseline: {baseline['rr_ratio']:.2f})")

    # Higher TF filter
    report.append("\n---\n")
    report.append("## 3. Higher Timeframe Filter")
    report.append("\n| Filter | Trades | Win Rate | Return % | R:R | Max DD |")
    report.append("|--------|--------|----------|----------|-----|--------|")

    htf = results['higher_tf']
    for _, row in htf.iterrows():
        report.append(f"| {row['filter']} | {row['total_trades']} | {row['win_rate']:.1f}% | "
                     f"{row['total_return_pct']:.2f}% | {row['rr_ratio']:.2f} | {row['max_drawdown']:.2f}% |")

    # Limit orders
    report.append("\n---\n")
    report.append("## 4. Limit Order Entry")
    report.append("\n| Order Type | Trades | Win Rate | Return % | Fees Impact |")
    report.append("|------------|--------|----------|----------|-------------|")

    limit = results['limit_orders']
    for _, row in limit.iterrows():
        report.append(f"| {row['order_type']} | {row['total_trades']} | {row['win_rate']:.1f}% | "
                     f"{row['total_return_pct']:.2f}% | - |")

    # Filters
    report.append("\n---\n")
    report.append("## 5. Additional Filters")
    report.append("\n| Filter | Trades | Win Rate | Return % | R:R | Max DD |")
    report.append("|--------|--------|----------|----------|-----|--------|")

    filters = results['filters'].sort_values('rr_ratio', ascending=False)
    for _, row in filters.iterrows():
        report.append(f"| {row['filter_name']} | {row['total_trades']} | {row['win_rate']:.1f}% | "
                     f"{row['total_return_pct']:.2f}% | {row['rr_ratio']:.2f} | {row['max_drawdown']:.2f}% |")

    # Final recommendations
    report.append("\n---\n")
    report.append("## Recommendations")
    report.append("\n### Optimized Strategy Configuration")

    # Find best overall config
    best_overall_rr = max(
        best_sl_tp['rr_ratio'],
        filters.iloc[0]['rr_ratio']
    )

    report.append(f"\n**Entry:**")
    report.append("- Price < 1.0% below 20-period SMA")
    report.append("- 4+ consecutive down bars")

    if filters.iloc[0]['total_trades'] >= 20 and filters.iloc[0]['rr_ratio'] > baseline['rr_ratio']:
        report.append(f"- Additional filter: {filters.iloc[0]['filter_name']}")

    if best_session['total_return_pct'] > baseline['total_return_pct'] * 1.2:
        report.append(f"- Trade only during: {best_session['session']}")

    report.append(f"\n**Exit:**")
    report.append(f"- Stop Loss: {best_sl_tp['sl_mult']}x ATR")
    report.append(f"- Take Profit: {best_sl_tp['tp_mult']}x ATR")

    if limit.iloc[1]['total_return_pct'] > limit.iloc[0]['total_return_pct']:
        report.append(f"\n**Order Type:** Limit orders (0.035% offset, 0.07% fees)")
    else:
        report.append(f"\n**Order Type:** Market orders (0.1% fees)")

    report.append("\n### Expected Performance")
    report.append(f"- Baseline R:R: {baseline['rr_ratio']:.2f}")
    report.append(f"- Optimized R:R: {best_overall_rr:.2f}")
    report.append(f"- Improvement: {((best_overall_rr / baseline['rr_ratio']) - 1) * 100:.1f}%")

    # Save report
    with open(f'{output_dir}/DOGE_OPTIMIZATION_REPORT.md', 'w') as f:
        f.write('\n'.join(report))

    print(f"\n✓ Report saved to {output_dir}/DOGE_OPTIMIZATION_REPORT.md")


if __name__ == '__main__':
    # Run optimization
    optimizer = DOGEStrategyOptimizer('/workspaces/Carebiuro_windykacja/trading/doge_usdt_1m_lbank.csv')
    results = optimizer.run_comprehensive_optimization()

    # Save detailed results
    output_dir = '/workspaces/Carebiuro_windykacja/trading/results'

    # Save comparison CSV
    comparison = []
    comparison.append({
        'config': 'Baseline',
        'trades': results['baseline']['total_trades'],
        'win_rate': results['baseline']['win_rate'],
        'return_pct': results['baseline']['total_return_pct'],
        'max_dd': results['baseline']['max_drawdown'],
        'rr_ratio': results['baseline']['rr_ratio']
    })

    # Add best from each optimization
    best_session = results['sessions'].sort_values('total_return_pct', ascending=False).iloc[0]
    comparison.append({
        'config': f"Best Session: {best_session['session']}",
        'trades': best_session['total_trades'],
        'win_rate': best_session['win_rate'],
        'return_pct': best_session['total_return_pct'],
        'max_dd': best_session['max_drawdown'],
        'rr_ratio': best_session['rr_ratio']
    })

    best_sl_tp = results['sl_tp'].sort_values('rr_ratio', ascending=False).iloc[0]
    comparison.append({
        'config': f"Best SL/TP: {best_sl_tp['config']}",
        'trades': best_sl_tp['total_trades'],
        'win_rate': best_sl_tp['win_rate'],
        'return_pct': best_sl_tp['total_return_pct'],
        'max_dd': best_sl_tp['max_drawdown'],
        'rr_ratio': best_sl_tp['rr_ratio']
    })

    pd.DataFrame(comparison).to_csv(f'{output_dir}/DOGE_optimization_comparison.csv', index=False)
    print(f"✓ Comparison saved to {output_dir}/DOGE_optimization_comparison.csv")

    # Generate report
    generate_optimization_report(results, output_dir)

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
