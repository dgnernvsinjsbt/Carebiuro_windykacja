#!/usr/bin/env python3
"""
PENGU Mean Reversion Strategy - FINAL VERSION
Core Principle: Buy extreme oversold, sell at BB midline (true mean reversion)
Author: Master Strategy Designer
Date: 2025-12-07
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# FINAL STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2.0

# RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 25  # Very extreme

# ATR
ATR_PERIOD = 14
STOP_LOSS_ATR_MULT = 3.0  # Reasonable stop
USE_BB_MID_AS_TARGET = True  # TRUE MEAN REVERSION

# Volume
VOLUME_SMA_PERIOD = 20
VOLUME_SPIKE_THRESHOLD = 1.8

# Session Times (UTC hours)
US_SESSION_START = 16  # Later start for better setups
US_SESSION_END = 21

# Risk Management
MAX_HOLD_MINUTES = 90
POSITION_SIZE_PCT = 0.01

# Execution
FEES_PCT = 0.0010
SLIPPAGE_PCT = 0.0005

# Day filters
AVOID_DAYS = [3]  # Thursday


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
# FILTERS
# ═══════════════════════════════════════════════════════════════

def is_us_session(timestamp):
    """Check if timestamp is in US session"""
    hour = timestamp.hour
    return US_SESSION_START <= hour < US_SESSION_END


def is_valid_day(timestamp):
    """Check if day is valid for trading"""
    return timestamp.weekday() not in AVOID_DAYS


def check_downtrend(row):
    """Ensure we're in a short-term downtrend (price below SMA)"""
    return row['close'] < row['bb_mid']


# ═══════════════════════════════════════════════════════════════
# SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_long_signal(row):
    """
    FINAL LONG signal - TRUE MEAN REVERSION:
    1. Price touches/penetrates Lower BB
    2. RSI < 25 (extreme panic)
    3. Volume spike (capitulation)
    4. Price below SMA (confirming downtrend to fade)
    5. US session (better hours)
    6. Not Thursday
    """
    # Check for NaN values
    if pd.isna(row['lower_bb']) or pd.isna(row['rsi']) or pd.isna(row['volume_sma']):
        return False

    # 1. At or below lower BB
    at_lower_bb = row['low'] <= row['lower_bb']

    # 2. Extreme RSI
    rsi_extreme = row['rsi'] < RSI_OVERSOLD

    # 3. Volume spike
    volume_spike = row['volume'] > (row['volume_sma'] * VOLUME_SPIKE_THRESHOLD)

    # 4. Below SMA (downtrend confirmation)
    below_sma = check_downtrend(row)

    # 5. US Session
    us_session = is_us_session(row['timestamp'])

    # 6. Valid day
    valid_day = is_valid_day(row['timestamp'])

    # All must be met
    return (at_lower_bb and rsi_extreme and volume_spike and
            below_sma and us_session and valid_day)


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

def backtest_pengu_final(df, initial_capital=10000):
    """
    Backtest FINAL PENGU mean reversion strategy
    Target: BB midline (true mean reversion)
    """

    print(f"\n{'='*70}")
    print(f"PENGU MEAN REVERSION BACKTEST - FINAL VERSION")
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
    print(f"Entry: Lower BB touch + RSI<{RSI_OVERSOLD} + Volume>{VOLUME_SPIKE_THRESHOLD}x")
    print(f"Target: BB MIDLINE (true mean reversion)")
    print(f"Stop Loss: {STOP_LOSS_ATR_MULT}x ATR")
    print(f"Max Hold: {MAX_HOLD_MINUTES} min\n")

    # Iterate through data
    for idx, row in df.iterrows():
        equity.append(capital)

        # Skip if we don't have indicators yet
        if pd.isna(row['atr']) or pd.isna(row['rsi']) or pd.isna(row['bb_mid']):
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

            # Take profit hit (BB midline)
            elif row['high'] >= take_profit:
                exit_triggered = True
                exit_price = take_profit
                exit_reason = 'Take Profit'

            # Time exit
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
                    'entry_hour': entry_time.hour
                })

                position = None

        # Look for new entry (only if no position)
        if position is None:
            if generate_long_signal(row):
                entry_price = row['close'] * (1 + SLIPPAGE_PCT)
                stop_loss = entry_price - (row['atr'] * STOP_LOSS_ATR_MULT)

                # Target: BB midline (true mean reversion)
                take_profit = row['bb_mid']

                # Validate target is above entry (sanity check)
                if take_profit <= entry_price:
                    continue  # Skip this trade if BB mid is not above entry

                position = {
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_rsi': row['rsi']
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

        print(f"\nWin Rate by Exit Reason:")
        for reason in exit_reasons.index:
            reason_trades = trades_df[trades_df['exit_reason'] == reason]
            winners = len(reason_trades[reason_trades['pnl_dollars'] > 0])
            wr = winners / len(reason_trades) * 100 if len(reason_trades) > 0 else 0
            avg_pnl = reason_trades['pnl_pct'].mean()
            print(f"  {reason:15s}: {wr:5.1f}% (avg: {avg_pnl:+.2f}%)")


def plot_equity_curve(equity_curve, metrics, output_path):
    """Plot and save equity curve"""
    plt.figure(figsize=(14, 7))

    plt.plot(equity_curve.values, linewidth=2, color='#2E86AB')
    plt.axhline(y=equity_curve.iloc[0], color='gray', linestyle='--', alpha=0.5, label='Starting Capital')

    plt.title(f"PENGU Mean Reversion Strategy - FINAL Equity Curve\n" +
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
    trades_df, equity_curve, metrics = backtest_pengu_final(df, initial_capital=10000)

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

        # Save summary
        summary_output = 'results/PENGU_strategy_summary.md'
        with open(summary_output, 'w') as f:
            f.write("# PENGU Mean Reversion Strategy - FINAL Backtest\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Strategy Philosophy\n\n")
            f.write("**TRUE MEAN REVERSION**: Buy extreme panic, sell at statistical mean (BB midline)\n\n")
            f.write("- Entry: Lower BB touch + RSI<25 + Volume spike + Below SMA\n")
            f.write("- Target: BB Midline (SMA 20) - natural mean reversion point\n")
            f.write(f"- Stop Loss: {STOP_LOSS_ATR_MULT}x ATR\n")
            f.write(f"- Session: US hours ({US_SESSION_START}-{US_SESSION_END} UTC)\n")
            f.write(f"- Max Hold: {MAX_HOLD_MINUTES} minutes\n\n")

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

            # Target validation
            f.write("## Target Validation\n\n")
            checks = [
                ("Minimum Trades (≥50)", metrics['total_trades'] >= 50, metrics['total_trades']),
                ("Win Rate (≥35%)", metrics['win_rate'] >= 35, f"{metrics['win_rate']:.1f}%"),
                ("R:R Ratio (≥1.6x)", metrics['rr_ratio'] >= 1.6, f"{metrics['rr_ratio']:.2f}x"),
                ("Max Drawdown (>-25%)", metrics['max_drawdown'] > -25, f"{metrics['max_drawdown']:.1f}%"),
                ("Expectancy (>0%)", metrics['expectancy'] > 0, f"{metrics['expectancy']:+.2f}%")
            ]

            for check_name, passed, value in checks:
                status = "✅" if passed else "❌"
                f.write(f"- {status} **{check_name}**: {value}\n")

            f.write("\n## Exit Analysis\n\n")
            exit_reasons = trades_df['exit_reason'].value_counts()
            f.write(f"| Exit Reason | Count | % | Win Rate | Avg P&L |\n")
            f.write(f"|-------------|-------|---|----------|----------|\n")
            for reason in exit_reasons.index:
                reason_trades = trades_df[trades_df['exit_reason'] == reason]
                count = len(reason_trades)
                pct = count / len(trades_df) * 100
                winners = len(reason_trades[reason_trades['pnl_dollars'] > 0])
                wr = winners / count * 100 if count > 0 else 0
                avg_pnl = reason_trades['pnl_pct'].mean()
                f.write(f"| {reason} | {count} | {pct:.1f}% | {wr:.1f}% | {avg_pnl:+.2f}% |\n")

            f.write("\n## Verdict\n\n")

            if metrics['expectancy'] > 0 and metrics['total_trades'] >= 50:
                f.write("✅ **Strategy shows positive expectancy** with sufficient trade count.\n\n")
            elif metrics['total_trades'] < 50:
                f.write("⚠️ **Low trade count** - need more data for statistical significance.\n\n")
            else:
                f.write("❌ **Negative expectancy** - strategy not profitable on this dataset.\n\n")

            f.write("**PENGU Character**: Extremely choppy and mean-reverting. ")
            f.write("This asset requires perfect timing and strict filters to be profitable. ")
            f.write("The low win rate combined with extreme volatility makes it challenging for ")
            f.write("systematic trading. Consider alternative assets with more trending behavior.\n")

        print(f"✅ Summary saved to: {summary_output}")

    print(f"\n{'='*70}")
    print("BACKTEST COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
