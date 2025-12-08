"""XLM/USDT Multi-Strategy Quick Test"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')

# Indicators
df['atr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))).rolling(14).mean()
df['ema8'] = df['close'].ewm(8).mean()
df['ema20'] = df['close'].ewm(20).mean()
df['ema50'] = df['close'].ewm(50).mean()
delta = df['close'].diff()
df['rsi'] = 100 - (100 / (1 + (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()))
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

def test_strategy(signal, name, sl_mult, tp_mult):
    """Quick test"""
    equity, peak, max_dd, wins, total = 1000, 1000, 0, 0, 0

    for idx in np.where(signal)[0][::5][:150]:  # Sample 150 trades max
        if idx < 250 or idx >= len(df) - 40:
            continue
        entry = df.iloc[idx]['close']
        sl = entry - sl_mult * df.iloc[idx]['atr']
        tp = entry + tp_mult * df.iloc[idx]['atr']

        for j in range(idx + 1, min(idx + 40, len(df))):
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

    if total < 20:
        return None

    wr = wins / total * 100
    pnl = (equity - 1000) / 1000 * 100
    rr = (equity - 1000) / (max_dd * peak) if max_dd > 0 else 0

    return {'name': name, 'sl': sl_mult, 'tp': tp_mult, 'trades': total, 'wr': wr, 'pnl': pnl, 'dd': max_dd*100, 'rr': rr}

# Define strategies
strategies = []

# 1. EMA8 Pullback (tighter)
strategies.append(('EMA8_Pullback', ((df['low'] <= df['ema8']) & (df['close'] > df['ema8']) & (df['rsi'] > 45)).fillna(False).values))

# 2. EMA20 Pullback
strategies.append(('EMA20_Pullback', ((df['low'] <= df['ema20']) & (df['close'] > df['ema20']) & (df['rsi'] > 40)).fillna(False).values))

# 3. BB Bounce
strategies.append(('BB_Bounce', ((df['low'] <= df['bb_lower']) & (df['close'] > df['bb_lower']) & (df['rsi'] > 25)).fillna(False).values))

# 4. RSI Oversold
strategies.append(('RSI_Oversold', ((df['rsi'] < 30) & (df['rsi'] > df['rsi'].shift(1)) & (df['close'] > df['open'])).fillna(False).values))

# 5. Strong Uptrend
strategies.append(('Strong_Uptrend', ((df['close'] > df['ema20']) & (df['ema20'] > df['ema50']) & (df['low'] <= df['ema8']) & (df['close'] > df['ema8'])).fillna(False).values))

# 6. Conservative
strategies.append(('Conservative', ((df['close'] > df['ema20']) & (df['close'] > df['ema50']) & (df['low'] <= df['ema20']) & (df['rsi'] > 50) & (df['rsi'] < 60)).fillna(False).values))

# Test all
results = []
for name, signal in strategies:
    for sl in [1.5, 2.0, 2.5, 3.0]:
        for tp in [3.0, 4.0, 5.0, 6.0]:
            if tp >= sl * 2:
                r = test_strategy(signal, name, sl, tp)
                if r:
                    results.append(r)

# Sort and display
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr', ascending=False)

print("\nXLM/USDT STRATEGY TEST RESULTS")
print("=" * 100)
print(f"Tested {len(results_df)} strategy variations\n")

print("TOP 20 BY R:R RATIO:")
print(results_df.head(20).to_string(index=False))

winners = results_df[(results_df['rr'] >= 2.0) & (results_df['wr'] >= 50.0)]
if len(winners) > 0:
    print(f"\n✅ WINNING STRATEGIES ({len(winners)}):")
    print(winners.to_string(index=False))
else:
    print("\n❌ NO WINNING STRATEGIES (R:R >= 2.0, WR >= 50%)")
    print("\nBest by different metrics:")
    print("\nBest Win Rate:")
    print(results_df.nlargest(3, 'wr')[['name', 'sl', 'tp', 'trades', 'wr', 'pnl', 'rr']].to_string(index=False))
    print("\nBest P&L:")
    print(results_df.nlargest(3, 'pnl')[['name', 'sl', 'tp', 'trades', 'wr', 'pnl', 'rr']].to_string(index=False))

# Save
results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_master_results.csv', index=False)
print(f"\n✓ Saved results to results/xlm_master_results.csv")
