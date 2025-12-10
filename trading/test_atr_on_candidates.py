#!/usr/bin/env python3
"""
Test MOODENG ATR Limit strategy on other candidate coins
Coins: BRETT, POPCAT
Strategy: ATR expansion 1.3x, SL 2.0x, TP 6.0x (MOODENG best config)
"""
import pandas as pd
import numpy as np

def backtest_atr_limit(df, symbol, params):
    """Backtest ATR limit strategy"""
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

    # Outlier dependency
    if len(df_trades) >= 5:
        top5_pnl = df_trades.nlargest(5, 'pnl_pct')['pnl_pct'].sum()
        top5_dependency = (top5_pnl / final_return * 100) if final_return > 0 else 0
    else:
        top5_dependency = 100.0

    # Longest streaks
    df_trades['is_win'] = df_trades['pnl_pct'] > 0
    df_trades['streak_id'] = (df_trades['is_win'] != df_trades['is_win'].shift()).cumsum()
    win_streaks = df_trades[df_trades['is_win']].groupby('streak_id').size()
    loss_streaks = df_trades[~df_trades['is_win']].groupby('streak_id').size()

    max_win_streak = win_streaks.max() if len(win_streaks) > 0 else 0
    max_loss_streak = loss_streaks.max() if len(loss_streaks) > 0 else 0

    return {
        'symbol': symbol,
        'trades': len(df_trades),
        'return': final_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'top5_dependency': top5_dependency,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean(),
        'avg_loss': df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean(),
        'profit_factor': abs(df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].sum() /
                            df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].sum()) if len(df_trades[df_trades['pnl_pct'] < 0]) > 0 else 0,
    }

print("="*100)
print("TESTING MOODENG ATR STRATEGY ON OTHER CANDIDATES")
print("="*100)

# MOODENG best parameters
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

print(f"\n📋 Strategy Parameters:")
print(f"  ATR Expansion: {params['atr_expansion_mult']}x")
print(f"  EMA Distance:  {params['ema_distance_max']}%")
print(f"  Stop Loss:     {params['sl_atr_mult']}x ATR")
print(f"  Take Profit:   {params['tp_atr_mult']}x ATR")
print(f"  Limit Offset:  {params['limit_offset_pct']}%")
print(f"  Max Wait:      {params['max_wait_bars']} bars")

results = []

# MOODENG (reference)
print(f"\n{'='*100}")
print("MOODENG (REFERENCE)")
print("="*100)
df_moodeng = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
df_moodeng['timestamp'] = pd.to_datetime(df_moodeng['timestamp'])
print(f"Data: {len(df_moodeng):,} candles, {(df_moodeng['timestamp'].max() - df_moodeng['timestamp'].min()).days} days")

moodeng_result = backtest_atr_limit(df_moodeng, 'MOODENG', params)
if moodeng_result:
    results.append(moodeng_result)
    print(f"✅ {moodeng_result['trades']} trades, {moodeng_result['return']:+.2f}% return, {moodeng_result['return_dd']:.2f}x R/DD")
else:
    print("❌ No trades generated")

# BRETT
print(f"\n{'='*100}")
print("BRETT")
print("="*100)
df_brett = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/brett_usdt_30d_bingx.csv')
df_brett['timestamp'] = pd.to_datetime(df_brett['timestamp'])
print(f"Data: {len(df_brett):,} candles, {(df_brett['timestamp'].max() - df_brett['timestamp'].min()).days} days")

brett_result = backtest_atr_limit(df_brett, 'BRETT', params)
if brett_result:
    results.append(brett_result)
    print(f"✅ {brett_result['trades']} trades, {brett_result['return']:+.2f}% return, {brett_result['return_dd']:.2f}x R/DD")
else:
    print("❌ No trades generated")

# POPCAT
print(f"\n{'='*100}")
print("POPCAT")
print("="*100)
df_popcat = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/popcat_usdt_30d_bingx.csv')
df_popcat['timestamp'] = pd.to_datetime(df_popcat['timestamp'])
print(f"Data: {len(df_popcat):,} candles, {(df_popcat['timestamp'].max() - df_popcat['timestamp'].min()).days} days")

popcat_result = backtest_atr_limit(df_popcat, 'POPCAT', params)
if popcat_result:
    results.append(popcat_result)
    print(f"✅ {popcat_result['trades']} trades, {popcat_result['return']:+.2f}% return, {popcat_result['return_dd']:.2f}x R/DD")
else:
    print("❌ No trades generated")

# Comparison
if len(results) > 0:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_dd', ascending=False)

    print("\n" + "="*100)
    print("COMPARISON TABLE")
    print("="*100)
    print(f"\n{'Symbol':<10} {'Trades':>7} {'Return':>9} {'Max DD':>9} {'R/DD':>7} {'Win%':>6} {'TP%':>6} {'Top5%':>7} {'MaxLS':>6} {'PF':>6}")
    print("-"*100)

    for idx, row in results_df.iterrows():
        # Color code Top5 dependency
        if row['top5_dependency'] < 60:
            emoji = "🟢"
        elif row['top5_dependency'] < 75:
            emoji = "🟡"
        else:
            emoji = "🔴"

        print(f"{row['symbol']:<10} {row['trades']:>7.0f} {row['return']:>8.2f}% {row['max_dd']:>8.2f}% "
              f"{row['return_dd']:>7.2f} {row['win_rate']:>5.1f}% {row['tp_rate']:>5.1f}% "
              f"{emoji} {row['top5_dependency']:>5.1f}% {row['max_loss_streak']:>6.0f} {row['profit_factor']:>6.2f}")

    # Best coin
    best = results_df.iloc[0]

    print("\n" + "="*100)
    print(f"🏆 BEST COIN: {best['symbol']}")
    print("="*100)
    print(f"\nReturn/DD:       {best['return_dd']:.2f}x")
    print(f"Return:          {best['return']:+.2f}%")
    print(f"Max Drawdown:    {best['max_dd']:.2f}%")
    print(f"Win Rate:        {best['win_rate']:.1f}%")
    print(f"TP Rate:         {best['tp_rate']:.1f}%")
    print(f"Top5 Dependency: {best['top5_dependency']:.1f}%")
    print(f"Max Loss Streak: {best['max_loss_streak']:.0f} trades")
    print(f"Profit Factor:   {best['profit_factor']:.2f}")

    # vs MOODENG
    if best['symbol'] != 'MOODENG':
        moodeng_row = results_df[results_df['symbol'] == 'MOODENG'].iloc[0]
        print(f"\nvs MOODENG:")
        print(f"  Return/DD:       {best['return_dd']:.2f}x vs {moodeng_row['return_dd']:.2f}x ({(best['return_dd'] / moodeng_row['return_dd'] - 1) * 100:+.1f}%)")
        print(f"  Top5 Dependency: {best['top5_dependency']:.1f}% vs {moodeng_row['top5_dependency']:.1f}% ({best['top5_dependency'] - moodeng_row['top5_dependency']:+.1f}pp)")
        print(f"  Win Rate:        {best['win_rate']:.1f}% vs {moodeng_row['win_rate']:.1f}% ({best['win_rate'] - moodeng_row['win_rate']:+.1f}pp)")

    # Save results
    results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/atr_strategy_coin_comparison.csv', index=False)
    print(f"\n💾 Saved: trading/results/atr_strategy_coin_comparison.csv")

    print("\n" + "="*100)
    print("🎯 RECOMMENDATION")
    print("="*100)

    if best['symbol'] == 'MOODENG':
        print(f"\n✅ MOODENG is still the best coin for this strategy")
        print(f"   No better alternative found among BRETT and POPCAT")
    else:
        print(f"\n🎉 {best['symbol']} OUTPERFORMS MOODENG!")
        print(f"   Consider deploying {best['symbol']} instead of MOODENG")

        if best['top5_dependency'] < 70:
            print(f"   ✅ BONUS: Lower outlier dependency ({best['top5_dependency']:.1f}% vs {moodeng_row['top5_dependency']:.1f}%)")
            print(f"   → More consistent profits, less lottery-style")
        else:
            print(f"   ⚠️  Still lottery-style ({best['top5_dependency']:.1f}% Top5 dependency)")
            print(f"   → Must take ALL signals to catch outliers")

        print(f"\n📋 Next step: High-resolution optimization on {best['symbol']}")

else:
    print("\n❌ No valid results from any coin")

print("\n" + "="*100)
print("Legend:")
print("  R/DD = Return/Drawdown ratio")
print("  Top5% = Percentage of profit from top 5 trades")
print("  MaxLS = Max losing streak")
print("  PF = Profit Factor")
print("  🟢 = Top5 < 60% (Low dependency)")
print("  🟡 = Top5 60-75% (Medium dependency)")
print("  🔴 = Top5 > 75% (High dependency)")
print("="*100)
