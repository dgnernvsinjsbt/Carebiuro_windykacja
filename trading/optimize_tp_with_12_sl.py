"""
Optimize TP from 1.5 ATR to 8.0 ATR in 0.2 increments
Fixed: Offset 0.1 ATR, SL 1.2x ATR
Focus: Avoid optimizing for outlier trades - need consistent TP hits
"""
import pandas as pd
import numpy as np

def backtest_fixed_offset_sl(df, offset_atr, sl_atr, tp_atr, max_wait_bars=8):
    """
    Backtest with FIXED offset and SL, varying only TP
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
print('=' * 140)
print('TP OPTIMIZATION - FIXED 0.1 ATR OFFSET & SL 1.2x ATR')
print('Testing TP from 1.5x to 8.0x ATR in 0.2 increments')
print('Focus: Avoid optimizing for outliers - need consistent TP hit rate')
print('Sept-Dec 2025 data')
print('=' * 140)

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
print(f'Fixed: Offset = 0.1 ATR, SL = 1.2x ATR')

results = []

# Fixed parameters
offset_atr = 0.1
sl_atr = 1.2

# Test TP levels from 1.5 to 8.0 in 0.2 increments
tp_levels = [round(x * 0.2, 1) for x in range(int(1.5/0.2), int(8.0/0.2) + 1)]
tp_levels = [x for x in tp_levels if x >= 1.5]  # Start from 1.5

print(f'Testing {len(tp_levels)} TP levels: {tp_levels[0]:.1f} to {tp_levels[-1]:.1f} ATR')

print('\n' + '=' * 140)
print('RESULTS')
print('=' * 140)
print(f"\n{'TP':<6} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<7} {'SL%':<7} "
      f"{'Avg W':<8} {'Avg L':<8} {'Return':<10} {'MaxDD':<9} {'R/DD':<9}")
print('-' * 140)

for tp_atr in tp_levels:
    result = backtest_fixed_offset_sl(df_all.copy(), offset_atr, sl_atr, tp_atr, max_wait_bars=8)

    if result and result['trades'] > 0:
        results.append({
            'tp_atr': tp_atr,
            **result
        })

        significance = '✅' if result['trades'] >= 40 else '⚠️'
        marker = ' ← CURRENT' if abs(tp_atr - 3.1) < 0.01 else ''

        print(f"{tp_atr:.1f}x  {result['trades']:<8} "
              f"{result['winners']:<4} {result['losers']:<4} {result['win_rate']:>5.1f}% "
              f"{result['tp_rate']:>6.1f}% {result['sl_rate']:>6.1f}% "
              f"{result['avg_win']:>+7.2f}% {result['avg_loss']:>+7.2f}% "
              f"{result['total_return']:>+9.1f}% {result['max_dd']:>+8.2f}% "
              f"{result['return_dd']:>8.2f}x {significance}{marker}")

# Analysis
if results:
    print('\n' + '=' * 140)
    print('ANALYSIS - AVOIDING OUTLIER OPTIMIZATION')
    print('=' * 140)

    # Sort by R/DD
    sorted_by_rdd = sorted(results, key=lambda x: x['return_dd'], reverse=True)

    print(f"\n{'Rank':<6} {'TP':<6} {'R/DD':<10} {'Return':<10} {'TP%':<7} {'Trades':<8} {'Avg Win':<10} {'Assessment':<20}")
    print('-' * 140)

    for i, r in enumerate(sorted_by_rdd[:10], 1):
        marker = '🏆' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else '  '

        # Flag outlier risk
        if r['tp_rate'] < 20:
            assessment = '⚠️ LOW TP RATE - OUTLIER RISK'
        elif r['tp_rate'] < 30:
            assessment = '⚠️ MARGINAL TP RATE'
        elif r['tp_rate'] < 40:
            assessment = '✅ ACCEPTABLE'
        else:
            assessment = '✅ CONSISTENT'

        print(f"{marker} {i:<4} {r['tp_atr']:.1f}x  {r['return_dd']:>9.2f}x "
              f"{r['total_return']:>+9.1f}% {r['tp_rate']:>6.1f}% {r['trades']:<8} "
              f"{r['avg_win']:>+9.2f}% {assessment:<20}")

    print('\n' + '=' * 140)
    print('CONSISTENCY ANALYSIS')
    print('=' * 140)

    # Find best with good TP rate (40%+)
    consistent = [r for r in results if r['tp_rate'] >= 40]
    if consistent:
        best_consistent = max(consistent, key=lambda x: x['return_dd'])
        print(f"\n✅ BEST WITH CONSISTENT TP HITS (TP% >= 40%):")
        print(f"   TP {best_consistent['tp_atr']:.1f}x ATR")
        print(f"   {best_consistent['trades']} trades, {best_consistent['tp_rate']:.1f}% TP hit rate")
        print(f"   {best_consistent['total_return']:+.1f}% return, {best_consistent['max_dd']:+.2f}% DD")
        print(f"   {best_consistent['return_dd']:.2f}x R/DD ⭐")
        print(f"   Avg win: {best_consistent['avg_win']:+.2f}%")

    # Find best with acceptable TP rate (30%+)
    acceptable = [r for r in results if r['tp_rate'] >= 30]
    if acceptable:
        best_acceptable = max(acceptable, key=lambda x: x['return_dd'])
        print(f"\n⚡ BEST WITH ACCEPTABLE TP RATE (TP% >= 30%):")
        print(f"   TP {best_acceptable['tp_atr']:.1f}x ATR")
        print(f"   {best_acceptable['trades']} trades, {best_acceptable['tp_rate']:.1f}% TP hit rate")
        print(f"   {best_acceptable['total_return']:+.1f}% return, {best_acceptable['max_dd']:+.2f}% DD")
        print(f"   {best_acceptable['return_dd']:.2f}x R/DD")

    # Overall best (might be outlier)
    best_overall = max(results, key=lambda x: x['return_dd'])
    print(f"\n📊 BEST R/DD OVERALL (may rely on outliers):")
    print(f"   TP {best_overall['tp_atr']:.1f}x ATR")
    print(f"   {best_overall['trades']} trades, {best_overall['tp_rate']:.1f}% TP hit rate")
    print(f"   {best_overall['total_return']:+.1f}% return, {best_overall['max_dd']:+.2f}% DD")
    print(f"   {best_overall['return_dd']:.2f}x R/DD")

    # TP hit rate vs performance
    print(f"\n📈 TP HIT RATE vs PERFORMANCE:")
    for r in sorted_by_rdd[:10]:
        tp_bar = '█' * int(r['tp_rate'] / 5)
        warning = ' ⚠️ OUTLIER RISK' if r['tp_rate'] < 30 else ''
        print(f"   TP {r['tp_atr']:4.1f}x: {r['tp_rate']:5.1f}% {tp_bar:<20} | "
              f"R/DD {r['return_dd']:7.2f}x | Return {r['total_return']:>+8.1f}%{warning}")

    print(f"\n💡 RECOMMENDATION:")
    print(f"   - Prioritize configs with TP% >= 40% for consistency")
    print(f"   - Avoid low TP% (<30%) - may be curve-fitted to outliers")
    print(f"   - Best balance: High TP% + High R/DD")

    # Save
    df_results = pd.DataFrame(results)
    df_results.to_csv('tp_optimization_12sl.csv', index=False)
    print(f'\n💾 Saved to: tp_optimization_12sl.csv')
