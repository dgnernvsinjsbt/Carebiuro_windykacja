#!/usr/bin/env python3
"""
FARTCOIN Regime Analysis
Analyze 3-month performance to identify when short strategy works vs fails
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def classify_regime(df: pd.DataFrame, idx: int) -> dict:
    """
    Classify market regime at given index
    Uses multiple indicators to avoid overfitting
    """
    row = df.iloc[idx]

    # Price vs long-term EMAs
    price_vs_ema50 = (row['close'] - row['ema50']) / row['ema50'] * 100 if row['ema50'] > 0 else 0
    price_vs_ema100 = (row['close'] - row['ema100']) / row['ema100'] * 100 if row['ema100'] > 0 else 0

    # EMA slopes
    ema50_slope = (row['ema50'] - df.iloc[max(0, idx-20)]['ema50']) / df.iloc[max(0, idx-20)]['ema50'] * 100 if idx >= 20 else 0

    # Recent price momentum
    price_7d = row['close'] / df.iloc[max(0, idx-28)]['close'] - 1 if idx >= 28 else 0  # 28 bars = 7 days
    price_14d = row['close'] / df.iloc[max(0, idx-56)]['close'] - 1 if idx >= 56 else 0

    # Classification logic
    regime = {
        'price_vs_ema50': price_vs_ema50,
        'price_vs_ema100': price_vs_ema100,
        'ema50_slope': ema50_slope,
        'price_7d_change': price_7d * 100,
        'price_14d_change': price_14d * 100,
    }

    # Determine regime type
    if price_vs_ema100 > 2 and ema50_slope > 0.5:
        regime['type'] = 'Strong Uptrend'
        regime['short_favorable'] = False
    elif price_vs_ema100 > 0 or ema50_slope > 0:
        regime['type'] = 'Weak Uptrend'
        regime['short_favorable'] = False
    elif price_vs_ema100 < -5 and ema50_slope < -0.5:
        regime['type'] = 'Strong Downtrend'
        regime['short_favorable'] = True
    elif price_vs_ema100 < 0:
        regime['type'] = 'Weak Downtrend'
        regime['short_favorable'] = True
    else:
        regime['type'] = 'Sideways'
        regime['short_favorable'] = None  # Mixed

    return regime

def backtest_with_regimes(df: pd.DataFrame, sl: float = 0.05, tp_multiplier: float = 1.5):
    """
    Backtest strategy and track regime at each trade
    Using FARTCOIN's best config from optimization: SL 5%, TP 7.5% (1.5x R:R)
    """
    df = df.copy()

    # Calculate all indicators
    df['ema5'] = calculate_ema(df['close'], 5)
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['ema100'] = calculate_ema(df['close'], 100)
    df['ema200'] = calculate_ema(df['close'], 200)
    df['atr'] = calculate_atr(df, 14)
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Rolling volatility
    df['volatility'] = df['close'].pct_change().rolling(20).std() * 100

    # Signal
    df['signal'] = 0
    df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

    # Backtest
    trades = []
    equity = 1.0
    max_equity = 1.0

    in_position = False
    entry_idx = 0

    fee = 0.00005  # 0.005% per side
    tp_pct = sl * tp_multiplier

    for i in range(200, len(df)):  # Start after indicators warm up
        row = df.iloc[i]

        if not in_position:
            if row['signal'] == -1:
                # Classify regime at entry
                regime = classify_regime(df, i)

                in_position = True
                entry_idx = i
                entry_price = row['close']
                entry_time = row['timestamp'] if 'timestamp' in row else None
                stop_loss = entry_price * (1 + sl)
                take_profit = entry_price * (1 - tp_pct)

                # Store entry info
                entry_regime = regime
        else:
            exit_price = None
            exit_reason = None

            if row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            elif row['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                pnl_pct = (entry_price - exit_price) / entry_price
                net_pnl = pnl_pct - (fee * 2)

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)
                dd = (max_equity - equity) / max_equity * 100

                trades.append({
                    'entry_time': entry_time,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl * 100,
                    'winner': net_pnl > 0,
                    'exit_reason': exit_reason,
                    'equity': equity,
                    'drawdown': dd,
                    'bars_held': i - entry_idx,
                    # Regime info
                    'regime_type': entry_regime['type'],
                    'regime_favorable': entry_regime['short_favorable'],
                    'price_vs_ema50': entry_regime['price_vs_ema50'],
                    'price_vs_ema100': entry_regime['price_vs_ema100'],
                    'ema50_slope': entry_regime['ema50_slope'],
                    'price_7d_change': entry_regime['price_7d_change'],
                    'price_14d_change': entry_regime['price_14d_change'],
                })

                in_position = False

    return pd.DataFrame(trades), equity

def analyze_regimes(trades_df: pd.DataFrame):
    """Analyze performance by regime type"""

    print("\n" + "=" * 80)
    print("REGIME-BASED PERFORMANCE ANALYSIS")
    print("=" * 80)

    print(f"\n{'Regime Type':<25} {'Trades':<8} {'Win%':<8} {'Avg P&L':<10} {'Profitable?':<12}")
    print("-" * 80)

    regime_stats = []

    for regime_type in ['Strong Downtrend', 'Weak Downtrend', 'Sideways', 'Weak Uptrend', 'Strong Uptrend']:
        subset = trades_df[trades_df['regime_type'] == regime_type]

        if len(subset) > 0:
            win_rate = subset['winner'].mean() * 100
            avg_pnl = subset['pnl_pct'].mean()
            total_pnl = subset['pnl_pct'].sum()

            profitable = "✅ YES" if total_pnl > 0 else "❌ NO"

            regime_stats.append({
                'regime': regime_type,
                'trades': len(subset),
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'profitable': total_pnl > 0
            })

            print(f"{regime_type:<25} {len(subset):<8} {win_rate:<7.1f}% {avg_pnl:<+9.2f}% {profitable:<12}")

    return pd.DataFrame(regime_stats)

def time_series_analysis(trades_df: pd.DataFrame):
    """Analyze performance over time"""

    print("\n" + "=" * 80)
    print("TIME-SERIES PERFORMANCE")
    print("=" * 80)

    if 'entry_time' not in trades_df.columns or trades_df['entry_time'].isna().all():
        print("\nNo timestamp data available for time-series analysis")
        return

    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time'])
    trades_df['week'] = trades_df['entry_date'].dt.to_period('W')

    weekly = trades_df.groupby('week').agg({
        'pnl_pct': ['count', 'sum', 'mean'],
        'winner': 'mean'
    }).round(2)

    weekly.columns = ['Trades', 'Total P&L %', 'Avg P&L %', 'Win Rate']
    weekly['Win Rate'] = weekly['Win Rate'] * 100

    print("\nWeekly Performance:")
    print(weekly.to_string())

    # Identify worst periods
    print("\n" + "=" * 80)
    print("WORST PERFORMING PERIODS")
    print("=" * 80)

    worst_weeks = weekly.nsmallest(3, 'Total P&L %')
    print(worst_weeks.to_string())

def main():
    print("=" * 80)
    print("FARTCOIN FULL 10-MONTH REGIME ANALYSIS")
    print("Strategy: EMA 5/20 Cross Down Short")
    print("Config: SL 5%, TP 7.5% (1.5:1 R:R), 0.01% fees")
    print("=" * 80)

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')

    # Data summary
    print(f"\nData Range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Total Bars: {len(df)}")
    print(f"Price Start: ${df['close'].iloc[200]:.4f}")
    print(f"Price End: ${df['close'].iloc[-1]:.4f}")
    print(f"Price Change: {(df['close'].iloc[-1] / df['close'].iloc[200] - 1) * 100:+.1f}%")

    # Run backtest with regime tracking
    trades_df, final_equity = backtest_with_regimes(df)

    # Overall performance
    print("\n" + "=" * 80)
    print("OVERALL PERFORMANCE (BLIND TRADING)")
    print("=" * 80)

    total_return = (final_equity - 1) * 100
    win_rate = trades_df['winner'].mean() * 100
    max_dd = trades_df['drawdown'].max()

    print(f"Total Return: {total_return:+.2f}%")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Avg Trade: {trades_df['pnl_pct'].mean():+.2f}%")

    # Regime analysis
    regime_stats = analyze_regimes(trades_df)

    # Time series
    time_series_analysis(trades_df)

    # Key insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)

    unfavorable_trades = trades_df[trades_df['regime_favorable'] == False]
    favorable_trades = trades_df[trades_df['regime_favorable'] == True]

    if len(unfavorable_trades) > 0:
        unfav_return = unfavorable_trades['pnl_pct'].sum()
        print(f"\nUnfavorable Regimes (Uptrends):")
        print(f"  Trades: {len(unfavorable_trades)} ({len(unfavorable_trades)/len(trades_df)*100:.1f}%)")
        print(f"  Total P&L: {unfav_return:+.2f}%")
        print(f"  Avg P&L: {unfavorable_trades['pnl_pct'].mean():+.2f}%")
        print(f"  Win Rate: {unfavorable_trades['winner'].mean()*100:.1f}%")

    if len(favorable_trades) > 0:
        fav_return = favorable_trades['pnl_pct'].sum()
        print(f"\nFavorable Regimes (Downtrends):")
        print(f"  Trades: {len(favorable_trades)} ({len(favorable_trades)/len(trades_df)*100:.1f}%)")
        print(f"  Total P&L: {fav_return:+.2f}%")
        print(f"  Avg P&L: {favorable_trades['pnl_pct'].mean():+.2f}%")
        print(f"  Win Rate: {favorable_trades['winner'].mean()*100:.1f}%")

    # What if we filtered uptrends?
    if len(unfavorable_trades) > 0 and len(favorable_trades) > 0:
        print("\n" + "=" * 80)
        print("WHAT IF WE FILTERED UNFAVORABLE REGIMES?")
        print("=" * 80)

        filtered_return = fav_return
        improvement = filtered_return - total_return

        print(f"\nFiltered Return (only favorable): {filtered_return:+.2f}%")
        print(f"Baseline Return (blind trading): {total_return:+.2f}%")
        print(f"Improvement: {improvement:+.2f}%")
        print(f"\nTrades Avoided: {len(unfavorable_trades)} ({len(unfavorable_trades)/len(trades_df)*100:.1f}%)")
        print(f"Trades Taken: {len(favorable_trades)} ({len(favorable_trades)/len(trades_df)*100:.1f}%)")

    # Save results
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_regime_trades.csv'
    trades_df.to_csv(output_path, index=False)
    print(f"\n\nDetailed results saved to: {output_path}")

    return trades_df, regime_stats

if __name__ == '__main__':
    trades_df, regime_stats = main()