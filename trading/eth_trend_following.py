"""
ETH/USDT 1-Minute Trend-Following Strategy Backtester
Goal: Achieve >4:1 profit-to-drawdown ratio with trend-following approaches
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading ETH/USDT 1-minute data...")
df = pd.read_csv('./trading/eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data loaded: {len(df)} candles")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
print(f"Avg volume: {df['volume'].mean():.2f}")
print()

# ============================================================================
# PART 1: DATA ANALYSIS - Understand ETH trending characteristics
# ============================================================================

print("=" * 80)
print("PART 1: ETH TREND ANALYSIS")
print("=" * 80)

# Calculate indicators for analysis
df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
df['ema100'] = df['close'].ewm(span=100, adjust=False).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['atr14'] = df['high'].rolling(14).max() - df['low'].rolling(14).min()

# Volume analysis
df['volume_ma20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma20']

# Trend strength
df['trend_strength_20_50'] = (df['ema20'] - df['ema50']).abs() / df['close'] * 100
df['trend_direction'] = np.where(df['ema20'] > df['ema50'], 1, -1)

# Hour of day analysis
df['hour'] = df['timestamp'].dt.hour

print("\n1. TRENDING vs RANGING PERIODS")
print("-" * 40)
strong_trend = df[df['trend_strength_20_50'] > 0.3]
weak_trend = df[df['trend_strength_20_50'] <= 0.3]
print(f"Strong trend periods (>0.3%): {len(strong_trend)/len(df)*100:.1f}%")
print(f"Ranging periods (<=0.3%): {len(weak_trend)/len(df)*100:.1f}%")

print("\n2. TREND DURATION ANALYSIS")
print("-" * 40)
# Calculate consecutive trend periods
df['trend_change'] = (df['trend_direction'] != df['trend_direction'].shift()).cumsum()
trend_durations = df.groupby('trend_change').size()
print(f"Average trend duration: {trend_durations.mean():.1f} minutes")
print(f"Median trend duration: {trend_durations.median():.1f} minutes")
print(f"Max trend duration: {trend_durations.max()} minutes")

print("\n3. VOLUME SPIKE CORRELATION")
print("-" * 40)
high_volume = df[df['volume_ratio'] > 2.0]
print(f"High volume candles (>2x avg): {len(high_volume)/len(df)*100:.1f}%")
# Check if high volume correlates with trend starts
df['is_trend_start'] = (df['trend_direction'] != df['trend_direction'].shift()).astype(int)
trend_starts = df[df['is_trend_start'] == 1]
trend_starts_high_vol = trend_starts[trend_starts['volume_ratio'] > 2.0]
print(f"Trend starts with high volume: {len(trend_starts_high_vol)/len(trend_starts)*100:.1f}%")

print("\n4. HOURLY TREND STRENGTH")
print("-" * 40)
hourly_trend = df.groupby('hour')['trend_strength_20_50'].mean().sort_values(ascending=False)
print("Top 5 hours with strongest trends:")
for hour, strength in hourly_trend.head(5).items():
    print(f"  Hour {hour:02d}:00 - Trend strength: {strength:.3f}%")

print("\n5. PRICE MOVEMENT STATISTICS")
print("-" * 40)
df['returns'] = df['close'].pct_change() * 100
print(f"Avg 1-min return: {df['returns'].mean():.4f}%")
print(f"Std dev 1-min return: {df['returns'].std():.4f}%")
print(f"Max 1-min gain: {df['returns'].max():.2f}%")
print(f"Max 1-min loss: {df['returns'].min():.2f}%")

# ============================================================================
# PART 2: STRATEGY BACKTESTING FRAMEWORK
# ============================================================================

print("\n")
print("=" * 80)
print("PART 2: TREND-FOLLOWING STRATEGY TESTING")
print("=" * 80)

def calculate_metrics(trades_df, strategy_name):
    """Calculate comprehensive metrics for a strategy"""
    if len(trades_df) == 0:
        return None

    # Basic stats
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    total_return = trades_df['pnl_pct'].sum()
    win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0

    # Calculate equity curve and drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl_pct'].cumsum()
    trades_df['peak'] = trades_df['cumulative_pnl'].cummax()
    trades_df['drawdown'] = trades_df['cumulative_pnl'] - trades_df['peak']
    max_drawdown = abs(trades_df['drawdown'].min()) if len(trades_df) > 0 else 0

    # Profit/DD ratio
    profit_dd_ratio = abs(total_return / max_drawdown) if max_drawdown > 0 else 0

    # R:R ratio
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    return {
        'strategy': strategy_name,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'profit_dd_ratio': profit_dd_ratio,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rr_ratio': rr_ratio,
        'wins': len(wins),
        'losses': len(losses),
        'trades_df': trades_df
    }

def backtest_strategy(df, strategy_func, strategy_name, params):
    """
    Row-by-row backtest framework
    strategy_func: function that returns 'long', 'short', or None
    """
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    entry_idx = 0
    stop_loss = 0
    take_profit = 0

    fee_pct = 0.005  # BingX taker fee

    for i in range(250, len(df)):  # Need 250 bars for indicators
        row = df.iloc[i]

        if not in_position:
            # Check for entry signal
            signal = strategy_func(df, i, params)

            if signal in ['long', 'short']:
                in_position = True
                position_type = signal
                entry_price = row['close']
                entry_idx = i

                # Calculate SL and TP based on ATR
                atr = row['atr14']
                sl_mult = params.get('sl_mult', 2.5)
                tp_mult = params.get('tp_mult', 8.0)

                if signal == 'long':
                    stop_loss = entry_price - (atr * sl_mult)
                    take_profit = entry_price + (atr * tp_mult)
                else:  # short
                    stop_loss = entry_price + (atr * sl_mult)
                    take_profit = entry_price - (atr * tp_mult)

        else:
            # Check exit conditions
            exit_reason = None
            exit_price = None

            if position_type == 'long':
                if row['low'] <= stop_loss:
                    exit_reason = 'stop_loss'
                    exit_price = stop_loss
                elif row['high'] >= take_profit:
                    exit_reason = 'take_profit'
                    exit_price = take_profit
            else:  # short
                if row['high'] >= stop_loss:
                    exit_reason = 'stop_loss'
                    exit_price = stop_loss
                elif row['low'] <= take_profit:
                    exit_reason = 'take_profit'
                    exit_price = take_profit

            if exit_reason:
                # Calculate PnL with fees
                if position_type == 'long':
                    pnl_pct = ((exit_price - entry_price) / entry_price * 100) - (fee_pct * 2)
                else:
                    pnl_pct = ((entry_price - exit_price) / entry_price * 100) - (fee_pct * 2)

                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'type': position_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'bars_held': i - entry_idx
                })

                in_position = False

    # Calculate metrics
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        return calculate_metrics(trades_df, strategy_name)
    else:
        return None

# ============================================================================
# STRATEGY 1: EMA PULLBACK
# ============================================================================

def ema_pullback_strategy(df, i, params):
    """
    Enter on pullback to fast EMA in trending market
    """
    row = df.iloc[i]
    prev = df.iloc[i-1]
    prev2 = df.iloc[i-2]

    fast_ema = params['fast_ema']
    slow_ema = params['slow_ema']
    pullback_depth = params.get('pullback_depth', 0.5)  # % of ATR

    fast = row[f'ema{fast_ema}']
    slow = row[f'ema{slow_ema}']
    fast_prev = prev[f'ema{fast_ema}']
    slow_prev = prev[f'ema{slow_ema}']

    # Trend identification
    uptrend = fast > slow and fast_prev > slow_prev
    downtrend = fast < slow and fast_prev < slow_prev

    # Pullback detection
    atr = row['atr14']

    # LONG: uptrend + price pulled back to fast EMA + crosses back up
    if uptrend:
        pullback = (prev['low'] <= fast_prev) and (prev['close'] < fast_prev)
        cross_up = row['close'] > fast
        if pullback and cross_up:
            return 'long'

    # SHORT: downtrend + price pulled back to fast EMA + crosses back down
    if downtrend:
        pullback = (prev['high'] >= fast_prev) and (prev['close'] > fast_prev)
        cross_down = row['close'] < fast
        if pullback and cross_down:
            return 'short'

    return None

# ============================================================================
# STRATEGY 2: VOLUME BREAKOUT
# ============================================================================

def volume_breakout_strategy(df, i, params):
    """
    Trade breakouts with high volume confirmation
    """
    row = df.iloc[i]
    prev = df.iloc[i-1]

    lookback = params.get('lookback', 20)
    volume_mult = params.get('volume_mult', 2.5)
    body_pct = params.get('body_pct', 0.5)

    # Get recent range
    recent = df.iloc[i-lookback:i]
    range_high = recent['high'].max()
    range_low = recent['low'].min()

    # Volume confirmation
    high_volume = row['volume_ratio'] > volume_mult

    # Strong body
    body = abs(row['close'] - row['open'])
    candle_range = row['high'] - row['low']
    strong_body = (body / candle_range) > body_pct if candle_range > 0 else False

    # LONG: breakout above range with volume
    if row['close'] > range_high and high_volume and strong_body and row['close'] > row['open']:
        return 'long'

    # SHORT: breakout below range with volume
    if row['close'] < range_low and high_volume and strong_body and row['close'] < row['open']:
        return 'short'

    return None

# ============================================================================
# STRATEGY 3: MULTI-TIMEFRAME TREND
# ============================================================================

# Create 5-minute data
df_5min = df.set_index('timestamp').resample('5min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

# Add indicators to 5-min data
df_5min['ema20'] = df_5min['close'].ewm(span=20, adjust=False).mean()
df_5min['ema50'] = df_5min['close'].ewm(span=50, adjust=False).mean()

def multi_timeframe_strategy(df, i, params):
    """
    Only trade when 1-min and 5-min trends align
    """
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # 1-min trend
    ema_fast_1m = row['ema20']
    ema_slow_1m = row['ema50']

    # Get CLOSED 5-min candle
    current_time = row['timestamp']
    closed_5min = df_5min[df_5min['timestamp'] < current_time]
    if len(closed_5min) == 0:
        return None

    last_5min = closed_5min.iloc[-1]
    ema20_5m = last_5min['ema20']
    ema50_5m = last_5min['ema50']

    # Both timeframes bullish
    both_bullish = (ema_fast_1m > ema_slow_1m) and (ema20_5m > ema50_5m)

    # Both timeframes bearish
    both_bearish = (ema_fast_1m < ema_slow_1m) and (ema20_5m < ema50_5m)

    # Entry on 1-min pullback in aligned trend
    if both_bullish:
        pullback = prev['low'] <= ema_fast_1m and prev['close'] < ema_fast_1m
        cross_up = row['close'] > ema_fast_1m
        if pullback and cross_up:
            return 'long'

    if both_bearish:
        pullback = prev['high'] >= ema_fast_1m and prev['close'] > ema_fast_1m
        cross_down = row['close'] < ema_fast_1m
        if pullback and cross_down:
            return 'short'

    return None

# ============================================================================
# STRATEGY 4: MOMENTUM CONTINUATION
# ============================================================================

def momentum_continuation_strategy(df, i, params):
    """
    Enter on strong momentum candles with high volume
    """
    row = df.iloc[i]
    prev = df.iloc[i-1]

    momentum_threshold = params.get('momentum_threshold', 0.15)  # % price move
    volume_mult = params.get('volume_mult', 2.0)
    body_ratio = params.get('body_ratio', 0.7)

    # Calculate momentum
    price_change_pct = abs(row['close'] - prev['close']) / prev['close'] * 100

    # High volume
    high_volume = row['volume_ratio'] > volume_mult

    # Strong body (bullish or bearish)
    body = abs(row['close'] - row['open'])
    candle_range = row['high'] - row['low']
    strong_body = (body / candle_range) > body_ratio if candle_range > 0 else False

    # LONG: strong bullish momentum
    bullish_candle = row['close'] > row['open']
    if price_change_pct > momentum_threshold and high_volume and strong_body and bullish_candle:
        return 'long'

    # SHORT: strong bearish momentum
    bearish_candle = row['close'] < row['open']
    if price_change_pct > momentum_threshold and high_volume and strong_body and bearish_candle:
        return 'short'

    return None

# ============================================================================
# RUN ALL STRATEGY VARIANTS
# ============================================================================

print("\nTesting strategy variants...")
all_results = []

# Strategy 1: EMA Pullback variations
print("\n1. Testing EMA Pullback strategies...")
ema_pairs = [(9, 50), (20, 50), (20, 100)]
sl_mults = [2.0, 2.5, 3.0, 3.5]
tp_mults = [6, 8, 10, 12]

for fast, slow in ema_pairs:
    for sl in sl_mults:
        for tp in tp_mults:
            params = {
                'fast_ema': fast,
                'slow_ema': slow,
                'sl_mult': sl,
                'tp_mult': tp
            }
            result = backtest_strategy(df, ema_pullback_strategy,
                                     f"EMA_Pullback_{fast}_{slow}_SL{sl}_TP{tp}", params)
            if result:
                all_results.append(result)

# Strategy 2: Volume Breakout variations
print("2. Testing Volume Breakout strategies...")
volume_mults = [2.0, 2.5, 3.0]
body_pcts = [0.5, 0.6, 0.7]

for vol_mult in volume_mults:
    for body_pct in body_pcts:
        for sl in [2.0, 2.5, 3.0]:
            for tp in [8, 10, 12]:
                params = {
                    'lookback': 20,
                    'volume_mult': vol_mult,
                    'body_pct': body_pct,
                    'sl_mult': sl,
                    'tp_mult': tp
                }
                result = backtest_strategy(df, volume_breakout_strategy,
                                         f"Vol_Breakout_V{vol_mult}_B{body_pct}_SL{sl}_TP{tp}", params)
                if result:
                    all_results.append(result)

# Strategy 3: Multi-Timeframe variations
print("3. Testing Multi-Timeframe strategies...")
for sl in [2.5, 3.0, 3.5]:
    for tp in [8, 10, 12]:
        params = {
            'sl_mult': sl,
            'tp_mult': tp
        }
        result = backtest_strategy(df, multi_timeframe_strategy,
                                 f"Multi_TF_SL{sl}_TP{tp}", params)
        if result:
            all_results.append(result)

# Strategy 4: Momentum Continuation variations
print("4. Testing Momentum Continuation strategies...")
momentum_thresholds = [0.10, 0.15, 0.20]
for threshold in momentum_thresholds:
    for vol_mult in [2.0, 2.5]:
        for sl in [2.0, 2.5, 3.0]:
            for tp in [8, 10, 12]:
                params = {
                    'momentum_threshold': threshold,
                    'volume_mult': vol_mult,
                    'body_ratio': 0.7,
                    'sl_mult': sl,
                    'tp_mult': tp
                }
                result = backtest_strategy(df, momentum_continuation_strategy,
                                         f"Momentum_{threshold}_V{vol_mult}_SL{sl}_TP{tp}", params)
                if result:
                    all_results.append(result)

# ============================================================================
# ANALYZE AND RANK RESULTS
# ============================================================================

print("\n")
print("=" * 80)
print("PART 3: RESULTS ANALYSIS")
print("=" * 80)

# Create results dataframe
results_df = pd.DataFrame([{
    'strategy': r['strategy'],
    'trades': r['trades'],
    'win_rate': r['win_rate'],
    'total_return': r['total_return'],
    'max_drawdown': r['max_drawdown'],
    'profit_dd_ratio': r['profit_dd_ratio'],
    'avg_win': r['avg_win'],
    'avg_loss': r['avg_loss'],
    'rr_ratio': r['rr_ratio']
} for r in all_results])

# Filter: minimum 8 trades and profit_dd_ratio >= 4.0
filtered = results_df[(results_df['trades'] >= 8) & (results_df['profit_dd_ratio'] >= 4.0)]

print(f"\nTotal strategies tested: {len(results_df)}")
print(f"Strategies meeting criteria (>=8 trades, profit/DD >= 4.0): {len(filtered)}")

if len(filtered) > 0:
    # Sort by profit/DD ratio
    top_strategies = filtered.sort_values('profit_dd_ratio', ascending=False).head(10)

    print("\n" + "=" * 80)
    print("TOP 10 STRATEGIES (sorted by Profit/DD Ratio)")
    print("=" * 80)
    print(top_strategies.to_string(index=False))

    # Get the BEST strategy
    best_idx = top_strategies.index[0]
    best_result = [r for r in all_results if r['strategy'] == top_strategies.iloc[0]['strategy']][0]

    print("\n" + "=" * 80)
    print(f"BEST STRATEGY: {best_result['strategy']}")
    print("=" * 80)

    print(f"\nPerformance Metrics:")
    print(f"  Total Trades: {best_result['trades']}")
    print(f"  Wins: {best_result['wins']} | Losses: {best_result['losses']}")
    print(f"  Win Rate: {best_result['win_rate']:.2f}%")
    print(f"  Total Return (1x): {best_result['total_return']:.2f}%")
    print(f"  Max Drawdown (1x): {best_result['max_drawdown']:.2f}%")
    print(f"  Profit/DD Ratio: {best_result['profit_dd_ratio']:.2f}")
    print(f"  Avg Win: {best_result['avg_win']:.2f}%")
    print(f"  Avg Loss: {best_result['avg_loss']:.2f}%")
    print(f"  R:R Ratio: {best_result['rr_ratio']:.2f}")

    # Leverage recommendations
    print(f"\nLeverage Scenarios:")
    for lev in [5, 10, 15, 20]:
        leveraged_return = best_result['total_return'] * lev
        leveraged_dd = best_result['max_drawdown'] * lev
        print(f"  {lev}x leverage: {leveraged_return:+.2f}% return | {leveraged_dd:.2f}% max DD")

    # Save detailed trades
    trades_df = best_result['trades_df']
    trades_df.to_csv('./trading/results/eth_trend_best_trades.csv', index=False)
    print(f"\nDetailed trades saved to: ./trading/results/eth_trend_best_trades.csv")

    # Save all results
    top_strategies.to_csv('./trading/results/eth_trend_top10.csv', index=False)
    print(f"Top 10 strategies saved to: ./trading/results/eth_trend_top10.csv")

else:
    print("\n⚠️ No strategies met the criteria (>=8 trades, profit/DD >= 4.0)")
    print("\nShowing top 10 by profit/DD ratio regardless of criteria:")
    top_any = results_df.sort_values('profit_dd_ratio', ascending=False).head(10)
    print(top_any.to_string(index=False))

print("\n" + "=" * 80)
print("BACKTEST COMPLETE")
print("=" * 80)
