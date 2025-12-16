"""
BACKTEST: RSI 35/65 BOTH LONG+SHORT Strategy
Test multiple SL/TP combinations to find best R:R
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("RSI 35/65 STRATEGY - FULL BACKTEST")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"\nDownloading MELANIA 15m data (3 months)...")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
        continue

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

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
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("Indicators calculated")

def backtest(df, config):
    """
    Backtest with exact parameters
    """
    long_rsi = config['long_rsi']
    short_rsi = config['short_rsi']
    min_atr_pct = config['min_atr_pct']
    min_range_96 = config['min_range_96']
    sl_mult = config['sl_mult']
    tp_mult = config['tp_mult']
    risk_pct = config['risk_pct']

    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['atr_pct']) or pd.isna(row['range_96']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                # SL
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'LONG',
                        'exit_type': 'SL',
                        'pnl': pnl,
                        'equity': equity,
                        'entry': position['entry'],
                        'exit': position['sl_price']
                    })
                    position = None
                    i += 1
                    continue

                # TP
                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'LONG',
                        'exit_type': 'TP',
                        'pnl': pnl,
                        'equity': equity,
                        'entry': position['entry'],
                        'exit': position['tp_price']
                    })
                    position = None
                    i += 1
                    continue

                # Opposite signal
                if i > 0:
                    prev_row = df.iloc[i-1]
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] > short_rsi and row['rsi'] <= short_rsi:
                        pnl = position['size'] * ((bar['close'] - position['entry']) / position['entry'])
                        pnl -= position['size'] * 0.001
                        equity += pnl
                        trades.append({
                            'direction': 'LONG',
                            'exit_type': 'OPPOSITE',
                            'pnl': pnl,
                            'equity': equity,
                            'entry': position['entry'],
                            'exit': bar['close']
                        })
                        position = None

            elif position['direction'] == 'SHORT':
                # SL
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'SHORT',
                        'exit_type': 'SL',
                        'pnl': pnl,
                        'equity': equity,
                        'entry': position['entry'],
                        'exit': position['sl_price']
                    })
                    position = None
                    i += 1
                    continue

                # TP
                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'SHORT',
                        'exit_type': 'TP',
                        'pnl': pnl,
                        'equity': equity,
                        'entry': position['entry'],
                        'exit': position['tp_price']
                    })
                    position = None
                    i += 1
                    continue

                # Opposite signal
                if i > 0:
                    prev_row = df.iloc[i-1]
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < long_rsi and row['rsi'] >= long_rsi:
                        pnl = position['size'] * ((position['entry'] - bar['close']) / position['entry'])
                        pnl -= position['size'] * 0.001
                        equity += pnl
                        trades.append({
                            'direction': 'SHORT',
                            'exit_type': 'OPPOSITE',
                            'pnl': pnl,
                            'equity': equity,
                            'entry': position['entry'],
                            'exit': bar['close']
                        })
                        position = None

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Filters
            if row['atr_pct'] < min_atr_pct or row['range_96'] < min_range_96:
                i += 1
                continue

            # LONG entry (RSI crosses above long_rsi)
            if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < long_rsi and row['rsi'] >= long_rsi:
                entry_price = row['close']
                sl_price = entry_price - (row['atr'] * sl_mult)
                tp_price = entry_price + (row['atr'] * tp_mult)

                sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
                risk_dollars = equity * (risk_pct / 100)
                position_size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'LONG',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': position_size
                }

            # SHORT entry (RSI crosses below short_rsi)
            elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > short_rsi and row['rsi'] <= short_rsi:
                entry_price = row['close']
                sl_price = entry_price + (row['atr'] * sl_mult)
                tp_price = entry_price - (row['atr'] * tp_mult)

                sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
                risk_dollars = equity * (risk_pct / 100)
                position_size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': position_size
                }

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl'] > 0).sum() / len(df_t) * 100

    long_trades = df_t[df_t['direction'] == 'LONG']
    short_trades = df_t[df_t['direction'] == 'SHORT']

    return {
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'risk_pct': risk_pct,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity,
        'long_trades': len(long_trades),
        'long_win_rate': (long_trades['pnl'] > 0).sum() / len(long_trades) * 100 if len(long_trades) > 0 else 0,
        'short_trades': len(short_trades),
        'short_win_rate': (short_trades['pnl'] > 0).sum() / len(short_trades) * 100 if len(short_trades) > 0 else 0,
        'tp_rate': (df_t['exit_type'] == 'TP').sum() / len(df_t) * 100,
        'sl_rate': (df_t['exit_type'] == 'SL').sum() / len(df_t) * 100
    }

# Test various SL/TP combinations
print("\nTesting SL/TP combinations...")
results = []

base_config = {
    'long_rsi': 35,
    'short_rsi': 65,
    'min_atr_pct': 1.5,
    'min_range_96': 10.0
}

# Test combinations
for sl in [1.5, 2.0, 2.5, 3.0]:
    for tp in [2.0, 3.0, 4.0, 5.0]:
        for risk in [12, 15, 18, 20]:
            config = base_config.copy()
            config['sl_mult'] = sl
            config['tp_mult'] = tp
            config['risk_pct'] = risk

            res = backtest(df, config)
            if res:
                results.append(res)

print(f"Tested {len(results)} combinations")

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("TOP 10 CONFIGS (by R/DD):")
print("=" * 80)

print(f"\n| # | SL   | TP   | Risk | Return  | DD     | R/DD    | Trades | Win%  | TP%  | LONG% | SHORT% |")
print("|---|------|------|------|---------|--------|---------|--------|-------|------|-------|--------|")

for i, (idx, row) in enumerate(results_df.head(10).iterrows(), 1):
    highlight = "🏆" if i == 1 else ""
    print(f"| {i:2d} | {row['sl_mult']:.1f}x | {row['tp_mult']:.1f}x | {row['risk_pct']:2.0f}% | "
          f"{row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:7.2f}x | "
          f"{row['trades']:3.0f} | {row['win_rate']:4.1f}% | {row['tp_rate']:3.0f}% | "
          f"{row['long_win_rate']:4.1f}% | {row['short_win_rate']:4.1f}% | {highlight}")

# Best config details
best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST STRATEGY:")
print("=" * 80)

print("\n📋 ENTRY RULES:")
print(f"  LONG:  RSI crosses above {base_config['long_rsi']}")
print(f"  SHORT: RSI crosses below {base_config['short_rsi']}")
print(f"  Filters:")
print(f"    - ATR% > {base_config['min_atr_pct']:.1f}%")
print(f"    - 24h Range > {base_config['min_range_96']:.0f}%")

print("\n💰 POSITION SIZING:")
print(f"  Risk: {best['risk_pct']:.0f}% of equity per trade")
print(f"  Position Size = (Equity × {best['risk_pct']:.0f}%) / SL_distance%")

print("\n🎯 EXITS:")
print(f"  Stop Loss:   {best['sl_mult']:.1f}x ATR from entry")
print(f"  Take Profit: {best['tp_mult']:.1f}x ATR from entry")
print(f"  R:R Ratio:   {best['tp_mult']/best['sl_mult']:.2f}:1")
print(f"  Opposite Signal: Exit on reverse RSI cross")

print("\n📊 PERFORMANCE (3 months):")
print(f"  Total Return:    {best['return']:+.2f}%")
print(f"  Max Drawdown:    {best['max_dd']:.2f}%")
print(f"  Return/DD Ratio: {best['return_dd']:.2f}x ⭐")
print(f"  Final Equity:    ${best['final_equity']:,.2f}")

print("\n📈 STATISTICS:")
print(f"  Total Trades:    {best['trades']:.0f}")
print(f"  Win Rate:        {best['win_rate']:.1f}%")
print(f"  TP Rate:         {best['tp_rate']:.1f}%")
print(f"  SL Rate:         {best['sl_rate']:.1f}%")

print(f"\n  LONG Trades:     {best['long_trades']:.0f} ({best['long_win_rate']:.1f}% win rate)")
print(f"  SHORT Trades:    {best['short_trades']:.0f} ({best['short_win_rate']:.1f}% win rate)")

print("\n" + "=" * 80)
print("✅ STRATEGY COMPLETE - READY FOR IMPLEMENTATION")
print("=" * 80)
