"""
DOGE/USDT Master Strategy Discovery
====================================
Comprehensive backtest system to find profitable DOGE strategies.

Note: BB3 strategies FAILED on DOGE (-3.18% to -7.85%)
Focus on: EMA crossovers, RSI, momentum, session-specific patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================

INITIAL_CAPITAL = 10000
MARKET_FEE = 0.001  # 0.1% for market orders (round-trip)
LIMIT_FEE = 0.00035  # 0.035% for limit orders (half of round-trip)
MIN_TRADES = 30

# ==================== UTILITY FUNCTIONS ====================

def calculate_indicators(df):
    """Calculate all technical indicators"""
    data = df.copy()

    # EMAs for trend following
    for period in [5, 10, 20, 50, 100, 200]:
        data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()

    # RSI for momentum
    for period in [7, 14, 21]:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        data[f'rsi_{period}'] = 100 - (100 / (1 + rs))

    # ATR for stop loss/take profit
    data['tr'] = np.maximum(
        data['high'] - data['low'],
        np.maximum(
            abs(data['high'] - data['close'].shift(1)),
            abs(data['low'] - data['close'].shift(1))
        )
    )
    data['atr'] = data['tr'].rolling(14).mean()
    data['atr_pct'] = data['atr'] / data['close'] * 100

    # MACD
    data['ema_12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['ema_26'] = data['close'].ewm(span=26, adjust=False).mean()
    data['macd'] = data['ema_12'] - data['ema_26']
    data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = data['macd'] - data['macd_signal']

    # Bollinger Bands (for volatility reference, not BB3)
    data['bb_mid'] = data['close'].rolling(20).mean()
    data['bb_std'] = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_mid'] + 2 * data['bb_std']
    data['bb_lower'] = data['bb_mid'] - 2 * data['bb_std']
    data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / data['bb_mid'] * 100

    # Volume analysis
    data['vol_ma_20'] = data['volume'].rolling(20).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma_20']

    # Session hours (UTC)
    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
    data['asian_session'] = ((data['hour'] >= 0) & (data['hour'] < 8)).astype(int)
    data['euro_session'] = ((data['hour'] >= 8) & (data['hour'] < 14)).astype(int)
    data['us_session'] = ((data['hour'] >= 14) & (data['hour'] < 22)).astype(int)

    return data

def backtest_strategy(df, strategy_func, strategy_name, params):
    """Backtest a single strategy"""

    # Calculate indicators if not already done
    if 'ema_20' not in df.columns:
        df = calculate_indicators(df)

    capital = INITIAL_CAPITAL
    position = None
    trades = []

    for i in range(200, len(df)):  # Start after warmup
        row = df.iloc[i]

        # Check if we have a position
        if position is not None:
            # Check exit conditions
            exit_result = None

            if position['type'] == 'LONG':
                if row['high'] >= position['tp']:
                    exit_result = {'type': 'TP', 'price': position['tp']}
                elif row['low'] <= position['sl']:
                    exit_result = {'type': 'SL', 'price': position['sl']}
            else:  # SHORT
                if row['low'] <= position['tp']:
                    exit_result = {'type': 'TP', 'price': position['tp']}
                elif row['high'] >= position['sl']:
                    exit_result = {'type': 'SL', 'price': position['sl']}

            if exit_result:
                # Calculate P&L
                if position['type'] == 'LONG':
                    pnl_pct = (exit_result['price'] - position['entry']) / position['entry'] * 100
                else:
                    pnl_pct = (position['entry'] - exit_result['price']) / position['entry'] * 100

                # Apply fees
                fee_pct = params.get('fee_pct', MARKET_FEE * 100)
                net_pnl_pct = pnl_pct - fee_pct

                capital = capital * (1 + net_pnl_pct / 100)

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'type': position['type'],
                    'entry': position['entry'],
                    'exit': exit_result['price'],
                    'sl': position['sl'],
                    'tp': position['tp'],
                    'exit_type': exit_result['type'],
                    'gross_pnl_pct': pnl_pct,
                    'fee_pct': fee_pct,
                    'net_pnl_pct': net_pnl_pct,
                    'capital': capital
                })

                position = None

        # Check for new entry signal (only if no position)
        if position is None:
            signal = strategy_func(df, i, params)

            if signal:
                position = {
                    'entry_time': row['timestamp'],
                    'type': signal['type'],
                    'entry': signal['entry'],
                    'sl': signal['sl'],
                    'tp': signal['tp']
                }

    # Calculate metrics
    if len(trades) < MIN_TRADES:
        return None

    trades_df = pd.DataFrame(trades)

    wins = trades_df[trades_df['net_pnl_pct'] > 0]
    losses = trades_df[trades_df['net_pnl_pct'] <= 0]

    win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
    avg_win = wins['net_pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses['net_pnl_pct'].mean()) if len(losses) > 0 else 0

    # Calculate drawdown
    trades_df['peak'] = trades_df['capital'].cummax()
    trades_df['drawdown'] = (trades_df['capital'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = abs(trades_df['drawdown'].min())

    total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    # R:R ratio
    rr_ratio = total_return / max_dd if max_dd > 0 else 0

    return {
        'strategy': strategy_name,
        'params': str(params),
        'total_trades': len(trades_df),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_drawdown': max_dd,
        'rr_ratio': rr_ratio,
        'final_capital': capital,
        'trades': trades_df
    }

# ==================== STRATEGY DEFINITIONS ====================

def ema_crossover_strategy(df, i, params):
    """EMA Crossover with trend confirmation"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    fast_ema = params['fast_period']
    slow_ema = params['slow_period']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']

    # Session filter
    if params.get('session') == 'asian' and row['asian_session'] == 0:
        return None
    if params.get('session') == 'euro' and row['euro_session'] == 0:
        return None
    if params.get('session') == 'us' and row['us_session'] == 0:
        return None

    # Volume filter
    if params.get('min_volume_ratio') and row['vol_ratio'] < params['min_volume_ratio']:
        return None

    # LONG: Fast crosses above slow
    if (prev[f'ema_{fast_ema}'] <= prev[f'ema_{slow_ema}'] and
        row[f'ema_{fast_ema}'] > row[f'ema_{slow_ema}']):

        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - (row['atr'] * sl_atr),
            'tp': row['close'] + (row['atr'] * tp_atr)
        }

    # SHORT: Fast crosses below slow
    if (prev[f'ema_{fast_ema}'] >= prev[f'ema_{slow_ema}'] and
        row[f'ema_{fast_ema}'] < row[f'ema_{slow_ema}']):

        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + (row['atr'] * sl_atr),
            'tp': row['close'] - (row['atr'] * tp_atr)
        }

    return None

def rsi_momentum_strategy(df, i, params):
    """RSI momentum strategy"""
    row = df.iloc[i]

    rsi_period = params['rsi_period']
    oversold = params['oversold']
    overbought = params['overbought']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']

    # Session filter
    if params.get('session') == 'asian' and row['asian_session'] == 0:
        return None
    if params.get('session') == 'euro' and row['euro_session'] == 0:
        return None
    if params.get('session') == 'us' and row['us_session'] == 0:
        return None

    # LONG: RSI oversold
    if row[f'rsi_{rsi_period}'] < oversold:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - (row['atr'] * sl_atr),
            'tp': row['close'] + (row['atr'] * tp_atr)
        }

    # SHORT: RSI overbought
    if row[f'rsi_{rsi_period}'] > overbought:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + (row['atr'] * sl_atr),
            'tp': row['close'] - (row['atr'] * tp_atr)
        }

    return None

def macd_strategy(df, i, params):
    """MACD crossover strategy"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']

    # Session filter
    if params.get('session') == 'asian' and row['asian_session'] == 0:
        return None
    if params.get('session') == 'euro' and row['euro_session'] == 0:
        return None
    if params.get('session') == 'us' and row['us_session'] == 0:
        return None

    # LONG: MACD crosses above signal
    if prev['macd'] <= prev['macd_signal'] and row['macd'] > row['macd_signal']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - (row['atr'] * sl_atr),
            'tp': row['close'] + (row['atr'] * tp_atr)
        }

    # SHORT: MACD crosses below signal
    if prev['macd'] >= prev['macd_signal'] and row['macd'] < row['macd_signal']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + (row['atr'] * sl_atr),
            'tp': row['close'] - (row['atr'] * tp_atr)
        }

    return None

def ema_pullback_strategy(df, i, params):
    """EMA pullback strategy - buy dips in uptrend"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    ema_period = params['ema_period']
    pullback_pct = params['pullback_pct']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']

    # Session filter
    if params.get('session') == 'asian' and row['asian_session'] == 0:
        return None
    if params.get('session') == 'euro' and row['euro_session'] == 0:
        return None
    if params.get('session') == 'us' and row['us_session'] == 0:
        return None

    ema = row[f'ema_{ema_period}']

    # LONG: Price pulls back to EMA in uptrend
    if row['close'] > row['ema_200']:  # Uptrend
        distance_from_ema = (row['close'] - ema) / ema * 100
        if abs(distance_from_ema) < pullback_pct and prev['close'] < prev[f'ema_{ema_period}']:
            return {
                'type': 'LONG',
                'entry': row['close'],
                'sl': row['close'] - (row['atr'] * sl_atr),
                'tp': row['close'] + (row['atr'] * tp_atr)
            }

    # SHORT: Price rallies to EMA in downtrend
    if row['close'] < row['ema_200']:  # Downtrend
        distance_from_ema = (ema - row['close']) / ema * 100
        if abs(distance_from_ema) < pullback_pct and prev['close'] > prev[f'ema_{ema_period}']:
            return {
                'type': 'SHORT',
                'entry': row['close'],
                'sl': row['close'] + (row['atr'] * sl_atr),
                'tp': row['close'] - (row['atr'] * tp_atr)
            }

    return None

def volume_breakout_strategy(df, i, params):
    """Volume breakout with EMA confirmation"""
    row = df.iloc[i]

    min_volume_ratio = params['min_volume_ratio']
    ema_period = params['ema_period']
    sl_atr = params['sl_atr']
    tp_atr = params['tp_atr']

    # Session filter
    if params.get('session') == 'asian' and row['asian_session'] == 0:
        return None
    if params.get('session') == 'euro' and row['euro_session'] == 0:
        return None
    if params.get('session') == 'us' and row['us_session'] == 0:
        return None

    # Volume surge
    if row['vol_ratio'] < min_volume_ratio:
        return None

    # LONG: Volume surge + close above EMA
    if row['close'] > row[f'ema_{ema_period}']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - (row['atr'] * sl_atr),
            'tp': row['close'] + (row['atr'] * tp_atr)
        }

    # SHORT: Volume surge + close below EMA
    if row['close'] < row[f'ema_{ema_period}']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + (row['atr'] * sl_atr),
            'tp': row['close'] - (row['atr'] * tp_atr)
        }

    return None

# ==================== MAIN EXECUTION ====================

def main():
    print("=" * 80)
    print("DOGE/USDT MASTER STRATEGY DISCOVERY")
    print("=" * 80)

    # Load data
    print("\nLoading DOGE/USDT data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/doge_usdt_1m_lbank.csv')
    print(f"Loaded {len(df):,} candles")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Calculate indicators
    print("\nCalculating indicators...")
    df = calculate_indicators(df)

    # Market analysis
    print("\n" + "=" * 80)
    print("MARKET ANALYSIS")
    print("=" * 80)
    print(f"Average ATR: {df['atr'].mean():.6f} ({df['atr_pct'].mean():.3f}%)")
    print(f"Average volume ratio: {df['vol_ratio'].mean():.2f}x")
    print(f"BB width: {df['bb_width'].mean():.3f}%")

    # Session distribution
    print("\nSession Distribution:")
    print(f"  Asian (0-8 UTC): {df['asian_session'].sum():,} candles")
    print(f"  Euro (8-14 UTC): {df['euro_session'].sum():,} candles")
    print(f"  US (14-22 UTC): {df['us_session'].sum():,} candles")

    # Define strategy configurations
    print("\n" + "=" * 80)
    print("RUNNING BACKTESTS")
    print("=" * 80)

    configs = []

    # 1. EMA Crossover strategies
    for fast in [5, 10, 20]:
        for slow in [20, 50, 100]:
            if fast >= slow:
                continue
            for sl_mult in [1.5, 2.0, 2.5]:
                for tp_mult in [3.0, 4.0, 5.0]:
                    # 24h
                    configs.append({
                        'func': ema_crossover_strategy,
                        'name': f'EMA_{fast}_{slow}_24h',
                        'params': {
                            'fast_period': fast,
                            'slow_period': slow,
                            'sl_atr': sl_mult,
                            'tp_atr': tp_mult,
                            'fee_pct': MARKET_FEE * 100
                        }
                    })
                    # Session-specific
                    for session in ['asian', 'euro', 'us']:
                        configs.append({
                            'func': ema_crossover_strategy,
                            'name': f'EMA_{fast}_{slow}_{session}',
                            'params': {
                                'fast_period': fast,
                                'slow_period': slow,
                                'sl_atr': sl_mult,
                                'tp_atr': tp_mult,
                                'session': session,
                                'fee_pct': MARKET_FEE * 100
                            }
                        })

    # 2. RSI strategies
    for rsi_period in [7, 14, 21]:
        for oversold in [20, 25, 30]:
            for overbought in [70, 75, 80]:
                for sl_mult in [1.5, 2.0, 2.5]:
                    for tp_mult in [3.0, 4.0, 5.0]:
                        configs.append({
                            'func': rsi_momentum_strategy,
                            'name': f'RSI_{rsi_period}_24h',
                            'params': {
                                'rsi_period': rsi_period,
                                'oversold': oversold,
                                'overbought': overbought,
                                'sl_atr': sl_mult,
                                'tp_atr': tp_mult,
                                'fee_pct': MARKET_FEE * 100
                            }
                        })

    # 3. MACD strategies
    for sl_mult in [1.5, 2.0, 2.5, 3.0]:
        for tp_mult in [3.0, 4.0, 5.0, 6.0]:
            configs.append({
                'func': macd_strategy,
                'name': 'MACD_24h',
                'params': {
                    'sl_atr': sl_mult,
                    'tp_atr': tp_mult,
                    'fee_pct': MARKET_FEE * 100
                }
            })
            # Session-specific
            for session in ['asian', 'euro', 'us']:
                configs.append({
                    'func': macd_strategy,
                    'name': f'MACD_{session}',
                    'params': {
                        'sl_atr': sl_mult,
                        'tp_atr': tp_mult,
                        'session': session,
                        'fee_pct': MARKET_FEE * 100
                    }
                })

    # 4. EMA Pullback strategies
    for ema_period in [20, 50]:
        for pullback_pct in [0.3, 0.5, 0.8]:
            for sl_mult in [1.5, 2.0, 2.5]:
                for tp_mult in [3.0, 4.0, 5.0]:
                    configs.append({
                        'func': ema_pullback_strategy,
                        'name': f'EMA_Pullback_{ema_period}_24h',
                        'params': {
                            'ema_period': ema_period,
                            'pullback_pct': pullback_pct,
                            'sl_atr': sl_mult,
                            'tp_atr': tp_mult,
                            'fee_pct': MARKET_FEE * 100
                        }
                    })

    # 5. Volume breakout strategies
    for min_vol in [1.5, 2.0, 2.5]:
        for ema_period in [20, 50]:
            for sl_mult in [1.5, 2.0, 2.5]:
                for tp_mult in [3.0, 4.0, 5.0]:
                    configs.append({
                        'func': volume_breakout_strategy,
                        'name': f'Volume_Breakout_{ema_period}_24h',
                        'params': {
                            'min_volume_ratio': min_vol,
                            'ema_period': ema_period,
                            'sl_atr': sl_mult,
                            'tp_atr': tp_mult,
                            'fee_pct': MARKET_FEE * 100
                        }
                    })

    print(f"\nTesting {len(configs)} strategy configurations...")

    # Run backtests
    results = []
    for idx, config in enumerate(configs):
        if (idx + 1) % 50 == 0:
            print(f"Progress: {idx + 1}/{len(configs)}")

        result = backtest_strategy(
            df,
            config['func'],
            config['name'],
            config['params']
        )

        if result:
            results.append(result)

    print(f"\nCompleted {len(results)} successful backtests")

    # Save results
    if results:
        results_df = pd.DataFrame([{
            'strategy': r['strategy'],
            'params': r['params'],
            'total_trades': r['total_trades'],
            'win_rate': r['win_rate'],
            'avg_win': r['avg_win'],
            'avg_loss': r['avg_loss'],
            'total_return': r['total_return'],
            'max_drawdown': r['max_drawdown'],
            'rr_ratio': r['rr_ratio'],
            'final_capital': r['final_capital']
        } for r in results])

        # Sort by R:R ratio
        results_df = results_df.sort_values('rr_ratio', ascending=False)

        output_path = '/workspaces/Carebiuro_windykacja/trading/results/doge_master_results.csv'
        results_df.to_csv(output_path, index=False)
        print(f"\nResults saved to: {output_path}")

        # Print top 10
        print("\n" + "=" * 80)
        print("TOP 10 STRATEGIES (by R:R ratio)")
        print("=" * 80)
        print(results_df.head(10).to_string(index=False))

        # Find best overall
        best = results_df.iloc[0]
        print("\n" + "=" * 80)
        print("BEST STRATEGY")
        print("=" * 80)
        print(f"Strategy: {best['strategy']}")
        print(f"Params: {best['params']}")
        print(f"Total trades: {best['total_trades']}")
        print(f"Win rate: {best['win_rate']:.1f}%")
        print(f"Avg win: {best['avg_win']:.2f}%")
        print(f"Avg loss: {best['avg_loss']:.2f}%")
        print(f"Total return: {best['total_return']:.2f}%")
        print(f"Max drawdown: {best['max_drawdown']:.2f}%")
        print(f"R:R ratio: {best['rr_ratio']:.2f}")
        print(f"Final capital: ${best['final_capital']:.2f}")

        # Check if meets criteria
        print("\n" + "=" * 80)
        print("CRITERIA CHECK")
        print("=" * 80)
        criteria_met = True

        if best['rr_ratio'] >= 2.0:
            print(f"✓ R:R ratio >= 2.0: {best['rr_ratio']:.2f}")
        else:
            print(f"✗ R:R ratio < 2.0: {best['rr_ratio']:.2f}")
            criteria_met = False

        if best['win_rate'] >= 50:
            print(f"✓ Win rate >= 50%: {best['win_rate']:.1f}%")
        else:
            print(f"✗ Win rate < 50%: {best['win_rate']:.1f}%")
            criteria_met = False

        if best['total_trades'] >= MIN_TRADES:
            print(f"✓ Trades >= {MIN_TRADES}: {best['total_trades']}")
        else:
            print(f"✗ Trades < {MIN_TRADES}: {best['total_trades']}")
            criteria_met = False

        if criteria_met:
            print("\n🎯 SUCCESS! Strategy meets all criteria.")
        else:
            print("\n⚠ Strategy does not meet all criteria. Keep searching.")

    else:
        print("\n⚠ No successful strategies found with minimum trade count.")

if __name__ == '__main__':
    main()
