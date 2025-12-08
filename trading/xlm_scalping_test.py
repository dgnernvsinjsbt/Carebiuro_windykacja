"""
XLM/USDT Scalping Test
Try very tight stops and quick profits - maybe XLM needs scalping approach
"""
import pandas as pd
import numpy as np

# Load
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')

# Minimal indicators
df['atr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))).rolling(14).mean()
df['ema8'] = df['close'].ewm(8).mean()
df['ema20'] = df['close'].ewm(20).mean()
delta = df['close'].diff()
df['rsi'] = 100 - (100 / (1 + (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()))

def test_scalp(signal, name, sl_mult, tp_mult):
    """Test scalping strategy"""
    equity, peak, max_dd, wins, total = 1000, 1000, 0, 0, 0

    for idx in np.where(signal)[0][::3][:200]:  # More trades, smaller sampling
        if idx < 250 or idx >= len(df) - 20:
            continue
        entry = df.iloc[idx]['close']
        sl = entry - sl_mult * df.iloc[idx]['atr']
        tp = entry + tp_mult * df.iloc[idx]['atr']

        # Check only next 20 bars (faster exits for scalping)
        for j in range(idx + 1, min(idx + 20, len(df))):
            if df.iloc[j]['low'] <= sl:
                pnl_pct = ((sl - entry) / entry) * 10 - 0.02
                equity += equity * pnl_pct
                total += 1
                break
            elif df.iloc[j]['high'] >= tp:
                pnl_pct = ((tp - entry) / entry) * 10 - 0.02
                equity += equity * pnl_pct
                wins += 1
                total += 1
                break

        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

    if total < 30:
        return None

    wr = wins / total * 100
    pnl = (equity - 1000) / 1000 * 100
    rr = (equity - 1000) / (max_dd * peak) if max_dd > 0 else 0

    return {'name': name, 'sl': sl_mult, 'tp': tp_mult, 'trades': total, 'wr': wr, 'pnl': pnl, 'dd': max_dd*100, 'rr': rr}

# Strategies
strategies = [
    ('EMA8_Bounce', ((df['low'] <= df['ema8']) & (df['close'] > df['ema8']) & (df['rsi'] > 45)).fillna(False).values),
    ('EMA20_Bounce', ((df['low'] <= df['ema20']) & (df['close'] > df['ema20']) & (df['rsi'] > 40)).fillna(False).values),
    ('RSI_Oversold', ((df['rsi'] < 35) & (df['rsi'] > df['rsi'].shift(1))).fillna(False).values),
]

results = []

# Test scalping parameters (tight stops, smaller targets)
scalp_configs = [
    (0.5, 1.0),  # 0.5x SL, 1x TP (2:1 R:R)
    (0.5, 1.5),  # 0.5x SL, 1.5x TP (3:1 R:R)
    (1.0, 2.0),  # 1x SL, 2x TP (2:1 R:R)
    (1.0, 2.5),  # 1x SL, 2.5x TP (2.5:1 R:R)
    (1.0, 3.0),  # 1x SL, 3x TP (3:1 R:R)
    (1.5, 3.0),  # 1.5x SL, 3x TP (2:1 R:R)
    (1.5, 4.0),  # 1.5x SL, 4x TP (2.67:1 R:R)
]

for name, signal in strategies:
    for sl, tp in scalp_configs:
        r = test_scalp(signal, name, sl, tp)
        if r:
            results.append(r)

# Display
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr', ascending=False)

print("\nXLM/USDT SCALPING TEST")
print("=" * 100)
print(f"Tested {len(results_df)} configurations\n")

print("TOP 20:")
print(results_df.head(20).to_string(index=False))

winners = results_df[(results_df['rr'] >= 2.0) & (results_df['wr'] >= 50.0)]
if len(winners) > 0:
    print(f"\n✅ WINNING STRATEGIES ({len(winners)}):")
    print(winners.to_string(index=False))
    winners.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_winning_strategies.csv', index=False)
else:
    print("\n❌ NO WINNING STRATEGIES")
    print("\nClosest to target:")
    print(results_df.head(5)[['name', 'sl', 'tp', 'trades', 'wr', 'pnl', 'rr']].to_string(index=False))

results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_master_results.csv', index=False)
print(f"\n✓ Saved to results/xlm_master_results.csv")
