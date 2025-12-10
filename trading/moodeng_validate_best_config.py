#!/usr/bin/env python3
"""
Extract individual trade data for MOODENG best config validation
Run full statistical analysis on the 126 trades
"""
import pandas as pd
import numpy as np

def backtest_atr_limit_detailed(df, params):
    """Backtest ATR limit strategy with DETAILED trade tracking"""
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
                    'entry_timestamp': df.iloc[i]['timestamp'],
                    'entry': order['limit_price'],
                    'direction': order['direction'],
                    'sl': order['sl'],
                    'tp': order['tp'],
                    'atr': order['atr'],
                    'signal_price': order['signal_price'],
                    'atr_expansion': order['atr_expansion']
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
                'atr': atr,
                'signal_price': signal_price,
                'atr_expansion': df.iloc[i]['atr_expansion']
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
        trade['exit_timestamp'] = df.iloc[exit_bar]['timestamp']
        trade['exit'] = exit_price
        trade['exit_reason'] = exit_reason
        trade['pnl_pct'] = pnl_pct
        trade['hold_bars'] = exit_bar - trade['entry_bar']

    return pd.DataFrame(trades)

# Load MOODENG data
print("=" * 100)
print("MOODENG ATR LIMIT STRATEGY - DETAILED VALIDATION")
print("=" * 100)

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"\nData: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

# BEST CONFIG from quick test
params = {
    'atr_expansion_mult': 1.3,
    'atr_lookback': 20,
    'ema_distance_max': 3.0,
    'limit_offset_pct': 1.0,
    'sl_atr_mult': 2.0,
    'tp_atr_mult': 6.0,
    'max_wait_bars': 3,
    'max_hold_bars': 200,
}

print(f"\n🔍 Testing BEST config:")
print(f"  ATR expansion: {params['atr_expansion_mult']:.1f}x")
print(f"  SL: {params['sl_atr_mult']:.1f}x ATR")
print(f"  TP: {params['tp_atr_mult']:.1f}x ATR")
print(f"  EMA distance max: {params['ema_distance_max']:.1f}%")

# Run backtest with detailed tracking
trades_df = backtest_atr_limit_detailed(df, params)

if trades_df.empty:
    print("\n❌ No trades generated!")
    exit(1)

# Calculate equity curve
trades_df['cumulative_pnl'] = trades_df['pnl_pct'].cumsum()
trades_df['equity'] = 100 + trades_df['cumulative_pnl']
trades_df['running_max'] = trades_df['equity'].cummax()
trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
trades_df['drawdown_pct'] = trades_df['drawdown'] / trades_df['running_max'] * 100

# Add trade metadata
trades_df['is_winner'] = trades_df['pnl_pct'] > 0
trades_df['trade_num'] = range(1, len(trades_df) + 1)

# Save
trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_trades.csv', index=False)
print(f"\n💾 Saved {len(trades_df)} trades to: trading/results/moodeng_validation_trades.csv")

# Basic summary
print(f"\n📊 SUMMARY:")
print(f"  Total Trades: {len(trades_df)}")
print(f"  Final Return: {trades_df['cumulative_pnl'].iloc[-1]:+.2f}%")
print(f"  Max Drawdown: {trades_df['drawdown_pct'].min():.2f}%")
print(f"  Return/DD: {trades_df['cumulative_pnl'].iloc[-1] / abs(trades_df['drawdown_pct'].min()):.2f}x")
print(f"  Win Rate: {(trades_df['pnl_pct'] > 0).sum() / len(trades_df) * 100:.1f}%")
print(f"  TP Rate: {(trades_df['exit_reason'] == 'TP').sum() / len(trades_df) * 100:.1f}%")

print("\n✅ Data ready for validation analysis")
