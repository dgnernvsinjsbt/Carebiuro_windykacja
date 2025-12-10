#!/usr/bin/env python3
"""
Low-resolution test of ATR Limit strategy on MOODENG
Quick parameter sweep to see if there's promise
"""
import pandas as pd
import numpy as np
from itertools import product

def backtest_atr_limit(df, params):
    """Backtest ATR limit strategy with given parameters"""
    df = df.copy()

    # Calculate indicators
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['atr_ma'] = df['atr'].rolling(params['atr_lookback']).mean()
    df['atr_expansion'] = df['atr'] / df['atr_ma']
    df['ema_dist_pct'] = abs((df['close'] - df['ema_20']) / df['ema_20'] * 100)
    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']

    trades = []
    pending_orders = []

    for i in range(50, len(df)):
        current = df.iloc[i]

        # Check pending orders for fills
        for order in pending_orders[:]:
            bars_waiting = i - order['signal_bar']

            # Cancel if waited too long
            if bars_waiting > params['max_wait_bars']:
                pending_orders.remove(order)
                continue

            # Check if filled
            filled = False
            if order['direction'] == 'LONG':
                if current['high'] >= order['limit_price']:
                    filled = True
            else:  # SHORT
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

        # Check for new signals
        if (df.iloc[i]['atr_expansion'] > params['atr_expansion_mult'] and
            df.iloc[i]['ema_dist_pct'] <= params['ema_distance_max'] and
            (df.iloc[i]['is_bullish'] or df.iloc[i]['is_bearish'])):

            direction = 'LONG' if df.iloc[i]['is_bullish'] else 'SHORT'
            signal_price = current['close']
            atr = current['atr']

            # Place limit order
            if direction == 'LONG':
                limit_price = signal_price * (1 + params['limit_offset_pct'] / 100)
                sl = limit_price - (params['sl_atr_mult'] * atr)
                tp = limit_price + (params['tp_atr_mult'] * atr)
            else:
                limit_price = signal_price * (1 - params['limit_offset_pct'] / 100)
                sl = limit_price + (params['sl_atr_mult'] * atr)
                tp = limit_price - (params['tp_atr_mult'] * atr)

            pending_orders.append({
                'signal_bar': i,
                'limit_price': limit_price,
                'direction': direction,
                'sl': sl,
                'tp': tp,
                'atr': atr
            })

    # Exit active trades
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
            else:  # SHORT
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

        # Time exit if not hit
        if exit_bar is None:
            exit_bar = min(trade['entry_bar'] + params['max_hold_bars'], len(df) - 1)
            exit_price = df.iloc[exit_bar]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if trade['direction'] == 'LONG':
            pnl_pct = (exit_price - trade['entry']) / trade['entry'] * 100
        else:
            pnl_pct = (trade['entry'] - exit_price) / trade['entry'] * 100

        # Apply fees
        pnl_pct -= 0.10  # 0.05% x2 sides

        trade['exit_bar'] = exit_bar
        trade['exit'] = exit_price
        trade['exit_reason'] = exit_reason
        trade['pnl_pct'] = pnl_pct

    if not trades:
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

    if max_dd == 0:
        return_dd = 0
    else:
        return_dd = final_return / abs(max_dd)

    win_rate = (df_trades['pnl_pct'] > 0).sum() / len(df_trades) * 100
    tp_rate = (df_trades['exit_reason'] == 'TP').sum() / len(df_trades) * 100

    return {
        'trades': len(df_trades),
        'return': final_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean(),
        'avg_loss': df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean(),
    }

# Load MOODENG data
print("=" * 100)
print("MOODENG ATR LIMIT STRATEGY - LOW RESOLUTION TEST")
print("=" * 100)

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"\nData: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# FARTCOIN baseline for reference
print(f"\n📊 FARTCOIN ATR Limit (Reference):")
print(f"  Parameters: ATR expansion 1.5x, SL 2.0x ATR, TP 8.0x ATR")
print(f"  Results: +101.11% return, -11.98% DD, 8.44x R/DD, 94 trades")

# LOW RESOLUTION parameter grid
print(f"\n🔍 Testing MOODENG-optimized parameters (LOW RESOLUTION)...")
print(f"Based on MOODENG profile:")
print(f"  - Lower ATR expansion frequency (1.5% vs 8.5%) → test lower thresholds")
print(f"  - Lower explosive moves (2.0% vs 2.9%) → test lower TP multiples")
print(f"  - Higher volume CV (2.10 vs 1.50) → keep volume-agnostic for now")
print(f"  - Higher daily volatility (16.82% vs 11.26%) → test tighter stops")

param_grid = {
    'atr_expansion_mult': [1.2, 1.3, 1.4, 1.5],     # Lower threshold
    'atr_lookback': [20],                            # Keep same
    'ema_distance_max': [3.0, 4.0],                 # Slightly wider
    'limit_offset_pct': [1.0],                       # Keep same
    'sl_atr_mult': [1.5, 2.0],                      # Test tighter
    'tp_atr_mult': [4.0, 6.0, 8.0],                 # Test lower targets
    'max_wait_bars': [3],                            # Keep same
    'max_hold_bars': [200],                          # Keep same
}

total_combinations = (len(param_grid['atr_expansion_mult']) *
                     len(param_grid['ema_distance_max']) *
                     len(param_grid['sl_atr_mult']) *
                     len(param_grid['tp_atr_mult']))

print(f"\nTesting {total_combinations} combinations...")

results = []
for atr_exp, ema_dist, sl_mult, tp_mult in product(
    param_grid['atr_expansion_mult'],
    param_grid['ema_distance_max'],
    param_grid['sl_atr_mult'],
    param_grid['tp_atr_mult']
):
    params = {
        'atr_expansion_mult': atr_exp,
        'atr_lookback': 20,
        'ema_distance_max': ema_dist,
        'limit_offset_pct': 1.0,
        'sl_atr_mult': sl_mult,
        'tp_atr_mult': tp_mult,
        'max_wait_bars': 3,
        'max_hold_bars': 200,
    }

    result = backtest_atr_limit(df, params)

    if result and result['trades'] >= 10:  # Min 10 trades
        results.append({
            **params,
            **result
        })

if not results:
    print("\n❌ No valid configurations found (need min 10 trades)")
    exit(1)

# Sort by Return/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print(f"\n✅ Found {len(results_df)} valid configurations")

# Top 10
top10 = results_df.head(10)

print("\n" + "=" * 100)
print("TOP 10 CONFIGURATIONS")
print("=" * 100)
print(f"\n{'Rank':<5} {'ATR Exp':>8} {'EMA Dist':>9} {'SL':>6} {'TP':>6} {'Trades':>7} {'Return':>8} {'Max DD':>8} {'R/DD':>7} {'Win%':>6} {'TP%':>6}")
print("-" * 100)

for idx, (i, row) in enumerate(top10.iterrows(), 1):
    print(f"{idx:<5} {row['atr_expansion_mult']:>8.1f} {row['ema_distance_max']:>8.1f}% "
          f"{row['sl_atr_mult']:>5.1f}x {row['tp_atr_mult']:>5.1f}x "
          f"{row['trades']:>7} {row['return']:>7.2f}% {row['max_dd']:>7.2f}% "
          f"{row['return_dd']:>7.2f} {row['win_rate']:>5.1f}% {row['tp_rate']:>5.1f}%")

# Best config
best = top10.iloc[0]

print("\n" + "=" * 100)
print("🏆 BEST CONFIGURATION")
print("=" * 100)
print(f"\nParameters:")
print(f"  ATR Expansion Threshold: {best['atr_expansion_mult']:.1f}x (FARTCOIN: 1.5x)")
print(f"  EMA Distance Max:        {best['ema_distance_max']:.1f}% (FARTCOIN: 3.0%)")
print(f"  Stop Loss:               {best['sl_atr_mult']:.1f}x ATR (FARTCOIN: 2.0x)")
print(f"  Take Profit:             {best['tp_atr_mult']:.1f}x ATR (FARTCOIN: 8.0x)")
print(f"  Limit Offset:            {best['limit_offset_pct']:.1f}%")
print(f"  Max Wait:                {best['max_wait_bars']:.0f} bars")

print(f"\nResults:")
print(f"  Trades:       {best['trades']:.0f}")
print(f"  Return:       {best['return']:+.2f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Return/DD:    {best['return_dd']:.2f}x")
print(f"  Win Rate:     {best['win_rate']:.1f}%")
print(f"  TP Rate:      {best['tp_rate']:.1f}%")
print(f"  Avg Win:      {best['avg_win']:+.2f}%")
print(f"  Avg Loss:     {best['avg_loss']:-.2f}%")

# Comparison to FARTCOIN
print(f"\n📊 vs FARTCOIN:")
print(f"  Return/DD: {best['return_dd']:.2f}x vs 8.44x (FARTCOIN)")
print(f"  Win Rate:  {best['win_rate']:.1f}% vs 42.6% (FARTCOIN)")

# Save top configs
top10.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_atr_quick_results.csv', index=False)
print(f"\n💾 Saved top 10 configs: trading/results/moodeng_atr_quick_results.csv")

# Decision
print("\n" + "=" * 100)
print("🎯 VERDICT")
print("=" * 100)

if best['return_dd'] >= 5.0:
    print(f"\n✅ PROMISING! Return/DD = {best['return_dd']:.2f}x")
    print(f"   Proceed with HIGH RESOLUTION optimization around these parameters:")
    print(f"   - ATR expansion: {best['atr_expansion_mult']:.1f}x ± 0.1")
    print(f"   - SL: {best['sl_atr_mult']:.1f}x ± 0.2")
    print(f"   - TP: {best['tp_atr_mult']:.1f}x ± 1.0")
elif best['return_dd'] >= 3.0:
    print(f"\n⚠️  DECENT. Return/DD = {best['return_dd']:.2f}x")
    print(f"   Worth exploring further but expectations should be moderate")
else:
    print(f"\n❌ POOR FIT. Return/DD = {best['return_dd']:.2f}x")
    print(f"   ATR Limit strategy may not be suitable for MOODENG's volatility profile")
    print(f"   Consider different strategy entirely")
