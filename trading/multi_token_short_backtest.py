#!/usr/bin/env python3
"""
Multi-Token Short Strategy Backtest
Applies EMA 5/20 Cross Down shorting strategy to all available crypto pairs
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration - same as winning PI strategy
STRATEGY_CONFIG = {
    'ema_fast': 5,
    'ema_slow': 20,
    'stop_loss_pct': 0.03,  # 3%
    'risk_reward': 1.5,     # 1.5:1
    'fee_per_side': 0.00005  # 0.005%
}

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

def backtest_short_strategy(df: pd.DataFrame, config: dict) -> dict:
    """
    Backtest EMA crossover short strategy on a single token
    Returns performance metrics
    """
    df = df.copy()

    # Calculate EMAs
    df['ema_fast'] = calculate_ema(df['close'], config['ema_fast'])
    df['ema_slow'] = calculate_ema(df['close'], config['ema_slow'])

    # Generate signals: Short when fast EMA crosses below slow EMA
    df['signal'] = 0
    df.loc[(df['ema_fast'] < df['ema_slow']) &
           (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)), 'signal'] = -1

    # Simulate trades
    trades = []
    equity = 1.0
    max_equity = 1.0
    in_position = False
    entry_price = 0
    entry_time = None
    stop_loss = 0
    take_profit = 0

    for i in range(len(df)):
        row = df.iloc[i]

        if not in_position:
            # Check for entry signal
            if row['signal'] == -1:
                in_position = True
                entry_price = row['close']
                entry_time = row['timestamp'] if 'timestamp' in df.columns else df.index[i]
                stop_loss = entry_price * (1 + config['stop_loss_pct'])
                take_profit = entry_price * (1 - config['stop_loss_pct'] * config['risk_reward'])
        else:
            # Check for exit conditions
            high = row['high']
            low = row['low']

            exit_price = None
            exit_reason = None

            # Check stop loss (price went up)
            if high >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'stop_loss'
            # Check take profit (price went down)
            elif low <= take_profit:
                exit_price = take_profit
                exit_reason = 'take_profit'

            if exit_price:
                # Calculate P&L for short
                pnl_pct = (entry_price - exit_price) / entry_price
                total_fee = config['fee_per_side'] * 2
                net_pnl = pnl_pct - total_fee

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)

                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl * 100,
                    'exit_reason': exit_reason,
                    'equity': equity
                })

                in_position = False

    # Calculate metrics
    if len(trades) == 0:
        return {
            'total_return': 0,
            'num_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'sharpe': 0
        }

    trade_df = pd.DataFrame(trades)
    winners = trade_df[trade_df['pnl_pct'] > 0]
    losers = trade_df[trade_df['pnl_pct'] <= 0]

    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0

    # Calculate max drawdown
    equity_series = [1.0] + list(trade_df['equity'])
    max_dd = 0
    peak = equity_series[0]
    for eq in equity_series:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        max_dd = max(max_dd, dd)

    # Sharpe ratio approximation
    returns = trade_df['pnl_pct'].values / 100
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(len(returns)) if np.std(returns) > 0 else 0

    return {
        'total_return': (equity - 1) * 100,
        'num_trades': len(trades),
        'win_rate': len(winners) / len(trades) * 100,
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
        'max_drawdown': max_dd * 100,
        'avg_win': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loss': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'sharpe': sharpe
    }

def main():
    # Find all data files
    data_dir = Path('/workspaces/Carebiuro_windykacja')
    data_files = list(data_dir.glob('*_15m_3months.csv'))

    print(f"Found {len(data_files)} crypto pairs to analyze\n")
    print("=" * 80)
    print("MULTI-TOKEN SHORT STRATEGY BACKTEST")
    print("Strategy: EMA 5/20 Cross Down | SL: 3% | TP: 4.5% (1.5:1 R:R)")
    print("Fees: 0.01% round-trip | Leverage: 1x")
    print("=" * 80)

    results = []

    for file in sorted(data_files):
        token = file.stem.replace('_15m_3months', '').upper()

        try:
            df = pd.read_csv(file)

            # Ensure we have required columns
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                print(f"  {token}: Missing required columns, skipping")
                continue

            metrics = backtest_short_strategy(df, STRATEGY_CONFIG)
            metrics['token'] = token
            metrics['data_file'] = file.name

            # Get price change over period
            start_price = df['close'].iloc[0]
            end_price = df['close'].iloc[-1]
            price_change = (end_price - start_price) / start_price * 100
            metrics['price_change'] = price_change

            results.append(metrics)

            # Print result
            status = "✓" if metrics['total_return'] > 0 else "✗"
            print(f"{status} {token:12} | Return: {metrics['total_return']:+7.2f}% | "
                  f"Trades: {metrics['num_trades']:3} | Win: {metrics['win_rate']:5.1f}% | "
                  f"PF: {metrics['profit_factor']:5.2f} | MaxDD: {metrics['max_drawdown']:5.1f}%")

        except Exception as e:
            print(f"  {token}: Error - {str(e)}")

    # Create summary DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('total_return', ascending=False)

    # Save detailed results
    output_path = Path('/workspaces/Carebiuro_windykacja/trading/results/multi_token_short_summary.csv')
    results_df.to_csv(output_path, index=False)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    profitable = results_df[results_df['total_return'] > 0]
    unprofitable = results_df[results_df['total_return'] <= 0]

    print(f"\nProfitable tokens: {len(profitable)}/{len(results_df)}")
    print(f"Unprofitable tokens: {len(unprofitable)}/{len(results_df)}")

    print(f"\nTotal trades across all tokens: {results_df['num_trades'].sum():.0f}")
    print(f"Average return: {results_df['total_return'].mean():+.2f}%")
    print(f"Median return: {results_df['total_return'].median():+.2f}%")

    print("\n" + "-" * 80)
    print("TOP PERFORMERS (Profitable)")
    print("-" * 80)
    for _, row in profitable.iterrows():
        print(f"  {row['token']:12} | {row['total_return']:+7.2f}% | {row['num_trades']:3} trades | "
              f"Win: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f}")

    if len(unprofitable) > 0:
        print("\n" + "-" * 80)
        print("UNDERPERFORMERS (Unprofitable)")
        print("-" * 80)
        for _, row in unprofitable.iterrows():
            print(f"  {row['token']:12} | {row['total_return']:+7.2f}% | {row['num_trades']:3} trades | "
                  f"Win: {row['win_rate']:.1f}% | Price: {row['price_change']:+.1f}%")

    # Portfolio simulation (equal weight all tokens)
    print("\n" + "=" * 80)
    print("PORTFOLIO SIMULATION (Equal Weight All Tokens)")
    print("=" * 80)

    avg_return = results_df['total_return'].mean()
    total_trades = results_df['num_trades'].sum()
    avg_win_rate = results_df['win_rate'].mean()
    avg_max_dd = results_df['max_drawdown'].mean()

    print(f"  Portfolio Return (avg): {avg_return:+.2f}%")
    print(f"  Total Trades: {total_trades:.0f}")
    print(f"  Avg Win Rate: {avg_win_rate:.1f}%")
    print(f"  Avg Max Drawdown: {avg_max_dd:.1f}%")

    # Best combo: only trade profitable tokens
    if len(profitable) > 0:
        best_return = profitable['total_return'].mean()
        best_trades = profitable['num_trades'].sum()
        print(f"\n  Selective Portfolio (profitable only): {best_return:+.2f}%")
        print(f"  Trades: {best_trades:.0f}")

    print(f"\nResults saved to: {output_path}")

    return results_df

if __name__ == '__main__':
    results = main()