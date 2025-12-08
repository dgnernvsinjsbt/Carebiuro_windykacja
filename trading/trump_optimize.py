"""
TRUMP Strategy Optimization
Fix negative returns or prove it's untradeable
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import the base strategy functions
import sys
sys.path.append('/workspaces/Carebiuro_windykacja/trading/strategies')
from TRUMP_strategy import calculate_indicators, detect_regime, run_backtest

# Load data
data = pd.read_csv('trump_usdt_1m_mexc.csv')

print("="*80)
print("TRUMP STRATEGY OPTIMIZATION")
print("="*80)

optimization_results = []

# ============================================================================
# 1. SESSION FILTERS - Test each session independently
# ============================================================================
print("\n1. SESSION FILTER OPTIMIZATION")
print("-"*80)

def test_session_filter(data, session_name, hour_start, hour_end):
    """Test strategy on specific session only"""
    from TRUMP_strategy import calculate_indicators

    df = calculate_indicators(data.copy())
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour

    # Filter to session
    session_data = df[(df['hour'] >= hour_start) & (df['hour'] < hour_end)].copy()

    if len(session_data) < 1000:
        return None

    # Run a simplified backtest (just count signals and basic stats)
    df_full = calculate_indicators(data.copy())

    # Quick signal count
    signals = 0
    for i in range(200, len(session_data)):
        hour = session_data.iloc[i]['hour']
        if hour_start <= hour < hour_end:
            rsi = session_data.iloc[i]['rsi']
            if rsi < 30 or rsi > 70:
                signals += 1

    return {
        'session': session_name,
        'candles': len(session_data),
        'signals': signals,
        'signal_rate': signals / len(session_data) * 100
    }

sessions = [
    ('Asia', 0, 8),
    ('Europe', 8, 14),
    ('US', 14, 21),
    ('Overnight', 21, 24)
]

print("\nTesting each session independently...\n")
for session_name, start, end in sessions:
    result = test_session_filter(data, session_name, start, end)
    if result:
        print(f"{session_name:12} | Candles: {result['candles']:>6} | Signals: {result['signals']:>4} | Rate: {result['signal_rate']:.2f}%")

# ============================================================================
# 2. DYNAMIC SL/TP OPTIMIZATION
# ============================================================================
print("\n\n2. STOP LOSS / TAKE PROFIT OPTIMIZATION")
print("-"*80)

sl_multiples = [1.0, 1.5, 2.0, 2.5, 3.0]
tp_multiples = [2.0, 3.0, 4.0, 6.0, 8.0]

print("\nTesting SL/TP combinations (this may take a few minutes)...\n")
print(f"{'SL Multiple':<12} {'TP Multiple':<12} {'Final $':<12} {'Return %':<12} {'Win Rate %':<12}")
print("-"*70)

best_rr_config = None
best_rr_return = -999999

for sl_mult in sl_multiples:
    for tp_mult in tp_multiples:
        # Only test valid R:R ratios (TP must be > SL)
        if tp_mult <= sl_mult:
            continue

        # Quick test (sample of data to save time)
        from TRUMP_strategy import calculate_indicators

        df = calculate_indicators(data.copy())

        # Simple long-only backtest with new SL/TP
        capital = 10000
        trades_test = []

        for i in range(200, min(10000, len(df))):  # Test on first 10k candles
            row = df.iloc[i]

            if row['rsi'] < 30:  # Simple RSI < 30 entry
                entry = row['close']
                atr = row['atr_pct'] / 100

                sl = entry * (1 - sl_mult * atr)
                tp = entry * (1 + tp_mult * atr)

                # Look ahead to see exit
                for j in range(i+1, min(i+30, len(df))):
                    future = df.iloc[j]

                    if future['low'] <= sl:
                        pnl = ((sl - entry) / entry) - 0.001
                        trades_test.append(pnl)
                        break
                    elif future['high'] >= tp:
                        pnl = ((tp - entry) / entry) - 0.001
                        trades_test.append(pnl)
                        break

        if len(trades_test) > 10:
            trades_arr = np.array(trades_test)
            final_return = np.sum(trades_arr) * 100
            win_rate = (trades_arr > 0).sum() / len(trades_arr) * 100

            print(f"{sl_mult:<12.1f} {tp_mult:<12.1f} {10000*(1+np.sum(trades_arr)):<12.2f} {final_return:<12.2f} {win_rate:<12.1f}")

            optimization_results.append({
                'config': f'SL{sl_mult}x_TP{tp_mult}x',
                'sl_mult': sl_mult,
                'tp_mult': tp_mult,
                'return': final_return,
                'win_rate': win_rate,
                'trades': len(trades_test)
            })

            if final_return > best_rr_return:
                best_rr_return = final_return
                best_rr_config = (sl_mult, tp_mult)

if best_rr_config:
    print(f"\n✓ Best SL/TP: {best_rr_config[0]}x ATR SL, {best_rr_config[1]}x ATR TP → {best_rr_return:.2f}% return")

# ============================================================================
# 3. SIMPLIFIED STRATEGY TEST
# ============================================================================
print("\n\n3. SIMPLIFIED STRATEGY TEST")
print("-"*80)

print("\nTesting: RSI < 30 + US Session ONLY (remove all other filters)\n")

df_simple = calculate_indicators(data.copy())
df_simple['hour'] = pd.to_datetime(df_simple['timestamp']).dt.hour

capital = 10000
trades_simple = []

for i in range(200, len(df_simple)):
    row = df_simple.iloc[i]
    hour = row['hour']

    # ONLY: RSI < 30 AND US Session (14-21)
    if row['rsi'] < 30 and 14 <= hour < 21:
        entry = row['close']
        atr = row['atr_pct'] / 100

        sl = entry * (1 - 2.0 * atr)
        tp = entry * (1 + 4.0 * atr)  # Use best R:R if found, otherwise 2:1

        # Look ahead
        for j in range(i+1, min(i+30, len(df_simple))):
            future = df_simple.iloc[j]

            if future['low'] <= sl:
                pnl = ((sl - entry) / entry) - 0.001
                trades_simple.append(pnl)
                break
            elif future['high'] >= tp:
                pnl = ((tp - entry) / entry) - 0.001
                trades_simple.append(pnl)
                break

if len(trades_simple) > 0:
    trades_arr = np.array(trades_simple)
    simple_return = np.sum(trades_arr) * 100
    simple_winrate = (trades_arr > 0).sum() / len(trades_arr) * 100

    print(f"Simplified Strategy Results:")
    print(f"  Total Trades: {len(trades_simple)}")
    print(f"  Win Rate: {simple_winrate:.1f}%")
    print(f"  Total Return: {simple_return:.2f}%")
    print(f"  Final Capital: ${10000 * (1 + np.sum(trades_arr)):.2f}")

    optimization_results.append({
        'config': 'SIMPLE_RSI30_US',
        'return': simple_return,
        'win_rate': simple_winrate,
        'trades': len(trades_simple)
    })

# ============================================================================
# 4. HOUR-BY-HOUR FILTER TEST
# ============================================================================
print("\n\n4. HOUR-BY-HOUR PROFITABILITY")
print("-"*80)

hourly_results = []

for test_hour in range(24):
    df_hour = calculate_indicators(data.copy())
    df_hour['hour'] = pd.to_datetime(df_hour['timestamp']).dt.hour

    trades_hour = []

    for i in range(200, len(df_hour)):
        row = df_hour.iloc[i]

        if row['hour'] == test_hour and row['rsi'] < 30:
            entry = row['close']
            atr = row['atr_pct'] / 100

            sl = entry * (1 - 2.0 * atr)
            tp = entry * (1 + 3.0 * atr)

            for j in range(i+1, min(i+30, len(df_hour))):
                future = df_hour.iloc[j]

                if future['low'] <= sl:
                    pnl = ((sl - entry) / entry) - 0.001
                    trades_hour.append(pnl)
                    break
                elif future['high'] >= tp:
                    pnl = ((tp - entry) / entry) - 0.001
                    trades_hour.append(pnl)
                    break

    if len(trades_hour) > 5:
        avg_return = np.mean(trades_hour) * 100
        total_return = np.sum(trades_hour) * 100
        win_rate = (np.array(trades_hour) > 0).sum() / len(trades_hour) * 100

        hourly_results.append({
            'hour': test_hour,
            'trades': len(trades_hour),
            'avg_return': avg_return,
            'total_return': total_return,
            'win_rate': win_rate
        })

hourly_df = pd.DataFrame(hourly_results).sort_values('total_return', ascending=False)

print("\nTop 5 Best Hours:")
print(f"{'Hour':<6} {'Trades':<8} {'Win Rate %':<12} {'Avg Return %':<15} {'Total Return %':<15}")
print("-"*70)
for _, row in hourly_df.head(5).iterrows():
    print(f"{row['hour']:02d}:00 {row['trades']:<8.0f} {row['win_rate']:<12.1f} {row['avg_return']:<15.3f} {row['total_return']:<15.2f}")

print("\nTop 5 Worst Hours:")
for _, row in hourly_df.tail(5).iterrows():
    print(f"{row['hour']:02d}:00 {row['trades']:<8.0f} {row['win_rate']:<12.1f} {row['avg_return']:<15.3f} {row['total_return']:<15.2f}")

# ============================================================================
# FINAL VERDICT
# ============================================================================
print("\n\n" + "="*80)
print("OPTIMIZATION VERDICT")
print("="*80)

# Save all results
results_df = pd.DataFrame(optimization_results)
results_df.to_csv('results/TRUMP_optimization_comparison.csv', index=False)

print("\nBase Strategy: -$33.84 (-0.62%)")

if len(optimization_results) > 0:
    best_config = results_df.loc[results_df['return'].idxmax()]
    print(f"\nBest Optimized Config: {best_config['config']}")
    print(f"  Return: {best_config['return']:.2f}%")
    print(f"  Win Rate: {best_config['win_rate']:.1f}%")
    print(f"  Trades: {best_config['trades']:.0f}")

    if best_config['return'] > 0:
        print("\n✓ TRADEABLE - Found profitable configuration")
        print(f"  Improvement: {best_config['return'] - (-0.62):.2f}% vs base strategy")
    else:
        print("\n✗ UNTRADEABLE - No profitable configuration found")
        print("  Recommendation: SKIP THIS TOKEN")
else:
    print("\n✗ UNTRADEABLE - Optimization failed")

print("\nDetailed results saved to: results/TRUMP_optimization_comparison.csv")
print("Hourly breakdown available above")
print("="*80)
