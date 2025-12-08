#!/usr/bin/env python3
"""
PENGU Mean Reversion Strategy - Backtest Implementation
Strategy: Fade BB extremes during US session with RSI+Volume confirmation
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
# STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2.0

# RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65

# ATR
ATR_PERIOD = 14
STOP_LOSS_ATR_MULT = 2.5
TAKE_PROFIT_ATR_MULT = 5.0

# Volume
VOLUME_SMA_PERIOD = 20
VOLUME_SPIKE_THRESHOLD = 1.5

# Session Times (UTC hours)
US_SESSION_START = 14
US_SESSION_END = 21
EUROPE_SESSION_START = 7
EUROPE_SESSION_END = 15

# Risk Management
MAX_HOLD_MINUTES = 120
POSITION_SIZE_PCT = 0.01  # 1% risk per trade

# Execution
FEES_PCT = 0.0010  # 0.10% round-trip (BingX futures taker)
SLIPPAGE_PCT = 0.0005  # 0.05% per fill

# Day filters
AVOID_DAYS = [3]  # Thursday (0=Monday, 3=Thursday)
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


def is_europe_session(timestamp):
    """Check if timestamp is in Europe session (7:00-15:00 UTC)"""
    hour = timestamp.hour
    return EUROPE_SESSION_START <= hour < EUROPE_SESSION_END


def is_valid_day(timestamp):
    """Check if day is valid for trading (avoid Thursday)"""
    return timestamp.weekday() not in AVOID_DAYS


# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_long_signal(row, df, idx):
    """
    Generate LONG signal based on:
    1. Price at Lower BB
    2. RSI < 35
    3. Volume spike > 1.5x avg
    4. US Session (14-21 UTC)
    5. Not Thursday
    """
    # Check for NaN values
    if pd.isna(row['lower_bb']) or pd.isna(row['rsi']) or pd.isna(row['volume_sma']):
        return False

    # 1. Price at Lower BB
    at_lower_bb = row['close'] <= row['lower_bb']

    # 2. RSI oversold
    rsi_oversold = row['rsi'] < RSI_OVERSOLD

    # 3. Volume spike
    volume_spike = row['volume'] > (row['volume_sma'] * VOLUME_SPIKE_THRESHOLD)

    # 4. US Session
    us_session = is_us_session(row['timestamp'])

    # 5. Valid day (not Thursday)
    valid_day = is_valid_day(row['timestamp'])

    # All conditions must be met
    return (at_lower_bb and rsi_oversold and volume_spike and
            us_session and valid_day)


def generate_short_signal(row, df, idx):
    """
    Generate SHORT signal based on:
    1. Price at Upper BB
    2. RSI > 65
    3. Volume spike > 1.5x avg
    4. Europe Session (7-15 UTC)
    5. Not Thursday
    """
    # Check for NaN values
    if pd.isna(row['upper_bb']) or pd.isna(row['rsi']) or pd.isna(row['volume_sma']):
        return False

    # 1. Price at Upper BB
    at_upper_bb = row['close'] >= row['upper_bb']

    # 2. RSI overbought
    rsi_overbought = row['rsi'] > RSI_OVERBOUGHT

    # 3. Volume spike
    volume_spike = row['volume'] > (row['volume_sma'] * VOLUME_SPIKE_THRESHOLD)

    # 4. Europe Session
    europe_session = is_europe_session(row['timestamp'])

    # 5. Valid day (not Thursday)
    valid_day = is_valid_day(row['timestamp'])

    # All conditions must be met
    return (at_upper_bb and rsi_overbought and volume_spike and
            europe_session and valid_day)


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

def backtest_pengu_strategy(df, initial_capital=10000, direction='LONG'):
    """
    Backtest PENGU mean reversion strategy

    Args:
        df: DataFrame with OHLCV data
        initial_capital: Starting capital
        direction: 'LONG', 'SHORT', or 'BOTH'

    Returns:
        trades_df: DataFrame with all trades
        equity_curve: Series with equity over time
        metrics: Dict with performance metrics
    """

    print(f"\n{'='*70}")
    print(f"PENGU MEAN REVERSION BACKTEST - {direction}")
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
    print(f"Direction: {direction}")
    print(f"Fees: {FEES_PCT*100:.2f}% round-trip")
    print(f"Slippage: {SLIPPAGE_PCT*100:.2f}% per fill\n")

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
            side = position['side']

            # Calculate hold time
            hold_minutes = (row['timestamp'] - entry_time).total_seconds() / 60

            # Check exit conditions
            exit_triggered = False
            exit_reason = None
            exit_price = row['close']

            if side == 'LONG':
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

            elif side == 'SHORT':
                # Stop loss hit
                if row['high'] >= stop_loss:
                    exit_triggered = True
                    exit_price = stop_loss
                    exit_reason = 'Stop Loss'

                # Take profit hit
                elif row['low'] <= take_profit:
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
                if side == 'LONG':
                    exit_price = exit_price * (1 - SLIPPAGE_PCT)
                else:
                    exit_price = exit_price * (1 + SLIPPAGE_PCT)

                # Calculate P&L
                if side == 'LONG':
                    pnl_pct = (exit_price / entry_price - 1) - FEES_PCT
                else:
                    pnl_pct = (entry_price / exit_price - 1) - FEES_PCT

                pnl_dollars = capital * POSITION_SIZE_PCT * pnl_pct / abs(pnl_pct) * abs(pnl_pct * 100)
                capital += pnl_dollars

                # Record trade
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'side': side,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'hold_minutes': hold_minutes,
                    'exit_reason': exit_reason,
                    'capital_after': capital
                })

                position = None

        # Look for new entry (only if no position)
        if position is None:
            signal_long = False
            signal_short = False

            if direction in ['LONG', 'BOTH']:
                signal_long = generate_long_signal(row, df, idx)

            if direction in ['SHORT', 'BOTH']:
                signal_short = generate_short_signal(row, df, idx)

            # Enter LONG
            if signal_long:
                entry_price = row['close'] * (1 + SLIPPAGE_PCT)
                stop_loss = entry_price - (row['atr'] * STOP_LOSS_ATR_MULT)

                # Take profit is closer of: BB mid or ATR target
                tp_atr = entry_price + (row['atr'] * TAKE_PROFIT_ATR_MULT)
                tp_bb_mid = row['bb_mid']
                take_profit = min(tp_atr, tp_bb_mid) if not pd.isna(tp_bb_mid) else tp_atr

                position = {
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'side': 'LONG'
                }

            # Enter SHORT
            elif signal_short:
                entry_price = row['close'] * (1 - SLIPPAGE_PCT)
                stop_loss = entry_price + (row['atr'] * STOP_LOSS_ATR_MULT)

                # Take profit is closer of: BB mid or ATR target
                tp_atr = entry_price - (row['atr'] * TAKE_PROFIT_ATR_MULT)
                tp_bb_mid = row['bb_mid']
                take_profit = max(tp_atr, tp_bb_mid) if not pd.isna(tp_bb_mid) else tp_atr

                position = {
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'side': 'SHORT'
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
            'avg_hold_minutes': trades_df['hold_minutes'].mean()
        }
    else:
        metrics = {
            'total_trades': 0,
            'error': 'No trades generated'
        }

    return trades_df, equity_curve, metrics


# ═══════════════════════════════════════════════════════════════
# REPORTING & VISUALIZATION
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

    print(f"\n{'='*70}\n")

    # Trade distribution
    if len(trades_df) > 0:
        print("Exit Reason Breakdown:")
        exit_reasons = trades_df['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pct = count / len(trades_df) * 100
            print(f"  {reason:15s}: {count:3d} ({pct:5.1f}%)")

        print(f"\nSide Breakdown:")
        side_counts = trades_df['side'].value_counts()
        for side, count in side_counts.items():
            pct = count / len(trades_df) * 100
            print(f"  {side:15s}: {count:3d} ({pct:5.1f}%)")


def plot_equity_curve(equity_curve, metrics, output_path):
    """Plot and save equity curve"""
    plt.figure(figsize=(14, 7))

    plt.plot(equity_curve.values, linewidth=2, color='#2E86AB')
    plt.axhline(y=equity_curve.iloc[0], color='gray', linestyle='--', alpha=0.5, label='Starting Capital')

    plt.title(f"PENGU Mean Reversion Strategy - Equity Curve\n" +
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

    # Run backtest for LONG only (primary strategy)
    trades_df, equity_curve, metrics = backtest_pengu_strategy(
        df,
        initial_capital=10000,
        direction='LONG'
    )

    # Print results
    print_backtest_results(metrics, trades_df)

    # Save results
    if len(trades_df) > 0:
        # Save trade log
        trades_output = 'results/PENGU_strategy_results.csv'
        trades_df.to_csv(trades_output, index=False)
        print(f"✅ Trade log saved to: {trades_output}")

        # Save equity curve plot
        equity_output = 'results/PENGU_strategy_equity.png'
        plot_equity_curve(equity_curve, metrics, equity_output)

        # Save summary markdown
        summary_output = 'results/PENGU_strategy_summary.md'
        with open(summary_output, 'w') as f:
            f.write("# PENGU Mean Reversion Strategy - Backtest Summary\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Strategy Configuration\n\n")
            f.write(f"- **Direction**: LONG-only\n")
            f.write(f"- **Timeframe**: 1-minute\n")
            f.write(f"- **Entry**: Lower BB touch + RSI<35 + Volume spike + US Session\n")
            f.write(f"- **Stop Loss**: {STOP_LOSS_ATR_MULT}x ATR\n")
            f.write(f"- **Take Profit**: {TAKE_PROFIT_ATR_MULT}x ATR or BB mid (whichever closer)\n")
            f.write(f"- **Max Hold**: {MAX_HOLD_MINUTES} minutes\n")
            f.write(f"- **Fees**: {FEES_PCT*100:.2f}% round-trip\n\n")

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
            f.write(f"| **Avg Hold Time** | {metrics['avg_hold_minutes']:.1f} min |\n\n")

            f.write("## Exit Breakdown\n\n")
            exit_reasons = trades_df['exit_reason'].value_counts()
            f.write(f"| Exit Reason | Count | % |\n")
            f.write(f"|-------------|-------|---|\n")
            for reason, count in exit_reasons.items():
                pct = count / len(trades_df) * 100
                f.write(f"| {reason} | {count} | {pct:.1f}% |\n")

            f.write("\n## Interpretation\n\n")

            if metrics['win_rate'] >= 35:
                f.write("✅ **Win rate meets target** (≥35%)\n\n")
            else:
                f.write("⚠️ **Win rate below target** (<35%)\n\n")

            if metrics['rr_ratio'] >= 1.6:
                f.write("✅ **R:R ratio meets target** (≥1.6x)\n\n")
            else:
                f.write("⚠️ **R:R ratio below target** (<1.6x)\n\n")

            if metrics['max_drawdown'] > -25:
                f.write("✅ **Max drawdown acceptable** (>-25%)\n\n")
            else:
                f.write("❌ **Max drawdown excessive** (<-25%)\n\n")

            if metrics['expectancy'] > 0:
                f.write(f"✅ **Positive expectancy** ({metrics['expectancy']:+.2f}%)\n\n")
            else:
                f.write(f"❌ **Negative expectancy** ({metrics['expectancy']:+.2f}%)\n\n")

        print(f"✅ Summary saved to: {summary_output}")

    print(f"\n{'='*70}")
    print("BACKTEST COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
