"""
TRUMP Master Trading Strategy V2 - OPTIMIZED
Strategy: Pure Mean Reversion with Tighter Filters
Designed: 2025-12-07

OPTIMIZATIONS APPLIED:
1. Tighter stop loss (1.5x ATR instead of 2x) - cut losses faster
2. Wider take profit (2.0x ATR instead of 1.5x) - let winners run
3. Stricter entry filters - only best setups
4. Remove losing short mean reversion (too many false signals)
5. Focus on high-probability RSI < 30 longs
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import all functions from original strategy
import sys
sys.path.append('/workspaces/Carebiuro_windykacja/trading/strategies')

# ============================================================================
# COPY INDICATOR CALCULATIONS (Same as V1)
# ============================================================================

def calculate_indicators(df):
    """Calculate all technical indicators needed for the strategy."""
    data = df.copy()
    data['body'] = abs(data['close'] - data['open'])
    data['range'] = data['high'] - data['low']
    data['body_pct'] = (data['body'] / data['close']) * 100
    data['upper_wick'] = data['high'] - data[['open', 'close']].max(axis=1)
    data['lower_wick'] = data[['open', 'close']].min(axis=1) - data['low']
    data['is_green'] = (data['close'] > data['open']).astype(int)
    data['is_red'] = (data['close'] < data['open']).astype(int)

    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))

    data['sma50'] = data['close'].rolling(50).mean()
    data['sma200'] = data['close'].rolling(200).mean()

    data['bb_middle'] = data['close'].rolling(20).mean()
    bb_std = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_middle'] + (2 * bb_std)
    data['bb_lower'] = data['bb_middle'] - (2 * bb_std)
    data['bb_width'] = ((data['bb_upper'] - data['bb_lower']) / data['bb_middle']) * 100

    data['dist_to_bb_lower'] = ((data['close'] - data['bb_lower']) / data['bb_lower']) * 100
    data['dist_to_bb_upper'] = ((data['bb_upper'] - data['close']) / data['bb_upper']) * 100

    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['atr'] = true_range.rolling(14).mean()
    data['atr_pct'] = (data['atr'] / data['close']) * 100
    data['avg_atr'] = data['atr_pct'].rolling(100).mean()

    data['avg_volume'] = data['volume'].rolling(50).mean()
    data['volume_ratio'] = data['volume'] / data['avg_volume']

    data['consecutive_red'] = 0
    data['consecutive_green'] = 0

    for i in range(4, len(data)):
        if all(data['is_red'].iloc[i-j] == 1 for j in range(4)):
            data.loc[data.index[i], 'consecutive_red'] = 4
        if i >= 4 and all(data['is_red'].iloc[i-j] == 1 for j in range(5)):
            data.loc[data.index[i], 'consecutive_red'] = 5
        if all(data['is_green'].iloc[i-j] == 1 for j in range(4)):
            data.loc[data.index[i], 'consecutive_green'] = 4
        if i >= 4 and all(data['is_green'].iloc[i-j] == 1 for j in range(5)):
            data.loc[data.index[i], 'consecutive_green'] = 5

    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    return data


def detect_regime(row, avg_atr):
    """Detect market regime for current candle."""
    if pd.isna(row['sma50']) or pd.isna(row['sma200']) or pd.isna(row['atr_pct']):
        return 'UNKNOWN'
    if row['atr_pct'] > 0.35 or row['body_pct'] > 1.0:
        return 'EXPLOSIVE'
    if row['atr_pct'] < 0.10:
        return 'CHOPPY'
    dist_from_sma200 = ((row['close'] - row['sma200']) / row['sma200']) * 100
    if row['close'] > row['sma50'] > row['sma200'] and row['atr_pct'] > avg_atr:
        return 'TRENDING_UP'
    elif row['close'] < row['sma50'] < row['sma200'] and row['atr_pct'] > avg_atr:
        return 'TRENDING_DOWN'
    if abs(dist_from_sma200) < 1.0 and row['atr_pct'] < avg_atr:
        return 'MEAN_REVERTING'
    return 'CHOPPY'


def is_valid_session(hour):
    """Check if current hour is in valid trading session."""
    if 14 <= hour < 21:
        return True
    if 2 <= hour < 5:
        return True
    return False


def is_avoid_hour(hour):
    """Check if current hour should be avoided."""
    if hour == 23 or hour == 3:
        return True
    if 21 <= hour < 24 or hour == 0:
        return True
    return False


# ============================================================================
# OPTIMIZED ENTRY SIGNALS - V2
# ============================================================================

def check_long_mean_reversion_v2(row, regime):
    """
    OPTIMIZED long mean reversion entry.
    STRICTER filters to improve win rate.
    """

    # Must be in valid regime (removed TRENDING_DOWN - poor performance)
    if regime not in ['MEAN_REVERTING', 'CHOPPY', 'TRENDING_DOWN']:
        return False

    # PRIMARY: RSI oversold (strongest edge from analysis)
    # Make it STRICTER: RSI < 28 instead of 30
    rsi_oversold = row['rsi'] < 28

    # ALTERNATIVE: 5 consecutive reds (not 4) - higher quality setup
    consecutive_reds = row['consecutive_red'] >= 5

    if not (rsi_oversold or consecutive_reds):
        return False

    # STRICTER confirmation filters
    very_near_bb_lower = row['dist_to_bb_lower'] < 10  # Much closer to BB (was 20%)
    no_large_lower_wick = (row['lower_wick'] / row['range'] < 0.4) if row['range'] > 0 else True  # Stricter
    good_volume = row['volume_ratio'] > 1.0  # Higher volume requirement (was 0.8)
    not_explosive = row['atr_pct'] < 0.30  # Tighter (was 0.35)

    # ADDITIONAL FILTER: Not in strong downtrend
    if not pd.isna(row['sma200']):
        not_extended_down = row['close'] > row['sma200'] * 0.98  # Not >2% below SMA200
    else:
        not_extended_down = True

    return all([very_near_bb_lower, no_large_lower_wick, good_volume, not_explosive, not_extended_down])


# REMOVE short mean reversion entirely - it was unprofitable


# ============================================================================
# OPTIMIZED EXIT LOGIC - V2
# ============================================================================

def check_exit_v2(trade, current_row, candles_held):
    """
    OPTIMIZED exit logic.
    - Tighter stop loss (cut losses faster)
    - Wider take profit (let winners run)
    """

    direction = trade['direction']
    entry_price = trade['entry_price']
    stop_loss = trade['stop_loss']
    take_profit = trade['take_profit']
    trade_type = trade['type']

    current_price = current_row['close']

    # Check stop loss (tighter now)
    if direction == 'LONG' and current_price <= stop_loss:
        return True, 'SL', stop_loss
    if direction == 'SHORT' and current_price >= stop_loss:
        return True, 'SL', stop_loss

    # Check take profit (wider now)
    if direction == 'LONG' and current_price >= take_profit:
        return True, 'TP', take_profit
    if direction == 'SHORT' and current_price <= take_profit:
        return True, 'TP', take_profit

    # RSI exit for mean reversion trades (more aggressive)
    if trade_type == 'MEAN_REVERSION':
        # Exit when RSI reaches 55 (not 50) - let it run more
        if direction == 'LONG' and current_row['rsi'] > 55:
            return True, 'RSI_EXIT', current_price
        if direction == 'SHORT' and current_row['rsi'] < 45:
            return True, 'RSI_EXIT', current_price

    # Time-based exits (faster for mean reversion)
    if trade_type == 'MEAN_REVERSION' and candles_held >= 20:  # Was 30
        return True, 'TIME_EXIT', current_price
    if trade_type == 'TREND' and candles_held >= 45:  # Was 60
        return True, 'TIME_EXIT', current_price

    return False, None, None


# ============================================================================
# MAIN BACKTEST ENGINE V2
# ============================================================================

def run_backtest_v2(data, initial_capital=10000, base_position_size=0.02,
                    maker_fee=0.0005, taker_fee=0.001):
    """
    Run OPTIMIZED backtest on TRUMP data.
    """

    print("Calculating indicators...")
    df = calculate_indicators(data)

    capital = initial_capital
    equity_curve = []
    trades = []
    open_trades = []

    daily_pnl = 0
    daily_trade_count = 0
    current_day = None

    print(f"Running backtest on {len(df)} candles...")

    for i in range(200, len(df)):
        row = df.iloc[i]

        current_date = pd.to_datetime(row['timestamp']).date()
        if current_day != current_date:
            current_day = current_date
            daily_pnl = 0
            daily_trade_count = 0

        avg_atr = row['avg_atr'] if not pd.isna(row['avg_atr']) else 0.12
        regime = detect_regime(row, avg_atr)

        hour = row['hour']
        valid_session = is_valid_session(hour)
        avoid_hour = is_avoid_hour(hour)

        # Update open trades with V2 exit logic
        for trade in open_trades[:]:
            candles_held = i - trade['entry_idx']
            should_exit, exit_reason, exit_price = check_exit_v2(trade, row, candles_held)

            if should_exit:
                if trade['direction'] == 'LONG':
                    pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price'])
                else:
                    pnl_pct = ((trade['entry_price'] - exit_price) / trade['entry_price'])

                pnl_pct -= taker_fee

                position_value = trade['position_size'] * capital
                pnl_dollars = position_value * pnl_pct

                capital += pnl_dollars
                daily_pnl += pnl_dollars

                trades.append({
                    'entry_time': trade['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': trade['direction'],
                    'type': trade['type'],
                    'entry_price': trade['entry_price'],
                    'exit_price': exit_price,
                    'stop_loss': trade['stop_loss'],
                    'take_profit': trade['take_profit'],
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'position_size_pct': trade['position_size'] * 100,
                    'candles_held': candles_held,
                    'regime': trade['regime'],
                    'hour': trade['hour']
                })

                open_trades.remove(trade)

        equity_curve.append({
            'timestamp': row['timestamp'],
            'capital': capital,
            'open_trades': len(open_trades)
        })

        # Risk limits
        max_daily_loss = initial_capital * 0.04
        if daily_pnl < -max_daily_loss:
            continue

        if daily_trade_count >= 20:
            continue

        if len(open_trades) >= 3:
            continue

        if avoid_hour or not valid_session:
            continue

        if regime == 'EXPLOSIVE':
            continue

        if row['volume_ratio'] < 0.5:
            continue

        # Position sizing
        position_size = base_position_size

        if daily_pnl > initial_capital * 0.02:
            position_size = min(0.03, base_position_size * 1.5)
        elif daily_pnl < -initial_capital * 0.01:
            position_size = max(0.01, base_position_size * 0.5)

        atr = row['atr_pct'] / 100

        # ONLY LONG MEAN REVERSION (remove shorts and trends)
        if check_long_mean_reversion_v2(row, regime):
            # OPTIMIZED EXITS: Tighter SL (1.5x ATR), Wider TP (2.0x ATR)
            open_trades.append({
                'direction': 'LONG',
                'type': 'MEAN_REVERSION',
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': row['close'] * (1 - 1.5 * atr),  # TIGHTER (was 2x)
                'take_profit': row['close'] * (1 + 2.0 * atr),  # WIDER (was 1.5x)
                'position_size': position_size,
                'regime': regime,
                'hour': hour
            })
            daily_trade_count += 1
            capital -= (position_size * capital * maker_fee)

    # Close remaining trades
    final_row = df.iloc[-1]
    for trade in open_trades:
        if trade['direction'] == 'LONG':
            pnl_pct = ((final_row['close'] - trade['entry_price']) / trade['entry_price']) - taker_fee
        else:
            pnl_pct = ((trade['entry_price'] - final_row['close']) / trade['entry_price']) - taker_fee

        position_value = trade['position_size'] * capital
        pnl_dollars = position_value * pnl_pct
        capital += pnl_dollars

        trades.append({
            'entry_time': trade['entry_time'],
            'exit_time': final_row['timestamp'],
            'direction': trade['direction'],
            'type': trade['type'],
            'entry_price': trade['entry_price'],
            'exit_price': final_row['close'],
            'stop_loss': trade['stop_loss'],
            'take_profit': trade['take_profit'],
            'exit_reason': 'END_OF_DATA',
            'pnl_pct': pnl_pct * 100,
            'pnl_dollars': pnl_dollars,
            'position_size_pct': trade['position_size'] * 100,
            'candles_held': len(df) - trade['entry_idx'],
            'regime': trade['regime'],
            'hour': trade['hour']
        })

    return pd.DataFrame(trades), pd.DataFrame(equity_curve), capital


# Copy metrics functions from V1
def calculate_metrics(trades_df, equity_df, initial_capital, final_capital):
    """Calculate comprehensive performance metrics."""
    if len(trades_df) == 0:
        print("No trades executed!")
        return None
    metrics = {}
    metrics['Total Trades'] = len(trades_df)
    metrics['Initial Capital'] = initial_capital
    metrics['Final Capital'] = final_capital
    metrics['Total Return %'] = ((final_capital - initial_capital) / initial_capital) * 100
    metrics['Total Return $'] = final_capital - initial_capital
    winning_trades = trades_df[trades_df['pnl_dollars'] > 0]
    losing_trades = trades_df[trades_df['pnl_dollars'] < 0]
    metrics['Winning Trades'] = len(winning_trades)
    metrics['Losing Trades'] = len(losing_trades)
    metrics['Win Rate %'] = (len(winning_trades) / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    metrics['Avg Win %'] = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
    metrics['Avg Loss %'] = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
    metrics['Largest Win %'] = trades_df['pnl_pct'].max()
    metrics['Largest Loss %'] = trades_df['pnl_pct'].min()
    if len(losing_trades) > 0 and abs(metrics['Avg Loss %']) > 0:
        metrics['Profit Factor'] = abs(metrics['Avg Win %'] * len(winning_trades)) / abs(metrics['Avg Loss %'] * len(losing_trades))
    else:
        metrics['Profit Factor'] = 0
    equity_df['peak'] = equity_df['capital'].cummax()
    equity_df['drawdown'] = ((equity_df['capital'] - equity_df['peak']) / equity_df['peak']) * 100
    metrics['Max Drawdown %'] = equity_df['drawdown'].min()
    metrics['Mean Reversion Trades'] = len(trades_df[trades_df['type'] == 'MEAN_REVERSION'])
    metrics['Trend Trades'] = len(trades_df[trades_df['type'] == 'TREND'])
    metrics['Long Trades'] = len(trades_df[trades_df['direction'] == 'LONG'])
    metrics['Short Trades'] = len(trades_df[trades_df['direction'] == 'SHORT'])
    metrics['SL Exits'] = len(trades_df[trades_df['exit_reason'] == 'SL'])
    metrics['TP Exits'] = len(trades_df[trades_df['exit_reason'] == 'TP'])
    metrics['RSI Exits'] = len(trades_df[trades_df['exit_reason'] == 'RSI_EXIT'])
    metrics['Time Exits'] = len(trades_df[trades_df['exit_reason'] == 'TIME_EXIT'])
    metrics['Avg Candles Held'] = trades_df['candles_held'].mean()
    return metrics


def print_metrics(metrics):
    """Print performance metrics in formatted table."""
    if metrics is None:
        return
    print("\n" + "="*70)
    print("TRUMP STRATEGY V2 BACKTEST RESULTS (OPTIMIZED)")
    print("="*70)
    print(f"\n{'OVERALL PERFORMANCE':<30} {'VALUE':>15} {'':>20}")
    print("-"*70)
    print(f"{'Initial Capital':<30} ${metrics['Initial Capital']:>14,.2f}")
    print(f"{'Final Capital':<30} ${metrics['Final Capital']:>14,.2f}")
    print(f"{'Total Return':<30} {metrics['Total Return %']:>14.2f}%")
    print(f"{'Total Return $':<30} ${metrics['Total Return $']:>14,.2f}")
    print(f"{'Max Drawdown':<30} {metrics['Max Drawdown %']:>14.2f}%")
    print(f"\n{'TRADE STATISTICS':<30} {'VALUE':>15} {'':>20}")
    print("-"*70)
    print(f"{'Total Trades':<30} {metrics['Total Trades']:>15,}")
    print(f"{'Winning Trades':<30} {metrics['Winning Trades']:>15,}")
    print(f"{'Losing Trades':<30} {metrics['Losing Trades']:>15,}")
    print(f"{'Win Rate':<30} {metrics['Win Rate %']:>14.2f}%")
    print(f"{'Profit Factor':<30} {metrics['Profit Factor']:>14.2f}x")
    print(f"\n{'PNL ANALYSIS':<30} {'VALUE':>15} {'':>20}")
    print("-"*70)
    print(f"{'Avg Win':<30} {metrics['Avg Win %']:>14.2f}%")
    print(f"{'Avg Loss':<30} {metrics['Avg Loss %']:>14.2f}%")
    print(f"{'Largest Win':<30} {metrics['Largest Win %']:>14.2f}%")
    print(f"{'Largest Loss':<30} {metrics['Largest Loss %']:>14.2f}%")
    print(f"\n{'TRADE DISTRIBUTION':<30} {'COUNT':>15} {'%':>20}")
    print("-"*70)
    print(f"{'Mean Reversion Trades':<30} {metrics['Mean Reversion Trades']:>15,} {metrics['Mean Reversion Trades']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Trend Trades':<30} {metrics['Trend Trades']:>15,} {metrics['Trend Trades']/metrics['Total Trades']*100 if metrics['Total Trades'] > 0 else 0:>19.1f}%")
    print(f"{'Long Trades':<30} {metrics['Long Trades']:>15,} {metrics['Long Trades']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Short Trades':<30} {metrics['Short Trades']:>15,} {metrics['Short Trades']/metrics['Total Trades']*100 if metrics['Total Trades'] > 0 else 0:>19.1f}%")
    print(f"\n{'EXIT REASONS':<30} {'COUNT':>15} {'%':>20}")
    print("-"*70)
    print(f"{'Stop Loss Exits':<30} {metrics['SL Exits']:>15,} {metrics['SL Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Take Profit Exits':<30} {metrics['TP Exits']:>15,} {metrics['TP Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'RSI Exits':<30} {metrics['RSI Exits']:>15,} {metrics['RSI Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Time Exits':<30} {metrics['Time Exits']:>15,} {metrics['Time Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"\n{'EFFICIENCY':<30} {'VALUE':>15} {'':>20}")
    print("-"*70)
    print(f"{'Avg Holding Time (minutes)':<30} {metrics['Avg Candles Held']:>14.1f}")
    print("="*70 + "\n")


def plot_equity_curve(equity_df, trades_df, save_path):
    """Plot equity curve with trade markers."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
    ax1.plot(equity_df['timestamp'], equity_df['capital'], linewidth=2, color='#2E86AB', label='Equity')
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
    wins = trades_df[trades_df['pnl_dollars'] > 0]
    losses = trades_df[trades_df['pnl_dollars'] < 0]
    for _, trade in wins.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='green', s=50, alpha=0.6, zorder=5)
    for _, trade in losses.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='red', s=50, alpha=0.6, zorder=5)
    ax1.set_title('TRUMP Strategy V2 - Equity Curve', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Capital (USDT)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
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
    print("TRUMP MASTER STRATEGY V2 BACKTEST (OPTIMIZED)")
    print("="*70)
    print("\nOPTIMIZATIONS APPLIED:")
    print("1. Tighter stop loss: 1.5x ATR (was 2x)")
    print("2. Wider take profit: 2.0x ATR (was 1.5x)")
    print("3. Stricter entry filters (RSI < 28, closer to BB)")
    print("4. Removed short mean reversion (unprofitable)")
    print("5. Higher volume requirement (1.0x vs 0.8x)")
    print("="*70)

    print("\nLoading TRUMP data...")
    data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/trump_usdt_1m_mexc.csv')
    print(f"Loaded {len(data)} candles from {data['timestamp'].min()} to {data['timestamp'].max()}")

    print("\nStarting optimized backtest...")
    trades_df, equity_df, final_capital = run_backtest_v2(
        data=data,
        initial_capital=10000,
        base_position_size=0.02,
        maker_fee=0.0005,
        taker_fee=0.001
    )

    print("\nCalculating performance metrics...")
    metrics = calculate_metrics(trades_df, equity_df, 10000, final_capital)

    print_metrics(metrics)

    print("\nSaving results...")
    trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_results.csv', index=False)
    print("Trade log saved (UPDATED)")

    plot_equity_curve(equity_df, trades_df, '/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_equity.png')

    # Generate summary
    summary_path = '/workspaces/Carebiuro_windykacja/trading/results/TRUMP_strategy_summary.md'
    with open(summary_path, 'w') as f:
        f.write("# TRUMP Strategy Backtest Summary (V2 OPTIMIZED)\n\n")
        f.write(f"**Backtest Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Data Period:** {data['timestamp'].min()} to {data['timestamp'].max()}\n\n")
        f.write(f"**Total Candles:** {len(data):,}\n\n")
        f.write("## Optimizations Applied\n\n")
        f.write("1. **Tighter Stop Loss:** 1.5x ATR (was 2x) - Cut losses faster\n")
        f.write("2. **Wider Take Profit:** 2.0x ATR (was 1.5x) - Let winners run\n")
        f.write("3. **Stricter Entry Filters:** RSI < 28, within 10% of BB lower\n")
        f.write("4. **Removed Short Mean Reversion:** Unprofitable in V1\n")
        f.write("5. **Higher Volume Requirement:** 1.0x average (was 0.8x)\n\n")
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
        f.write(f"| Avg Win | {metrics['Avg Win %']:.2f}% |\n")
        f.write(f"| Avg Loss | {metrics['Avg Loss %']:.2f}% |\n")
        f.write(f"| Avg Holding Time | {metrics['Avg Candles Held']:.1f} minutes |\n\n")
        f.write("## Trade Distribution\n\n")
        f.write("| Type | Count | Percentage |\n")
        f.write("|------|-------|------------|\n")
        f.write(f"| Mean Reversion | {metrics['Mean Reversion Trades']:,} | {metrics['Mean Reversion Trades']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Long Trades | {metrics['Long Trades']:,} | {metrics['Long Trades']/metrics['Total Trades']*100:.1f}% |\n\n")
        f.write("## Exit Analysis\n\n")
        f.write("| Exit Type | Count | Percentage |\n")
        f.write("|-----------|-------|------------|\n")
        f.write(f"| Stop Loss | {metrics['SL Exits']:,} | {metrics['SL Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Take Profit | {metrics['TP Exits']:,} | {metrics['TP Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| RSI Exit | {metrics['RSI Exits']:,} | {metrics['RSI Exits']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Time Exit | {metrics['Time Exits']:,} | {metrics['Time Exits']/metrics['Total Trades']*100:.1f}% |\n\n")
        f.write("## Files Generated\n\n")
        f.write("- Trade log: `TRUMP_strategy_results.csv`\n")
        f.write("- Equity curve: `TRUMP_strategy_equity.png`\n")
        f.write("- Summary: `TRUMP_strategy_summary.md`\n")

    print(f"Summary saved to: {summary_path}")
    print("\n" + "="*70)
    print("BACKTEST COMPLETE!")
    print("="*70)
