"""
FARTCOIN - PHASE 2: ADD FILTERS TO ATR EXPANSION
Baseline: 34.7% WR, +205.59% return, Top10 11.71%
Goal: Remove losers, keep big winners
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import itertools

def calculate_atr(high, low, close, period=14):
    """ATR calculation"""
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    """EMA calculation"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(close, period=14):
    """RSI calculation"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ====================================================================================
# BASELINE: ATR EXPANSION (from Phase 1)
# ====================================================================================
def generate_baseline_signals(df):
    """Baseline ATR Expansion strategy"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']

    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']
    df['atr_expanding'] = df['atr_ratio'] > 1.5

    signals = []
    for i in range(len(df)):
        if df['atr_expanding'].iloc[i]:
            if df['bullish'].iloc[i]:
                signals.append(('LONG', i))
            elif df['bearish'].iloc[i]:
                signals.append(('SHORT', i))

    return signals

# ====================================================================================
# FILTERS
# ====================================================================================

def apply_htf_trend_filter(df, signals, ema_period=50):
    """
    Filter 1: Higher Timeframe Trend
    Only trade WITH the 5m trend (50-bar EMA on 1m ≈ 10-bar EMA on 5m)
    """
    df['ema_htf'] = calculate_ema(df['close'], ema_period)

    filtered = []
    for direction, idx in signals:
        if direction == 'LONG' and df['close'].iloc[idx] > df['ema_htf'].iloc[idx]:
            filtered.append((direction, idx))
        elif direction == 'SHORT' and df['close'].iloc[idx] < df['ema_htf'].iloc[idx]:
            filtered.append((direction, idx))

    return filtered

def apply_ema_distance_filter(df, signals, max_distance=3.0):
    """
    Filter 2: Don't enter if too far from EMA20
    Avoid chasing overextended moves
    """
    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)

    filtered = []
    for direction, idx in signals:
        if df['distance'].iloc[idx] < max_distance:
            filtered.append((direction, idx))

    return filtered

def apply_session_filter(df, signals):
    """
    Filter 3: Session filter
    Trade only during best sessions (based on volatility analysis)
    Asia/EU: 07:00-14:00 UTC (like DOGE Volume Zones)
    """
    df['hour'] = df['timestamp'].dt.hour

    filtered = []
    for direction, idx in signals:
        hour = df['hour'].iloc[idx]
        if 7 <= hour < 14:  # Asia/EU session
            filtered.append((direction, idx))

    return filtered

def apply_volume_filter(df, signals, threshold=2.0):
    """
    Filter 4: Stronger volume confirmation
    Require 2x average volume (not just any volume spike)
    """
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']

    filtered = []
    for direction, idx in signals:
        if df['vol_ratio'].iloc[idx] > threshold:
            filtered.append((direction, idx))

    return filtered

def apply_rsi_filter(df, signals, long_min=30, long_max=70, short_min=30, short_max=70):
    """
    Filter 5: RSI extremes
    Don't buy overbought or sell oversold
    """
    df['rsi'] = calculate_rsi(df['close'])

    filtered = []
    for direction, idx in signals:
        rsi = df['rsi'].iloc[idx]
        if direction == 'LONG' and long_min < rsi < long_max:
            filtered.append((direction, idx))
        elif direction == 'SHORT' and short_min < rsi < short_max:
            filtered.append((direction, idx))

    return filtered

def apply_consecutive_bars_filter(df, signals, max_consecutive=3):
    """
    Filter 6: Don't enter after too many consecutive same-direction bars
    Avoid late entries
    """
    df['bullish'] = (df['close'] > df['open']).astype(int)
    df['bearish'] = (df['close'] < df['open']).astype(int)

    # Count consecutive
    df['consecutive_bull'] = 0
    df['consecutive_bear'] = 0

    bull_count = 0
    bear_count = 0
    for i in range(len(df)):
        if df['bullish'].iloc[i]:
            bull_count += 1
            bear_count = 0
        elif df['bearish'].iloc[i]:
            bear_count += 1
            bull_count = 0
        else:
            bull_count = 0
            bear_count = 0

        df.loc[df.index[i], 'consecutive_bull'] = bull_count
        df.loc[df.index[i], 'consecutive_bear'] = bear_count

    filtered = []
    for direction, idx in signals:
        if direction == 'LONG' and df['consecutive_bull'].iloc[idx] <= max_consecutive:
            filtered.append((direction, idx))
        elif direction == 'SHORT' and df['consecutive_bear'].iloc[idx] <= max_consecutive:
            filtered.append((direction, idx))

    return filtered

def apply_body_size_filter(df, signals, min_body_pct=0.8):
    """
    Filter 7: Strong candle body
    Require meaningful body size (not doji)
    """
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

    filtered = []
    for direction, idx in signals:
        if df['body_pct'].iloc[idx] > min_body_pct:
            filtered.append((direction, idx))

    return filtered

# ====================================================================================
# BACKTESTING
# ====================================================================================
def backtest_signals(df, signals, config_name):
    """Backtest with same rules as Phase 1"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []

    for direction, entry_idx in signals:
        if entry_idx >= len(df) - 1:
            continue

        entry_price = df['close'].iloc[entry_idx]
        entry_atr = df['atr'].iloc[entry_idx]

        if pd.isna(entry_atr) or entry_atr == 0:
            continue

        # Same exits as Phase 1
        sl_dist = 2.0 * entry_atr
        tp_dist = 8.0 * entry_atr

        if direction == 'LONG':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

        # Walk forward
        exit_idx = None
        exit_price = None
        exit_reason = None
        max_profit = 0

        for i in range(entry_idx + 1, min(entry_idx + 200, len(df))):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            if direction == 'LONG':
                if current_low <= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_high >= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
                profit_pct = (current_high - entry_price) / entry_price * 100
                max_profit = max(max_profit, profit_pct)
            else:
                if current_high >= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_low <= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
                profit_pct = (entry_price - current_low) / entry_price * 100
                max_profit = max(max_profit, profit_pct)

        if exit_idx is None:
            exit_idx = min(entry_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        # P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        pnl_pct -= 0.1  # Fees

        trades.append({
            'config': config_name,
            'direction': direction,
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'max_profit_pct': max_profit
        })

    return trades

def analyze_results(trades, config_name):
    """Analyze results with Return/DD ratio"""
    if not trades:
        return {
            'config': config_name,
            'trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'top10_avg': 0,
            'max_winner': 0,
            'tp_rate': 0
        }

    df_trades = pd.DataFrame(trades)

    # Sort by entry to build equity curve
    df_trades = df_trades.sort_values('entry_idx')

    # Build equity curve
    df_trades['cumulative_return'] = df_trades['pnl_pct'].cumsum()
    equity_curve = 100 + df_trades['cumulative_return']

    # Max drawdown
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Return/DD ratio
    total_return = df_trades['pnl_pct'].sum()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = df_trades[df_trades['pnl_pct'] > 0]

    top10 = df_trades.nlargest(10, 'pnl_pct')['pnl_pct'].mean() if len(df_trades) >= 10 else df_trades['pnl_pct'].max()

    return {
        'config': config_name,
        'trades': len(trades),
        'win_rate': len(winners) / len(trades) * 100 if trades else 0,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'top10_avg': top10,
        'max_winner': df_trades['pnl_pct'].max(),
        'tp_rate': (df_trades['exit_reason'] == 'TP').sum() / len(trades) * 100,
        'avg_winner': winners['pnl_pct'].mean() if len(winners) > 0 else 0
    }

# ====================================================================================
# MAIN
# ====================================================================================
def main():
    print("🔍 FARTCOIN - PHASE 2: ADD FILTERS TO ATR EXPANSION\n")

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"📊 Data: {len(df):,} candles\n")

    # Baseline
    baseline_signals = generate_baseline_signals(df)
    baseline_trades = backtest_signals(df, baseline_signals, "BASELINE")
    baseline_results = analyze_results(baseline_trades, "BASELINE")

    print("="*100)
    print("📍 BASELINE (ATR Expansion, no filters)")
    print("="*100)
    print(f"Trades: {baseline_results['trades']} | WR: {baseline_results['win_rate']:.1f}%")
    print(f"Return: {baseline_results['total_return']:.2f}% | Max DD: {baseline_results['max_dd']:.2f}% | Return/DD: {baseline_results['return_dd']:.2f}x")
    print(f"Top10 Avg: {baseline_results['top10_avg']:.2f}% | Max: {baseline_results['max_winner']:.2f}%\n")

    # Test individual filters
    print("="*100)
    print("🧪 TESTING INDIVIDUAL FILTERS")
    print("="*100)

    filters = [
        ("HTF_Trend_EMA50", lambda df, sigs: apply_htf_trend_filter(df, sigs, 50)),
        ("HTF_Trend_EMA100", lambda df, sigs: apply_htf_trend_filter(df, sigs, 100)),
        ("EMA_Distance_2pct", lambda df, sigs: apply_ema_distance_filter(df, sigs, 2.0)),
        ("EMA_Distance_3pct", lambda df, sigs: apply_ema_distance_filter(df, sigs, 3.0)),
        ("Session_AsiaEU", lambda df, sigs: apply_session_filter(df, sigs)),
        ("Volume_2x", lambda df, sigs: apply_volume_filter(df, sigs, 2.0)),
        ("Volume_2.5x", lambda df, sigs: apply_volume_filter(df, sigs, 2.5)),
        ("RSI_30-70", lambda df, sigs: apply_rsi_filter(df, sigs, 30, 70, 30, 70)),
        ("RSI_40-60", lambda df, sigs: apply_rsi_filter(df, sigs, 40, 60, 40, 60)),
        ("Consecutive_Max3", lambda df, sigs: apply_consecutive_bars_filter(df, sigs, 3)),
        ("Consecutive_Max2", lambda df, sigs: apply_consecutive_bars_filter(df, sigs, 2)),
        ("Body_Size_0.8pct", lambda df, sigs: apply_body_size_filter(df, sigs, 0.8)),
    ]

    all_results = [baseline_results]

    for filter_name, filter_func in filters:
        filtered_signals = filter_func(df.copy(), baseline_signals)
        trades = backtest_signals(df, filtered_signals, filter_name)
        results = analyze_results(trades, filter_name)
        all_results.append(results)

        # Compare to baseline
        trade_reduction = (1 - results['trades'] / baseline_results['trades']) * 100 if baseline_results['trades'] > 0 else 0
        return_change = results['total_return'] - baseline_results['total_return']
        rr_change = results['return_dd'] - baseline_results['return_dd']

        print(f"\n{filter_name}:")
        print(f"  Trades: {results['trades']} ({trade_reduction:+.0f}%) | WR: {results['win_rate']:.1f}%")
        print(f"  Return: {results['total_return']:.2f}% ({return_change:+.2f}%) | DD: {results['max_dd']:.2f}% | R/DD: {results['return_dd']:.2f}x ({rr_change:+.2f}x)")
        print(f"  Top10: {results['top10_avg']:.2f}% | Max: {results['max_winner']:.2f}%")

    # Now test combinations of best filters
    print("\n" + "="*100)
    print("🎯 TESTING FILTER COMBINATIONS")
    print("="*100)

    # Find best individual filters (improved Return/DD)
    df_results = pd.DataFrame(all_results[1:])  # Skip baseline
    df_results['rr_vs_baseline'] = df_results['return_dd'] - baseline_results['return_dd']

    # Good filters = improved Return/DD
    good_filters = df_results[df_results['rr_vs_baseline'] > 0]

    if len(good_filters) > 0:
        print(f"\n✅ Found {len(good_filters)} promising filters (improved Return/DD):")
        print(good_filters[['config', 'trades', 'win_rate', 'total_return', 'max_dd', 'return_dd']].to_string(index=False))

        # Test combinations
        print("\n🔬 Testing combinations of top filters...\n")

        filter_map = dict(filters)
        top_filter_names = good_filters.nlargest(3, 'rr_vs_baseline')['config'].tolist()

        # Try 2-filter combinations
        for combo in itertools.combinations(top_filter_names, 2):
            signals = baseline_signals
            combo_name = " + ".join(combo)

            for filter_name in combo:
                if filter_name in filter_map:
                    signals = filter_map[filter_name](df.copy(), signals)

            trades = backtest_signals(df, signals, combo_name)
            results = analyze_results(trades, combo_name)

            rr_change = results['return_dd'] - baseline_results['return_dd']

            print(f"{combo_name}:")
            print(f"  Trades: {results['trades']} | WR: {results['win_rate']:.1f}%")
            print(f"  Return: {results['total_return']:.2f}% | DD: {results['max_dd']:.2f}% | R/DD: {results['return_dd']:.2f}x ({rr_change:+.2f}x)")
            print(f"  Top10: {results['top10_avg']:.2f}% | Max: {results['max_winner']:.2f}%\n")

            all_results.append(results)

    # Final ranking
    print("\n" + "="*100)
    print("📊 FINAL RANKING (by Return/DD Ratio)")
    print("="*100)

    df_final = pd.DataFrame(all_results)
    df_final = df_final.sort_values('return_dd', ascending=False)
    print(df_final[['config', 'trades', 'win_rate', 'total_return', 'max_dd', 'return_dd', 'top10_avg']].head(10).to_string(index=False))

    # Save
    df_final.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_filter_optimization.csv', index=False)
    print("\n✅ Saved: trading/results/fartcoin_filter_optimization.csv")

    # Best config
    best = df_final.iloc[0]
    print("\n" + "="*100)
    print("⭐ BEST CONFIGURATION (Highest Return/DD)")
    print("="*100)
    print(f"Config: {best['config']}")
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Total Return: {best['total_return']:.2f}%")
    print(f"Max Drawdown: {best['max_dd']:.2f}%")
    print(f"Return/DD Ratio: {best['return_dd']:.2f}x")
    print(f"Top 10 Avg: {best['top10_avg']:.2f}%")
    print(f"Max Winner: {best['max_winner']:.2f}%")

if __name__ == '__main__':
    main()
