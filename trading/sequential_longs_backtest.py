"""
Sequential Longs Strategy Backtest
===================================
Tests 30 configurations of position sizing and daily trade limits.

Strategy:
- Enter LONG on any green candle (close > open)
- Stop loss = LOW of entry candle
- NO take profit - let winners run
- Sequential (one position at a time)
- Daily limit on stopped-out trades
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =====================================
# POSITION SIZING FUNCTIONS
# =====================================

def get_fixed_100_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """Fixed 100% capital every trade"""
    return 1.0

def get_ramp_up_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """
    Ramp up after losses:
    - Trade 1-2: 10%
    - Trade 3-4: 50%
    - Trade 5+: 100%
    - Reset to 10% after win
    """
    if consecutive_losses == 0:  # Just won
        return 0.10
    elif consecutive_losses <= 2:
        return 0.10
    elif consecutive_losses <= 4:
        return 0.50
    else:
        return 1.0

def get_gradual_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """
    Gradual increase per trade within day:
    - Trade 1: 20%
    - Trade 2: 40%
    - Trade 3: 60%
    - Trade 4: 80%
    - Trade 5+: 100%
    """
    sizes = [0.20, 0.40, 0.60, 0.80, 1.0]
    idx = min(trade_num_today, len(sizes) - 1)
    return sizes[idx]

def get_martingale_light_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """
    Martingale Light - double after each loss (capped):
    - Start: 10%
    - After loss 1: 20%
    - After loss 2: 40%
    - After loss 3: 80%
    - After loss 4+: 100% (cap)
    - Reset to 10% after win
    """
    if consecutive_losses == 0:  # Just won
        return 0.10

    sizes = [0.10, 0.20, 0.40, 0.80, 1.0]
    idx = min(consecutive_losses, len(sizes) - 1)
    return sizes[idx]

def get_anti_martingale_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """
    Anti-Martingale - increase after wins, decrease after losses:
    - Start: 50%
    - After win: 75%, then 100%
    - After loss: 25%, then 10%
    """
    if consecutive_wins >= 2:
        return 1.0
    elif consecutive_wins == 1:
        return 0.75
    elif consecutive_losses == 0 and consecutive_wins == 0:
        return 0.50
    elif consecutive_losses == 1:
        return 0.25
    else:  # 2+ losses
        return 0.10

def get_kelly_inspired_size(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats):
    """
    Kelly-Inspired sizing based on rolling statistics:
    - Calculate from rolling 20-trade window
    - Formula: size = win_rate - (lose_rate / reward_risk_ratio)
    - Minimum 10%, maximum 100%
    """
    if rolling_stats['total_trades'] < 5:
        return 0.50  # Default until we have enough data

    win_rate = rolling_stats['win_rate']
    lose_rate = 1 - win_rate

    if rolling_stats['avg_loss'] == 0:
        return 1.0

    reward_risk = abs(rolling_stats['avg_win'] / rolling_stats['avg_loss'])

    if reward_risk == 0:
        kelly_fraction = 0.10
    else:
        kelly_fraction = win_rate - (lose_rate / reward_risk)

    # Cap between 10% and 100%
    kelly_fraction = max(0.10, min(1.0, kelly_fraction))

    # Use half-kelly for safety
    return kelly_fraction * 0.5

SIZING_FUNCTIONS = {
    'Fixed100': get_fixed_100_size,
    'RampUp': get_ramp_up_size,
    'Gradual': get_gradual_size,
    'MartingaleLight': get_martingale_light_size,
    'AntiMartingale': get_anti_martingale_size,
    'KellyInspired': get_kelly_inspired_size,
}

# =====================================
# BACKTEST ENGINE
# =====================================

def calculate_rolling_stats(recent_trades, window=20):
    """Calculate rolling statistics for Kelly sizing"""
    if len(recent_trades) == 0:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0
        }

    recent = recent_trades[-window:]
    wins = [t for t in recent if t['pnl_pct'] > 0]
    losses = [t for t in recent if t['pnl_pct'] <= 0]

    return {
        'total_trades': len(recent),
        'win_rate': len(wins) / len(recent) if recent else 0,
        'avg_win': np.mean([t['pnl_pct'] for t in wins]) if wins else 0,
        'avg_loss': np.mean([t['pnl_pct'] for t in losses]) if losses else 0,
    }

def backtest_sequential_longs(df, daily_limit, sizing_func_name, initial_capital=10000):
    """
    Backtest the Sequential Longs strategy.

    Parameters:
    -----------
    df : DataFrame with OHLCV data
    daily_limit : int or None (unlimited)
    sizing_func_name : str, name of sizing function
    initial_capital : float, starting capital

    Returns:
    --------
    trades : list of trade dictionaries
    equity_curve : list of (timestamp, equity) tuples
    """
    sizing_func = SIZING_FUNCTIONS[sizing_func_name]

    capital = initial_capital
    position = None
    daily_stopped_trades = 0
    current_day = None
    trades = []
    equity_curve = [(df.iloc[0]['timestamp'], capital)]

    # For position sizing
    consecutive_losses = 0
    consecutive_wins = 0
    trade_num_today = 0
    all_trades_for_stats = []

    FEE = 0.001  # 0.10% round-trip

    for i in range(len(df)):
        row = df.iloc[i]
        day = row['timestamp'].date()

        # Reset daily counter at midnight
        if day != current_day:
            current_day = day
            daily_stopped_trades = 0
            trade_num_today = 0

        # Check if we have an open position
        if position is not None:
            # Check if stop loss was hit
            if row['low'] <= position['stop_loss']:
                # Exit at stop loss
                exit_price = position['stop_loss']
                exit_time = row['timestamp']

                # Calculate P&L
                price_change = (exit_price - position['entry']) / position['entry']
                pnl_pct = price_change - FEE
                position_size_capital = capital * position['size_pct']
                pnl_dollars = position_size_capital * pnl_pct

                # Update capital
                capital += pnl_dollars

                # Record trade
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': exit_time,
                    'entry_price': position['entry'],
                    'exit_price': exit_price,
                    'stop_loss': position['stop_loss'],
                    'size_pct': position['size_pct'],
                    'pnl_pct': pnl_pct,
                    'pnl_dollars': pnl_dollars,
                    'capital_after': capital,
                    'trade_num_today': trade_num_today,
                }
                trades.append(trade)
                all_trades_for_stats.append(trade)

                # Update consecutive counters
                if pnl_pct > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0

                # Close position
                position = None
                daily_stopped_trades += 1

                # Update equity curve
                equity_curve.append((exit_time, capital))

        # Check for entry signal (no position + green candle + within daily limit)
        if position is None:
            # Check daily limit
            if daily_limit is not None and daily_stopped_trades >= daily_limit:
                continue  # Skip rest of day

            # Check for green candle
            is_green = row['close'] > row['open']

            if is_green:
                # Calculate position size
                rolling_stats = calculate_rolling_stats(all_trades_for_stats)
                size_pct = sizing_func(trade_num_today, consecutive_losses, consecutive_wins, rolling_stats)

                # Enter position
                position = {
                    'entry': row['close'],
                    'stop_loss': row['low'],
                    'size_pct': size_pct,
                    'entry_time': row['timestamp'],
                }

                trade_num_today += 1

    # Close any open position at end of data
    if position is not None:
        last_row = df.iloc[-1]
        exit_price = last_row['close']
        exit_time = last_row['timestamp']

        price_change = (exit_price - position['entry']) / position['entry']
        pnl_pct = price_change - FEE
        position_size_capital = capital * position['size_pct']
        pnl_dollars = position_size_capital * pnl_pct

        capital += pnl_dollars

        trade = {
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'entry_price': position['entry'],
            'exit_price': exit_price,
            'stop_loss': position['stop_loss'],
            'size_pct': position['size_pct'],
            'pnl_pct': pnl_pct,
            'pnl_dollars': pnl_dollars,
            'capital_after': capital,
            'trade_num_today': trade_num_today,
        }
        trades.append(trade)
        equity_curve.append((exit_time, capital))

    return trades, equity_curve

# =====================================
# ANALYSIS FUNCTIONS
# =====================================

def calculate_metrics(trades, equity_curve, initial_capital):
    """Calculate performance metrics from trades"""
    if len(trades) == 0:
        return {
            'total_return_pct': 0,
            'final_capital': initial_capital,
            'max_drawdown_pct': 0,
            'total_trades': 0,
            'win_rate_pct': 0,
            'avg_win_pct': 0,
            'avg_loss_pct': 0,
            'profit_factor': 0,
            'best_trade_pct': 0,
            'worst_trade_pct': 0,
            'avg_trades_per_day': 0,
        }

    final_capital = trades[-1]['capital_after']
    total_return = (final_capital - initial_capital) / initial_capital * 100

    # Calculate drawdown
    equity_values = [e[1] for e in equity_curve]
    peak = equity_values[0]
    max_dd = 0
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Win/loss stats
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]

    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t['pnl_pct'] for t in wins]) * 100 if wins else 0
    avg_loss = np.mean([t['pnl_pct'] for t in losses]) * 100 if losses else 0

    # Profit factor
    total_wins = sum([t['pnl_dollars'] for t in wins])
    total_losses = abs(sum([t['pnl_dollars'] for t in losses]))
    profit_factor = total_wins / total_losses if total_losses > 0 else 0

    # Best/worst
    best_trade = max([t['pnl_pct'] for t in trades]) * 100
    worst_trade = min([t['pnl_pct'] for t in trades]) * 100

    # Trades per day
    if len(equity_curve) > 1:
        days = (equity_curve[-1][0] - equity_curve[0][0]).days
        avg_trades_per_day = len(trades) / max(days, 1)
    else:
        avg_trades_per_day = 0

    return {
        'total_return_pct': round(total_return, 2),
        'final_capital': round(final_capital, 2),
        'max_drawdown_pct': round(max_dd, 2),
        'total_trades': len(trades),
        'win_rate_pct': round(win_rate, 2),
        'avg_win_pct': round(avg_win, 2),
        'avg_loss_pct': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'best_trade_pct': round(best_trade, 2),
        'worst_trade_pct': round(worst_trade, 2),
        'avg_trades_per_day': round(avg_trades_per_day, 2),
    }

# =====================================
# MAIN EXECUTION
# =====================================

def main():
    print("=" * 80)
    print("SEQUENTIAL LONGS STRATEGY BACKTEST")
    print("=" * 80)
    print()

    # Load data
    print("Loading data...")
    data_path = "/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv"
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter to last 3 months
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=90)
    df = df[df['timestamp'] >= start_date].reset_index(drop=True)

    print(f"Data loaded: {len(df)} candles")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")
    print()

    # Define test configurations
    daily_limits = [3, 5, 7, 10, None]  # None = unlimited
    sizing_strategies = list(SIZING_FUNCTIONS.keys())

    print(f"Testing {len(daily_limits)} daily limits × {len(sizing_strategies)} sizing strategies")
    print(f"= {len(daily_limits) * len(sizing_strategies)} configurations")
    print()

    # Run backtests
    results = []
    all_equity_curves = {}
    all_trades = {}

    config_num = 0
    total_configs = len(daily_limits) * len(sizing_strategies)

    for daily_limit in daily_limits:
        for sizing_name in sizing_strategies:
            config_num += 1

            # Create config name
            limit_str = f"Limit{daily_limit}" if daily_limit else "LimitNone"
            config_name = f"{limit_str}_{sizing_name}"

            print(f"[{config_num}/{total_configs}] Running {config_name}...", end=" ")

            # Run backtest
            trades, equity_curve = backtest_sequential_longs(
                df,
                daily_limit,
                sizing_name,
                initial_capital=10000
            )

            # Calculate metrics
            metrics = calculate_metrics(trades, equity_curve, 10000)

            # Add config info
            metrics['config_name'] = config_name
            metrics['daily_limit'] = daily_limit if daily_limit else 999
            metrics['sizing_strategy'] = sizing_name

            results.append(metrics)
            all_equity_curves[config_name] = equity_curve
            all_trades[config_name] = trades

            print(f"Return: {metrics['total_return_pct']:+.2f}% | Trades: {metrics['total_trades']} | Win Rate: {metrics['win_rate_pct']:.1f}%")

    print()
    print("=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
    print()

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Sort by total return
    results_df = results_df.sort_values('total_return_pct', ascending=False)

    # Display top 10
    print("TOP 10 CONFIGURATIONS:")
    print("-" * 80)
    display_cols = ['config_name', 'total_return_pct', 'max_drawdown_pct', 'total_trades', 'win_rate_pct', 'profit_factor']
    print(results_df[display_cols].head(10).to_string(index=False))
    print()

    # Save results
    results_path = "/workspaces/Carebiuro_windykacja/trading/results"
    Path(results_path).mkdir(exist_ok=True, parents=True)

    # Save summary
    summary_file = f"{results_path}/sequential_longs_summary.csv"
    results_df.to_csv(summary_file, index=False)
    print(f"✓ Summary saved to: {summary_file}")

    # Save top 5 trade logs
    print()
    print("Saving top 5 trade logs...")
    top_5 = results_df.head(5)
    for idx, row in top_5.iterrows():
        config_name = row['config_name']
        trades = all_trades[config_name]

        if trades:
            trades_df = pd.DataFrame(trades)
            trades_file = f"{results_path}/sequential_longs_trades_{config_name}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"  ✓ {config_name}: {len(trades)} trades")

    # Create equity curve chart
    print()
    print("Creating equity curve chart...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

    # Plot top 5 equity curves
    colors = ['green', 'blue', 'orange', 'red', 'purple']
    for idx, (_, row) in enumerate(top_5.iterrows()):
        config_name = row['config_name']
        equity_curve = all_equity_curves[config_name]

        times = [e[0] for e in equity_curve]
        equities = [e[1] for e in equity_curve]

        label = f"{config_name} ({row['total_return_pct']:+.1f}%)"
        ax1.plot(times, equities, label=label, linewidth=2, alpha=0.8, color=colors[idx])

    ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_title('Sequential Longs Strategy - Top 5 Equity Curves', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Capital ($)')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # Plot drawdown comparison
    for idx, (_, row) in enumerate(top_5.iterrows()):
        config_name = row['config_name']
        equity_curve = all_equity_curves[config_name]

        times = [e[0] for e in equity_curve]
        equities = [e[1] for e in equity_curve]

        # Calculate drawdown
        peak = equities[0]
        drawdowns = []
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            drawdowns.append(-dd)  # Negative for plotting

        label = f"{config_name} (Max: {row['max_drawdown_pct']:.1f}%)"
        ax2.plot(times, drawdowns, label=label, linewidth=2, alpha=0.8, color=colors[idx])

    ax2.set_title('Drawdown Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)

    plt.tight_layout()

    chart_file = f"{results_path}/sequential_longs_equity.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    print(f"✓ Chart saved to: {chart_file}")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Key findings:")
    print(f"  • Best config: {results_df.iloc[0]['config_name']}")
    print(f"  • Best return: {results_df.iloc[0]['total_return_pct']:+.2f}%")
    print(f"  • Best drawdown: {results_df.iloc[0]['max_drawdown_pct']:.2f}%")
    print(f"  • Configs with positive returns: {len(results_df[results_df['total_return_pct'] > 0])}/30")
    print()

if __name__ == "__main__":
    main()
