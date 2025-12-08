#!/usr/bin/env python3
"""
PENGU Mean Reversion Strategy - OPTIMIZED VERSION
Adjustments: Wider stops, tighter targets, stricter filters
Author: Master Strategy Designer
Date: 2025-12-07
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# OPTIMIZED STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2.5  # Wider bands for stronger extremes

# RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 30  # More extreme
RSI_OVERBOUGHT = 70

# ATR
ATR_PERIOD = 14
STOP_LOSS_ATR_MULT = 4.0  # Wider stops (was 2.5)
TAKE_PROFIT_ATR_MULT = 8.0  # Better R:R (was 5.0)

# Volume
VOLUME_SMA_PERIOD = 20
VOLUME_SPIKE_THRESHOLD = 2.0  # Require stronger spike (was 1.5)

# Session Times (UTC hours)
US_SESSION_START = 14
US_SESSION_END = 21

# Risk Management
MAX_HOLD_MINUTES = 60  # Tighter time constraint (was 120)
POSITION_SIZE_PCT = 0.01

# Execution
FEES_PCT = 0.0010
SLIPPAGE_PCT = 0.0005

# Day filters
AVOID_DAYS = [3]  # Thursday
PREFER_DAYS = [1]  # Tuesday


# ═══════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ═══════════════════════════════════════════════════════════════

def calculate_rsi(series, period=14):
    """Calculate RSI indicator"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(series, period=20, std_dev=2.0):
    """Calculate Bollinger Bands"""
    sma = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()

    upper_bb = sma + (std * std_dev)
    lower_bb = sma - (std * std_dev)

    return upper_bb, sma, lower_bb


def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()

    return atr


# ═══════════════════════════════════════════════════════════════
# SESSION & TIMING FILTERS
# ═══════════════════════════════════════════════════════════════

def is_us_session(timestamp):
    """Check if timestamp is in US session (14:00-21:00 UTC)"""
    hour = timestamp.hour
    return US_SESSION_START <= hour < US_SESSION_END


def is_valid_day(timestamp):
    """Check if day is valid for trading (avoid Thursday)"""
    return timestamp.weekday() not in AVOID_DAYS


def is_best_hour(timestamp):
    """Check if it's the best trading hour (21:00 UTC)"""
    return timestamp.hour == 21


# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION - OPTIMIZED
# ═══════════════════════════════════════════════════════════════

def generate_long_signal(row, df, idx):
    """
    OPTIMIZED LONG signal:
    - Stricter BB touch (2.5 std)
    - More extreme RSI (<30)
    - Stronger volume requirement (2x)
    - US Session only
    - Not Thursday
    """
    # Check for NaN values
    if pd.isna(row['lower_bb']) or pd.isna(row['rsi']) or pd.isna(row['volume_sma']):
        return False

    # 1. Price BELOW Lower BB (overshoot)
    below_lower_bb = row['close'] < row['lower_bb']

    # 2. RSI deeply oversold
    rsi_oversold = row['rsi'] < RSI_OVERSOLD

    # 3. Strong volume spike (capitulation)
    volume_spike = row['volume'] > (row['volume_sma'] * VOLUME_SPIKE_THRESHOLD)

    # 4. US Session
    us_session = is_us_session(row['timestamp'])

    # 5. Valid day (not Thursday)
    valid_day = is_valid_day(row['timestamp'])

    # 6. Bonus: Best hour
    best_hour = is_best_hour(row['timestamp'])

    # All conditions must be met (bonus hour is optional boost)
    base_signal = (below_lower_bb and rsi_oversold and volume_spike and
                   us_session and valid_day)

    return base_signal


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

def backtest_pengu_optimized(df, initial_capital=10000):
    """
    Backtest OPTIMIZED PENGU mean reversion strategy
    """

    print(f"\n{'='*70}")
    print(f"PENGU MEAN REVERSION BACKTEST - OPTIMIZED")
    print(f"{'='*70}\n")

    # Calculate indicators
    print("Calculating indicators...")
    df['rsi'] = calculate_rsi(df['close'], RSI_PERIOD)
    df['upper_bb'], df['bb_mid'], df['lower_bb'] = calculate_bollinger_bands(
        df['close'], BB_PERIOD, BB_STD
    )
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], ATR_PERIOD)
    df['volume_sma'] = df['volume'].rolling(window=VOLUME_SMA_PERIOD, min_periods=VOLUME_SMA_PERIOD).mean()

    # Trading variables
    capital = initial_capital
    position = None
    trades = []
    equity = []

    print(f"Starting backtest with ${initial_capital:,.2f}...")
    print(f"BB Std: {BB_STD}")
    print(f"RSI Threshold: <{RSI_OVERSOLD}")
    print(f"Volume Spike: >{VOLUME_SPIKE_THRESHOLD}x")
    print(f"Stop Loss: {STOP_LOSS_ATR_MULT}x ATR")
    print(f"Take Profit: {TAKE_PROFIT_ATR_MULT}x ATR")
    print(f"Max Hold: {MAX_HOLD_MINUTES} min\n")

    # Iterate through data
    for idx, row in df.iterrows():
        equity.append(capital)

        # Skip if we don't have indicators yet
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            continue

        # Manage existing position
        if position is not None:
            entry_time = position['entry_time']
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']

            # Calculate hold time
            hold_minutes = (row['timestamp'] - entry_time).total_seconds() / 60

            # Check exit conditions
            exit_triggered = False
            exit_reason = None
            exit_price = row['close']

            # Stop loss hit
            if row['low'] <= stop_loss:
                exit_triggered = True
                exit_price = stop_loss
                exit_reason = 'Stop Loss'

            # Take profit hit
            elif row['high'] >= take_profit:
                exit_triggered = True
                exit_price = take_profit
                exit_reason = 'Take Profit'

            # Time exit (max hold)
            elif hold_minutes >= MAX_HOLD_MINUTES:
                exit_triggered = True
                exit_price = row['close']
                exit_reason = 'Time Exit'

            # Execute exit
            if exit_triggered:
                # Apply slippage
                exit_price = exit_price * (1 - SLIPPAGE_PCT)

                # Calculate P&L
                pnl_pct = (exit_price / entry_price - 1) - FEES_PCT
                pnl_dollars = capital * POSITION_SIZE_PCT * pnl_pct / abs(pnl_pct) * abs(pnl_pct * 100)
                capital += pnl_dollars

                # Record trade
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'hold_minutes': hold_minutes,
                    'exit_reason': exit_reason,
                    'capital_after': capital,
                    'entry_rsi': position['entry_rsi'],
                    'bb_distance': position['bb_distance']
                })

                position = None

        # Look for new entry (only if no position)
        if position is None:
            if generate_long_signal(row, df, idx):
                entry_price = row['close'] * (1 + SLIPPAGE_PCT)
                stop_loss = entry_price - (row['atr'] * STOP_LOSS_ATR_MULT)
                take_profit = entry_price + (row['atr'] * TAKE_PROFIT_ATR_MULT)

                # Calculate how far below BB we are (for analysis)
                bb_distance_pct = (row['close'] - row['lower_bb']) / row['close'] * 100

                position = {
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_rsi': row['rsi'],
                    'bb_distance': bb_distance_pct
                }

    # Create results DataFrames
    trades_df = pd.DataFrame(trades)
    equity_curve = pd.Series(equity, index=df.index)

    # Calculate metrics
    if len(trades_df) > 0:
        total_return = (capital / initial_capital - 1) * 100
        winning_trades = trades_df[trades_df['pnl_dollars'] > 0]
        losing_trades = trades_df[trades_df['pnl_dollars'] <= 0]

        win_rate = len(winning_trades) / len(trades_df) * 100
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0

        # Risk-Reward Ratio
        rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Max Drawdown
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # Expectancy
        expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

        metrics = {
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'final_capital': capital,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'rr_ratio': rr_ratio,
            'max_drawdown': max_drawdown,
            'expectancy': expectancy,
            'avg_hold_minutes': trades_df['hold_minutes'].mean(),
            'avg_entry_rsi': trades_df['entry_rsi'].mean()
        }
    else:
        metrics = {
            'total_trades': 0,
            'error': 'No trades generated'
        }

    return trades_df, equity_curve, metrics


# ═══════════════════════════════════════════════════════════════
# REPORTING
# ═══════════════════════════════════════════════════════════════

def print_backtest_results(metrics, trades_df):
    """Print formatted backtest results"""
    print(f"\n{'='*70}")
    print("BACKTEST RESULTS")
    print(f"{'='*70}\n")

    if 'error' in metrics:
        print(f"❌ {metrics['error']}")
        return

    print(f"Total Trades:      {metrics['total_trades']}")
    print(f"Winning Trades:    {metrics['winning_trades']} ({metrics['win_rate']:.2f}%)")
    print(f"Losing Trades:     {metrics['losing_trades']}")
    print(f"\nTotal Return:      {metrics['total_return']:+.2f}%")
    print(f"Final Capital:     ${metrics['final_capital']:,.2f}")
    print(f"\nAvg Win:           {metrics['avg_win']:+.2f}%")
    print(f"Avg Loss:          {metrics['avg_loss']:+.2f}%")
    print(f"R:R Ratio:         {metrics['rr_ratio']:.2f}x")
    print(f"Expectancy:        {metrics['expectancy']:+.2f}%")
    print(f"\nMax Drawdown:      {metrics['max_drawdown']:.2f}%")
    print(f"Avg Hold Time:     {metrics['avg_hold_minutes']:.1f} minutes")
    print(f"Avg Entry RSI:     {metrics['avg_entry_rsi']:.1f}")

    print(f"\n{'='*70}\n")

    # Trade distribution
    if len(trades_df) > 0:
        print("Exit Reason Breakdown:")
        exit_reasons = trades_df['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pct = count / len(trades_df) * 100
            print(f"  {reason:15s}: {count:3d} ({pct:5.1f}%)")

        # Win rate by exit reason
        print(f"\nWin Rate by Exit Reason:")
        for reason in exit_reasons.index:
            reason_trades = trades_df[trades_df['exit_reason'] == reason]
            winners = len(reason_trades[reason_trades['pnl_dollars'] > 0])
            wr = winners / len(reason_trades) * 100 if len(reason_trades) > 0 else 0
            print(f"  {reason:15s}: {wr:5.1f}%")


def plot_equity_curve(equity_curve, metrics, output_path):
    """Plot and save equity curve"""
    plt.figure(figsize=(14, 7))

    plt.plot(equity_curve.values, linewidth=2, color='#2E86AB')
    plt.axhline(y=equity_curve.iloc[0], color='gray', linestyle='--', alpha=0.5, label='Starting Capital')

    plt.title(f"PENGU Mean Reversion Strategy - OPTIMIZED Equity Curve\n" +
              f"Return: {metrics['total_return']:+.2f}% | Win Rate: {metrics['win_rate']:.1f}% | " +
              f"R:R: {metrics['rr_ratio']:.2f}x | Max DD: {metrics['max_drawdown']:.2f}%",
              fontsize=14, fontweight='bold')

    plt.xlabel('Trade Number', fontsize=12)
    plt.ylabel('Capital ($)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Equity curve saved to: {output_path}")
    plt.close()


# ═══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════

def main():
    """Main execution function"""

    # Load data
    print("Loading PENGU data...")
    df = pd.read_csv('pengu_usdt_1m_lbank.csv')

    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"Loaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range: ${df['close'].min():.6f} - ${df['close'].max():.6f}\n")

    # Run backtest
    trades_df, equity_curve, metrics = backtest_pengu_optimized(df, initial_capital=10000)

    # Print results
    print_backtest_results(metrics, trades_df)

    # Save results
    if len(trades_df) > 0:
        # Save trade log
        trades_output = 'results/PENGU_strategy_optimized_results.csv'
        trades_df.to_csv(trades_output, index=False)
        print(f"✅ Trade log saved to: {trades_output}")

        # Save equity curve plot
        equity_output = 'results/PENGU_strategy_optimized_equity.png'
        plot_equity_curve(equity_curve, metrics, equity_output)

        # Save summary
        summary_output = 'results/PENGU_strategy_optimized_summary.md'
        with open(summary_output, 'w') as f:
            f.write("# PENGU Mean Reversion Strategy - OPTIMIZED Backtest\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Optimization Changes\n\n")
            f.write("1. **BB Std Dev**: 2.0 → 2.5 (wider bands, stronger extremes)\n")
            f.write("2. **RSI Threshold**: 35 → 30 (more extreme oversold)\n")
            f.write("3. **Volume Spike**: 1.5x → 2.0x (require stronger capitulation)\n")
            f.write("4. **Stop Loss**: 2.5 ATR → 4.0 ATR (wider stops)\n")
            f.write("5. **Take Profit**: 5.0 ATR → 8.0 ATR (better R:R)\n")
            f.write("6. **Max Hold**: 120 min → 60 min (faster exits)\n\n")

            f.write("## Performance Metrics\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| **Total Trades** | {metrics['total_trades']} |\n")
            f.write(f"| **Win Rate** | {metrics['win_rate']:.2f}% |\n")
            f.write(f"| **Total Return** | {metrics['total_return']:+.2f}% |\n")
            f.write(f"| **Final Capital** | ${metrics['final_capital']:,.2f} |\n")
            f.write(f"| **Avg Win** | {metrics['avg_win']:+.2f}% |\n")
            f.write(f"| **Avg Loss** | {metrics['avg_loss']:+.2f}% |\n")
            f.write(f"| **R:R Ratio** | {metrics['rr_ratio']:.2f}x |\n")
            f.write(f"| **Expectancy** | {metrics['expectancy']:+.2f}% |\n")
            f.write(f"| **Max Drawdown** | {metrics['max_drawdown']:.2f}% |\n")
            f.write(f"| **Avg Hold Time** | {metrics['avg_hold_minutes']:.1f} min |\n")
            f.write(f"| **Avg Entry RSI** | {metrics['avg_entry_rsi']:.1f} |\n\n")

            # Validation against targets
            f.write("## Target Validation\n\n")
            checks = []
            checks.append(("Minimum Trades (≥50)", metrics['total_trades'] >= 50, metrics['total_trades']))
            checks.append(("Win Rate (≥35%)", metrics['win_rate'] >= 35, f"{metrics['win_rate']:.1f}%"))
            checks.append(("R:R Ratio (≥1.6x)", metrics['rr_ratio'] >= 1.6, f"{metrics['rr_ratio']:.2f}x"))
            checks.append(("Max Drawdown (>-25%)", metrics['max_drawdown'] > -25, f"{metrics['max_drawdown']:.1f}%"))
            checks.append(("Expectancy (>0%)", metrics['expectancy'] > 0, f"{metrics['expectancy']:+.2f}%"))

            for check_name, passed, value in checks:
                status = "✅" if passed else "❌"
                f.write(f"- {status} **{check_name}**: {value}\n")

        print(f"✅ Summary saved to: {summary_output}")

    print(f"\n{'='*70}")
    print("BACKTEST COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
