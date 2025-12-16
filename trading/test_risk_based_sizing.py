"""
Test best config with RISK-BASED position sizing
Each trade risks X% of account (1-10%), position size adjusted by SL distance

Formula:
- risk_dollars = equity * (risk_pct / 100)
- sl_distance_pct = abs((entry - sl) / entry) * 100
- position_size = risk_dollars / (sl_distance_pct / 100)
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("Risk-Based Position Sizing: 25/68 | 0.3% | 3.0x SL | 2.0x TP")
print("=" * 80)

# Load combined dataset
df_july = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df_sepdec = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_sepdec = df_sepdec[(df_sepdec['timestamp'] >= '2025-09-15') & (df_sepdec['timestamp'] < '2025-12-08')]

df_july['timestamp'] = pd.to_datetime(df_july['timestamp']).dt.tz_localize(None)
df_sepdec['timestamp'] = pd.to_datetime(df_sepdec['timestamp']).dt.tz_localize(None)

df = pd.concat([df_july, df_sepdec]).sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
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

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0

def backtest_with_risk(df, risk_pct):
    """Backtest with fixed risk % per trade"""
    trades = []
    equity = 100.0

    i = 14
    while i < len(df):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
            i += 1
            continue

        # LONG signal
        if prev_row['rsi'] < RSI_LOW and row['rsi'] >= RSI_LOW:
            signal_price = row['close']
            entry_price = signal_price * (1 + LIMIT_PCT / 100)
            sl_price = entry_price - (row['atr'] * SL_MULT)
            tp_price = entry_price + (row['atr'] * TP_MULT)

            # Calculate position size based on risk
            risk_dollars = equity * (risk_pct / 100)
            sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
            position_size_dollars = risk_dollars / (sl_distance_pct / 100)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['low'] <= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] > RSI_HIGH and bar['rsi'] <= RSI_HIGH:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            # Calculate P&L in dollars
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_before_fees = position_size_dollars * (price_change_pct / 100)

            # Fees: 0.05% on position size (entry + exit)
            fees = position_size_dollars * 0.001
            pnl_dollars = pnl_before_fees - fees

            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_dollars': pnl_dollars,
                'pnl_pct': (pnl_dollars / equity) * 100 if equity > 0 else 0,
                'position_size': position_size_dollars,
                'equity': equity
            })

            i = exit_idx + 1
            continue

        # SHORT signal
        if prev_row['rsi'] > RSI_HIGH and row['rsi'] <= RSI_HIGH:
            signal_price = row['close']
            entry_price = signal_price * (1 - LIMIT_PCT / 100)
            sl_price = entry_price + (row['atr'] * SL_MULT)
            tp_price = entry_price - (row['atr'] * TP_MULT)

            # Calculate position size based on risk
            risk_dollars = equity * (risk_pct / 100)
            sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
            position_size_dollars = risk_dollars / (sl_distance_pct / 100)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['high'] >= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] < RSI_LOW and bar['rsi'] >= RSI_LOW:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            # Calculate P&L in dollars
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_before_fees = position_size_dollars * (price_change_pct / 100)

            # Fees
            fees = position_size_dollars * 0.001
            pnl_dollars = pnl_before_fees - fees

            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_dollars': pnl_dollars,
                'pnl_pct': (pnl_dollars / equity) * 100 if equity > 0 else 0,
                'position_size': position_size_dollars,
                'equity': equity
            })

            i = exit_idx + 1
            continue

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100

    return {
        'risk_pct': risk_pct,
        'total_return': total_return,
        'max_dd': dd,
        'return_dd': total_return / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity,
        'avg_position_size': df_t['position_size'].mean()
    }

# Test different risk levels
print("\nTesting risk levels from 1% to 10%...\n")

results = []
for risk_pct in range(1, 11):
    result = backtest_with_risk(df, risk_pct)
    if result:
        results.append(result)

# Display results
print("=" * 80)
print("RESULTS BY RISK LEVEL:")
print("=" * 80)

for r in results:
    print(f"\nRisk {r['risk_pct']}% per trade:")
    print(f"  Final Equity: ${r['final_equity']:.2f} (from $100)")
    print(f"  Total Return: {r['total_return']:+.2f}%")
    print(f"  Max DD: {r['max_dd']:.2f}%")
    print(f"  R/DD Ratio: {r['return_dd']:.2f}x")
    print(f"  Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}%")
    print(f"  Avg Position Size: ${r['avg_position_size']:.2f}")

# Find best by R/DD
best = max(results, key=lambda x: x['return_dd'])

print("\n" + "=" * 80)
print("BEST RISK LEVEL (by Return/DD):")
print("=" * 80)

print(f"\nRisk {best['risk_pct']}% per trade:")
print(f"  Total Return: {best['total_return']:+.2f}%")
print(f"  Max DD: {best['max_dd']:.2f}%")
print(f"  R/DD: {best['return_dd']:.2f}x ⭐")
print(f"  Final Equity: ${best['final_equity']:.2f}")
print(f"  Win Rate: {best['win_rate']:.1f}%")

print("\n" + "=" * 80)
print("COMPARISON:")
print("=" * 80)

print(f"\n100% position sizing (original):")
print(f"  Return: +155.81% | DD: -19.13% | R/DD: 8.15x")

print(f"\nBest risk-based ({best['risk_pct']}%):")
print(f"  Return: {best['total_return']:+.2f}% | DD: {best['max_dd']:.2f}% | R/DD: {best['return_dd']:.2f}x")

print("\n" + "=" * 80)
