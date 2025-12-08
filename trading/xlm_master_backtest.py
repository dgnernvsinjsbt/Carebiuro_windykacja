"""
XLM/USDT Strategy Discovery - Comprehensive Backtester
Goal: Find profitable strategy with R:R >= 2.0, Win Rate >= 50%, Min 30 trades

Approach: Probe First, Then Optimize
1. Test diverse strategies across different sessions
2. Identify what works
3. Optimize only promising approaches

Fee Structure:
- Market orders: 0.1% round-trip
- Limit orders: 0.07% round-trip (0.035% offset)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==================== DATA LOADING ====================

def load_data():
    """Load XLM/USDT 1m data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"Loaded {len(df):,} candles")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Price range: ${df['close'].min():.4f} - ${df['close'].max():.4f}")
    print()

    return df

# ==================== MARKET ANALYSIS ====================

def analyze_market(df):
    """Analyze XLM market characteristics"""
    print("=" * 80)
    print("XLM/USDT MARKET ANALYSIS")
    print("=" * 80)

    # Calculate returns
    df['returns'] = df['close'].pct_change()
    df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Volume analysis
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    print(f"\nVolatility:")
    print(f"  ATR (14): {df['atr'].mean():.6f} ({df['atr_pct'].mean():.3f}%)")
    print(f"  Range: {df['range_pct'].mean():.3f}% avg")

    print(f"\nVolume:")
    print(f"  Average: {df['volume'].mean():,.0f}")
    print(f"  High volume (>2x avg): {(df['volume_ratio'] > 2).sum() / len(df) * 100:.1f}%")

    # Session analysis
    df['hour'] = df['timestamp'].dt.hour
    print(f"\nSession Distribution:")
    print(f"  Asian (0-8 UTC): {len(df[df['hour'] < 8]) / len(df) * 100:.1f}%")
    print(f"  Euro (8-14 UTC): {len(df[(df['hour'] >= 8) & (df['hour'] < 14)]) / len(df) * 100:.1f}%")
    print(f"  US (14-22 UTC): {len(df[(df['hour'] >= 14) & (df['hour'] < 22)]) / len(df) * 100:.1f}%")
    print()

    return df

# ==================== INDICATOR CALCULATIONS ====================

def calculate_indicators(df):
    """Calculate all technical indicators"""

    # EMAs
    for period in [8, 20, 50, 100, 200]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    # SMAs
    for period in [10, 20, 50]:
        df[f'sma_{period}'] = df['close'].rolling(period).mean()

    # RSI
    for period in [7, 14, 21]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    for period in [20, 30]:
        for std_dev in [2.0, 2.5]:
            df[f'bb_mid_{period}'] = df['close'].rolling(period).mean()
            df[f'bb_std_{period}'] = df['close'].rolling(period).std()
            df[f'bb_upper_{period}_{std_dev}'] = df[f'bb_mid_{period}'] + std_dev * df[f'bb_std_{period}']
            df[f'bb_lower_{period}_{std_dev}'] = df[f'bb_mid_{period}'] - std_dev * df[f'bb_std_{period}']
            df[f'bb_width_{period}'] = (df[f'bb_upper_{period}_{std_dev}'] - df[f'bb_lower_{period}_{std_dev}']) / df[f'bb_mid_{period}'] * 100

    # MACD
    df['macd'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()

    # ADX (trend strength)
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr14 = df['tr'].rolling(14).sum()
    plus_di = 100 * plus_dm.rolling(14).sum() / tr14
    minus_di = 100 * minus_dm.rolling(14).sum() / tr14
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(14).mean()
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di

    # Sessions
    df['hour'] = df['timestamp'].dt.hour
    df['session'] = 'other'
    df.loc[df['hour'] < 8, 'session'] = 'asian'
    df.loc[(df['hour'] >= 8) & (df['hour'] < 14), 'session'] = 'euro'
    df.loc[(df['hour'] >= 14) & (df['hour'] < 22), 'session'] = 'us'

    return df

# ==================== BACKTEST ENGINE ====================

def backtest_strategy(df, strategy_func, config):
    """
    Universal backtest engine

    config must include:
    - sl_atr_mult: Stop loss ATR multiplier
    - tp_atr_mult: Take profit ATR multiplier
    - order_type: 'market' or 'limit'
    - session: 'all', 'asian', 'euro', 'us'
    - leverage: default 10
    """

    capital = 1000.0
    equity = capital
    peak_equity = capital
    max_drawdown = 0.0

    in_position = False
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    entry_idx = 0

    trades = []

    # Fee calculation
    leverage = config.get('leverage', 10)
    if config['order_type'] == 'market':
        fee_rate = 0.001  # 0.1% per side
    else:
        fee_rate = 0.00035  # 0.035% per side

    # Filter by session if specified
    if config.get('session', 'all') != 'all':
        df_trade = df[df['session'] == config['session']].copy()
    else:
        df_trade = df.copy()

    # Generate signals
    signals = strategy_func(df_trade, config)

    # Start after indicators are ready
    for i in range(250, len(df_trade)):
        row = df_trade.iloc[i]

        # Update equity tracking
        if equity > peak_equity:
            peak_equity = equity
        current_dd = (peak_equity - equity) / peak_equity
        if current_dd > max_drawdown:
            max_drawdown = current_dd

        # Exit logic
        if in_position:
            exit_price = None
            exit_reason = None

            # Check stop loss
            if row['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            # Check take profit
            elif row['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                # Calculate P&L
                price_change = (exit_price - entry_price) / entry_price
                pnl_pct = price_change * leverage
                total_fee = 2 * fee_rate * leverage
                pnl_pct -= total_fee

                pnl_dollars = equity * pnl_pct
                equity += pnl_dollars

                trades.append({
                    'entry_time': df_trade.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pnl_pct': pnl_pct,
                    'pnl_dollars': pnl_dollars,
                    'exit_reason': exit_reason,
                    'bars_held': i - entry_idx,
                    'equity': equity
                })

                in_position = False

        # Entry logic
        if not in_position and signals.iloc[i] == 1:
            # Determine entry price
            if config['order_type'] == 'market':
                entry_price = row['close']
            else:
                # Limit order slightly above close (0.035% offset)
                entry_price = row['close'] * 1.00035
                # Check if filled in next bar
                if i + 1 < len(df_trade):
                    next_bar = df_trade.iloc[i + 1]
                    if next_bar['low'] > entry_price:
                        continue  # Not filled, skip

            # Set stops using ATR
            atr = row['atr']
            stop_loss = entry_price - (config['sl_atr_mult'] * atr)
            take_profit = entry_price + (config['tp_atr_mult'] * atr)

            in_position = True
            entry_idx = i

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)

    total_trades = len(trades_df)
    winners = len(trades_df[trades_df['pnl_dollars'] > 0])
    losers = len(trades_df[trades_df['pnl_dollars'] < 0])
    win_rate = winners / total_trades if total_trades > 0 else 0

    total_pnl = trades_df['pnl_dollars'].sum()
    total_pnl_pct = (equity - capital) / capital * 100

    avg_win = trades_df[trades_df['pnl_dollars'] > 0]['pnl_dollars'].mean() if winners > 0 else 0
    avg_loss = abs(trades_df[trades_df['pnl_dollars'] < 0]['pnl_dollars'].mean()) if losers > 0 else 0
    profit_factor = (winners * avg_win) / (losers * avg_loss) if losers > 0 and avg_loss > 0 else 0

    # R:R ratio = Net P&L / Max Drawdown
    max_dd_dollars = max_drawdown * peak_equity
    rr_ratio = total_pnl / max_dd_dollars if max_dd_dollars > 0 else 0

    avg_bars_held = trades_df['bars_held'].mean()

    return {
        'total_trades': total_trades,
        'winners': winners,
        'losers': losers,
        'win_rate': win_rate * 100,
        'total_pnl_pct': total_pnl_pct,
        'max_dd_pct': max_drawdown * 100,
        'rr_ratio': rr_ratio,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_bars_held': avg_bars_held,
        'final_equity': equity,
        'trades': trades_df
    }

# ==================== STRATEGY DEFINITIONS ====================

def strategy_ema_pullback(df, config):
    """
    EMA Pullback Strategy:
    - Price pulls back to EMA during uptrend
    - Enter on bounce from EMA
    """
    signals = pd.Series(0, index=df.index)

    ema_period = config.get('ema_period', 20)
    rsi_period = config.get('rsi_period', 14)
    rsi_threshold = config.get('rsi_threshold', 40)

    ema = df[f'ema_{ema_period}']
    rsi = df[f'rsi_{rsi_period}']

    # Uptrend: price above EMA
    uptrend = df['close'] > ema

    # Pullback: price touched or went below EMA in last 3 bars
    pullback = (df['low'].rolling(3).min() <= ema) & (df['close'] > ema)

    # Not oversold
    not_oversold = rsi > rsi_threshold

    # Entry: bounce confirmed
    entry = uptrend & pullback & not_oversold

    signals[entry] = 1
    return signals

def strategy_bb_mean_reversion(df, config):
    """
    Bollinger Band Mean Reversion:
    - Buy when price touches lower BB
    - Sell target at middle BB
    """
    signals = pd.Series(0, index=df.index)

    bb_period = config.get('bb_period', 20)
    bb_std = config.get('bb_std', 2.0)
    rsi_period = config.get('rsi_period', 14)

    bb_lower = df[f'bb_lower_{bb_period}_{bb_std}']
    bb_mid = df[f'bb_mid_{bb_period}']
    rsi = df[f'rsi_{rsi_period}']

    # Price touches lower BB
    touches_lower = df['low'] <= bb_lower

    # Not extremely oversold (filter out crashes)
    not_crash = rsi > 20

    # Close back above lower BB (bounce confirmation)
    bounce = df['close'] > bb_lower

    entry = touches_lower & not_crash & bounce

    signals[entry] = 1
    return signals

def strategy_momentum_breakout(df, config):
    """
    Momentum Breakout Strategy:
    - Price breaks above recent high with volume
    - RSI confirms momentum
    """
    signals = pd.Series(0, index=df.index)

    lookback = config.get('lookback', 20)
    rsi_threshold = config.get('rsi_threshold', 55)
    volume_mult = config.get('volume_mult', 1.5)

    # Recent high
    recent_high = df['high'].rolling(lookback).max().shift(1)

    # Breakout
    breakout = df['close'] > recent_high

    # RSI confirms
    rsi_ok = df[f'rsi_14'] > rsi_threshold

    # Volume confirmation
    volume_ok = df['volume'] > df['volume_ma'] * volume_mult

    entry = breakout & rsi_ok & volume_ok

    signals[entry] = 1
    return signals

def strategy_rsi_divergence(df, config):
    """
    RSI Oversold Bounce:
    - RSI below threshold
    - Price starting to turn up
    """
    signals = pd.Series(0, index=df.index)

    rsi_period = config.get('rsi_period', 14)
    rsi_oversold = config.get('rsi_oversold', 30)

    rsi = df[f'rsi_{rsi_period}']

    # RSI oversold
    oversold = rsi < rsi_oversold

    # RSI turning up
    rsi_rising = rsi > rsi.shift(1)

    # Price action confirms
    green_candle = df['close'] > df['open']

    entry = oversold & rsi_rising & green_candle

    signals[entry] = 1
    return signals

def strategy_macd_crossover(df, config):
    """
    MACD Crossover:
    - MACD crosses above signal
    - Histogram confirms
    """
    signals = pd.Series(0, index=df.index)

    # MACD crossover
    macd_cross = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))

    # Histogram positive and growing
    hist_growing = df['macd_hist'] > df['macd_hist'].shift(1)

    # Price above EMA20 (trend filter)
    trend_ok = df['close'] > df['ema_20']

    entry = macd_cross & hist_growing & trend_ok

    signals[entry] = 1
    return signals

def strategy_stochastic_oversold(df, config):
    """
    Stochastic Oversold Bounce:
    - Stochastic crosses above 20
    """
    signals = pd.Series(0, index=df.index)

    oversold_level = config.get('oversold_level', 20)

    # Stochastic oversold and turning up
    stoch_oversold = df['stoch_k'].shift(1) < oversold_level
    stoch_cross = df['stoch_k'] > df['stoch_d']

    # Trend filter
    uptrend = df['close'] > df['ema_50']

    entry = stoch_oversold & stoch_cross & uptrend

    signals[entry] = 1
    return signals

def strategy_trend_following(df, config):
    """
    Strong Trend Following:
    - ADX shows strong trend
    - Price pullback to EMA8
    """
    signals = pd.Series(0, index=df.index)

    adx_threshold = config.get('adx_threshold', 25)

    # Strong trend
    strong_trend = df['adx'] > adx_threshold

    # Uptrend (price above EMA20)
    uptrend = df['close'] > df['ema_20']

    # Pullback to EMA8
    pullback = (df['low'] <= df['ema_8']) & (df['close'] > df['ema_8'])

    entry = strong_trend & uptrend & pullback

    signals[entry] = 1
    return signals

def strategy_volume_spike(df, config):
    """
    Volume Spike Strategy:
    - Unusual volume spike
    - Price moving up
    """
    signals = pd.Series(0, index=df.index)

    volume_mult = config.get('volume_mult', 3.0)

    # Volume spike
    volume_spike = df['volume'] > df['volume_ma'] * volume_mult

    # Price moving up
    bullish = df['close'] > df['open']
    close_near_high = (df['close'] - df['low']) / (df['high'] - df['low']) > 0.7

    # Not already extended
    not_extended = df['rsi_14'] < 70

    entry = volume_spike & bullish & close_near_high & not_extended

    signals[entry] = 1
    return signals

# ==================== MAIN TESTING LOOP ====================

def run_comprehensive_test():
    """Test all strategies with various configurations"""

    # Load and prepare data
    df = load_data()
    df = analyze_market(df)
    df = calculate_indicators(df)

    print("=" * 80)
    print("RUNNING COMPREHENSIVE STRATEGY TESTS")
    print("=" * 80)
    print()

    results = []

    strategies = [
        ('EMA_Pullback', strategy_ema_pullback, [
            {'ema_period': 20, 'rsi_threshold': 40},
            {'ema_period': 20, 'rsi_threshold': 35},
            {'ema_period': 50, 'rsi_threshold': 40},
        ]),
        ('BB_MeanReversion', strategy_bb_mean_reversion, [
            {'bb_period': 20, 'bb_std': 2.0},
            {'bb_period': 20, 'bb_std': 2.5},
            {'bb_period': 30, 'bb_std': 2.0},
        ]),
        ('Momentum_Breakout', strategy_momentum_breakout, [
            {'lookback': 20, 'rsi_threshold': 55, 'volume_mult': 1.5},
            {'lookback': 30, 'rsi_threshold': 50, 'volume_mult': 2.0},
            {'lookback': 15, 'rsi_threshold': 60, 'volume_mult': 1.5},
        ]),
        ('RSI_Oversold', strategy_rsi_divergence, [
            {'rsi_period': 14, 'rsi_oversold': 30},
            {'rsi_period': 14, 'rsi_oversold': 25},
            {'rsi_period': 7, 'rsi_oversold': 30},
        ]),
        ('MACD_Crossover', strategy_macd_crossover, [
            {},
        ]),
        ('Stochastic_Oversold', strategy_stochastic_oversold, [
            {'oversold_level': 20},
            {'oversold_level': 25},
        ]),
        ('Trend_Following', strategy_trend_following, [
            {'adx_threshold': 25},
            {'adx_threshold': 30},
        ]),
        ('Volume_Spike', strategy_volume_spike, [
            {'volume_mult': 3.0},
            {'volume_mult': 4.0},
        ]),
    ]

    # Test parameters
    sl_tp_configs = [
        {'sl': 1.5, 'tp': 3.0},
        {'sl': 2.0, 'tp': 4.0},
        {'sl': 2.0, 'tp': 5.0},
        {'sl': 2.5, 'tp': 5.0},
        {'sl': 3.0, 'tp': 6.0},
    ]

    sessions = ['all', 'asian', 'euro', 'us']
    order_types = ['market', 'limit']

    test_count = 0
    total_tests = sum(len(configs) for _, _, configs in strategies) * len(sl_tp_configs) * len(sessions) * len(order_types)

    for strategy_name, strategy_func, param_sets in strategies:
        for params in param_sets:
            for sl_tp in sl_tp_configs:
                for session in sessions:
                    for order_type in order_types:
                        test_count += 1

                        # Build config
                        config = {
                            **params,
                            'sl_atr_mult': sl_tp['sl'],
                            'tp_atr_mult': sl_tp['tp'],
                            'session': session,
                            'order_type': order_type,
                            'leverage': 10
                        }

                        # Run backtest
                        result = backtest_strategy(df, strategy_func, config)

                        if result and result['total_trades'] >= 30:
                            results.append({
                                'strategy': strategy_name,
                                'params': str(params),
                                'sl_atr': sl_tp['sl'],
                                'tp_atr': sl_tp['tp'],
                                'session': session,
                                'order_type': order_type,
                                'total_trades': result['total_trades'],
                                'win_rate': result['win_rate'],
                                'total_pnl_pct': result['total_pnl_pct'],
                                'max_dd_pct': result['max_dd_pct'],
                                'rr_ratio': result['rr_ratio'],
                                'profit_factor': result['profit_factor'],
                                'avg_win': result['avg_win'],
                                'avg_loss': result['avg_loss'],
                                'avg_bars': result['avg_bars_held'],
                                'final_equity': result['final_equity']
                            })

                        # Progress update
                        if test_count % 100 == 0:
                            print(f"Progress: {test_count}/{total_tests} tests completed...")

    # Convert to DataFrame and sort
    results_df = pd.DataFrame(results)

    if len(results_df) == 0:
        print("No strategies met the minimum criteria (30+ trades)")
        return

    # Sort by R:R ratio
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save all results
    results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_master_results.csv', index=False)
    print(f"\nSaved {len(results_df)} results to results/xlm_master_results.csv")

    # Filter winning strategies
    winners = results_df[
        (results_df['rr_ratio'] >= 2.0) &
        (results_df['win_rate'] >= 50.0)
    ]

    print("\n" + "=" * 80)
    print("TOP 20 STRATEGIES BY R:R RATIO")
    print("=" * 80)
    print(results_df.head(20)[['strategy', 'session', 'order_type', 'sl_atr', 'tp_atr',
                                 'total_trades', 'win_rate', 'total_pnl_pct', 'rr_ratio']].to_string(index=False))

    if len(winners) > 0:
        print("\n" + "=" * 80)
        print(f"WINNING STRATEGIES (R:R >= 2.0, Win Rate >= 50%): {len(winners)}")
        print("=" * 80)
        print(winners.head(10)[['strategy', 'session', 'order_type', 'sl_atr', 'tp_atr',
                                 'total_trades', 'win_rate', 'total_pnl_pct', 'rr_ratio']].to_string(index=False))

        # Save winning strategies
        winners.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_winning_strategies.csv', index=False)
        print(f"\nSaved {len(winners)} winning strategies to results/xlm_winning_strategies.csv")
    else:
        print("\n" + "=" * 80)
        print("NO STRATEGIES MET WINNING CRITERIA (R:R >= 2.0, Win Rate >= 50%)")
        print("=" * 80)
        print("\nBest performers by different metrics:")
        print("\nBest by Win Rate:")
        print(results_df.nlargest(5, 'win_rate')[['strategy', 'session', 'win_rate', 'rr_ratio', 'total_pnl_pct']].to_string(index=False))
        print("\nBest by Total P&L:")
        print(results_df.nlargest(5, 'total_pnl_pct')[['strategy', 'session', 'win_rate', 'rr_ratio', 'total_pnl_pct']].to_string(index=False))
        print("\nBest by Profit Factor:")
        print(results_df.nlargest(5, 'profit_factor')[['strategy', 'session', 'win_rate', 'rr_ratio', 'profit_factor']].to_string(index=False))

if __name__ == '__main__':
    run_comprehensive_test()
