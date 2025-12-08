#!/usr/bin/env python3
"""
Short Strategy Optimization
1. Test different TP/SL combinations
2. Analyze losing trade patterns
3. Develop filters to eliminate bad trades
"""

import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product
import warnings
warnings.filterwarnings('ignore')

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def backtest_with_details(df: pd.DataFrame, sl_pct: float, rr_ratio: float,
                          fee_per_side: float = 0.00005) -> tuple:
    """
    Backtest and return detailed trade info for analysis
    """
    df = df.copy()

    # Calculate indicators
    df['ema5'] = calculate_ema(df['close'], 5)
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Volume indicators (if available)
    if 'volume' in df.columns:
        df['vol_sma'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_sma']
    else:
        df['vol_ratio'] = 1.0  # Default neutral value

    # Trend strength
    df['trend'] = (df['ema5'] - df['ema50']) / df['close'] * 100

    # Price position relative to recent range
    df['high_20'] = df['high'].rolling(20).max()
    df['low_20'] = df['low'].rolling(20).min()
    df['price_position'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'])

    # Candle characteristics
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close'] * 100
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close'] * 100

    # Hour of day
    if 'timestamp' in df.columns:
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek

    # Signal
    df['signal'] = 0
    df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

    trades = []
    equity = 1.0
    max_equity = 1.0

    in_position = False
    entry_idx = 0
    entry_price = 0

    tp_pct = sl_pct * rr_ratio

    for i in range(50, len(df)):  # Start after indicators warm up
        row = df.iloc[i]

        if not in_position:
            if row['signal'] == -1:
                in_position = True
                entry_idx = i
                entry_price = row['close']
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)
        else:
            high = row['high']
            low = row['low']

            exit_price = None
            exit_reason = None

            if high >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'stop_loss'
            elif low <= take_profit:
                exit_price = take_profit
                exit_reason = 'take_profit'

            if exit_price:
                pnl_pct = (entry_price - exit_price) / entry_price
                total_fee = fee_per_side * 2
                net_pnl = pnl_pct - total_fee

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)
                dd = (max_equity - equity) / max_equity

                # Capture entry conditions for analysis
                entry_row = df.iloc[entry_idx]

                trade = {
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl * 100,
                    'exit_reason': exit_reason,
                    'winner': net_pnl > 0,
                    'equity': equity,
                    'drawdown': dd * 100,
                    # Entry conditions
                    'entry_rsi': entry_row['rsi'],
                    'entry_atr_pct': entry_row['atr_pct'],
                    'entry_vol_ratio': entry_row['vol_ratio'],
                    'entry_trend': entry_row['trend'],
                    'entry_price_position': entry_row['price_position'],
                    'entry_body_pct': entry_row['body_pct'],
                    'entry_upper_wick': entry_row['upper_wick'],
                    'entry_hour': entry_row.get('hour', 0),
                    'entry_dow': entry_row.get('day_of_week', 0),
                    'bars_held': i - entry_idx,
                }
                trades.append(trade)
                in_position = False

    return trades, equity

def analyze_losing_patterns(trades_df: pd.DataFrame):
    """Analyze what distinguishes winners from losers"""

    winners = trades_df[trades_df['winner'] == True]
    losers = trades_df[trades_df['winner'] == False]

    print("\n" + "=" * 70)
    print("WINNER vs LOSER ANALYSIS")
    print("=" * 70)

    features = ['entry_rsi', 'entry_atr_pct', 'entry_vol_ratio', 'entry_trend',
                'entry_price_position', 'entry_body_pct', 'entry_upper_wick',
                'entry_hour', 'bars_held']

    print(f"\n{'Feature':<25} {'Winners':<15} {'Losers':<15} {'Diff':<15}")
    print("-" * 70)

    insights = {}
    for feat in features:
        if feat in trades_df.columns:
            w_mean = winners[feat].mean()
            l_mean = losers[feat].mean()
            diff = w_mean - l_mean
            diff_pct = (diff / l_mean * 100) if l_mean != 0 else 0

            insights[feat] = {'winners': w_mean, 'losers': l_mean, 'diff': diff}
            print(f"{feat:<25} {w_mean:>12.2f}   {l_mean:>12.2f}   {diff:>+10.2f} ({diff_pct:+.1f}%)")

    return insights

def test_filters(trades_df: pd.DataFrame, original_equity: float):
    """Test various filters to eliminate losing trades"""

    print("\n" + "=" * 70)
    print("FILTER TESTING")
    print("=" * 70)

    filters = [
        ('RSI < 65 (not overbought enough)', lambda t: t['entry_rsi'] < 65),
        ('RSI > 50 (momentum confirmation)', lambda t: t['entry_rsi'] > 50),
        ('RSI 50-70 (sweet spot)', lambda t: (t['entry_rsi'] > 50) & (t['entry_rsi'] < 70)),
        ('High volatility (ATR > 1.5%)', lambda t: t['entry_atr_pct'] > 1.5),
        ('Low volatility (ATR < 2%)', lambda t: t['entry_atr_pct'] < 2),
        ('Above avg volume', lambda t: t['entry_vol_ratio'] > 1.0),
        ('Below avg volume', lambda t: t['entry_vol_ratio'] < 1.0),
        ('Downtrend (trend < 0)', lambda t: t['entry_trend'] < 0),
        ('Uptrend (trend > 0)', lambda t: t['entry_trend'] > 0),
        ('Price near highs (pos > 0.7)', lambda t: t['entry_price_position'] > 0.7),
        ('Price mid-range (0.3-0.7)', lambda t: (t['entry_price_position'] > 0.3) & (t['entry_price_position'] < 0.7)),
        ('Strong candle body > 0.5%', lambda t: t['entry_body_pct'] > 0.5),
        ('Upper wick > 0.3%', lambda t: t['entry_upper_wick'] > 0.3),
        ('Trading hours 8-20 UTC', lambda t: (t['entry_hour'] >= 8) & (t['entry_hour'] <= 20)),
        ('Weekdays only', lambda t: t['entry_dow'] < 5),
    ]

    results = []

    print(f"\n{'Filter':<40} {'Trades':<8} {'Win%':<8} {'Return':<10} {'MaxDD':<8}")
    print("-" * 80)

    # Baseline
    base_trades = len(trades_df)
    base_wins = trades_df['winner'].sum()
    base_return = (original_equity - 1) * 100
    base_dd = trades_df['drawdown'].max()
    print(f"{'BASELINE (no filter)':<40} {base_trades:<8} {base_wins/base_trades*100:<7.1f}% {base_return:<+9.2f}% {base_dd:<7.1f}%")
    print("-" * 80)

    for name, filter_func in filters:
        try:
            mask = filter_func(trades_df)
            filtered = trades_df[mask]

            if len(filtered) < 5:
                continue

            # Recalculate equity with filtered trades
            equity = 1.0
            max_eq = 1.0
            max_dd = 0
            for _, t in filtered.iterrows():
                equity *= (1 + t['pnl_pct'] / 100)
                max_eq = max(max_eq, equity)
                dd = (max_eq - equity) / max_eq * 100
                max_dd = max(max_dd, dd)

            n_trades = len(filtered)
            win_rate = filtered['winner'].sum() / n_trades * 100
            ret = (equity - 1) * 100

            results.append({
                'filter': name,
                'trades': n_trades,
                'win_rate': win_rate,
                'return': ret,
                'max_dd': max_dd,
                'return_per_trade': ret / n_trades,
                'risk_reward': ret / max_dd if max_dd > 0 else 0
            })

            improvement = "✓" if ret > base_return else " "
            print(f"{improvement} {name:<38} {n_trades:<8} {win_rate:<7.1f}% {ret:<+9.2f}% {max_dd:<7.1f}%")

        except Exception as e:
            continue

    return pd.DataFrame(results)

def optimize_sl_tp(token: str, df: pd.DataFrame):
    """Test different SL/TP combinations"""

    print(f"\n{'=' * 70}")
    print(f"OPTIMIZING {token}")
    print(f"{'=' * 70}")

    # Test grid
    sl_levels = [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05]
    rr_levels = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

    results = []

    for sl, rr in product(sl_levels, rr_levels):
        trades, equity = backtest_with_details(df, sl, rr)

        if len(trades) < 10:
            continue

        trades_df = pd.DataFrame(trades)
        wins = trades_df['winner'].sum()
        max_dd = trades_df['drawdown'].max()

        results.append({
            'sl_pct': sl * 100,
            'tp_pct': sl * rr * 100,
            'rr_ratio': rr,
            'trades': len(trades),
            'win_rate': wins / len(trades) * 100,
            'return': (equity - 1) * 100,
            'max_dd': max_dd,
            'risk_reward': (equity - 1) * 100 / max_dd if max_dd > 0 else 0
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return', ascending=False)

    print(f"\nTOP 10 SL/TP COMBINATIONS BY RETURN:")
    print(f"{'SL%':<6} {'TP%':<6} {'R:R':<6} {'Trades':<8} {'Win%':<8} {'Return':<10} {'MaxDD':<8} {'Ret/DD':<8}")
    print("-" * 70)

    for _, row in results_df.head(10).iterrows():
        print(f"{row['sl_pct']:<6.1f} {row['tp_pct']:<6.1f} {row['rr_ratio']:<6.1f} "
              f"{row['trades']:<8.0f} {row['win_rate']:<7.1f}% {row['return']:<+9.2f}% "
              f"{row['max_dd']:<7.1f}% {row['risk_reward']:<7.2f}x")

    # Best by risk-adjusted return
    print(f"\nTOP 5 BY RISK-ADJUSTED RETURN (Return/MaxDD):")
    best_risk = results_df.sort_values('risk_reward', ascending=False).head(5)
    for _, row in best_risk.iterrows():
        print(f"  SL:{row['sl_pct']:.1f}% TP:{row['tp_pct']:.1f}% → {row['return']:+.1f}% return, {row['max_dd']:.1f}% DD, {row['risk_reward']:.2f}x R:R")

    return results_df

def main():
    # Focus on top performers
    tokens = ['PENGU', 'FARTCOIN', 'MELANIA', 'CRV', 'XLM']

    all_results = {}
    all_trades = []

    for token in tokens:
        file_path = Path(f'/workspaces/Carebiuro_windykacja/{token.lower()}_15m_3months.csv')
        if not file_path.exists():
            continue

        df = pd.read_csv(file_path)

        # Optimize SL/TP
        opt_results = optimize_sl_tp(token, df)
        all_results[token] = opt_results

        # Get trades with best config for pattern analysis
        best = opt_results.iloc[0]
        trades, equity = backtest_with_details(df, best['sl_pct']/100, best['rr_ratio'])
        trades_df = pd.DataFrame(trades)
        trades_df['token'] = token
        all_trades.append(trades_df)

        # Analyze patterns
        if len(trades_df) > 20:
            insights = analyze_losing_patterns(trades_df)
            filter_results = test_filters(trades_df, equity)

    # Combine all trades for cross-token analysis
    print("\n" + "=" * 70)
    print("COMBINED ANALYSIS ACROSS ALL TOP TOKENS")
    print("=" * 70)

    combined = pd.concat(all_trades, ignore_index=True)
    print(f"\nTotal trades analyzed: {len(combined)}")
    print(f"Overall win rate: {combined['winner'].mean()*100:.1f}%")

    analyze_losing_patterns(combined)

    # Find best universal filters
    print("\n" + "=" * 70)
    print("BEST FILTERS (Combined Dataset)")
    print("=" * 70)

    # Recalculate equity for combined
    combined = combined.sort_values('entry_idx')
    equity = 1.0
    for _, t in combined.iterrows():
        equity *= (1 + t['pnl_pct'] / 100)

    filter_results = test_filters(combined, equity)

    if len(filter_results) > 0:
        best_filters = filter_results.sort_values('risk_reward', ascending=False)
        print("\n\nTOP FILTERS BY RISK-ADJUSTED RETURN:")
        for _, row in best_filters.head(5).iterrows():
            print(f"  {row['filter']}: {row['return']:+.1f}% return, {row['max_dd']:.1f}% DD, {row['trades']} trades")

    # Save results
    output_path = Path('/workspaces/Carebiuro_windykacja/trading/results/optimization_results.csv')
    combined.to_csv(output_path, index=False)
    print(f"\nDetailed trades saved to: {output_path}")

if __name__ == '__main__':
    main()