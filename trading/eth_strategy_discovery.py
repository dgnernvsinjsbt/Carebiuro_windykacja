"""
ETH Strategy Discovery - Find profitable strategies with >4:1 profit/DD ratio

Tests multiple approaches:
- Mean reversion strategies (RSI oversold/overbought)
- Breakout strategies (range breakouts, volume spikes)
- Trend following (EMA crossovers, pullbacks)
- Time-based filters (trading session optimization)
- Dynamic position sizing (volatility-based, Kelly criterion)
- Multi-timeframe confirmation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import itertools


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

    # RSI (multiple periods)
    for period in [14, 21, 7]:
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

    # Hour of day (for session trading)
    df['hour'] = df['timestamp'].dt.hour

    return df


def backtest_strategy(df, strategy_func, name, **kwargs):
    """Generic backtest function"""

    trades = []
    in_position = False
    entry_price = None
    stop_loss = None
    take_profit = None
    entry_idx = None
    direction = None

    for i in range(250, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Check for entry signal
            signal = strategy_func(df, i, **kwargs)

            if signal:
                in_position = True
                entry_price = signal['entry_price']
                stop_loss = signal['stop_loss']
                take_profit = signal['take_profit']
                direction = signal['direction']
                entry_idx = i

        else:
            # Check for exit
            if direction == 'LONG':
                if row['low'] <= stop_loss:
                    # SL hit
                    pnl_pct = ((stop_loss - entry_price) / entry_price) * 100
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'exit_type': 'SL',
                        'pnl_pct': pnl_pct
                    })
                    in_position = False

                elif row['high'] >= take_profit:
                    # TP hit
                    pnl_pct = ((take_profit - entry_price) / entry_price) * 100
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'exit_type': 'TP',
                        'pnl_pct': pnl_pct
                    })
                    in_position = False

            elif direction == 'SHORT':
                if row['high'] >= stop_loss:
                    # SL hit
                    pnl_pct = ((entry_price - stop_loss) / entry_price) * 100
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'exit_type': 'SL',
                        'pnl_pct': pnl_pct
                    })
                    in_position = False

                elif row['low'] <= take_profit:
                    # TP hit
                    pnl_pct = ((entry_price - take_profit) / entry_price) * 100
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'exit_type': 'TP',
                        'pnl_pct': pnl_pct
                    })
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)

    # Calculate metrics
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0

    avg_win = wins['pnl_pct'].mean() if num_wins > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if num_losses > 0 else 0

    total_return = trades_df['pnl_pct'].sum()

    # Drawdown
    cumulative = (1 + trades_df['pnl_pct'] / 100).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Profit/DD ratio
    profit_dd_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    return {
        'name': name,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'profit_dd_ratio': profit_dd_ratio,
        'trades_df': trades_df
    }


# =============================================================================
# STRATEGY 1: RSI Mean Reversion
# =============================================================================

def rsi_mean_reversion(df, i, rsi_period=14, oversold=30, overbought=70,
                       stop_mult=2.0, target_mult=4.0):
    """
    Buy oversold, sell overbought
    Works well in ranging markets
    """
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


# =============================================================================
# STRATEGY 2: Bollinger Band Bounce
# =============================================================================

def bb_bounce(df, i, stop_mult=2.0, target_mult=4.0, bb_threshold=0.1):
    """
    Buy at lower band, sell at upper band
    Only in low volatility (tight BB)
    """
    row = df.iloc[i]

    if pd.isna(row['bb_position']) or pd.isna(row['atr']):
        return None

    # Only trade when BB is not too wide (ranging market)
    if row['bb_width'] > 3.0:  # Skip high volatility
        return None

    # LONG: Price at lower BB
    if row['bb_position'] < bb_threshold:
        return {
            'direction': 'LONG',
            'entry_price': row['close'],
            'stop_loss': row['close'] - (stop_mult * row['atr']),
            'take_profit': row['close'] + (target_mult * row['atr'])
        }

    # SHORT: Price at upper BB
    elif row['bb_position'] > (1 - bb_threshold):
        return {
            'direction': 'SHORT',
            'entry_price': row['close'],
            'stop_loss': row['close'] + (stop_mult * row['atr']),
            'take_profit': row['close'] - (target_mult * row['atr'])
        }

    return None


# =============================================================================
# STRATEGY 3: EMA Pullback (Trend Following)
# =============================================================================

def ema_pullback(df, i, fast_ema=20, slow_ema=50, stop_mult=2.0, target_mult=6.0):
    """
    Buy pullbacks in uptrend, sell rallies in downtrend
    """
    row = df.iloc[i]
    prev = df.iloc[i-1]

    if pd.isna(row[f'ema_{fast_ema}']) or pd.isna(row[f'ema_{slow_ema}']):
        return None

    # LONG: Pullback in uptrend
    if (row[f'ema_{fast_ema}'] > row[f'ema_{slow_ema}'] and  # Uptrend
        prev['close'] < prev[f'ema_{fast_ema}'] and  # Was below EMA
        row['close'] > row[f'ema_{fast_ema}']):  # Now crossed above

        return {
            'direction': 'LONG',
            'entry_price': row['close'],
            'stop_loss': row['close'] - (stop_mult * row['atr']),
            'take_profit': row['close'] + (target_mult * row['atr'])
        }

    # SHORT: Rally in downtrend
    elif (row[f'ema_{fast_ema}'] < row[f'ema_{slow_ema}'] and  # Downtrend
          prev['close'] > prev[f'ema_{fast_ema}'] and  # Was above EMA
          row['close'] < row[f'ema_{fast_ema}']):  # Now crossed below

        return {
            'direction': 'SHORT',
            'entry_price': row['close'],
            'stop_loss': row['close'] + (stop_mult * row['atr']),
            'take_profit': row['close'] - (target_mult * row['atr'])
        }

    return None


# =============================================================================
# STRATEGY 4: Volume Breakout
# =============================================================================

def volume_breakout(df, i, vol_threshold=2.5, stop_mult=2.0, target_mult=5.0):
    """
    Trade breakouts with high volume confirmation
    """
    row = df.iloc[i]

    if pd.isna(row['vol_ratio']) or pd.isna(row['sma_20']):
        return None

    # Need high volume
    if row['vol_ratio'] < vol_threshold:
        return None

    # LONG: Bullish breakout
    if (row['close'] > row['sma_20'] and
        row['close'] > row['open'] and
        row['body_pct'] > 50):

        return {
            'direction': 'LONG',
            'entry_price': row['close'],
            'stop_loss': row['close'] - (stop_mult * row['atr']),
            'take_profit': row['close'] + (target_mult * row['atr'])
        }

    # SHORT: Bearish breakdown
    elif (row['close'] < row['sma_20'] and
          row['close'] < row['open'] and
          row['body_pct'] > 50):

        return {
            'direction': 'SHORT',
            'entry_price': row['close'],
            'stop_loss': row['close'] + (stop_mult * row['atr']),
            'take_profit': row['close'] - (target_mult * row['atr'])
        }

    return None


# =============================================================================
# STRATEGY 5: Time-Based Trading (Session Optimization)
# =============================================================================

def session_trading(df, i, strategy_func, allowed_hours, **kwargs):
    """
    Wrapper to only trade during specific hours
    US session: 13-21 UTC
    Asian session: 23-7 UTC
    European session: 7-15 UTC
    """
    row = df.iloc[i]

    if row['hour'] not in allowed_hours:
        return None

    return strategy_func(df, i, **kwargs)


# =============================================================================
# MAIN TESTING
# =============================================================================

def main():
    print("="*80)
    print("ETH STRATEGY DISCOVERY - Finding >4:1 Profit/DD Strategies")
    print("="*80)

    # Load data
    data_path = Path(__file__).parent / 'eth_usdt_1m_bingx.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Calculate indicators
    print("\nCalculating indicators...")
    df = calculate_indicators(df)
    df = df.dropna()

    print(f"Candles after indicator calculation: {len(df):,}")

    # Test strategies
    results = []

    print("\n" + "="*80)
    print("TESTING STRATEGIES")
    print("="*80)

    # 1. RSI Mean Reversion - Multiple Parameters
    print("\n1. RSI Mean Reversion...")
    for rsi_period in [7, 14, 21]:
        for oversold in [20, 25, 30]:
            for overbought in [70, 75, 80]:
                for stop_mult in [1.5, 2.0, 2.5]:
                    for target_mult in [3.0, 4.0, 5.0, 6.0]:
                        result = backtest_strategy(
                            df, rsi_mean_reversion,
                            f"RSI{rsi_period}_OS{oversold}_OB{overbought}_S{stop_mult}_T{target_mult}",
                            rsi_period=rsi_period,
                            oversold=oversold,
                            overbought=overbought,
                            stop_mult=stop_mult,
                            target_mult=target_mult
                        )
                        if result:
                            results.append(result)

    # 2. Bollinger Band Bounce
    print("2. Bollinger Band Bounce...")
    for stop_mult in [1.5, 2.0, 2.5]:
        for target_mult in [3.0, 4.0, 5.0, 6.0]:
            for bb_threshold in [0.05, 0.1, 0.15]:
                result = backtest_strategy(
                    df, bb_bounce,
                    f"BB_S{stop_mult}_T{target_mult}_Thresh{bb_threshold}",
                    stop_mult=stop_mult,
                    target_mult=target_mult,
                    bb_threshold=bb_threshold
                )
                if result:
                    results.append(result)

    # 3. EMA Pullback
    print("3. EMA Pullback...")
    for fast_ema in [9, 20]:
        for slow_ema in [50, 100]:
            for stop_mult in [1.5, 2.0, 2.5, 3.0]:
                for target_mult in [4.0, 5.0, 6.0, 8.0]:
                    result = backtest_strategy(
                        df, ema_pullback,
                        f"EMA_{fast_ema}_{slow_ema}_S{stop_mult}_T{target_mult}",
                        fast_ema=fast_ema,
                        slow_ema=slow_ema,
                        stop_mult=stop_mult,
                        target_mult=target_mult
                    )
                    if result:
                        results.append(result)

    # 4. Volume Breakout
    print("4. Volume Breakout...")
    for vol_threshold in [2.0, 2.5, 3.0]:
        for stop_mult in [1.5, 2.0, 2.5]:
            for target_mult in [4.0, 5.0, 6.0, 8.0]:
                result = backtest_strategy(
                    df, volume_breakout,
                    f"VolBreak_{vol_threshold}_S{stop_mult}_T{target_mult}",
                    vol_threshold=vol_threshold,
                    stop_mult=stop_mult,
                    target_mult=target_mult
                )
                if result:
                    results.append(result)

    print(f"\nTotal strategies tested: {len(results)}")

    # Filter for >4:1 profit/DD ratio
    winners = [r for r in results if r['profit_dd_ratio'] >= 4.0 and r['total_return'] > 0]

    if not winners:
        print("\n❌ No strategies met the 4:1 profit/DD criteria")
        print("\nBest strategies by profit/DD ratio:")
        best = sorted(results, key=lambda x: x['profit_dd_ratio'], reverse=True)[:10]
    else:
        print(f"\n✅ Found {len(winners)} strategies with >4:1 profit/DD ratio!")
        best = sorted(winners, key=lambda x: x['total_return'], reverse=True)[:20]

    # Display top strategies
    print("\n" + "="*80)
    print("TOP STRATEGIES")
    print("="*80)

    for i, result in enumerate(best, 1):
        print(f"\n#{i}: {result['name']}")
        print(f"    Total Return: {result['total_return']:+.2f}%")
        print(f"    Max DD: {result['max_dd']:.2f}%")
        print(f"    Profit/DD Ratio: {result['profit_dd_ratio']:.2f}:1")
        print(f"    Trades: {result['total_trades']}")
        print(f"    Win Rate: {result['win_rate']:.1f}%")
        print(f"    Avg Win: {result['avg_win']:.2f}% | Avg Loss: {result['avg_loss']:.2f}%")

        # Calculate with 10x leverage
        leverage = 10
        fee_pct = 0.005

        leveraged_win = result['avg_win'] * leverage
        leveraged_loss = result['avg_loss'] * leverage
        fee_per_trade = (fee_pct * 2) * leverage

        net_win = leveraged_win - fee_per_trade
        net_loss = leveraged_loss - fee_per_trade

        ev_per_trade = (result['win_rate']/100 * net_win) + ((1-result['win_rate']/100) * net_loss)
        total_expected = ev_per_trade * result['total_trades']

        print(f"    10x Leverage Expected: {total_expected:+.2f}%")
        print(f"    10x Leverage Max DD: {result['max_dd'] * 10:.2f}%")

    # Save detailed results
    if winners:
        print("\n" + "="*80)
        print("SAVING BEST STRATEGY DETAILS")
        print("="*80)

        best_strategy = best[0]
        trades_file = 'eth_best_strategy_trades.csv'
        best_strategy['trades_df'].to_csv(trades_file, index=False)
        print(f"\nBest strategy trades saved to: {trades_file}")
        print(f"Strategy: {best_strategy['name']}")


if __name__ == "__main__":
    main()
