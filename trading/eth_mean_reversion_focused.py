"""
ETH/USDT Mean Reversion Strategy Backtester - FOCUSED VERSION
Tests fewer but higher-quality strategy variations
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ==================== DATA ANALYSIS ====================

def analyze_market_characteristics(df):
    """Analyze ETH characteristics to inform strategy design"""
    print("=" * 80)
    print("ETH/USDT MARKET ANALYSIS")
    print("=" * 80)

    # Calculate basic statistics
    df['returns'] = df['close'].pct_change()
    df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100

    # ATR calculation
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Bollinger Bands (20 period, 2 std dev)
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100

    # RSI (14 period)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    print(f"\nDataset: {len(df):,} candles")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    print(f"\nVolatility Profile:")
    print(f"  ATR (14): ${df['atr'].mean():.2f} ± ${df['atr'].std():.2f}")
    print(f"  ATR %: {df['atr_pct'].mean():.3f}% (median: {df['atr_pct'].median():.3f}%)")

    print(f"\nBollinger Band Analysis:")
    print(f"  Avg BB width: {df['bb_width'].mean():.3f}%")
    print(f"  Tight BB (<1.5%): {(df['bb_width'] < 1.5).sum() / len(df) * 100:.1f}% of time")

    print(f"\nRSI Distribution:")
    print(f"  Mean RSI: {df['rsi'].mean():.1f}")
    print(f"  Oversold (<30): {(df['rsi'] < 30).sum() / len(df) * 100:.1f}% of time")
    print(f"  Overbought (>70): {(df['rsi'] > 70).sum() / len(df) * 100:.1f}% of time")

    return df

# ==================== BACKTEST ENGINE ====================

def backtest_mean_reversion(df, config):
    """
    Row-by-row mean reversion backtest

    config = {
        'strategy_type': 'rsi' | 'bb' | 'combined',
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'bb_threshold': 0.002,  # 0.2% from band
        'max_bb_width': 2.0,    # Only trade when BB width < this
        'sl_atr_mult': 2.0,
        'tp_atr_mult': 5.0,
        'leverage': 10,
        'min_spacing': 10       # Minimum bars between trades
    }
    """

    capital = 1000.0
    equity = capital
    peak_equity = capital
    max_drawdown = 0.0

    in_position = False
    position_type = None
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    entry_time = None
    last_trade_idx = -999

    trades = []

    leverage = config['leverage']
    fee_rate = 0.00005  # BingX 0.005%

    # Start after enough data for indicators
    for i in range(250, len(df)):
        row = df.iloc[i]

        # Update max drawdown
        if equity > peak_equity:
            peak_equity = equity
        current_dd = (peak_equity - equity) / peak_equity
        if current_dd > max_drawdown:
            max_drawdown = current_dd

        # Exit logic
        if in_position:
            exit_price = None
            exit_reason = None

            if position_type == 'long':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
            elif position_type == 'short':
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'

            if exit_price:
                # Calculate P&L
                if position_type == 'long':
                    price_change = (exit_price - entry_price) / entry_price
                else:
                    price_change = (entry_price - exit_price) / entry_price

                pnl_pct = price_change * leverage
                total_fee = 2 * fee_rate * leverage
                pnl_pct -= total_fee

                pnl_dollars = equity * pnl_pct
                equity += pnl_dollars

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'type': position_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'equity': equity
                })

                in_position = False
                last_trade_idx = i

        # Entry logic
        if not in_position and (i - last_trade_idx) >= config['min_spacing']:
            long_signal = False
            short_signal = False

            # Check strategy type
            if config['strategy_type'] == 'rsi':
                long_signal = row['rsi'] < config['rsi_oversold']
                short_signal = row['rsi'] > config['rsi_overbought']

            elif config['strategy_type'] == 'bb':
                # Only trade in tight BB (ranging market)
                if row['bb_width'] < config['max_bb_width']:
                    distance_from_lower = (row['close'] - row['bb_lower']) / row['close']
                    distance_from_upper = (row['bb_upper'] - row['close']) / row['close']

                    long_signal = distance_from_lower < config['bb_threshold']
                    short_signal = distance_from_upper < config['bb_threshold']

            elif config['strategy_type'] == 'combined':
                # Both RSI and BB must confirm
                rsi_long = row['rsi'] < config['rsi_oversold']
                rsi_short = row['rsi'] > config['rsi_overbought']

                distance_from_lower = (row['close'] - row['bb_lower']) / row['close']
                distance_from_upper = (row['bb_upper'] - row['close']) / row['close']

                bb_long = distance_from_lower < config['bb_threshold']
                bb_short = distance_from_upper < config['bb_threshold']

                ranging = row['bb_width'] < config['max_bb_width']

                long_signal = rsi_long and bb_long and ranging
                short_signal = rsi_short and bb_short and ranging

            # Enter long
            if long_signal:
                position_type = 'long'
                entry_price = row['close']

                sl_distance = row['atr'] * config['sl_atr_mult']
                tp_distance = row['atr'] * config['tp_atr_mult']

                stop_loss = entry_price - sl_distance
                take_profit = entry_price + tp_distance

                entry_time = row['timestamp']
                in_position = True

            # Enter short
            elif short_signal:
                position_type = 'short'
                entry_price = row['close']

                sl_distance = row['atr'] * config['sl_atr_mult']
                tp_distance = row['atr'] * config['tp_atr_mult']

                stop_loss = entry_price + sl_distance
                take_profit = entry_price - tp_distance

                entry_time = row['timestamp']
                in_position = True

    # Close final position
    if in_position:
        row = df.iloc[-1]
        exit_price = row['close']

        if position_type == 'long':
            price_change = (exit_price - entry_price) / entry_price
        else:
            price_change = (entry_price - exit_price) / entry_price

        pnl_pct = price_change * leverage - (2 * fee_rate * leverage)
        pnl_dollars = equity * pnl_pct
        equity += pnl_dollars

        trades.append({
            'entry_time': entry_time,
            'exit_time': row['timestamp'],
            'type': position_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_reason': 'EOD',
            'pnl_pct': pnl_pct * 100,
            'pnl_dollars': pnl_dollars,
            'equity': equity
        })

    return {
        'trades': trades,
        'final_equity': equity,
        'max_drawdown': max_drawdown
    }

# ==================== STRATEGY GRID SEARCH ====================

def run_strategy_tests(df):
    """Test focused set of strategy variations"""

    all_results = []

    # Test matrix (reduced from thousands to hundreds)
    test_configs = []

    # 1. RSI Strategies
    for oversold in [25, 30]:
        for overbought in [70, 75]:
            for sl in [1.5, 2.0, 2.5]:
                for tp in [3.0, 4.0, 5.0, 6.0]:
                    for lev in [5, 10, 15, 20]:
                        test_configs.append({
                            'strategy_type': 'rsi',
                            'rsi_oversold': oversold,
                            'rsi_overbought': overbought,
                            'bb_threshold': 0.002,  # Not used but needed
                            'max_bb_width': 2.0,
                            'sl_atr_mult': sl,
                            'tp_atr_mult': tp,
                            'leverage': lev,
                            'min_spacing': 10
                        })

    # 2. Bollinger Band Strategies
    for bb_thresh in [0.001, 0.002, 0.003]:
        for max_width in [1.5, 2.0]:
            for sl in [1.5, 2.0, 2.5]:
                for tp in [3.0, 4.0, 5.0, 6.0]:
                    for lev in [5, 10, 15, 20]:
                        test_configs.append({
                            'strategy_type': 'bb',
                            'rsi_oversold': 30,  # Not used
                            'rsi_overbought': 70,
                            'bb_threshold': bb_thresh,
                            'max_bb_width': max_width,
                            'sl_atr_mult': sl,
                            'tp_atr_mult': tp,
                            'leverage': lev,
                            'min_spacing': 10
                        })

    # 3. Combined Strategies (most selective)
    for oversold in [25, 30]:
        for overbought in [70, 75]:
            for bb_thresh in [0.002, 0.003]:
                for max_width in [1.5, 2.0]:
                    for sl in [2.0, 2.5]:
                        for tp in [4.0, 5.0, 6.0]:
                            for lev in [10, 15, 20]:
                                test_configs.append({
                                    'strategy_type': 'combined',
                                    'rsi_oversold': oversold,
                                    'rsi_overbought': overbought,
                                    'bb_threshold': bb_thresh,
                                    'max_bb_width': max_width,
                                    'sl_atr_mult': sl,
                                    'tp_atr_mult': tp,
                                    'leverage': lev,
                                    'min_spacing': 10
                                })

    print(f"\nTesting {len(test_configs)} strategy configurations...")
    print(f"  RSI strategies: {sum(1 for c in test_configs if c['strategy_type'] == 'rsi')}")
    print(f"  BB strategies: {sum(1 for c in test_configs if c['strategy_type'] == 'bb')}")
    print(f"  Combined strategies: {sum(1 for c in test_configs if c['strategy_type'] == 'combined')}")

    for idx, config in enumerate(test_configs):
        result = backtest_mean_reversion(df, config)

        if len(result['trades']) >= 10:  # At least 10 trades
            trades_df = pd.DataFrame(result['trades'])
            wins = trades_df[trades_df['pnl_dollars'] > 0]
            losses = trades_df[trades_df['pnl_dollars'] < 0]

            total_return_pct = (result['final_equity'] - 1000) / 1000 * 100
            max_dd_pct = result['max_drawdown'] * 100

            all_results.append({
                'strategy_type': config['strategy_type'],
                'rsi_oversold': config['rsi_oversold'],
                'rsi_overbought': config['rsi_overbought'],
                'bb_threshold': config['bb_threshold'],
                'max_bb_width': config['max_bb_width'],
                'sl_atr_mult': config['sl_atr_mult'],
                'tp_atr_mult': config['tp_atr_mult'],
                'leverage': config['leverage'],
                'num_trades': len(trades_df),
                'win_rate': len(wins) / len(trades_df) * 100,
                'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
                'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
                'total_return_pct': total_return_pct,
                'max_dd_pct': max_dd_pct,
                'profit_dd_ratio': abs(total_return_pct) / max(max_dd_pct, 0.01),
                'final_equity': result['final_equity'],
                'trades': trades_df
            })

        if (idx + 1) % 100 == 0:
            print(f"  Progress: {idx + 1}/{len(test_configs)} ({(idx+1)/len(test_configs)*100:.1f}%)")

    return pd.DataFrame(all_results)

# ==================== MAIN ====================

def main():
    print("\n" + "="*80)
    print("ETH/USDT MEAN REVERSION STRATEGY DISCOVERY (FOCUSED)")
    print("="*80 + "\n")

    # Load data
    print("Loading ETH/USDT 1m data...")
    df = pd.read_csv('eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Analyze market
    df = analyze_market_characteristics(df)

    # Run tests
    print("\n" + "="*80)
    print("BACKTESTING STRATEGIES")
    print("="*80)

    results_df = run_strategy_tests(df)

    # Filter and sort
    profitable = results_df[results_df['total_return_pct'] > 0].copy()
    profitable = profitable.sort_values('profit_dd_ratio', ascending=False)

    print(f"\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Total tests: {len(results_df)}")
    print(f"Profitable strategies: {len(profitable)}")
    print(f"Strategies with profit/DD >= 4.0: {len(profitable[profitable['profit_dd_ratio'] >= 4.0])}")

    # Save results
    profitable.to_csv('eth_mean_reversion_summary.csv', index=False)
    print(f"\nSaved summary to: eth_mean_reversion_summary.csv")

    # Display top 10
    if len(profitable) > 0:
        print("\n" + "="*80)
        print("TOP 10 STRATEGIES")
        print("="*80)

        display_cols = ['strategy_type', 'leverage', 'num_trades', 'win_rate',
                       'total_return_pct', 'max_dd_pct', 'profit_dd_ratio']

        top10 = profitable[display_cols].head(10).copy()
        top10['win_rate'] = top10['win_rate'].round(1)
        top10['total_return_pct'] = top10['total_return_pct'].round(2)
        top10['max_dd_pct'] = top10['max_dd_pct'].round(2)
        top10['profit_dd_ratio'] = top10['profit_dd_ratio'].round(2)

        print(f"\n{top10.to_string(index=False)}")

        # Best strategy details
        best = profitable.iloc[0]
        print("\n" + "="*80)
        print("BEST STRATEGY DETAILS")
        print("="*80)
        print(f"\nStrategy Type: {best['strategy_type'].upper()}")
        print(f"Leverage: {best['leverage']}x")
        print(f"\nParameters:")
        print(f"  RSI Oversold: {best['rsi_oversold']}")
        print(f"  RSI Overbought: {best['rsi_overbought']}")
        print(f"  BB Threshold: {best['bb_threshold']*100:.2f}%")
        print(f"  Max BB Width: {best['max_bb_width']:.1f}%")
        print(f"  Stop Loss: {best['sl_atr_mult']:.1f}x ATR")
        print(f"  Take Profit: {best['tp_atr_mult']:.1f}x ATR")

        print(f"\nPerformance:")
        print(f"  Total Return: {best['total_return_pct']:.2f}%")
        print(f"  Max Drawdown: {best['max_dd_pct']:.2f}%")
        print(f"  Profit/DD Ratio: {best['profit_dd_ratio']:.2f}")
        print(f"  Number of Trades: {best['num_trades']}")
        print(f"  Win Rate: {best['win_rate']:.2f}%")
        print(f"  Avg Win: {best['avg_win']:.2f}%")
        print(f"  Avg Loss: {best['avg_loss']:.2f}%")
        print(f"  Final Equity: ${best['final_equity']:.2f}")

        # Save best trades
        best_trades = best['trades']
        best_trades.to_csv('eth_mean_reversion_best_trades.csv', index=False)
        print(f"\nSaved best strategy trades to: eth_mean_reversion_best_trades.csv")

        # Exit breakdown
        print(f"\nExit Breakdown:")
        print(best_trades['exit_reason'].value_counts())

    return profitable, df

if __name__ == "__main__":
    results, data = main()
    print("\n" + "="*80)
    print("BACKTEST COMPLETE!")
    print("="*80)
