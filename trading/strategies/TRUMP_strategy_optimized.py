"""
TRUMP OPTIMIZED Trading Strategy - Version 2
Strategy: RSI Mean Reversion with STRICT Filters
Designed: 2025-12-07
Author: Master Trader AI

IMPROVED based on backtest analysis:
- Focus ONLY on strongest edge: RSI < 30 (55% win rate)
- Tighter filters to increase win rate
- Better R:R ratio (wider TP, tighter SL)
- US session ONLY
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================

def calculate_indicators(df):
    """Calculate all technical indicators needed for the strategy."""

    data = df.copy()

    # Basic calculations
    data['body'] = abs(data['close'] - data['open'])
    data['range'] = data['high'] - data['low']
    data['body_pct'] = (data['body'] / data['close']) * 100
    data['upper_wick'] = data['high'] - data[['open', 'close']].max(axis=1)
    data['lower_wick'] = data[['open', 'close']].min(axis=1) - data['low']
    data['is_green'] = (data['close'] > data['open']).astype(int)
    data['is_red'] = (data['close'] < data['open']).astype(int)

    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))

    # SMAs
    data['sma20'] = data['close'].rolling(20).mean()
    data['sma50'] = data['close'].rolling(50).mean()
    data['sma200'] = data['close'].rolling(200).mean()

    # Bollinger Bands
    data['bb_middle'] = data['close'].rolling(20).mean()
    bb_std = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_middle'] + (2 * bb_std)
    data['bb_lower'] = data['bb_middle'] - (2 * bb_std)

    # Distance to BB
    data['dist_to_bb_lower'] = ((data['close'] - data['bb_lower']) / data['bb_lower']) * 100

    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['atr'] = true_range.rolling(14).mean()
    data['atr_pct'] = (data['atr'] / data['close']) * 100

    # Volume metrics
    data['avg_volume'] = data['volume'].rolling(50).mean()
    data['volume_ratio'] = data['volume'] / data['avg_volume']

    # Sequential patterns (consecutive reds)
    data['consecutive_red'] = 0
    for i in range(4, len(data)):
        if all(data['is_red'].iloc[i-j] == 1 for j in range(4)):
            data.loc[data.index[i], 'consecutive_red'] = 4
        if i >= 4 and all(data['is_red'].iloc[i-j] == 1 for j in range(5)):
            data.loc[data.index[i], 'consecutive_red'] = 5

    # Hour of day (UTC)
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour

    return data


# ============================================================================
# OPTIMIZED ENTRY SIGNALS
# ============================================================================

def check_long_entry(row):
    """
    STRICT LONG entry criteria - ONLY the strongest edge.

    Based on pattern analysis:
    - RSI < 30 shows 55% win rate (our BEST edge)
    - 5 consecutive red candles → +0.0052% avg bounce
    - US session best performance
    """

    # PRIMARY SIGNAL: RSI oversold (our strongest edge)
    rsi_oversold = row['rsi'] < 30

    if not rsi_oversold:
        # Alternative: 5 consecutive reds (strong sequential pattern)
        if row['consecutive_red'] < 5:
            return False

    # STRICT CONFIRMATION FILTERS:

    # 1. Price near lower BB (within 10% of distance)
    near_bb_lower = row['dist_to_bb_lower'] < 10

    # 2. NOT in strong downtrend (allow slight downtrend for bounce)
    if not pd.isna(row['sma200']):
        not_extended_down = row['close'] > row['sma200'] * 0.98  # Max 2% below SMA200
    else:
        not_extended_down = True

    # 3. Sufficient volume (at least 1x average)
    sufficient_volume = row['volume_ratio'] >= 1.0

    # 4. Normal volatility (not explosive)
    normal_volatility = row['atr_pct'] < 0.30

    # 5. No large lower wick (avoid false bottoms)
    if row['range'] > 0:
        no_false_bottom = (row['lower_wick'] / row['range']) < 0.4
    else:
        no_false_bottom = True

    return all([
        near_bb_lower,
        not_extended_down,
        sufficient_volume,
        normal_volatility,
        no_false_bottom
    ])


def is_us_session(hour):
    """Check if in US trading session (best performance)."""
    # US session: 14:00-21:00 UTC (best avg return, highest volume)
    return 14 <= hour < 21


def is_best_hour(hour):
    """Check if in best trading hours."""
    # Best hours from pattern analysis: 2, 4, 19
    # Focus on hour 19 (US session peak)
    return hour == 19


# ============================================================================
# EXIT LOGIC
# ============================================================================

def check_exit(trade, current_row, candles_held):
    """
    Optimized exit logic with better R:R ratio.

    Changes from v1:
    - Wider TP (3x ATR instead of 1.5x) for better R:R
    - Tighter SL (1.5x ATR instead of 2x) to cut losses faster
    - Faster RSI exit (when RSI > 45 instead of 50)
    """

    entry_price = trade['entry_price']
    stop_loss = trade['stop_loss']
    take_profit = trade['take_profit']
    current_price = current_row['close']

    # Check stop loss
    if current_price <= stop_loss:
        return True, 'SL', stop_loss

    # Check take profit
    if current_price >= take_profit:
        return True, 'TP', take_profit

    # RSI exit (faster exit when RSI recovers to neutral)
    if current_row['rsi'] > 45:
        return True, 'RSI_EXIT', current_price

    # Time-based exit (max 20 candles = 20 minutes)
    if candles_held >= 20:
        return True, 'TIME_EXIT', current_price

    return False, None, None


# ============================================================================
# MAIN BACKTEST ENGINE
# ============================================================================

def run_backtest(data, initial_capital=10000, position_size=0.02,
                 maker_fee=0.0005, taker_fee=0.001):
    """
    Run OPTIMIZED backtest on TRUMP data.

    Key changes:
    - ONLY trade during US session
    - ONLY long entries (simplify strategy)
    - Better R:R: SL 1.5x ATR, TP 3x ATR
    - Stricter entry filters
    """

    print("Calculating indicators...")
    df = calculate_indicators(data)

    # Initialize tracking
    capital = initial_capital
    equity_curve = []
    trades = []
    open_trades = []

    daily_trade_count = 0
    current_day = None

    print(f"Running backtest on {len(df)} candles...")

    for i in range(200, len(df)):  # Start after enough data for indicators
        row = df.iloc[i]

        # Track day changes
        current_date = pd.to_datetime(row['timestamp']).date()
        if current_day != current_date:
            current_day = current_date
            daily_trade_count = 0

        hour = row['hour']

        # Update open trades
        for trade in open_trades[:]:
            candles_held = i - trade['entry_idx']
            should_exit, exit_reason, exit_price = check_exit(trade, row, candles_held)

            if should_exit:
                # Calculate PnL
                pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price'])

                # Apply fees
                pnl_pct -= taker_fee

                # Calculate dollar PnL
                position_value = position_size * capital
                pnl_dollars = position_value * pnl_pct

                capital += pnl_dollars

                # Record trade
                trades.append({
                    'entry_time': trade['entry_time'],
                    'exit_time': row['timestamp'],
                    'entry_price': trade['entry_price'],
                    'exit_price': exit_price,
                    'stop_loss': trade['stop_loss'],
                    'take_profit': trade['take_profit'],
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'candles_held': candles_held,
                    'hour': trade['hour'],
                    'rsi_entry': trade['rsi_entry']
                })

                open_trades.remove(trade)

        # Record equity
        equity_curve.append({
            'timestamp': row['timestamp'],
            'capital': capital,
            'open_trades': len(open_trades)
        })

        # Check if we can enter new trade

        # Risk limits
        if daily_trade_count >= 15:  # Max 15 trades per day
            continue

        if len(open_trades) >= 2:  # Max 2 concurrent trades
            continue

        # Session filter: ONLY US session
        if not is_us_session(hour):
            continue

        # Check entry signal
        if check_long_entry(row):
            atr = row['atr_pct'] / 100  # Convert to decimal

            # Optimized stops and targets
            stop_loss = row['close'] * (1 - 1.5 * atr)  # Tighter SL
            take_profit = row['close'] * (1 + 3 * atr)  # Wider TP (R:R = 2.0)

            open_trades.append({
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'hour': hour,
                'rsi_entry': row['rsi']
            })
            daily_trade_count += 1

            # Apply entry fee
            capital -= (position_size * capital * maker_fee)

    # Close any remaining open trades at final price
    final_row = df.iloc[-1]
    for trade in open_trades:
        pnl_pct = ((final_row['close'] - trade['entry_price']) / trade['entry_price']) - taker_fee
        position_value = position_size * capital
        pnl_dollars = position_value * pnl_pct
        capital += pnl_dollars

        trades.append({
            'entry_time': trade['entry_time'],
            'exit_time': final_row['timestamp'],
            'entry_price': trade['entry_price'],
            'exit_price': final_row['close'],
            'stop_loss': trade['stop_loss'],
            'take_profit': trade['take_profit'],
            'exit_reason': 'END_OF_DATA',
            'pnl_pct': pnl_pct * 100,
            'pnl_dollars': pnl_dollars,
            'candles_held': len(df) - trade['entry_idx'],
            'hour': trade['hour'],
            'rsi_entry': trade['rsi_entry']
        })

    return pd.DataFrame(trades), pd.DataFrame(equity_curve), capital


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

def calculate_metrics(trades_df, equity_df, initial_capital, final_capital):
    """Calculate comprehensive performance metrics."""

    if len(trades_df) == 0:
        print("No trades executed!")
        return None

    metrics = {}

    # Basic stats
    metrics['Total Trades'] = len(trades_df)
    metrics['Initial Capital'] = initial_capital
    metrics['Final Capital'] = final_capital
    metrics['Total Return %'] = ((final_capital - initial_capital) / initial_capital) * 100
    metrics['Total Return $'] = final_capital - initial_capital

    # Win/Loss stats
    winning_trades = trades_df[trades_df['pnl_dollars'] > 0]
    losing_trades = trades_df[trades_df['pnl_dollars'] < 0]

    metrics['Winning Trades'] = len(winning_trades)
    metrics['Losing Trades'] = len(losing_trades)
    metrics['Win Rate %'] = (len(winning_trades) / len(trades_df)) * 100 if len(trades_df) > 0 else 0

    # PnL stats
    metrics['Avg Win %'] = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
    metrics['Avg Loss %'] = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
    metrics['Largest Win %'] = trades_df['pnl_pct'].max()
    metrics['Largest Loss %'] = trades_df['pnl_pct'].min()

    # Risk metrics
    if len(losing_trades) > 0 and abs(metrics['Avg Loss %']) > 0:
        metrics['Profit Factor'] = abs(metrics['Avg Win %'] * len(winning_trades)) / abs(metrics['Avg Loss %'] * len(losing_trades))
    else:
        metrics['Profit Factor'] = 0

    # R:R ratio
    if abs(metrics['Avg Loss %']) > 0:
        metrics['Avg R:R'] = abs(metrics['Avg Win %']) / abs(metrics['Avg Loss %'])
    else:
        metrics['Avg R:R'] = 0

    # Drawdown
    equity_df['peak'] = equity_df['capital'].cummax()
    equity_df['drawdown'] = ((equity_df['capital'] - equity_df['peak']) / equity_df['peak']) * 100
    metrics['Max Drawdown %'] = equity_df['drawdown'].min()

    # Exit analysis
    metrics['SL Exits'] = len(trades_df[trades_df['exit_reason'] == 'SL'])
    metrics['TP Exits'] = len(trades_df[trades_df['exit_reason'] == 'TP'])
    metrics['RSI Exits'] = len(trades_df[trades_df['exit_reason'] == 'RSI_EXIT'])
    metrics['Time Exits'] = len(trades_df[trades_df['exit_reason'] == 'TIME_EXIT'])

    # Holding time
    metrics['Avg Candles Held'] = trades_df['candles_held'].mean()

    return metrics


def print_metrics(metrics):
    """Print performance metrics in formatted table."""

    if metrics is None:
        return

    print("\n" + "="*70)
    print("TRUMP OPTIMIZED STRATEGY BACKTEST RESULTS")
    print("="*70)

    print(f"\n{'OVERALL PERFORMANCE':<30} {'VALUE':>15}")
    print("-"*70)
    print(f"{'Initial Capital':<30} ${metrics['Initial Capital']:>14,.2f}")
    print(f"{'Final Capital':<30} ${metrics['Final Capital']:>14,.2f}")
    print(f"{'Total Return':<30} {metrics['Total Return %']:>14.2f}%")
    print(f"{'Total Return $':<30} ${metrics['Total Return $']:>14,.2f}")
    print(f"{'Max Drawdown':<30} {metrics['Max Drawdown %']:>14.2f}%")

    print(f"\n{'TRADE STATISTICS':<30} {'VALUE':>15}")
    print("-"*70)
    print(f"{'Total Trades':<30} {metrics['Total Trades']:>15,}")
    print(f"{'Winning Trades':<30} {metrics['Winning Trades']:>15,}")
    print(f"{'Losing Trades':<30} {metrics['Losing Trades']:>15,}")
    print(f"{'Win Rate':<30} {metrics['Win Rate %']:>14.2f}%")
    print(f"{'Profit Factor':<30} {metrics['Profit Factor']:>14.2f}x")
    print(f"{'Avg R:R Ratio':<30} {metrics['Avg R:R']:>14.2f}x")

    print(f"\n{'PNL ANALYSIS':<30} {'VALUE':>15}")
    print("-"*70)
    print(f"{'Avg Win':<30} {metrics['Avg Win %']:>14.2f}%")
    print(f"{'Avg Loss':<30} {metrics['Avg Loss %']:>14.2f}%")
    print(f"{'Largest Win':<30} {metrics['Largest Win %']:>14.2f}%")
    print(f"{'Largest Loss':<30} {metrics['Largest Loss %']:>14.2f}%")

    print(f"\n{'EXIT REASONS':<30} {'COUNT':>15} {'%':>20}")
    print("-"*70)
    print(f"{'Stop Loss Exits':<30} {metrics['SL Exits']:>15,} {metrics['SL Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Take Profit Exits':<30} {metrics['TP Exits']:>15,} {metrics['TP Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'RSI Exits':<30} {metrics['RSI Exits']:>15,} {metrics['RSI Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Time Exits':<30} {metrics['Time Exits']:>15,} {metrics['Time Exits']/metrics['Total Trades']*100:>19.1f}%")

    print(f"\n{'EFFICIENCY':<30} {'VALUE':>15}")
    print("-"*70)
    print(f"{'Avg Holding Time (minutes)':<30} {metrics['Avg Candles Held']:>14.1f}")

    print("="*70 + "\n")


def plot_equity_curve(equity_df, trades_df, save_path):
    """Plot equity curve with trade markers."""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Equity curve
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
    ax1.plot(equity_df['timestamp'], equity_df['capital'], linewidth=2, color='#2E86AB', label='Equity')

    # Mark winning and losing trades
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    wins = trades_df[trades_df['pnl_dollars'] > 0]
    losses = trades_df[trades_df['pnl_dollars'] < 0]

    for _, trade in wins.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='green', s=50, alpha=0.6, zorder=5)

    for _, trade in losses.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='red', s=50, alpha=0.6, zorder=5)

    ax1.set_title('TRUMP Optimized Strategy - Equity Curve', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Capital (USDT)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # Drawdown
    equity_df['peak'] = equity_df['capital'].cummax()
    equity_df['drawdown'] = ((equity_df['capital'] - equity_df['peak']) / equity_df['peak']) * 100

    ax2.fill_between(equity_df['timestamp'], equity_df['drawdown'], 0,
                     color='red', alpha=0.3, label='Drawdown')
    ax2.plot(equity_df['timestamp'], equity_df['drawdown'], color='darkred', linewidth=1.5)
    ax2.set_ylabel('Drawdown (%)', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Equity curve saved to: {save_path}")
    plt.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":

    print("="*70)
    print("TRUMP OPTIMIZED STRATEGY BACKTEST")
    print("Strategy: RSI Mean Reversion (Long Only, US Session)")
    print("="*70)

    # Load data
    print("\nLoading TRUMP data...")
    data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/trump_usdt_1m_mexc.csv')
    print(f"Loaded {len(data)} candles from {data['timestamp'].min()} to {data['timestamp'].max()}")

    # Run backtest
    print("\nStarting backtest...")
    trades_df, equity_df, final_capital = run_backtest(
        data=data,
        initial_capital=10000,
        position_size=0.02,  # 2%
        maker_fee=0.0005,
        taker_fee=0.001
    )

    # Calculate metrics
    print("\nCalculating performance metrics...")
    metrics = calculate_metrics(trades_df, equity_df, 10000, final_capital)

    # Print results
    print_metrics(metrics)

    # Save results
    print("\nSaving results...")
    trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_results.csv', index=False)
    print("Trade log saved to: /workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_results.csv")

    # Plot equity curve
    plot_equity_curve(equity_df, trades_df, '/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_equity.png')

    # Generate summary markdown
    summary_path = '/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_summary.md'
    with open(summary_path, 'w') as f:
        f.write("# TRUMP Optimized Strategy Backtest Summary\n\n")
        f.write(f"**Strategy:** RSI Mean Reversion (Long Only, US Session)\n\n")
        f.write(f"**Backtest Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Data Period:** {data['timestamp'].min()} to {data['timestamp'].max()}\n\n")
        f.write(f"**Total Candles:** {len(data):,}\n\n")
        f.write("---\n\n")

        f.write("## Performance Summary\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Initial Capital | ${metrics['Initial Capital']:,.2f} |\n")
        f.write(f"| Final Capital | ${metrics['Final Capital']:,.2f} |\n")
        f.write(f"| Total Return | {metrics['Total Return %']:.2f}% |\n")
        f.write(f"| Max Drawdown | {metrics['Max Drawdown %']:.2f}% |\n")
        f.write(f"| Total Trades | {metrics['Total Trades']:,} |\n")
        f.write(f"| Win Rate | {metrics['Win Rate %']:.2f}% |\n")
        f.write(f"| Profit Factor | {metrics['Profit Factor']:.2f}x |\n")
        f.write(f"| Avg R:R Ratio | {metrics['Avg R:R']:.2f}x |\n")
        f.write(f"| Avg Win | {metrics['Avg Win %']:.2f}% |\n")
        f.write(f"| Avg Loss | {metrics['Avg Loss %']:.2f}% |\n")
        f.write(f"| Avg Holding Time | {metrics['Avg Candles Held']:.1f} minutes |\n")

        f.write("\n## Strategy Details\n\n")
        f.write("**Entry Criteria:**\n")
        f.write("- RSI < 30 (strongest statistical edge: 55% win rate)\n")
        f.write("- OR 5+ consecutive red candles\n")
        f.write("- Price within 10% of lower Bollinger Band\n")
        f.write("- Volume >= 1.0x average\n")
        f.write("- Normal volatility (ATR < 0.30%)\n")
        f.write("- US session ONLY (14:00-21:00 UTC)\n\n")

        f.write("**Exit Criteria:**\n")
        f.write("- Stop Loss: 1.5x ATR below entry\n")
        f.write("- Take Profit: 3x ATR above entry (R:R = 2.0)\n")
        f.write("- RSI Exit: When RSI > 45\n")
        f.write("- Time Exit: After 20 candles (20 minutes)\n\n")

        f.write("**Position Sizing:**\n")
        f.write("- 2% of capital per trade\n")
        f.write("- Max 2 concurrent trades\n")
        f.write("- Max 15 trades per day\n\n")

        f.write("\n## Exit Analysis\n\n")
        f.write("| Exit Type | Count | Percentage |\n")
        f.write("|-----------|-------|------------|\n")
        f.write(f"| Stop Loss | {metrics['SL Exits']:,} | {metrics['SL Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Take Profit | {metrics['TP Exits']:,} | {metrics['TP Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| RSI Exit | {metrics['RSI Exits']:,} | {metrics['RSI Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Time Exit | {metrics['Time Exits']:,} | {metrics['Time Exits']/metrics['Total Trades']*100:.1f}% |\n")

        f.write("\n## Files Generated\n\n")
        f.write("- Trade log: `TRUMP_strategy_results.csv`\n")
        f.write("- Equity curve: `TRUMP_strategy_equity.png`\n")
        f.write("- Summary: `TRUMP_strategy_summary.md`\n")

    print(f"Summary saved to: {summary_path}")

    print("\n" + "="*70)
    print("BACKTEST COMPLETE!")
    print("="*70)
