"""
ETH/USDT Mean Reversion Strategy Backtester
Discovers profitable mean reversion strategies using RSI, Bollinger Bands, and combined approaches
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

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100

    # RSI
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
    print(f"  Avg candle range: {df['range_pct'].mean():.3f}%")

    print(f"\nBollinger Band Analysis:")
    print(f"  Avg BB width: {df['bb_width'].mean():.3f}%")
    print(f"  Tight BB (<1%): {(df['bb_width'] < 1.0).sum() / len(df) * 100:.1f}% of time")
    print(f"  Wide BB (>2%): {(df['bb_width'] > 2.0).sum() / len(df) * 100:.1f}% of time")

    # Touches to bands
    touches_lower = (df['low'] <= df['bb_lower']).sum()
    touches_upper = (df['high'] >= df['bb_upper']).sum()
    print(f"  Lower band touches: {touches_lower} ({touches_lower/len(df)*100:.1f}%)")
    print(f"  Upper band touches: {touches_upper} ({touches_upper/len(df)*100:.1f}%)")

    print(f"\nRSI Distribution:")
    print(f"  Mean RSI: {df['rsi'].mean():.1f}")
    print(f"  Oversold (<30): {(df['rsi'] < 30).sum() / len(df) * 100:.1f}% of time")
    print(f"  Overbought (>70): {(df['rsi'] > 70).sum() / len(df) * 100:.1f}% of time")

    # Trend vs Range detection
    df['ema_fast'] = df['close'].ewm(span=20).mean()
    df['ema_slow'] = df['close'].ewm(span=50).mean()
    trending = abs(df['ema_fast'] - df['ema_slow']) / df['close'] > 0.005
    print(f"\nMarket Regime:")
    print(f"  Trending periods: {trending.sum() / len(df) * 100:.1f}%")
    print(f"  Ranging periods: {(~trending).sum() / len(df) * 100:.1f}%")

    return df

# ==================== STRATEGY DEFINITIONS ====================

class MeanReversionStrategy:
    """Base class for mean reversion strategies"""

    def __init__(self, name, params):
        self.name = name
        self.params = params
        self.results = []

    def check_long_entry(self, row, prev_rows):
        """Override in subclass"""
        return False

    def check_short_entry(self, row, prev_rows):
        """Override in subclass"""
        return False

class RSIStrategy(MeanReversionStrategy):
    """RSI Mean Reversion Strategy"""

    def check_long_entry(self, row, prev_rows):
        return row['rsi'] < self.params['oversold']

    def check_short_entry(self, row, prev_rows):
        return row['rsi'] > self.params['overbought']

class BollingerBounceStrategy(MeanReversionStrategy):
    """Bollinger Band Bounce Strategy"""

    def check_long_entry(self, row, prev_rows):
        # Only trade in tight BB (ranging market)
        if row['bb_width'] > self.params['max_bb_width']:
            return False

        # Price touches or breaks lower band
        distance_from_lower = (row['close'] - row['bb_lower']) / row['close']
        return distance_from_lower < self.params['bb_threshold']

    def check_short_entry(self, row, prev_rows):
        if row['bb_width'] > self.params['max_bb_width']:
            return False

        distance_from_upper = (row['bb_upper'] - row['close']) / row['close']
        return distance_from_upper < self.params['bb_threshold']

class CombinedStrategy(MeanReversionStrategy):
    """Combined RSI + Bollinger Band Strategy"""

    def check_long_entry(self, row, prev_rows):
        # Both indicators must confirm
        rsi_signal = row['rsi'] < self.params['oversold']

        distance_from_lower = (row['close'] - row['bb_lower']) / row['close']
        bb_signal = distance_from_lower < self.params['bb_threshold']

        # Only in ranging market
        ranging = row['bb_width'] < self.params['max_bb_width']

        return rsi_signal and bb_signal and ranging

    def check_short_entry(self, row, prev_rows):
        rsi_signal = row['rsi'] > self.params['overbought']

        distance_from_upper = (row['bb_upper'] - row['close']) / row['close']
        bb_signal = distance_from_upper < self.params['bb_threshold']

        ranging = row['bb_width'] < self.params['max_bb_width']

        return rsi_signal and bb_signal and ranging

# ==================== BACKTESTING ENGINE ====================

def backtest_strategy(df, strategy, leverage=10, fee_rate=0.00005, min_spacing=10):
    """
    Row-by-row backtest to avoid look-ahead bias

    Args:
        df: DataFrame with indicators already calculated
        strategy: Strategy instance
        leverage: Trading leverage
        fee_rate: BingX taker fee (0.005% = 0.00005)
        min_spacing: Minimum candles between trades
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
    equity_curve = []

    # Start after enough data for indicators
    for i in range(250, len(df)):
        row = df.iloc[i]
        prev_rows = df.iloc[max(0, i-50):i]

        # Update equity curve
        equity_curve.append({
            'timestamp': row['timestamp'],
            'equity': equity,
            'in_position': in_position
        })

        # Update max drawdown
        if equity > peak_equity:
            peak_equity = equity
        current_dd = (peak_equity - equity) / peak_equity
        if current_dd > max_drawdown:
            max_drawdown = current_dd

        # Exit logic (check first)
        if in_position:
            exit_price = None
            exit_reason = None

            if position_type == 'long':
                # Stop loss hit
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                # Take profit hit
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'

            elif position_type == 'short':
                # Stop loss hit
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                # Take profit hit
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'

            if exit_price:
                # Calculate P&L
                if position_type == 'long':
                    price_change = (exit_price - entry_price) / entry_price
                else:
                    price_change = (entry_price - exit_price) / entry_price

                # Apply leverage
                pnl_pct = price_change * leverage

                # Apply fees (entry + exit)
                total_fee = 2 * fee_rate * leverage
                pnl_pct -= total_fee

                # Update equity
                pnl_dollars = equity * pnl_pct
                equity += pnl_dollars

                # Record trade
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
        if not in_position and (i - last_trade_idx) >= min_spacing:
            # Check for long signal
            if strategy.check_long_entry(row, prev_rows):
                position_type = 'long'
                entry_price = row['close']

                # Set stops based on ATR
                sl_distance = row['atr'] * strategy.params['sl_atr_mult']
                tp_distance = row['atr'] * strategy.params['tp_atr_mult']

                stop_loss = entry_price - sl_distance
                take_profit = entry_price + tp_distance

                entry_time = row['timestamp']
                in_position = True

            # Check for short signal
            elif strategy.check_short_entry(row, prev_rows):
                position_type = 'short'
                entry_price = row['close']

                sl_distance = row['atr'] * strategy.params['sl_atr_mult']
                tp_distance = row['atr'] * strategy.params['tp_atr_mult']

                stop_loss = entry_price + sl_distance
                take_profit = entry_price - tp_distance

                entry_time = row['timestamp']
                in_position = True

    # Close any remaining position at market close
    if in_position:
        row = df.iloc[-1]
        exit_price = row['close']

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
            'exit_reason': 'EOD',
            'pnl_pct': pnl_pct * 100,
            'pnl_dollars': pnl_dollars,
            'equity': equity
        })

    return {
        'trades': trades,
        'equity_curve': equity_curve,
        'final_equity': equity,
        'max_drawdown': max_drawdown
    }

# ==================== STRATEGY GENERATION ====================

def generate_strategies():
    """Generate all strategy variations to test"""
    strategies = []

    # 1. RSI Strategies
    for rsi_period in [7, 14, 21]:
        for oversold in [20, 25, 30]:
            for overbought in [70, 75, 80]:
                for sl_mult in [1.5, 2.0, 2.5]:
                    for tp_mult in [3.0, 4.0, 5.0, 6.0]:
                        strategies.append(RSIStrategy(
                            name=f"RSI_{rsi_period}_OS{oversold}_OB{overbought}_SL{sl_mult}_TP{tp_mult}",
                            params={
                                'rsi_period': rsi_period,
                                'oversold': oversold,
                                'overbought': overbought,
                                'sl_atr_mult': sl_mult,
                                'tp_atr_mult': tp_mult
                            }
                        ))

    # 2. Bollinger Band Strategies
    for bb_threshold in [0.001, 0.002, 0.003]:  # 0.1%, 0.2%, 0.3%
        for max_width in [1.5, 2.0, 2.5]:
            for sl_mult in [1.5, 2.0, 2.5]:
                for tp_mult in [3.0, 4.0, 5.0, 6.0]:
                    strategies.append(BollingerBounceStrategy(
                        name=f"BB_thresh{bb_threshold*100:.1f}_width{max_width}_SL{sl_mult}_TP{tp_mult}",
                        params={
                            'bb_threshold': bb_threshold,
                            'max_bb_width': max_width,
                            'sl_atr_mult': sl_mult,
                            'tp_atr_mult': tp_mult
                        }
                    ))

    # 3. Combined Strategies (more selective)
    for oversold in [25, 30]:
        for overbought in [70, 75]:
            for bb_threshold in [0.002, 0.003]:
                for max_width in [1.5, 2.0]:
                    for sl_mult in [2.0, 2.5]:
                        for tp_mult in [4.0, 5.0, 6.0]:
                            strategies.append(CombinedStrategy(
                                name=f"COMBO_OS{oversold}_OB{overbought}_BB{bb_threshold*100:.1f}_W{max_width}_SL{sl_mult}_TP{tp_mult}",
                                params={
                                    'oversold': oversold,
                                    'overbought': overbought,
                                    'bb_threshold': bb_threshold,
                                    'max_bb_width': max_width,
                                    'sl_atr_mult': sl_mult,
                                    'tp_atr_mult': tp_mult
                                }
                            ))

    print(f"\nGenerated {len(strategies)} strategy variations to test")
    return strategies

# ==================== RESULTS ANALYSIS ====================

def analyze_results(results_df):
    """Analyze and rank strategies"""

    # Calculate metrics
    results_df['total_return_pct'] = (results_df['final_equity'] - 1000) / 1000 * 100
    results_df['max_dd_pct'] = results_df['max_drawdown'] * 100

    # Profit/DD ratio (absolute values)
    results_df['profit_dd_ratio'] = results_df['total_return_pct'].abs() / results_df['max_dd_pct'].clip(lower=0.01)

    # Filter: at least 10 trades and positive returns
    qualified = results_df[
        (results_df['num_trades'] >= 10) &
        (results_df['total_return_pct'] > 0)
    ].copy()

    # Sort by profit/DD ratio
    qualified = qualified.sort_values('profit_dd_ratio', ascending=False)

    return qualified

# ==================== MAIN EXECUTION ====================

def main():
    print("\n" + "="*80)
    print("ETH/USDT MEAN REVERSION STRATEGY DISCOVERY")
    print("="*80 + "\n")

    # Load data
    print("Loading ETH/USDT 1m data...")
    df = pd.read_csv('eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Analyze market
    df = analyze_market_characteristics(df)

    # Generate strategies
    print("\n" + "="*80)
    print("GENERATING STRATEGY VARIATIONS")
    print("="*80)
    strategies = generate_strategies()

    # Test strategies with different leverages
    leverages = [5, 10, 15, 20]

    all_results = []

    print("\n" + "="*80)
    print("BACKTESTING STRATEGIES")
    print("="*80)

    total_tests = len(strategies) * len(leverages)
    completed = 0

    for strategy in strategies:
        for leverage in leverages:
            result = backtest_strategy(df, strategy, leverage=leverage)

            if len(result['trades']) > 0:
                trades_df = pd.DataFrame(result['trades'])

                wins = trades_df[trades_df['pnl_dollars'] > 0]
                losses = trades_df[trades_df['pnl_dollars'] < 0]

                all_results.append({
                    'strategy': strategy.name,
                    'leverage': leverage,
                    'num_trades': len(trades_df),
                    'win_rate': len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
                    'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
                    'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
                    'final_equity': result['final_equity'],
                    'max_drawdown': result['max_drawdown'],
                    'params': strategy.params,
                    'trades': trades_df,
                    'equity_curve': result['equity_curve']
                })

            completed += 1
            if completed % 50 == 0:
                print(f"Progress: {completed}/{total_tests} ({completed/total_tests*100:.1f}%)")

    # Analyze results
    print("\n" + "="*80)
    print("ANALYZING RESULTS")
    print("="*80)

    results_df = pd.DataFrame(all_results)
    qualified = analyze_results(results_df)

    print(f"\nTotal strategy tests: {len(results_df)}")
    print(f"Profitable strategies (>10 trades): {len(qualified)}")
    print(f"Strategies with profit/DD >= 4.0: {len(qualified[qualified['profit_dd_ratio'] >= 4.0])}")

    # Save top strategies
    top_strategies = qualified.head(20)

    # Create summary
    summary_df = top_strategies[[
        'strategy', 'leverage', 'num_trades', 'win_rate',
        'avg_win', 'avg_loss', 'total_return_pct', 'max_dd_pct', 'profit_dd_ratio'
    ]].copy()

    summary_df.to_csv('eth_mean_reversion_summary.csv', index=False)
    print(f"\nSaved summary to: eth_mean_reversion_summary.csv")

    # Save detailed results for best strategy
    if len(qualified) > 0:
        best = qualified.iloc[0]
        best_trades = best['trades']
        best_trades.to_csv('eth_mean_reversion_best_trades.csv', index=False)
        print(f"Saved best strategy trades to: eth_mean_reversion_best_trades.csv")

        # Print top 10
        print("\n" + "="*80)
        print("TOP 10 STRATEGIES (by Profit/DD Ratio)")
        print("="*80)
        print(f"\n{summary_df.head(10).to_string(index=False)}")

        # Detailed analysis of best
        print("\n" + "="*80)
        print("BEST STRATEGY DETAILED ANALYSIS")
        print("="*80)
        print(f"\nStrategy: {best['strategy']}")
        print(f"Leverage: {best['leverage']}x")
        print(f"\nParameters:")
        for key, val in best['params'].items():
            print(f"  {key}: {val}")

        print(f"\nPerformance Metrics:")
        print(f"  Total Return: {best['total_return_pct']:.2f}%")
        print(f"  Max Drawdown: {best['max_dd_pct']:.2f}%")
        print(f"  Profit/DD Ratio: {best['profit_dd_ratio']:.2f}")
        print(f"  Number of Trades: {best['num_trades']}")
        print(f"  Win Rate: {best['win_rate']:.2f}%")
        print(f"  Avg Win: {best['avg_win']:.2f}%")
        print(f"  Avg Loss: {best['avg_loss']:.2f}%")
        print(f"  Final Equity: ${best['final_equity']:.2f}")

        # Additional analysis
        trades = best['trades']
        print(f"\nTrade Distribution:")
        print(f"  Long trades: {len(trades[trades['type'] == 'long'])}")
        print(f"  Short trades: {len(trades[trades['type'] == 'short'])}")
        print(f"\nExit Reasons:")
        print(trades['exit_reason'].value_counts())

    return qualified, df

if __name__ == "__main__":
    results, data = main()
    print("\n" + "="*80)
    print("BACKTEST COMPLETE!")
    print("="*80)
