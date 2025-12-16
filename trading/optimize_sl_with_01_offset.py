"""
Optimize SL with 0.1 ATR offset fixed
Keep offset=0.1 ATR and TP=3.1 ATR constant
Test SL from 1.5x to 2.4x in 0.1 ATR increments
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
print('=' * 120)
print('SL OPTIMIZATION - FIXED 0.1 ATR OFFSET & TP 3.1x ATR')
print('Testing SL from 1.5x to 2.4x ATR in 0.1 increments')
print('Sept-Dec 2025 data')
print('=' * 120)

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
print(f'Fixed: Offset = 0.1 ATR, TP = 3.1x ATR')
print(f'Variable: SL = 1.5x, 1.6x, 1.7x, 1.8x, 1.9x, 2.0x, 2.1x, 2.2x, 2.3x, 2.4x ATR')

results = []

# Fixed parameters
offset_atr = 0.1
tp_atr = 3.1

# Test SL levels
sl_levels = [1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4]

print('\n' + '=' * 120)
print('RESULTS')
print('=' * 120)
print(f"\n{'SL':<6} {'Trades':<8} {'Fill%':<7} {'W':<4} {'L':<4} {'WR%':<6} "
      f"{'TP%':<6} {'SL%':<6} {'Avg W':<8} {'Avg L':<8} {'Return':<9} {'MaxDD':<9} {'R/DD':<8}")
print('-' * 120)

for sl_atr in sl_levels:
    result = backtest_fixed_offset(df_all.copy(), offset_atr, sl_atr, tp_atr, max_wait_bars=8)

    if result and result['trades'] > 0:
        results.append({
            'sl_atr': sl_atr,
            **result
        })

        significance = '✅' if result['trades'] >= 40 else '⚠️'
        marker = ' ← CURRENT' if sl_atr == 1.9 else ''

        print(f"{sl_atr:.1f}x  {result['trades']:<8} {result['fill_rate']:>6.1f}% "
              f"{result['winners']:<4} {result['losers']:<4} {result['win_rate']:>5.1f}% "
              f"{result['tp_rate']:>5.1f}% {result['sl_rate']:>5.1f}% "
              f"{result['avg_win']:>+7.2f}% {result['avg_loss']:>+7.2f}% "
              f"{result['total_return']:>+8.1f}% {result['max_dd']:>+8.2f}% "
              f"{result['return_dd']:>7.2f}x {significance}{marker}")

# Analysis
if results:
    print('\n' + '=' * 120)
    print('ANALYSIS')
    print('=' * 120)

    # Best by return
    best_return = max(results, key=lambda x: x['total_return'])
    print(f"\n📈 BEST RETURN: SL {best_return['sl_atr']:.1f}x ATR")
    print(f"   {best_return['trades']} trades, {best_return['win_rate']:.1f}% WR, "
          f"{best_return['total_return']:+.1f}% return, {best_return['max_dd']:+.2f}% DD")

    # Best by R/DD
    best_rdd = max(results, key=lambda x: x['return_dd'])
    print(f"\n🎯 BEST R/DD: SL {best_rdd['sl_atr']:.1f}x ATR")
    print(f"   {best_rdd['trades']} trades, {best_rdd['win_rate']:.1f}% WR, "
          f"{best_rdd['total_return']:+.1f}% return, {best_rdd['max_dd']:+.2f}% DD, "
          f"{best_rdd['return_dd']:.2f}x R/DD")

    # Best win rate
    best_wr = max(results, key=lambda x: x['win_rate'])
    print(f"\n✅ BEST WIN RATE: SL {best_wr['sl_atr']:.1f}x ATR")
    print(f"   {best_wr['trades']} trades, {best_wr['win_rate']:.1f}% WR, "
          f"{best_wr['total_return']:+.1f}% return")

    # SL vs Exit type analysis
    print(f"\n📊 SL vs EXIT TYPE:")
    for r in results:
        tp_bar = '█' * int(r['tp_rate'] / 5)
        sl_bar = '█' * int(r['sl_rate'] / 5)
        print(f"   SL {r['sl_atr']:.1f}x: TP {r['tp_rate']:5.1f}% {tp_bar} | "
              f"SL {r['sl_rate']:5.1f}% {sl_bar}")

    print(f"\n💡 INSIGHTS:")
    print(f"   - Tighter SL = Higher TP rate (less stopped out)")
    print(f"   - Wider SL = Lower TP rate (more stopped out)")
    print(f"   - But tighter SL = Smaller avg loss")
    print(f"   - Need to find sweet spot for best return")

    # Save
    df_results = pd.DataFrame(results)
    df_results.to_csv('sl_optimization_01offset.csv', index=False)
    print(f'\n💾 Saved to: sl_optimization_01offset.csv')
