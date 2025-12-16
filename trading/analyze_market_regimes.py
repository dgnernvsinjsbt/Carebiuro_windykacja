"""
Deep Analysis: What Makes This Strategy Work vs Fail?
Compare market conditions in losing months (Jun-Sep) vs winning months (Oct-Dec)
"""
import pandas as pd
import numpy as np

def analyze_month(df, month_name):
    """Extract market condition metrics for a month"""

    # Basic indicators
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    # Calculate SMA for trend
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # Price changes
    df['ret_1'] = df['close'].pct_change() * 100
    df['ret_4h'] = (df['close'] / df['close'].shift(16) - 1) * 100  # 16 bars = 4 hours

    # Drop NaN
    df = df.dropna().copy()

    if len(df) < 100:
        return None

    # === VOLATILITY METRICS ===
    avg_atr = df['atr'].mean()
    atr_std = df['atr'].std()
    avg_atr_pct = (df['atr'] / df['close'] * 100).mean()

    # Range expansion (how often ATR > 1.5x rolling avg)
    df['atr_ma20'] = df['atr'].rolling(20).mean()
    expansion_pct = ((df['atr'] > df['atr_ma20'] * 1.5).sum() / len(df) * 100)

    # === TREND METRICS ===
    # Price vs SMA
    above_sma50 = (df['close'] > df['sma_50']).sum() / len(df) * 100
    above_sma200 = (df['close'] > df['sma_200']).sum() / len(df) * 100

    # Directional consistency (how often daily moves are in same direction)
    up_bars = (df['close'] > df['open']).sum()
    down_bars = (df['close'] < df['open']).sum()
    directional_bias = abs(up_bars - down_bars) / len(df) * 100

    # Trend strength (SMA slope)
    sma50_slope = (df['sma_50'].iloc[-1] - df['sma_50'].iloc[0]) / df['sma_50'].iloc[0] * 100

    # === RSI BEHAVIOR ===
    rsi_mean = df['rsi'].mean()
    rsi_std = df['rsi'].std()

    # Time spent in extremes
    rsi_below_35 = (df['rsi'] < 35).sum() / len(df) * 100
    rsi_above_65 = (df['rsi'] > 65).sum() / len(df) * 100
    rsi_middle = ((df['rsi'] >= 40) & (df['rsi'] <= 60)).sum() / len(df) * 100

    # RSI crossovers (signal frequency)
    rsi_cross_35_up = ((df['rsi'].shift(1) < 35) & (df['rsi'] >= 35)).sum()
    rsi_cross_65_down = ((df['rsi'].shift(1) > 65) & (df['rsi'] <= 65)).sum()
    total_signals = rsi_cross_35_up + rsi_cross_65_down
    signals_per_day = total_signals / (len(df) / 96)  # 96 bars per day

    # === MOMENTUM METRICS ===
    avg_ret_1 = df['ret_1'].mean()
    avg_abs_ret_1 = df['ret_1'].abs().mean()
    avg_ret_4h = df['ret_4h'].mean()
    avg_abs_ret_4h = df['ret_4h'].abs().mean()

    # Positive momentum filter quality
    ret20_positive = (df['ret_20'] > 0).sum() / len(df) * 100

    # === PRICE ACTION ===
    # Move quality after RSI signals
    df['signal'] = 0
    df.loc[(df['rsi'].shift(1) < 35) & (df['rsi'] >= 35), 'signal'] = 1  # LONG
    df.loc[(df['rsi'].shift(1) > 65) & (df['rsi'] <= 65), 'signal'] = -1  # SHORT

    # Calculate forward returns after signals (next 12 bars = 3 hours)
    long_signals = df[df['signal'] == 1].copy()
    short_signals = df[df['signal'] == -1].copy()

    if len(long_signals) > 0:
        long_fwd_returns = []
        for idx in long_signals.index:
            if idx + 12 < len(df):
                fwd_ret = (df.loc[idx + 12, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                long_fwd_returns.append(fwd_ret)
        avg_long_fwd_3h = np.mean(long_fwd_returns) if long_fwd_returns else 0
    else:
        avg_long_fwd_3h = 0

    if len(short_signals) > 0:
        short_fwd_returns = []
        for idx in short_signals.index:
            if idx + 12 < len(df):
                fwd_ret = (df.loc[idx, 'close'] - df.loc[idx + 12, 'close']) / df.loc[idx, 'close'] * 100
                short_fwd_returns.append(fwd_ret)
        avg_short_fwd_3h = np.mean(short_fwd_returns) if short_fwd_returns else 0
    else:
        avg_short_fwd_3h = 0

    # === CHOPPINESS ===
    # How often price reverses (whipsaw indicator)
    df['direction_change'] = (df['ret_1'] * df['ret_1'].shift(1) < 0).astype(int)
    whipsaw_rate = df['direction_change'].sum() / len(df) * 100

    return {
        'month': month_name,

        # Volatility
        'avg_atr': avg_atr,
        'avg_atr_pct': avg_atr_pct,
        'atr_std': atr_std,
        'expansion_pct': expansion_pct,

        # Trend
        'above_sma50_pct': above_sma50,
        'above_sma200_pct': above_sma200,
        'directional_bias': directional_bias,
        'sma50_slope': sma50_slope,

        # RSI
        'rsi_mean': rsi_mean,
        'rsi_std': rsi_std,
        'rsi_below_35_pct': rsi_below_35,
        'rsi_above_65_pct': rsi_above_65,
        'rsi_middle_pct': rsi_middle,
        'signals_per_day': signals_per_day,

        # Momentum
        'avg_ret_1': avg_ret_1,
        'avg_abs_ret_1': avg_abs_ret_1,
        'avg_ret_4h': avg_ret_4h,
        'avg_abs_ret_4h': avg_abs_ret_4h,
        'ret20_positive_pct': ret20_positive,

        # Signal Quality
        'avg_long_fwd_3h': avg_long_fwd_3h,
        'avg_short_fwd_3h': avg_short_fwd_3h,
        'avg_signal_fwd_3h': (avg_long_fwd_3h + avg_short_fwd_3h) / 2,

        # Choppiness
        'whipsaw_rate': whipsaw_rate,
    }

print('=' * 140)
print('MARKET REGIME ANALYSIS: What Makes The Strategy Work?')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv', 'LOSER'),
    ('July', 'melania_july_2025_15m.csv', 'LOSER'),
    ('August', 'melania_august_2025_15m.csv', 'LOSER'),
    ('September', 'melania_september_2025_15m.csv', 'LOSER'),
    ('October', 'melania_october_2025_15m.csv', 'WINNER'),
    ('November', 'melania_november_2025_15m.csv', 'WINNER'),
    ('December', 'melania_december_2025_15m.csv', 'WINNER'),
]

results = []

for month_name, filename, category in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = analyze_month(df.copy(), month_name)
    if result:
        result['category'] = category
        results.append(result)
        print(f'✅ Analyzed {month_name}')

df_results = pd.DataFrame(results)

# Split into winners and losers
losers = df_results[df_results['category'] == 'LOSER']
winners = df_results[df_results['category'] == 'WINNER']

print('\n' + '=' * 140)
print('KEY DIFFERENTIATORS: LOSERS (Jun-Sep) vs WINNERS (Oct-Dec)')
print('=' * 140)

# Compare averages
metrics = [
    ('avg_atr_pct', 'ATR % of Price', '%', False),
    ('expansion_pct', 'ATR Expansion Events', '%', False),
    ('directional_bias', 'Directional Bias', '%', False),
    ('sma50_slope', 'SMA50 Slope (trend)', '%', False),
    ('rsi_std', 'RSI Volatility', '', False),
    ('rsi_middle_pct', 'Time in RSI 40-60', '%', True),
    ('signals_per_day', 'Signals Per Day', '', True),
    ('avg_abs_ret_4h', 'Avg 4h Move Size', '%', False),
    ('ret20_positive_pct', 'Bars with ret_20>0', '%', False),
    ('avg_signal_fwd_3h', 'Avg Signal Follow-Through', '%', False),
    ('whipsaw_rate', 'Whipsaw Rate', '%', True),
]

print(f"\n{'Metric':<30} {'Losers':<12} {'Winners':<12} {'Diff':<12} {'Better?'}")
print('-' * 140)

key_findings = []

for metric, label, unit, lower_is_better in metrics:
    loser_avg = losers[metric].mean()
    winner_avg = winners[metric].mean()
    diff = winner_avg - loser_avg
    diff_pct = (diff / loser_avg * 100) if loser_avg != 0 else 0

    if lower_is_better:
        better = '✅ WINNERS' if winner_avg < loser_avg else '❌ LOSERS'
        significance = abs(diff_pct)
    else:
        better = '✅ WINNERS' if winner_avg > loser_avg else '❌ LOSERS'
        significance = abs(diff_pct)

    print(f"{label:<30} {loser_avg:>10.2f}{unit:>2} {winner_avg:>10.2f}{unit:>2} "
          f"{diff:>+10.2f}{unit:>2} {better}")

    if significance > 20:  # More than 20% difference
        key_findings.append({
            'metric': label,
            'loser_avg': loser_avg,
            'winner_avg': winner_avg,
            'diff_pct': diff_pct,
            'better': better
        })

# Print key findings
print('\n' + '=' * 140)
print('🔍 KEY FINDINGS (>20% difference)')
print('=' * 140)

for i, finding in enumerate(sorted(key_findings, key=lambda x: abs(x['diff_pct']), reverse=True), 1):
    print(f"\n{i}. {finding['metric']}:")
    print(f"   Losers:  {finding['loser_avg']:.2f}")
    print(f"   Winners: {finding['winner_avg']:.2f}")
    print(f"   Change:  {finding['diff_pct']:+.1f}%")
    print(f"   {finding['better']}")

# Save detailed results
df_results.to_csv('market_regime_analysis.csv', index=False)
print(f'\n💾 Saved detailed analysis to: market_regime_analysis.csv')

# MONTHLY DETAIL TABLE
print('\n' + '=' * 140)
print('MONTHLY DETAIL')
print('=' * 140)
print(f"\n{'Month':<12} {'Cat':<7} {'ATR%':<8} {'Trend':<8} {'Signals/d':<10} {'Fwd 3h%':<10} {'Whipsaw%':<10}")
print('-' * 140)

for _, row in df_results.iterrows():
    print(f"{row['month']:<12} {row['category']:<7} {row['avg_atr_pct']:>7.2f}% "
          f"{row['sma50_slope']:>+7.1f}% {row['signals_per_day']:>9.1f} "
          f"{row['avg_signal_fwd_3h']:>+9.2f}% {row['whipsaw_rate']:>9.1f}%")

print('=' * 140)
