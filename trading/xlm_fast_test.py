"""
XLM/USDT Fast Vectorized Test
Much faster implementation
"""

import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Loaded {len(df):,} candles\n")

# Calculate indicators
print("Calculating indicators...")
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
df['rsi'] = 100 - (100 / (1 + gain / loss))

df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

# Test Strategy 1: EMA20 Pullback with tight stops
print("\nTesting strategies...\n")

def test_strategy(df, name, entry_condition, sl_mult, tp_mult):
    """Vectorized backtest - much faster"""
    entries = entry_condition.fillna(False).astype(bool)

    results = []
    for idx in np.where(entries)[0]:
        if idx < 250 or idx >= len(df) - 1:
            continue

        entry_price = df.iloc[idx]['close']
        sl_price = entry_price - sl_mult * df.iloc[idx]['atr']
        tp_price = entry_price + tp_mult * df.iloc[idx]['atr']

        # Check next 100 bars for exit
        for j in range(idx + 1, min(idx + 100, len(df))):
            if df.iloc[j]['low'] <= sl_price:
                pnl_pct = ((sl_price - entry_price) / entry_price) * 10 - 0.02
                results.append({'pnl': pnl_pct, 'reason': 'SL'})
                break
            elif df.iloc[j]['high'] >= tp_price:
                pnl_pct = ((tp_price - entry_price) / entry_price) * 10 - 0.02
                results.append({'pnl': pnl_pct, 'reason': 'TP'})
                break

    if len(results) < 30:
        return None

    results_df = pd.DataFrame(results)

    # Calculate equity curve
    equity = 1000
    equity_curve = [equity]
    peak = equity
    max_dd = 0

    for pnl_pct in results_df['pnl']:
        equity += equity * pnl_pct
        equity_curve.append(equity)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

    total = len(results_df)
    winners = len(results_df[results_df['pnl'] > 0])
    win_rate = winners / total * 100
    total_pnl = (equity - 1000) / 1000 * 100
    rr_ratio = (equity - 1000) / (max_dd * peak) if max_dd > 0 else 0

    return {
        'strategy': name,
        'sl': sl_mult,
        'tp': tp_mult,
        'trades': total,
        'win_rate': win_rate,
        'pnl': total_pnl,
        'max_dd': max_dd * 100,
        'rr': rr_ratio,
        'final_equity': equity
    }

# Define strategies
strategies = []

# 1. EMA20 Pullback
uptrend = df['close'] > df['ema_20']
pullback = (df['low'] <= df['ema_20']) & (df['close'] > df['ema_20'])
rsi_ok = (df['rsi'] > 40) & (df['rsi'] < 60)
strategies.append(('EMA20_Pullback', uptrend & pullback & rsi_ok))

# 2. BB Bounce from Lower
touches_bb = df['low'] <= df['bb_lower']
bounces = df['close'] > df['bb_lower']
rsi_low = (df['rsi'] > 25) & (df['rsi'] < 35)
strategies.append(('BB_Bounce', touches_bb & bounces & rsi_low))

# 3. RSI Oversold
oversold = df['rsi'] < 30
rsi_rising = df['rsi'] > df['rsi'].shift(1)
green = df['close'] > df['open']
strategies.append(('RSI_Oversold', oversold & rsi_rising & green))

# 4. Conservative: Only strong uptrends
strong_up = (df['close'] > df['ema_20']) & (df['ema_20'] > df['ema_50'])
pullback_to_ema = (df['low'] <= df['ema_20']) & (df['close'] > df['ema_20'])
not_overbought = df['rsi'] < 65
strategies.append(('Conservative_Uptrend', strong_up & pullback_to_ema & not_overbought))

# Test all combinations
results = []
for name, condition in strategies:
    for sl in [1.5, 2.0, 2.5, 3.0]:
        for tp in [3.0, 4.0, 5.0, 6.0]:
            if tp >= sl * 2:  # Ensure R:R is at least 2:1
                result = test_strategy(df, name, condition, sl, tp)
                if result:
                    results.append(result)
                    print(f"✓ {name} (SL:{sl}, TP:{tp}): {result['trades']} trades, {result['win_rate']:.1f}% WR, {result['pnl']:.1f}% PnL, R:R {result['rr']:.2f}")

# Sort and display
results_df = pd.DataFrame(results)
if len(results_df) > 0:
    results_df = results_df.sort_values('rr', ascending=False)
    results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_master_results.csv', index=False)

    print("\n" + "=" * 80)
    print("TOP 15 STRATEGIES BY R:R RATIO")
    print("=" * 80)
    print(results_df.head(15).to_string(index=False))

    # Winners
    winners = results_df[(results_df['rr'] >= 2.0) & (results_df['win_rate'] >= 50.0)]
    if len(winners) > 0:
        print(f"\n✅ WINNING STRATEGIES ({len(winners)}):")
        print(winners.to_string(index=False))
        winners.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_winning_strategies.csv', index=False)
    else:
        print("\n⚠️  No strategies met winning criteria (R:R >= 2.0, WR >= 50%)")
else:
    print("\n❌ No strategies generated enough trades")
