"""
ETH Dynamic Position Sizing - Test if intelligent sizing improves profit/DD ratio

Tests multiple sizing approaches:
1. Fixed sizing (baseline)
2. Volatility-based sizing
3. Confidence-based sizing
4. Anti-martingale (winning streak scaling)
5. Kelly Criterion
6. Hybrid approach

Goal: Achieve >4:1 profit/DD ratio with 40%+ return and <10% max drawdown
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import matplotlib.pyplot as plt


def calculate_indicators(df):
    """Calculate technical indicators"""

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    # ATR percentiles for volatility regime detection
    df['atr_20'] = df['tr'].rolling(20).mean()
    df['atr_50'] = df['tr'].rolling(50).mean()
    df['atr_100'] = df['tr'].rolling(100).mean()

    # RSI (multiple periods)
    for period in [7, 14, 21]:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0).rolling(period).mean()
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))

    # EMAs
    for period in [9, 20, 50, 100, 200]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    # SMAs
    for period in [20, 50, 200]:
        df[f'sma_{period}'] = df['close'].rolling(period).mean()

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
    df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
    df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_mid']) * 100
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Volume
    df['vol_sma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_sma']

    # Price action
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['body_pct'] = (df['body'] / df['range'] * 100).fillna(0)

    # Hour of day
    df['hour'] = df['timestamp'].dt.hour

    return df


def calculate_confidence_score(row, df, i):
    """
    Calculate confidence score for a trade setup (0-100)
    Higher score = higher confidence = larger position size
    """
    score = 0

    # RSI extremes (0-20 points)
    if row['rsi_14'] < 25:
        score += 20  # Very oversold
    elif row['rsi_14'] < 30:
        score += 15
    elif row['rsi_14'] > 75:
        score += 20  # Very overbought
    elif row['rsi_14'] > 70:
        score += 15

    # BB position (0-20 points)
    if not pd.isna(row['bb_position']):
        if row['bb_position'] < 0.1:
            score += 20  # At lower band
        elif row['bb_position'] < 0.2:
            score += 15
        elif row['bb_position'] > 0.9:
            score += 20  # At upper band
        elif row['bb_position'] > 0.8:
            score += 15

    # Volume (0-20 points)
    if not pd.isna(row['vol_ratio']):
        if row['vol_ratio'] > 3.0:
            score += 20  # Very high volume
        elif row['vol_ratio'] > 2.5:
            score += 15
        elif row['vol_ratio'] > 2.0:
            score += 10

    # Trend alignment (0-20 points)
    if not pd.isna(row['ema_20']) and not pd.isna(row['ema_50']):
        # Check if EMAs are aligned
        if row['ema_20'] > row['ema_50'] and row['close'] > row['ema_20']:
            score += 20  # Strong uptrend alignment
        elif row['ema_20'] < row['ema_50'] and row['close'] < row['ema_20']:
            score += 20  # Strong downtrend alignment
        elif row['ema_20'] > row['ema_50']:
            score += 10  # Uptrend but price not aligned
        elif row['ema_20'] < row['ema_50']:
            score += 10  # Downtrend but price not aligned

    # Time session (0-20 points) - US session typically best for crypto
    if 13 <= row['hour'] <= 21:  # US session
        score += 20
    elif 7 <= row['hour'] <= 15:  # European session
        score += 10

    return min(score, 100)  # Cap at 100


def calculate_kelly_fraction(recent_trades, max_kelly=0.25):
    """
    Calculate Kelly Criterion fraction based on recent performance
    f = (bp - q) / b
    where:
    - b = odds (avg_win / abs(avg_loss))
    - p = win rate
    - q = 1 - p

    Returns fraction to multiply base size by (0.0 to max_kelly)
    """
    if len(recent_trades) < 10:
        return 1.0  # Not enough data, use base size

    wins = [t['pnl_pct'] for t in recent_trades if t['pnl_pct'] > 0]
    losses = [t['pnl_pct'] for t in recent_trades if t['pnl_pct'] <= 0]

    if not wins or not losses:
        return 0.5  # Conservative if no wins or no losses

    avg_win = np.mean(wins)
    avg_loss = abs(np.mean(losses))

    if avg_loss == 0:
        return 1.0

    b = avg_win / avg_loss  # Odds
    p = len(wins) / len(recent_trades)  # Win rate
    q = 1 - p

    kelly = (b * p - q) / b

    # Use fractional Kelly for safety
    kelly_fraction = max(0.0, min(kelly * max_kelly, max_kelly))

    # Convert to size multiplier (0.5x to 1.5x)
    size_mult = 0.5 + (kelly_fraction / max_kelly)

    return size_mult


def calculate_position_size(row, df, i, recent_trades, base_size=100, method='fixed',
                           avg_atr_pct=None):
    """
    Calculate position size based on method

    Args:
        row: Current row data
        df: Full dataframe
        i: Current index
        recent_trades: List of recent trades for performance tracking
        base_size: Base position size (e.g., $100)
        method: Sizing method to use
        avg_atr_pct: Average ATR% for volatility comparison

    Returns:
        Position size as float
    """

    if method == 'fixed':
        return base_size

    elif method == 'volatility':
        if pd.isna(row['atr_pct']) or avg_atr_pct is None or avg_atr_pct == 0:
            return base_size

        atr_ratio = row['atr_pct'] / avg_atr_pct

        if atr_ratio < 0.8:
            return base_size * 1.5  # Low volatility = larger size
        elif atr_ratio > 1.2:
            return base_size * 0.5  # High volatility = smaller size
        else:
            return base_size

    elif method == 'confidence':
        score = calculate_confidence_score(row, df, i)

        if score >= 80:
            return base_size * 1.5  # High confidence
        elif score >= 60:
            return base_size * 1.0  # Medium confidence
        elif score >= 40:
            return base_size * 0.7  # Low confidence
        else:
            return 0  # Skip trade (too low confidence)

    elif method == 'anti_martingale':
        if len(recent_trades) < 2:
            return base_size

        # Count consecutive wins
        consecutive_wins = 0
        for trade in reversed(recent_trades):
            if trade['pnl_pct'] > 0:
                consecutive_wins += 1
            else:
                break

        if consecutive_wins >= 3:
            return base_size * 1.5
        elif consecutive_wins >= 2:
            return base_size * 1.3
        else:
            return base_size

    elif method == 'kelly':
        kelly_mult = calculate_kelly_fraction(recent_trades[-30:] if len(recent_trades) > 30 else recent_trades)
        return base_size * kelly_mult

    elif method == 'hybrid':
        # Combine volatility + confidence
        vol_mult = 1.0
        if not pd.isna(row['atr_pct']) and avg_atr_pct is not None and avg_atr_pct > 0:
            atr_ratio = row['atr_pct'] / avg_atr_pct
            if atr_ratio < 0.8:
                vol_mult = 1.3
            elif atr_ratio > 1.2:
                vol_mult = 0.6

        conf_mult = 1.0
        score = calculate_confidence_score(row, df, i)
        if score >= 80:
            conf_mult = 1.3
        elif score >= 60:
            conf_mult = 1.0
        elif score >= 40:
            conf_mult = 0.7
        else:
            return 0  # Skip

        return base_size * vol_mult * conf_mult

    return base_size


def rsi_mean_reversion_strategy(df, i, rsi_period=14, oversold=30, overbought=70,
                                stop_mult=2.0, target_mult=4.0):
    """RSI mean reversion strategy - baseline"""
    row = df.iloc[i]

    if pd.isna(row[f'rsi_{rsi_period}']) or pd.isna(row['atr']):
        return None

    rsi = row[f'rsi_{rsi_period}']

    # LONG: RSI oversold
    if rsi < oversold:
        return {
            'direction': 'LONG',
            'entry_price': row['close'],
            'stop_loss': row['close'] - (stop_mult * row['atr']),
            'take_profit': row['close'] + (target_mult * row['atr'])
        }

    # SHORT: RSI overbought
    elif rsi > overbought:
        return {
            'direction': 'SHORT',
            'entry_price': row['close'],
            'stop_loss': row['close'] + (stop_mult * row['atr']),
            'take_profit': row['close'] - (target_mult * row['atr'])
        }

    return None


def backtest_with_sizing(df, strategy_func, sizing_method='fixed', base_size=100,
                        strategy_params=None):
    """
    Backtest a strategy with dynamic position sizing

    Returns:
        Dictionary with performance metrics and trades
    """
    if strategy_params is None:
        strategy_params = {}

    trades = []
    in_position = False
    entry_price = None
    stop_loss = None
    take_profit = None
    entry_idx = None
    direction = None
    position_size = None

    # Calculate average ATR% for volatility sizing
    avg_atr_pct = df['atr_pct'].mean() if 'atr_pct' in df.columns else None

    for i in range(250, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Check for entry signal
            signal = strategy_func(df, i, **strategy_params)

            if signal:
                # Calculate position size based on method
                size = calculate_position_size(
                    row, df, i, trades, base_size, sizing_method, avg_atr_pct
                )

                if size > 0:  # Only enter if size > 0 (confidence filter)
                    in_position = True
                    entry_price = signal['entry_price']
                    stop_loss = signal['stop_loss']
                    take_profit = signal['take_profit']
                    direction = signal['direction']
                    entry_idx = i
                    position_size = size

        else:
            # Check for exit
            exit_price = None
            exit_type = None

            if direction == 'LONG':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'

            elif direction == 'SHORT':
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'

            if exit_price:
                # Calculate PnL
                if direction == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'pnl_pct': pnl_pct,
                    'position_size': position_size,
                    'timestamp': df.iloc[i]['timestamp']
                })

                in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)

    # Calculate metrics WITH position sizing
    # Each trade's PnL is weighted by its position size
    trades_df['weighted_pnl'] = trades_df['pnl_pct'] * (trades_df['position_size'] / base_size)

    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0

    avg_win = wins['pnl_pct'].mean() if num_wins > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if num_losses > 0 else 0

    # Total return using weighted PnL
    total_return = trades_df['weighted_pnl'].sum()

    # Drawdown using weighted PnL
    cumulative = (1 + trades_df['weighted_pnl'] / 100).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Profit/DD ratio
    profit_dd_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    # Position sizing stats
    avg_position_size = trades_df['position_size'].mean()
    max_position_size = trades_df['position_size'].max()
    min_position_size = trades_df['position_size'].min()

    return {
        'sizing_method': sizing_method,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'profit_dd_ratio': profit_dd_ratio,
        'avg_position_size': avg_position_size,
        'max_position_size': max_position_size,
        'min_position_size': min_position_size,
        'trades_df': trades_df
    }


def analyze_sizing_effectiveness(trades_df, base_size):
    """
    Analyze when sizing up/down helped or hurt
    """
    trades_df['size_mult'] = trades_df['position_size'] / base_size

    # Group by size multiplier
    large_positions = trades_df[trades_df['size_mult'] >= 1.3]
    normal_positions = trades_df[(trades_df['size_mult'] > 0.9) & (trades_df['size_mult'] < 1.3)]
    small_positions = trades_df[trades_df['size_mult'] <= 0.9]

    analysis = {}

    for name, group in [('Large (1.3x+)', large_positions),
                        ('Normal (0.9-1.3x)', normal_positions),
                        ('Small (<0.9x)', small_positions)]:
        if len(group) > 0:
            wins = len(group[group['pnl_pct'] > 0])
            analysis[name] = {
                'count': len(group),
                'win_rate': (wins / len(group)) * 100,
                'avg_pnl': group['pnl_pct'].mean(),
                'total_contribution': group['weighted_pnl'].sum()
            }

    return analysis


def main():
    print("="*80)
    print("ETH DYNAMIC POSITION SIZING TEST")
    print("="*80)

    # Load data
    data_path = Path(__file__).parent / 'eth_usdt_1m_lbank.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

    # Calculate indicators
    print("\nCalculating indicators...")
    df = calculate_indicators(df)
    df = df.dropna()

    print(f"Candles after indicator calculation: {len(df):,}")

    # Best strategy from discovery (RSI mean reversion)
    strategy_params = {
        'rsi_period': 14,
        'oversold': 30,
        'overbought': 70,
        'stop_mult': 2.0,
        'target_mult': 4.0
    }

    base_size = 100  # Base position size ($100)

    # Test all sizing methods
    methods = ['fixed', 'volatility', 'confidence', 'anti_martingale', 'kelly', 'hybrid']
    results = []

    print("\n" + "="*80)
    print("TESTING POSITION SIZING METHODS")
    print("="*80)

    for method in methods:
        print(f"\nTesting: {method.upper()}...")
        result = backtest_with_sizing(
            df,
            rsi_mean_reversion_strategy,
            sizing_method=method,
            base_size=base_size,
            strategy_params=strategy_params
        )

        if result:
            results.append(result)
            print(f"  Trades: {result['total_trades']}")
            print(f"  Return: {result['total_return']:+.2f}%")
            print(f"  Max DD: {result['max_dd']:.2f}%")
            print(f"  Profit/DD: {result['profit_dd_ratio']:.2f}:1")
            print(f"  Avg Size: ${result['avg_position_size']:.0f}")
            print(f"  Size Range: ${result['min_position_size']:.0f} - ${result['max_position_size']:.0f}")

    # Compare results
    print("\n" + "="*80)
    print("SIZING METHOD COMPARISON")
    print("="*80)

    comparison_df = pd.DataFrame([{
        'Method': r['sizing_method'],
        'Profit/DD Ratio': r['profit_dd_ratio'],
        'Total Return %': r['total_return'],
        'Max DD %': r['max_dd'],
        'Trades': r['total_trades'],
        'Win Rate %': r['win_rate'],
        'Avg Size $': r['avg_position_size'],
        'Max Size $': r['max_position_size']
    } for r in results])

    comparison_df = comparison_df.sort_values('Profit/DD Ratio', ascending=False)
    print("\n" + comparison_df.to_string(index=False))

    # Calculate improvement vs fixed
    fixed_result = next((r for r in results if r['sizing_method'] == 'fixed'), None)

    if fixed_result:
        print("\n" + "="*80)
        print("IMPROVEMENT VS FIXED SIZING")
        print("="*80)

        for result in results:
            if result['sizing_method'] != 'fixed':
                ratio_improvement = ((result['profit_dd_ratio'] - fixed_result['profit_dd_ratio'])
                                   / fixed_result['profit_dd_ratio'] * 100)
                return_improvement = result['total_return'] - fixed_result['total_return']

                print(f"\n{result['sizing_method'].upper()}:")
                print(f"  Profit/DD Ratio: {ratio_improvement:+.1f}% improvement")
                print(f"  Total Return: {return_improvement:+.2f}% difference")

    # Find best method
    best_result = max(results, key=lambda x: x['profit_dd_ratio'])

    print("\n" + "="*80)
    print("BEST DYNAMIC SIZING STRATEGY")
    print("="*80)

    print(f"\nMethod: {best_result['sizing_method'].upper()}")
    print(f"Profit/DD Ratio: {best_result['profit_dd_ratio']:.2f}:1")
    print(f"Total Return: {best_result['total_return']:+.2f}%")
    print(f"Max Drawdown: {best_result['max_dd']:.2f}%")
    print(f"Win Rate: {best_result['win_rate']:.1f}%")
    print(f"Total Trades: {best_result['total_trades']}")

    # Analyze sizing effectiveness
    sizing_analysis = analyze_sizing_effectiveness(best_result['trades_df'], base_size)

    print("\n" + "="*80)
    print("POSITION SIZE DISTRIBUTION ANALYSIS")
    print("="*80)

    for size_group, stats in sizing_analysis.items():
        print(f"\n{size_group}:")
        print(f"  Count: {stats['count']} trades ({stats['count']/best_result['total_trades']*100:.1f}%)")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Avg PnL: {stats['avg_pnl']:+.2f}%")
        print(f"  Total Contribution: {stats['total_contribution']:+.2f}%")

    # Calculate with leverage
    print("\n" + "="*80)
    print("LEVERAGE PROJECTION")
    print("="*80)

    for leverage in [5, 10, 20]:
        fee_pct = 0.005
        leveraged_return = best_result['total_return'] * leverage
        leveraged_dd = best_result['max_dd'] * leverage

        # Subtract fees
        total_fees = best_result['total_trades'] * 2 * fee_pct * leverage
        net_return = leveraged_return - total_fees

        print(f"\n{leverage}x Leverage:")
        print(f"  Expected Return: {net_return:+.2f}% (gross: {leveraged_return:+.2f}%)")
        print(f"  Max Drawdown: {leveraged_dd:.2f}%")
        print(f"  Total Fees: {total_fees:.2f}%")

        if leveraged_dd > 0:
            net_ratio = abs(net_return / leveraged_dd)
            print(f"  Profit/DD Ratio: {net_ratio:.2f}:1")

            if net_return > 40 and leveraged_dd < 10:
                print(f"  ✅ MEETS TARGET: >40% return with <10% DD")

    # Save detailed results
    output_path = Path(__file__).parent / 'results'
    output_path.mkdir(exist_ok=True)

    # Save comparison
    comparison_file = output_path / 'eth_sizing_comparison.csv'
    comparison_df.to_csv(comparison_file, index=False)
    print(f"\n\nComparison saved to: {comparison_file}")

    # Save best strategy trades
    trades_file = output_path / f'eth_{best_result["sizing_method"]}_trades.csv'
    best_result['trades_df'].to_csv(trades_file, index=False)
    print(f"Best strategy trades saved to: {trades_file}")

    # Generate markdown report
    report = generate_markdown_report(results, fixed_result, best_result, sizing_analysis,
                                     strategy_params, base_size)

    report_file = output_path / 'eth_dynamic_sizing_results.md'
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"Full report saved to: {report_file}")

    # Plot equity curves
    plot_equity_curves(results, output_path)


def plot_equity_curves(results, output_path):
    """Plot equity curves for all sizing methods"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    for result in results:
        trades_df = result['trades_df']
        cumulative = (1 + trades_df['weighted_pnl'] / 100).cumprod()

        ax1.plot(range(len(cumulative)), cumulative, label=result['sizing_method'], linewidth=2)

    ax1.set_title('Equity Curves - All Sizing Methods', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Trade Number')
    ax1.set_ylabel('Cumulative Return (multiple)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Profit/DD comparison bar chart
    methods = [r['sizing_method'] for r in results]
    ratios = [r['profit_dd_ratio'] for r in results]

    colors = ['red' if r['sizing_method'] == 'fixed' else 'green' for r in results]
    ax2.bar(methods, ratios, color=colors, alpha=0.7)
    ax2.set_title('Profit/DD Ratio Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Sizing Method')
    ax2.set_ylabel('Profit/DD Ratio')
    ax2.axhline(y=4.0, color='blue', linestyle='--', label='Target (4:1)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plot_file = output_path / 'eth_sizing_comparison.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {plot_file}")
    plt.close()


def generate_markdown_report(results, fixed_result, best_result, sizing_analysis,
                            strategy_params, base_size):
    """Generate markdown report"""

    report = f"""# ETH Dynamic Position Sizing Results

## Executive Summary

**Goal:** Test if dynamic position sizing improves profit-to-drawdown ratio on ETH/USDT
**Target:** >4:1 profit/DD ratio with 40%+ return and <10% max drawdown

### Best Result: {best_result['sizing_method'].upper()}

- **Profit/DD Ratio:** {best_result['profit_dd_ratio']:.2f}:1
- **Total Return:** {best_result['total_return']:+.2f}%
- **Max Drawdown:** {best_result['max_dd']:.2f}%
- **Win Rate:** {best_result['win_rate']:.1f}%
- **Total Trades:** {best_result['total_trades']}

"""

    if best_result['profit_dd_ratio'] >= 4.0:
        report += "✅ **SUCCESS:** Achieved >4:1 profit/DD ratio!\n\n"
    else:
        report += "⚠️ **PARTIAL SUCCESS:** Did not achieve 4:1 ratio, but improved over baseline\n\n"

    report += f"""## Strategy Details

**Base Strategy:** RSI Mean Reversion
- RSI Period: {strategy_params['rsi_period']}
- Oversold Threshold: {strategy_params['oversold']}
- Overbought Threshold: {strategy_params['overbought']}
- Stop Loss: {strategy_params['stop_mult']}x ATR
- Take Profit: {strategy_params['target_mult']}x ATR

**Base Position Size:** ${base_size}

## 1. Baseline (Fixed Sizing)

"""

    if fixed_result:
        report += f"""| Metric | Value |
|--------|-------|
| Profit/DD Ratio | {fixed_result['profit_dd_ratio']:.2f}:1 |
| Total Return | {fixed_result['total_return']:+.2f}% |
| Max Drawdown | {fixed_result['max_dd']:.2f}% |
| Win Rate | {fixed_result['win_rate']:.1f}% |
| Total Trades | {fixed_result['total_trades']} |
| Avg Win | {fixed_result['avg_win']:+.2f}% |
| Avg Loss | {fixed_result['avg_loss']:.2f}% |

"""

    report += """## 2. Sizing Method Comparison

| Method | Profit/DD | Return % | Max DD % | Trades | Win Rate % | Avg Size | Max Size | Improvement |
|--------|-----------|----------|----------|--------|------------|----------|----------|-------------|
"""

    for result in sorted(results, key=lambda x: x['profit_dd_ratio'], reverse=True):
        improvement = ""
        if fixed_result and result['sizing_method'] != 'fixed':
            ratio_imp = ((result['profit_dd_ratio'] - fixed_result['profit_dd_ratio'])
                        / fixed_result['profit_dd_ratio'] * 100)
            improvement = f"{ratio_imp:+.1f}%"

        report += f"| {result['sizing_method']} | {result['profit_dd_ratio']:.2f}:1 | "
        report += f"{result['total_return']:+.2f}% | {result['max_dd']:.2f}% | "
        report += f"{result['total_trades']} | {result['win_rate']:.1f}% | "
        report += f"${result['avg_position_size']:.0f} | ${result['max_position_size']:.0f} | "
        report += f"{improvement} |\n"

    report += f"""
## 3. Best Dynamic Sizing Strategy: {best_result['sizing_method'].upper()}

### Method Description

"""

    if best_result['sizing_method'] == 'volatility':
        report += """**Volatility-Based Sizing:**
- Low volatility (ATR < 0.8x avg) → 1.5x size (ranging market = better for mean reversion)
- Normal volatility → 1.0x size
- High volatility (ATR > 1.2x avg) → 0.5x size (reduce risk)
"""
    elif best_result['sizing_method'] == 'confidence':
        report += """**Confidence-Based Sizing:**
Scores each setup 0-100 based on:
- RSI extremes: +20 points
- BB position: +20 points
- Volume spike: +20 points
- Trend alignment: +20 points
- Time session: +20 points

Size based on score:
- 80-100: 1.5x (high confidence)
- 60-79: 1.0x (medium)
- 40-59: 0.7x (low)
- <40: skip trade
"""
    elif best_result['sizing_method'] == 'anti_martingale':
        report += """**Anti-Martingale (Winning Streak Scaling):**
- 3+ wins in row → 1.5x size
- 2 wins in row → 1.3x size
- After any loss → reset to 1.0x size
- Never increase after losses
"""
    elif best_result['sizing_method'] == 'kelly':
        report += """**Kelly Criterion:**
- Calculate optimal size: f = (bp - q) / b
- Use 0.25x fractional Kelly for safety
- Recalculate every 30 trades
- Size range: 0.5x to 1.5x
"""
    elif best_result['sizing_method'] == 'hybrid':
        report += """**Hybrid (Volatility + Confidence):**
- Combines volatility multiplier (0.6x to 1.3x)
- With confidence multiplier (0.7x to 1.3x)
- Final size = base × vol_mult × conf_mult
- Skips trades with confidence <40
"""

    report += f"""
### Position Size Distribution

"""

    for size_group, stats in sizing_analysis.items():
        pct = (stats['count'] / best_result['total_trades']) * 100
        report += f"""**{size_group}:**
- Trades: {stats['count']} ({pct:.1f}%)
- Win Rate: {stats['win_rate']:.1f}%
- Avg PnL: {stats['avg_pnl']:+.2f}%
- Total Contribution: {stats['total_contribution']:+.2f}%

"""

    report += """## 4. Leverage Projection

"""

    for leverage in [5, 10, 20]:
        fee_pct = 0.005
        leveraged_return = best_result['total_return'] * leverage
        leveraged_dd = best_result['max_dd'] * leverage
        total_fees = best_result['total_trades'] * 2 * fee_pct * leverage
        net_return = leveraged_return - total_fees

        report += f"""### {leverage}x Leverage

- Gross Return: {leveraged_return:+.2f}%
- Fees ({fee_pct*100:.2f}% per side): -{total_fees:.2f}%
- **Net Return: {net_return:+.2f}%**
- **Max Drawdown: {leveraged_dd:.2f}%**
"""

        if leveraged_dd > 0:
            net_ratio = abs(net_return / leveraged_dd)
            report += f"- Profit/DD Ratio: {net_ratio:.2f}:1\n"

            if net_return > 40 and leveraged_dd < 10:
                report += "- ✅ **MEETS TARGET:** >40% return with <10% DD\n"

        report += "\n"

    report += """## 5. Key Insights

"""

    # Compare best vs fixed
    if fixed_result and best_result['sizing_method'] != 'fixed':
        ratio_imp = ((best_result['profit_dd_ratio'] - fixed_result['profit_dd_ratio'])
                    / fixed_result['profit_dd_ratio'] * 100)
        return_diff = best_result['total_return'] - fixed_result['total_return']

        if ratio_imp > 10:
            report += f"### ✅ Dynamic Sizing Significantly Improves Performance\n\n"
            report += f"- Profit/DD ratio improved by **{ratio_imp:.1f}%**\n"
            report += f"- Total return increased by **{return_diff:+.2f}%**\n"
        elif ratio_imp > 0:
            report += f"### ⚠️ Dynamic Sizing Shows Modest Improvement\n\n"
            report += f"- Profit/DD ratio improved by {ratio_imp:.1f}%\n"
            report += f"- Total return changed by {return_diff:+.2f}%\n"
        else:
            report += f"### ❌ Dynamic Sizing Did Not Improve Performance\n\n"
            report += f"- Fixed sizing outperformed by {abs(ratio_imp):.1f}%\n"

    # Analyze which method works best
    top_3 = sorted(results, key=lambda x: x['profit_dd_ratio'], reverse=True)[:3]
    report += f"\n### Best Sizing Methods (Top 3)\n\n"
    for i, r in enumerate(top_3, 1):
        report += f"{i}. **{r['sizing_method']}**: {r['profit_dd_ratio']:.2f}:1 profit/DD\n"

    report += f"""
### When Did Sizing Up/Down Help?

The {best_result['sizing_method']} method achieved best results by:
"""

    # Analyze sizing patterns
    if 'Large (1.3x+)' in sizing_analysis:
        large_stats = sizing_analysis['Large (1.3x+)']
        if large_stats['avg_pnl'] > 0:
            report += f"- **Sizing up (1.3x+)** on {large_stats['count']} trades with {large_stats['win_rate']:.1f}% win rate contributed {large_stats['total_contribution']:+.2f}%\n"
        else:
            report += f"- ⚠️ **Sizing up** on {large_stats['count']} trades hurt performance (avg PnL: {large_stats['avg_pnl']:.2f}%)\n"

    if 'Small (<0.9x)' in sizing_analysis:
        small_stats = sizing_analysis['Small (<0.9x)']
        report += f"- **Sizing down (<0.9x)** on {small_stats['count']} trades protected capital\n"

    report += """
## 6. Risks & Considerations

### Position Sizing Risks

"""

    max_size_multiple = best_result['max_position_size'] / base_size

    if max_size_multiple > 2.0:
        report += f"⚠️ **High Risk:** Max position reached {max_size_multiple:.1f}x base size\n"

    report += f"""- Maximum position: ${best_result['max_position_size']:.0f} ({max_size_multiple:.1f}x base)
- Minimum position: ${best_result['min_position_size']:.0f}
- Average position: ${best_result['avg_position_size']:.0f}

### What Could Go Wrong?

"""

    if best_result['sizing_method'] == 'anti_martingale':
        report += """- **Winning streak followed by large loss:** Could hurt if max-sized positions start losing
- **Mitigation:** Cap max multiplier at 1.5x, reset after any loss
"""
    elif best_result['sizing_method'] == 'confidence':
        report += """- **Overconfidence in signals:** High-confidence setups could still lose
- **Mitigation:** Diversify signals used in scoring, backtest extensively
"""
    elif best_result['sizing_method'] == 'volatility':
        report += """- **Volatility regime shifts:** Low volatility can suddenly spike
- **Mitigation:** Use real-time ATR, update frequently
"""

    report += """
## 7. Recommendation

"""

    if best_result['profit_dd_ratio'] >= 4.0:
        report += f"### ✅ USE DYNAMIC SIZING: {best_result['sizing_method'].upper()}\n\n"
        report += f"The {best_result['sizing_method']} method achieved the target >4:1 profit/DD ratio.\n\n"
        report += "**Recommended Parameters:**\n"
        report += f"- Base position size: ${base_size}\n"
        report += f"- Expected profit/DD ratio: {best_result['profit_dd_ratio']:.2f}:1\n"

        # Find optimal leverage
        for lev in [5, 10, 15, 20]:
            net_ret = (best_result['total_return'] * lev) - (best_result['total_trades'] * 2 * 0.005 * lev)
            net_dd = best_result['max_dd'] * lev
            if 40 <= net_ret <= 60 and net_dd < 10:
                report += f"- **Recommended leverage: {lev}x** (expected: {net_ret:+.1f}% return, {net_dd:.1f}% DD)\n"
                break

    else:
        best_fixed_or_dynamic = max(results, key=lambda x: x['profit_dd_ratio'])

        if best_fixed_or_dynamic['sizing_method'] == 'fixed':
            report += f"### ⚠️ STICK WITH FIXED SIZING\n\n"
            report += f"Dynamic sizing did not improve results. Fixed sizing achieved {fixed_result['profit_dd_ratio']:.2f}:1 profit/DD.\n\n"
        else:
            report += f"### ✅ USE {best_result['sizing_method'].upper()} WITH CAUTION\n\n"
            report += f"Improved profit/DD to {best_result['profit_dd_ratio']:.2f}:1 (target was 4:1).\n\n"
            report += "**Consider:**\n"
            report += "- Further optimization of sizing parameters\n"
            report += "- Combining with better base strategy\n"
            report += "- Testing on different market conditions\n"

    report += """
## 8. Files Generated

- `eth_sizing_comparison.csv` - Comparison table of all methods
- `eth_{method}_trades.csv` - Detailed trade log for best method
- `eth_sizing_comparison.png` - Equity curves and profit/DD chart
- `eth_dynamic_sizing_results.md` - This report

---

*Generated by eth_dynamic_sizing_test.py*
"""

    return report


if __name__ == "__main__":
    main()
