#!/usr/bin/env python3
"""
MOODENG ATR Limit Strategy - Improvement Analysis & Testing

Goal: Reduce 85.3% outlier dependency while maintaining profitability
Current best: 6.78x R/DD, but lottery-style (Top 5 = 85.3%)

Improvement Ideas to Test:
1. Volatility regime filter - avoid dead zones
2. Adaptive TP based on ATR magnitude - lock gains faster in spikes
3. RSI momentum confirmation - filter weak signals
4. Session time filter - like DOGE strategy
5. Max ATR cap - reduce exposure during extreme volatility
"""
import pandas as pd
import numpy as np
from datetime import time

def analyze_outliers(trades_df):
    """Deep dive into what made the outliers work"""
    print("\n" + "="*100)
    print("OUTLIER ANALYSIS - What caused 73% profit concentration?")
    print("="*100)

    # Top 5 trades
    top5 = trades_df.nlargest(5, 'pnl_pct')

    print(f"\n📊 TOP 5 TRADES (85.3% of profits):")
    print(f"\n{'Trade':<6} {'Time':<17} {'Entry':<9} {'Exit':<9} {'Dir':<5} {'PnL':<8} {'ATR':<9} {'ATR Exp':<9} {'Hold':<5}")
    print("-"*100)

    for idx, row in top5.iterrows():
        print(f"{row['trade_num']:<6} {str(row['entry_timestamp']):<17} "
              f"{row['entry']:<9.6f} {row['exit']:<9.6f} {row['direction']:<5} "
              f"{row['pnl_pct']:<7.2f}% {row['atr']:<9.6f} "
              f"{row['atr_expansion']:<9.2f} {row['hold_bars']:<5.0f}")

    # Compare outliers vs normal trades
    outliers = trades_df[trades_df['pnl_pct'] > 10]
    normal = trades_df[trades_df['pnl_pct'] <= 10]

    print(f"\n🔬 OUTLIER CHARACTERISTICS:")
    print(f"\nMetric                    Outliers (>10%)    Normal (<=10%)    Difference")
    print("-"*100)
    print(f"Count                     {len(outliers):<18} {len(normal):<18} -")
    print(f"Avg ATR                   {outliers['atr'].mean():<18.6f} {normal['atr'].mean():<18.6f} {(outliers['atr'].mean() / normal['atr'].mean() - 1) * 100:+.1f}%")
    print(f"Avg ATR Expansion         {outliers['atr_expansion'].mean():<18.2f} {normal['atr_expansion'].mean():<18.2f} {(outliers['atr_expansion'].mean() / normal['atr_expansion'].mean() - 1) * 100:+.1f}%")
    print(f"Avg Hold Bars             {outliers['hold_bars'].mean():<18.1f} {normal['hold_bars'].mean():<18.1f} {(outliers['hold_bars'].mean() / normal['hold_bars'].mean() - 1) * 100:+.1f}%")
    print(f"TP Rate                   {(outliers['exit_reason'] == 'TP').sum() / len(outliers) * 100:<17.1f}% {(normal['exit_reason'] == 'TP').sum() / len(normal) * 100:<17.1f}% -")

    # The critical 7-minute window
    window_trades = trades_df[(trades_df['trade_num'] >= 108) & (trades_df['trade_num'] <= 112)]

    print(f"\n⚠️  CRITICAL 7-MINUTE WINDOW (73% of all profits):")
    print(f"\n4 trades from 23:55 to 00:02 on Dec 6-7:")
    print(f"- Combined PnL: {window_trades['pnl_pct'].sum():.2f}%")
    print(f"- All LONG entries")
    print(f"- All hit TP")
    print(f"- ATR range: {window_trades['atr'].min():.6f} to {window_trades['atr'].max():.6f} (EXTREME)")
    print(f"- Normal ATR: ~0.0003-0.0006 (10x spike!)")

    return outliers, normal

def backtest_improved(df, variant_name, params, improvements):
    """Backtest with specific improvements applied"""
    df = df.copy()

    # Calculate indicators
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['atr_ma'] = df['atr'].rolling(params['atr_lookback']).mean()
    df['atr_expansion'] = df['atr'] / df['atr_ma']
    df['ema_dist_pct'] = abs((df['close'] - df['ema_20']) / df['ema_20'] * 100)
    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']

    # Add improvement-specific indicators
    if 'rsi_filter' in improvements:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

    if 'session_filter' in improvements:
        df['hour'] = df['timestamp'].dt.hour

    if 'atr_regime_filter' in improvements:
        df['atr_ma_50'] = df['atr'].rolling(50).mean()
        df['atr_regime'] = df['atr'] / df['atr_ma_50']

    trades = []
    pending_orders = []

    for i in range(50, len(df)):
        current = df.iloc[i]

        # Check pending orders for fills
        for order in pending_orders[:]:
            bars_waiting = i - order['signal_bar']

            if bars_waiting > params['max_wait_bars']:
                pending_orders.remove(order)
                continue

            filled = False
            if order['direction'] == 'LONG':
                if current['high'] >= order['limit_price']:
                    filled = True
            else:
                if current['low'] <= order['limit_price']:
                    filled = True

            if filled:
                trades.append({
                    'entry_bar': i,
                    'entry': order['limit_price'],
                    'direction': order['direction'],
                    'sl': order['sl'],
                    'tp': order['tp'],
                    'atr': order['atr']
                })
                pending_orders.remove(order)

        # Base signal
        base_signal = (df.iloc[i]['atr_expansion'] > params['atr_expansion_mult'] and
                      df.iloc[i]['ema_dist_pct'] <= params['ema_distance_max'] and
                      (df.iloc[i]['is_bullish'] or df.iloc[i]['is_bearish']))

        if not base_signal:
            continue

        # Apply improvements
        signal_valid = True

        # 1. RSI momentum filter
        if 'rsi_filter' in improvements:
            rsi_threshold = improvements['rsi_filter']
            if df.iloc[i]['rsi'] < rsi_threshold:
                signal_valid = False

        # 2. Session time filter
        if 'session_filter' in improvements:
            allowed_hours = improvements['session_filter']
            if df.iloc[i]['hour'] not in allowed_hours:
                signal_valid = False

        # 3. ATR regime filter (avoid dead zones)
        if 'atr_regime_filter' in improvements:
            min_regime = improvements['atr_regime_filter']
            if df.iloc[i]['atr_regime'] < min_regime:
                signal_valid = False

        # 4. Max ATR cap (reduce extreme volatility exposure)
        if 'max_atr_cap' in improvements:
            max_atr_mult = improvements['max_atr_cap']
            atr_multiple = df.iloc[i]['atr'] / df.iloc[i]['atr_ma']
            if atr_multiple > max_atr_mult:
                signal_valid = False

        if not signal_valid:
            continue

        # Place order
        direction = 'LONG' if df.iloc[i]['is_bullish'] else 'SHORT'
        signal_price = current['close']
        atr = current['atr']

        # 5. Adaptive TP based on ATR magnitude
        if 'adaptive_tp' in improvements:
            atr_mult = df.iloc[i]['atr'] / df.iloc[i]['atr_ma']
            # If ATR is extreme (>2x), use lower TP to lock gains faster
            if atr_mult > improvements['adaptive_tp']['threshold']:
                tp_mult = improvements['adaptive_tp']['low_tp']
            else:
                tp_mult = params['tp_atr_mult']
        else:
            tp_mult = params['tp_atr_mult']

        if direction == 'LONG':
            limit_price = signal_price * (1 + params['limit_offset_pct'] / 100)
            sl = limit_price - (params['sl_atr_mult'] * atr)
            tp = limit_price + (tp_mult * atr)
        else:
            limit_price = signal_price * (1 - params['limit_offset_pct'] / 100)
            sl = limit_price + (params['sl_atr_mult'] * atr)
            tp = limit_price - (tp_mult * atr)

        pending_orders.append({
            'signal_bar': i,
            'limit_price': limit_price,
            'direction': direction,
            'sl': sl,
            'tp': tp,
            'atr': atr
        })

    # Exit trades
    for trade in trades:
        exit_bar = None
        exit_price = None
        exit_reason = None

        for j in range(trade['entry_bar'] + 1, min(trade['entry_bar'] + params['max_hold_bars'], len(df))):
            bar = df.iloc[j]

            if trade['direction'] == 'LONG':
                if bar['low'] <= trade['sl']:
                    exit_bar = j
                    exit_price = trade['sl']
                    exit_reason = 'SL'
                    break
                elif bar['high'] >= trade['tp']:
                    exit_bar = j
                    exit_price = trade['tp']
                    exit_reason = 'TP'
                    break
            else:
                if bar['high'] >= trade['sl']:
                    exit_bar = j
                    exit_price = trade['sl']
                    exit_reason = 'SL'
                    break
                elif bar['low'] <= trade['tp']:
                    exit_bar = j
                    exit_price = trade['tp']
                    exit_reason = 'TP'
                    break

        if exit_bar is None:
            exit_bar = min(trade['entry_bar'] + params['max_hold_bars'], len(df) - 1)
            exit_price = df.iloc[exit_bar]['close']
            exit_reason = 'TIME'

        if trade['direction'] == 'LONG':
            pnl_pct = (exit_price - trade['entry']) / trade['entry'] * 100
        else:
            pnl_pct = (trade['entry'] - exit_price) / trade['entry'] * 100

        pnl_pct -= 0.10

        trade['exit_bar'] = exit_bar
        trade['exit'] = exit_price
        trade['exit_reason'] = exit_reason
        trade['pnl_pct'] = pnl_pct

    if len(trades) < 10:
        return None

    # Calculate metrics
    df_trades = pd.DataFrame(trades)
    df_trades['cumulative_pnl'] = df_trades['pnl_pct'].cumsum()
    df_trades['equity'] = 100 + df_trades['cumulative_pnl']
    df_trades['running_max'] = df_trades['equity'].cummax()
    df_trades['drawdown'] = df_trades['equity'] - df_trades['running_max']
    df_trades['drawdown_pct'] = df_trades['drawdown'] / df_trades['running_max'] * 100

    final_return = df_trades['cumulative_pnl'].iloc[-1]
    max_dd = df_trades['drawdown_pct'].min()
    return_dd = final_return / abs(max_dd) if max_dd != 0 else 0
    win_rate = (df_trades['pnl_pct'] > 0).sum() / len(df_trades) * 100
    tp_rate = (df_trades['exit_reason'] == 'TP').sum() / len(df_trades) * 100

    # Outlier dependency
    top5_pnl = df_trades.nlargest(5, 'pnl_pct')['pnl_pct'].sum()
    top5_dependency = (top5_pnl / final_return * 100) if final_return > 0 else 0

    return {
        'variant': variant_name,
        'trades': len(df_trades),
        'return': final_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'top5_dependency': top5_dependency,
        'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean(),
        'avg_loss': df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean(),
    }

# Load data
print("="*100)
print("MOODENG ATR LIMIT - STRATEGY IMPROVEMENT TESTING")
print("="*100)

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Load original trades for outlier analysis
trades_orig = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_trades.csv')
trades_orig['entry_timestamp'] = pd.to_datetime(trades_orig['entry_timestamp'])
trades_orig['exit_timestamp'] = pd.to_datetime(trades_orig['exit_timestamp'])

# Analyze outliers first
outliers, normal = analyze_outliers(trades_orig)

# Base parameters (best from quick test)
base_params = {
    'atr_expansion_mult': 1.3,
    'atr_lookback': 20,
    'ema_distance_max': 3.0,
    'limit_offset_pct': 1.0,
    'sl_atr_mult': 2.0,
    'tp_atr_mult': 6.0,
    'max_wait_bars': 3,
    'max_hold_bars': 200,
}

print("\n" + "="*100)
print("TESTING IMPROVEMENT VARIANTS")
print("="*100)

variants = []

# Baseline
baseline = backtest_improved(df, 'BASELINE', base_params, {})
variants.append(baseline)

# 1. RSI momentum filter
rsi_result = backtest_improved(df, 'RSI_50', base_params, {
    'rsi_filter': 50
})
variants.append(rsi_result)

rsi_result2 = backtest_improved(df, 'RSI_55', base_params, {
    'rsi_filter': 55
})
variants.append(rsi_result2)

# 2. Session time filter (test Asia/EU like DOGE)
session_result = backtest_improved(df, 'SESSION_ASIA_EU', base_params, {
    'session_filter': list(range(7, 15))  # 07:00-14:00 UTC
})
variants.append(session_result)

# 3. ATR regime filter (avoid dead zones)
regime_result = backtest_improved(df, 'ATR_REGIME_1.0', base_params, {
    'atr_regime_filter': 1.0  # Only trade when ATR >= average
})
variants.append(regime_result)

regime_result2 = backtest_improved(df, 'ATR_REGIME_0.8', base_params, {
    'atr_regime_filter': 0.8  # Less strict
})
variants.append(regime_result2)

# 4. Max ATR cap (avoid extreme volatility)
cap_result = backtest_improved(df, 'MAX_ATR_2.0x', base_params, {
    'max_atr_cap': 2.0  # Skip signals when ATR > 2x average
})
variants.append(cap_result)

# 5. Adaptive TP (lower TP during extreme ATR)
adaptive_result = backtest_improved(df, 'ADAPTIVE_TP', base_params, {
    'adaptive_tp': {
        'threshold': 2.0,  # If ATR > 2x average
        'low_tp': 4.0      # Use 4x TP instead of 6x
    }
})
variants.append(adaptive_result)

# 6. Combined best filters
combo1 = backtest_improved(df, 'COMBO: RSI+REGIME', base_params, {
    'rsi_filter': 50,
    'atr_regime_filter': 0.8
})
variants.append(combo1)

combo2 = backtest_improved(df, 'COMBO: SESSION+ADAPTIVE', base_params, {
    'session_filter': list(range(7, 15)),
    'adaptive_tp': {'threshold': 2.0, 'low_tp': 4.0}
})
variants.append(combo2)

combo3 = backtest_improved(df, 'COMBO: CAP+RSI+REGIME', base_params, {
    'max_atr_cap': 2.5,
    'rsi_filter': 50,
    'atr_regime_filter': 0.8
})
variants.append(combo3)

# Results
results_df = pd.DataFrame([v for v in variants if v is not None])
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "="*100)
print("IMPROVEMENT RESULTS")
print("="*100)
print(f"\n{'Variant':<25} {'Trades':>7} {'Return':>8} {'Max DD':>8} {'R/DD':>7} {'Win%':>6} {'TP%':>6} {'Top5%':>7}")
print("-"*100)

for idx, row in results_df.iterrows():
    emoji = ""
    if row['top5_dependency'] < 60:
        emoji = "🟢"  # LOW dependency
    elif row['top5_dependency'] < 75:
        emoji = "🟡"  # MEDIUM
    else:
        emoji = "🔴"  # HIGH

    print(f"{row['variant']:<25} {row['trades']:>7.0f} {row['return']:>7.2f}% {row['max_dd']:>7.2f}% "
          f"{row['return_dd']:>7.2f} {row['win_rate']:>5.1f}% {row['tp_rate']:>5.1f}% "
          f"{emoji} {row['top5_dependency']:>5.1f}%")

# Best variant
best = results_df.iloc[0]

print("\n" + "="*100)
print("🏆 BEST IMPROVEMENT")
print("="*100)
print(f"\nVariant: {best['variant']}")
print(f"\nResults:")
print(f"  Trades:          {best['trades']:.0f}")
print(f"  Return:          {best['return']:+.2f}%")
print(f"  Max Drawdown:    {best['max_dd']:.2f}%")
print(f"  Return/DD:       {best['return_dd']:.2f}x")
print(f"  Win Rate:        {best['win_rate']:.1f}%")
print(f"  TP Rate:         {best['tp_rate']:.1f}%")
print(f"  Top5 Dependency: {best['top5_dependency']:.1f}%")

print(f"\nvs BASELINE:")
baseline_row = results_df[results_df['variant'] == 'BASELINE'].iloc[0]
print(f"  Return/DD:       {best['return_dd']:.2f}x vs {baseline_row['return_dd']:.2f}x ({(best['return_dd'] / baseline_row['return_dd'] - 1) * 100:+.1f}%)")
print(f"  Win Rate:        {best['win_rate']:.1f}% vs {baseline_row['win_rate']:.1f}% ({best['win_rate'] - baseline_row['win_rate']:+.1f}pp)")
print(f"  Top5 Dependency: {best['top5_dependency']:.1f}% vs {baseline_row['top5_dependency']:.1f}% ({best['top5_dependency'] - baseline_row['top5_dependency']:.1f}pp)")

# Save results
results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_improvement_results.csv', index=False)
print(f"\n💾 Saved: trading/results/moodeng_improvement_results.csv")

print("\n" + "="*100)
print("🎯 RECOMMENDATIONS")
print("="*100)

if best['top5_dependency'] < 70:
    print(f"\n✅ SUCCESS! Top5 dependency reduced to {best['top5_dependency']:.1f}% (<70%)")
    print(f"   This variant distributes profits more evenly across trades")
    print(f"   Proceed with high-resolution optimization using these filters")
elif best['return_dd'] > baseline_row['return_dd']:
    print(f"\n⚠️  PARTIAL SUCCESS: R/DD improved to {best['return_dd']:.2f}x")
    print(f"   But Top5 dependency still high ({best['top5_dependency']:.1f}%)")
    print(f"   Strategy remains lottery-style but with better risk-adjusted returns")
else:
    print(f"\n❌ NO IMPROVEMENT: All filters either reduce performance or maintain lottery-style")
    print(f"   This may be inherent to MOODENG's volatility profile")
    print(f"   Recommendation: Accept lottery-style nature or test different strategy entirely")
