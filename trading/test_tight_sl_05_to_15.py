"""
Test VERY tight SL from 0.5x to 1.5x ATR
Optimize for best Return/DD ratio (profit:max dd)
Fixed: Offset 0.1 ATR, TP 3.1x ATR
"""
import pandas as pd
import numpy as np

def backtest_fixed_offset(df, offset_atr, sl_atr, tp_atr, max_wait_bars=8):
    """
    Backtest with FIXED offset and TP, varying only SL
    """

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
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    trades = []
    signals = 0
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Check pending limit order
        if pending_order:
            bars_waiting = i - pending_order['signal_bar']

            if bars_waiting > max_wait_bars:
                pending_order = None
                continue

            if pending_order['direction'] == 'LONG':
                if row['low'] <= pending_order['limit_price']:
                    position = {
                        'direction': 'LONG',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None
            else:  # SHORT
                if row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None

        # Manage active position
        if position:
            bar = row
            pnl_pct = None
            exit_type = None

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'SL'
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'TP'
            else:  # SHORT
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    exit_type = 'SL'
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    exit_type = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)

                trades.append({
                    'pnl_pct': pnl_pct,
                    'exit': exit_type,
                    'direction': position['direction']
                })
                position = None
                continue

        # Generate new signals
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                signal_price = row['close']
                atr = row['atr']

                if prev_row['rsi'] < 35 and row['rsi'] >= 35:  # LONG signal
                    signals += 1
                    limit_price = signal_price - (atr * offset_atr)
                    sl_price = limit_price - (atr * sl_atr)
                    tp_price = limit_price + (atr * tp_atr)
                    sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'LONG',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:  # SHORT signal
                    signals += 1
                    limit_price = signal_price + (atr * offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'SHORT',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    if not trades:
        return None

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    total_return = ((equity - 100) / 100) * 100
    win_rate = len(winners) / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100
    sl_rate = (df_t['exit'] == 'SL').sum() / len(df_t) * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    fill_rate = (len(trades) / signals * 100) if signals > 0 else 0

    return {
        'trades': len(df_t),
        'signals': signals,
        'fill_rate': fill_rate,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

# Load Sept-Dec months
print('=' * 130)
print('VERY TIGHT SL TEST - OPTIMIZING FOR RETURN/DD RATIO')
print('Testing SL from 0.5x to 1.5x ATR in 0.1 increments')
print('Fixed: Offset 0.1 ATR, TP 3.1x ATR | Sept-Dec 2025 data')
print('=' * 130)

months_data = []
for month_name, filename in [
    ('September', 'melania_september_2025_15m_fresh.csv'),
    ('October', 'melania_october_2025_15m_fresh.csv'),
    ('November', 'melania_november_2025_15m_fresh.csv'),
    ('December', 'melania_december_2025_15m_fresh.csv'),
]:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    months_data.append((month_name, df))

df_all = pd.concat([df for _, df in months_data], ignore_index=True)
df_all = df_all.sort_values('timestamp').reset_index(drop=True)

print(f'\nTotal data: {len(df_all)} bars')
print(f'Testing SL: 0.5x, 0.6x, 0.7x, 0.8x, 0.9x, 1.0x, 1.1x, 1.2x, 1.3x, 1.4x, 1.5x ATR')

results = []

# Fixed parameters
offset_atr = 0.1
tp_atr = 3.1

# Test TIGHT SL levels
sl_levels = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]

print('\n' + '=' * 130)
print('RESULTS')
print('=' * 130)
print(f"\n{'SL':<6} {'Trades':<8} {'Fill%':<7} {'W':<4} {'L':<4} {'WR%':<6} "
      f"{'TP%':<6} {'SL%':<6} {'Avg W':<8} {'Avg L':<8} {'Return':<10} {'MaxDD':<9} {'R/DD':<9}")
print('-' * 130)

for sl_atr in sl_levels:
    result = backtest_fixed_offset(df_all.copy(), offset_atr, sl_atr, tp_atr, max_wait_bars=8)

    if result and result['trades'] > 0:
        results.append({
            'sl_atr': sl_atr,
            **result
        })

        significance = '✅' if result['trades'] >= 40 else '⚠️'

        print(f"{sl_atr:.1f}x  {result['trades']:<8} {result['fill_rate']:>6.1f}% "
              f"{result['winners']:<4} {result['losers']:<4} {result['win_rate']:>5.1f}% "
              f"{result['tp_rate']:>5.1f}% {result['sl_rate']:>5.1f}% "
              f"{result['avg_win']:>+7.2f}% {result['avg_loss']:>+7.2f}% "
              f"{result['total_return']:>+9.1f}% {result['max_dd']:>+8.2f}% "
              f"{result['return_dd']:>8.2f}x {significance}")

# Analysis
if results:
    print('\n' + '=' * 130)
    print('ANALYSIS - SORTED BY RETURN/DD RATIO (BEST FIRST)')
    print('=' * 130)

    # Sort by R/DD
    sorted_by_rdd = sorted(results, key=lambda x: x['return_dd'], reverse=True)

    print(f"\n{'Rank':<6} {'SL':<6} {'R/DD':<10} {'Return':<10} {'MaxDD':<9} {'Trades':<8} {'WR%':<6} {'Avg Loss':<10}")
    print('-' * 130)

    for i, r in enumerate(sorted_by_rdd[:5], 1):
        marker = '🏆' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else '  '
        print(f"{marker} {i:<4} {r['sl_atr']:.1f}x  {r['return_dd']:>9.2f}x "
              f"{r['total_return']:>+9.1f}% {r['max_dd']:>+8.2f}% {r['trades']:<8} "
              f"{r['win_rate']:>5.1f}% {r['avg_loss']:>+9.2f}%")

    # Best by return
    best_return = max(results, key=lambda x: x['total_return'])
    print(f"\n📈 HIGHEST RETURN: SL {best_return['sl_atr']:.1f}x ATR")
    print(f"   {best_return['total_return']:+.1f}% return, {best_return['max_dd']:+.2f}% DD, "
          f"{best_return['return_dd']:.2f}x R/DD")

    # Best by R/DD
    best_rdd = max(results, key=lambda x: x['return_dd'])
    print(f"\n🎯 BEST RETURN/DD: SL {best_rdd['sl_atr']:.1f}x ATR")
    print(f"   {best_rdd['trades']} trades, {best_rdd['win_rate']:.1f}% WR")
    print(f"   {best_rdd['total_return']:+.1f}% return, {best_rdd['max_dd']:+.2f}% DD")
    print(f"   {best_rdd['return_dd']:.2f}x R/DD ⭐")
    print(f"   Avg win: {best_rdd['avg_win']:+.2f}%, Avg loss: {best_rdd['avg_loss']:+.2f}%")

    # Smallest max DD
    best_dd = max(results, key=lambda x: x['max_dd'])  # Max because DD is negative
    print(f"\n✅ SMALLEST MAX DD: SL {best_dd['sl_atr']:.1f}x ATR")
    print(f"   {best_dd['max_dd']:+.2f}% max DD, {best_dd['total_return']:+.1f}% return")

    # Analysis by SL size
    print(f"\n📊 SL vs PERFORMANCE:")
    for r in results:
        bar_return = '█' * max(0, int(r['total_return'] / 100))
        bar_dd = '█' * max(0, int(abs(r['max_dd']) / 5))
        rdd_marker = '⭐' if r['return_dd'] == best_rdd['return_dd'] else ''
        print(f"   SL {r['sl_atr']:.1f}x: Return {r['total_return']:>+8.1f}% {bar_return[:20]:<20} | "
              f"DD {r['max_dd']:>+7.2f}% {bar_dd[:15]:<15} | R/DD {r['return_dd']:>6.2f}x {rdd_marker}")

    print(f"\n💡 KEY INSIGHTS:")
    print(f"   - Tighter SL = Smaller avg loss = Better compounding")
    print(f"   - But TOO tight = Lower TP rate = Fewer winners")
    print(f"   - Sweet spot balances loss size vs TP hit rate")
    print(f"   - Best R/DD: {best_rdd['sl_atr']:.1f}x ATR with {best_rdd['return_dd']:.2f}x ratio")

    # Save
    df_results = pd.DataFrame(results)
    df_results.to_csv('tight_sl_optimization_05_to_15.csv', index=False)
    print(f'\n💾 Saved to: tight_sl_optimization_05_to_15.csv')
