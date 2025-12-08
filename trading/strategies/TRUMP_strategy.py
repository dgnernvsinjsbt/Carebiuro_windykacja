"""
TRUMP Master Trading Strategy - Backtest Implementation
Strategy: Hybrid Mean Reversion + Trend Following
Designed: 2025-12-07
Author: Master Trader AI

Custom-tailored for TRUMP's ultra-low volatility, mean-reverting personality.
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

    # Make a copy
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
    data['sma50'] = data['close'].rolling(50).mean()
    data['sma200'] = data['close'].rolling(200).mean()

    # Bollinger Bands
    data['bb_middle'] = data['close'].rolling(20).mean()
    bb_std = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_middle'] + (2 * bb_std)
    data['bb_lower'] = data['bb_middle'] - (2 * bb_std)
    data['bb_width'] = ((data['bb_upper'] - data['bb_lower']) / data['bb_middle']) * 100

    # Distance to BB
    data['dist_to_bb_lower'] = ((data['close'] - data['bb_lower']) / data['bb_lower']) * 100
    data['dist_to_bb_upper'] = ((data['bb_upper'] - data['close']) / data['bb_upper']) * 100

    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift())
    low_close = abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['atr'] = true_range.rolling(14).mean()
    data['atr_pct'] = (data['atr'] / data['close']) * 100

    # Average ATR for regime detection
    data['avg_atr'] = data['atr_pct'].rolling(100).mean()

    # Volume metrics
    data['avg_volume'] = data['volume'].rolling(50).mean()
    data['volume_ratio'] = data['volume'] / data['avg_volume']

    # Sequential patterns
    data['consecutive_red'] = 0
    data['consecutive_green'] = 0

    for i in range(4, len(data)):
        # Count consecutive reds
        if all(data['is_red'].iloc[i-j] == 1 for j in range(4)):
            data.loc[data.index[i], 'consecutive_red'] = 4
        if i >= 4 and all(data['is_red'].iloc[i-j] == 1 for j in range(5)):
            data.loc[data.index[i], 'consecutive_red'] = 5

        # Count consecutive greens
        if all(data['is_green'].iloc[i-j] == 1 for j in range(4)):
            data.loc[data.index[i], 'consecutive_green'] = 4
        if i >= 4 and all(data['is_green'].iloc[i-j] == 1 for j in range(5)):
            data.loc[data.index[i], 'consecutive_green'] = 5

    # Hour of day (UTC)
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour

    return data


# ============================================================================
# REGIME DETECTION
# ============================================================================

def detect_regime(row, avg_atr):
    """Detect market regime for current candle."""

    # Missing data
    if pd.isna(row['sma50']) or pd.isna(row['sma200']) or pd.isna(row['atr_pct']):
        return 'UNKNOWN'

    # EXPLOSIVE regime
    if row['atr_pct'] > 0.35 or row['body_pct'] > 1.0:
        return 'EXPLOSIVE'

    # CHOPPY regime (very low volatility)
    if row['atr_pct'] < 0.10:
        return 'CHOPPY'

    # Distance from SMA200
    dist_from_sma200 = ((row['close'] - row['sma200']) / row['sma200']) * 100

    # TRENDING regimes
    if row['close'] > row['sma50'] > row['sma200'] and row['atr_pct'] > avg_atr:
        return 'TRENDING_UP'
    elif row['close'] < row['sma50'] < row['sma200'] and row['atr_pct'] > avg_atr:
        return 'TRENDING_DOWN'

    # MEAN REVERTING regime
    if abs(dist_from_sma200) < 1.0 and row['atr_pct'] < avg_atr:
        return 'MEAN_REVERTING'

    return 'CHOPPY'


# ============================================================================
# SESSION FILTERS
# ============================================================================

def is_valid_session(hour):
    """Check if current hour is in valid trading session."""

    # US session (primary) - 14:00-21:00 UTC
    if 14 <= hour < 21:
        return True

    # Asia prime hours - 2:00-4:00 UTC
    if 2 <= hour < 5:
        return True

    return False


def is_avoid_hour(hour):
    """Check if current hour should be avoided."""

    # Hard avoid hours
    if hour == 23 or hour == 3:
        return True

    # Overnight session (soft avoid)
    if 21 <= hour < 24 or hour == 0:
        return True

    return False


# ============================================================================
# ENTRY SIGNALS
# ============================================================================

def check_long_mean_reversion(row, regime):
    """Check for long mean reversion entry signal."""

    # Must be in valid regime
    if regime not in ['MEAN_REVERTING', 'TRENDING_DOWN', 'CHOPPY']:
        return False

    # Primary signal: RSI oversold OR consecutive reds
    primary_signal = (row['rsi'] < 30) or (row['consecutive_red'] >= 4)

    if not primary_signal:
        return False

    # Confirmation filters
    near_bb_lower = row['dist_to_bb_lower'] < 20  # Within 20% of distance to BB lower
    no_large_lower_wick = (row['lower_wick'] / row['range'] < 0.5) if row['range'] > 0 else True
    sufficient_volume = row['volume_ratio'] > 0.8
    not_explosive = row['atr_pct'] < 0.35

    return all([near_bb_lower, no_large_lower_wick, sufficient_volume, not_explosive])


def check_short_mean_reversion(row, regime):
    """Check for short mean reversion entry signal."""

    # Must be in valid regime
    if regime not in ['MEAN_REVERTING', 'TRENDING_UP']:
        return False

    # Primary signal: RSI overbought AND near BB upper
    if row['rsi'] < 70:
        return False

    price_at_bb = row['dist_to_bb_upper'] < 5  # Very close to upper BB

    if not price_at_bb:
        return False

    # Confirmation filters
    no_large_upper_wick = (row['upper_wick'] / row['range'] < 0.5) if row['range'] > 0 else True
    sufficient_volume = row['volume_ratio'] > 0.8
    in_uptrend = row['close'] > row['sma50'] * 1.01 if not pd.isna(row['sma50']) else False

    return all([no_large_upper_wick, sufficient_volume, in_uptrend])


def check_long_trend(row, regime):
    """Check for long trend entry signal."""

    # Must be trending up
    if regime != 'TRENDING_UP':
        return False

    # Check trend structure
    if pd.isna(row['sma50']) or pd.isna(row['sma200']):
        return False

    uptrend = row['close'] > row['sma50'] > row['sma200']
    strong_candle = row['body_pct'] > 0.15
    volume_surge = row['volume_ratio'] > 2.0
    rsi_momentum = 50 <= row['rsi'] <= 65

    return all([uptrend, strong_candle, volume_surge, rsi_momentum])


def check_short_trend(row, regime):
    """Check for short trend entry signal."""

    # Must be trending down
    if regime != 'TRENDING_DOWN':
        return False

    # Check trend structure
    if pd.isna(row['sma50']) or pd.isna(row['sma200']):
        return False

    downtrend = row['close'] < row['sma50'] < row['sma200']
    strong_candle = row['body_pct'] > 0.15
    volume_surge = row['volume_ratio'] > 2.0
    rsi_momentum = 35 <= row['rsi'] <= 50

    return all([downtrend, strong_candle, volume_surge, rsi_momentum])


# ============================================================================
# EXIT LOGIC
# ============================================================================

def check_exit(trade, current_row, candles_held):
    """Check if current trade should be exited."""

    direction = trade['direction']
    entry_price = trade['entry_price']
    stop_loss = trade['stop_loss']
    take_profit = trade['take_profit']
    trade_type = trade['type']

    current_price = current_row['close']

    # Check stop loss
    if direction == 'LONG' and current_price <= stop_loss:
        return True, 'SL', stop_loss
    if direction == 'SHORT' and current_price >= stop_loss:
        return True, 'SL', stop_loss

    # Check take profit
    if direction == 'LONG' and current_price >= take_profit:
        return True, 'TP', take_profit
    if direction == 'SHORT' and current_price <= take_profit:
        return True, 'TP', take_profit

    # RSI exit for mean reversion trades
    if trade_type == 'MEAN_REVERSION':
        if direction == 'LONG' and current_row['rsi'] > 50:
            return True, 'RSI_EXIT', current_price
        if direction == 'SHORT' and current_row['rsi'] < 50:
            return True, 'RSI_EXIT', current_price

    # Time-based exits
    if trade_type == 'MEAN_REVERSION' and candles_held >= 30:
        return True, 'TIME_EXIT', current_price
    if trade_type == 'TREND' and candles_held >= 60:
        return True, 'TIME_EXIT', current_price

    return False, None, None


# ============================================================================
# MAIN BACKTEST ENGINE
# ============================================================================

def run_backtest(data, initial_capital=10000, base_position_size=0.02,
                 maker_fee=0.0005, taker_fee=0.001):
    """
    Run complete backtest on TRUMP data.

    Parameters:
    - data: DataFrame with OHLCV data
    - initial_capital: Starting capital in USDT
    - base_position_size: Base position size as fraction of capital (0.02 = 2%)
    - maker_fee: Maker fee (0.0005 = 0.05%)
    - taker_fee: Taker fee (0.001 = 0.10%)
    """

    print("Calculating indicators...")
    df = calculate_indicators(data)

    # Initialize tracking
    capital = initial_capital
    equity_curve = []
    trades = []
    open_trades = []

    daily_pnl = 0
    daily_trade_count = 0
    current_day = None

    print(f"Running backtest on {len(df)} candles...")

    for i in range(200, len(df)):  # Start after enough data for indicators
        row = df.iloc[i]

        # Track day changes
        current_date = pd.to_datetime(row['timestamp']).date()
        if current_day != current_date:
            current_day = current_date
            daily_pnl = 0
            daily_trade_count = 0

        # Detect regime
        avg_atr = row['avg_atr'] if not pd.isna(row['avg_atr']) else 0.12
        regime = detect_regime(row, avg_atr)

        # Check session filters
        hour = row['hour']
        valid_session = is_valid_session(hour)
        avoid_hour = is_avoid_hour(hour)

        # Update open trades
        for trade in open_trades[:]:
            candles_held = i - trade['entry_idx']
            should_exit, exit_reason, exit_price = check_exit(trade, row, candles_held)

            if should_exit:
                # Calculate PnL
                if trade['direction'] == 'LONG':
                    pnl_pct = ((exit_price - trade['entry_price']) / trade['entry_price'])
                else:  # SHORT
                    pnl_pct = ((trade['entry_price'] - exit_price) / trade['entry_price'])

                # Apply fees (taker fee on exit)
                pnl_pct -= taker_fee

                # Calculate dollar PnL
                position_value = trade['position_size'] * capital
                pnl_dollars = position_value * pnl_pct

                capital += pnl_dollars
                daily_pnl += pnl_dollars

                # Record trade
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

        # Record equity
        equity_curve.append({
            'timestamp': row['timestamp'],
            'capital': capital,
            'open_trades': len(open_trades)
        })

        # Check risk limits
        max_daily_loss = initial_capital * 0.04
        if daily_pnl < -max_daily_loss:
            continue  # Stop trading for the day

        if daily_trade_count >= 20:
            continue  # Max trades per day

        if len(open_trades) >= 3:
            continue  # Max concurrent trades

        # Skip if avoid conditions
        if avoid_hour or not valid_session:
            continue

        if regime == 'EXPLOSIVE':
            continue

        if row['volume_ratio'] < 0.5:
            continue  # Insufficient volume

        # Calculate position size
        position_size = base_position_size

        # Scale based on performance (simplified - would track win rate in production)
        if daily_pnl > initial_capital * 0.02:  # Winning day
            position_size = min(0.03, base_position_size * 1.5)
        elif daily_pnl < -initial_capital * 0.01:  # Losing day
            position_size = max(0.01, base_position_size * 0.5)

        # Check entry signals
        atr = row['atr_pct'] / 100  # Convert to decimal

        # LONG MEAN REVERSION
        if check_long_mean_reversion(row, regime):
            open_trades.append({
                'direction': 'LONG',
                'type': 'MEAN_REVERSION',
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': row['close'] * (1 - 2 * atr),
                'take_profit': row['close'] * (1 + 1.5 * atr),
                'position_size': position_size,
                'regime': regime,
                'hour': hour
            })
            daily_trade_count += 1
            # Apply entry fee
            capital -= (position_size * capital * maker_fee)

        # SHORT MEAN REVERSION
        elif check_short_mean_reversion(row, regime):
            open_trades.append({
                'direction': 'SHORT',
                'type': 'MEAN_REVERSION',
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': row['close'] * (1 + 2 * atr),
                'take_profit': row['close'] * (1 - 1.5 * atr),
                'position_size': position_size,
                'regime': regime,
                'hour': hour
            })
            daily_trade_count += 1
            capital -= (position_size * capital * maker_fee)

        # LONG TREND
        elif check_long_trend(row, regime):
            open_trades.append({
                'direction': 'LONG',
                'type': 'TREND',
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': row['close'] * (1 - 3 * atr),
                'take_profit': row['close'] * (1 + 5 * atr),
                'position_size': position_size,
                'regime': regime,
                'hour': hour
            })
            daily_trade_count += 1
            capital -= (position_size * capital * taker_fee)  # Trend = market order

        # SHORT TREND
        elif check_short_trend(row, regime):
            open_trades.append({
                'direction': 'SHORT',
                'type': 'TREND',
                'entry_time': row['timestamp'],
                'entry_idx': i,
                'entry_price': row['close'],
                'stop_loss': row['close'] * (1 + 3 * atr),
                'take_profit': row['close'] * (1 - 5 * atr),
                'position_size': position_size,
                'regime': regime,
                'hour': hour
            })
            daily_trade_count += 1
            capital -= (position_size * capital * taker_fee)

    # Close any remaining open trades at final price
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

    # Drawdown
    equity_df['peak'] = equity_df['capital'].cummax()
    equity_df['drawdown'] = ((equity_df['capital'] - equity_df['peak']) / equity_df['peak']) * 100
    metrics['Max Drawdown %'] = equity_df['drawdown'].min()

    # Trade distribution
    metrics['Mean Reversion Trades'] = len(trades_df[trades_df['type'] == 'MEAN_REVERSION'])
    metrics['Trend Trades'] = len(trades_df[trades_df['type'] == 'TREND'])
    metrics['Long Trades'] = len(trades_df[trades_df['direction'] == 'LONG'])
    metrics['Short Trades'] = len(trades_df[trades_df['direction'] == 'SHORT'])

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
    print("TRUMP STRATEGY BACKTEST RESULTS")
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
    print(f"{'Trend Trades':<30} {metrics['Trend Trades']:>15,} {metrics['Trend Trades']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Long Trades':<30} {metrics['Long Trades']:>15,} {metrics['Long Trades']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Short Trades':<30} {metrics['Short Trades']:>15,} {metrics['Short Trades']/metrics['Total Trades']*100:>19.1f}%")

    print(f"\n{'EXIT REASONS':<30} {'COUNT':>15} {'%':>20}")
    print("-"*70)
    print(f"{'Stop Loss Exits':<30} {metrics['SL Exits']:>15,} {metrics['SL Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Take Profit Exits':<30} {metrics['TP Exits']:>15,} {metrics['TP Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'RSI Exits':<30} {metrics['RSI Exits']:>15,} {metrics['RSI Exits']/metrics['Total Trades']*100:>19.1f}%")
    print(f"{'Time Exits':<30} {metrics['Time Exits']:>15,} {metrics['Time Exits']/metrics['Total Trades']*100:>19.1f}%")

    print(f"\n{'EFFICIENCY':<30} {'VALUE':>15} {'':>20}")
    print("-"*70)
    print(f"{'Avg Holding Time (candles)':<30} {metrics['Avg Candles Held']:>14.1f}")
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

    # Merge with equity to get capital at entry time
    for _, trade in wins.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='green', s=50, alpha=0.6, zorder=5)

    for _, trade in losses.iterrows():
        equity_at_entry = equity_df[equity_df['timestamp'] >= trade['entry_time']].iloc[0]['capital']
        ax1.scatter(trade['entry_time'], equity_at_entry, color='red', s=50, alpha=0.6, zorder=5)

    ax1.set_title('TRUMP Strategy - Equity Curve', fontsize=16, fontweight='bold')
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
    print("TRUMP MASTER STRATEGY BACKTEST")
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
        base_position_size=0.02,  # 2%
        maker_fee=0.0005,  # 0.05%
        taker_fee=0.001    # 0.10%
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
        f.write("# TRUMP Strategy Backtest Summary\n\n")
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
        f.write(f"| Avg Win | {metrics['Avg Win %']:.2f}% |\n")
        f.write(f"| Avg Loss | {metrics['Avg Loss %']:.2f}% |\n")
        f.write(f"| Avg Holding Time | {metrics['Avg Candles Held']:.1f} minutes |\n")

        f.write("\n## Trade Distribution\n\n")
        f.write("| Type | Count | Percentage |\n")
        f.write("|------|-------|------------|\n")
        f.write(f"| Mean Reversion | {metrics['Mean Reversion Trades']:,} | {metrics['Mean Reversion Trades']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Trend Following | {metrics['Trend Trades']:,} | {metrics['Trend Trades']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Long Trades | {metrics['Long Trades']:,} | {metrics['Long Trades']/metrics['Total Trades']*100:.1f}% |\n")
        f.write(f"| Short Trades | {metrics['Short Trades']:,} | {metrics['Short Trades']/metrics['Total Trades']*100:.1f}% |\n")

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
