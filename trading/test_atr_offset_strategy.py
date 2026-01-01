"""
Test ATR-based offset strategy with dynamic SL/TP adjustment
As offset increases, SL tightens and TP widens
"""
import pandas as pd
import numpy as np

def backtest_atr_offset(df, offset_atr, sl_base, tp_base, max_wait_bars=8):
    """
    Backtest with ATR-based offset and dynamic SL/TP

    offset_atr: offset from signal price in ATR multiples
    sl_base: base SL in ATR (shrinks as offset increases)
    tp_base: base TP in ATR (grows as offset increases)
    max_wait_bars: max bars to wait for limit fill (2 hours = 8 bars on 15m)
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

            # Cancel if waited too long
            if bars_waiting > max_wait_bars:
                pending_order = None
                continue

            # Check if filled
            if pending_order['direction'] == 'LONG':
                if row['low'] <= pending_order['limit_price']:
                    # Filled! Enter position
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
                    # Filled! Enter position
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

        # Generate new signals (only if no position or pending order)
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                signal_price = row['close']
                atr = row['atr']

                # Adjust SL/TP based on offset
                # As offset increases by 0.2 ATR, SL shrinks by 0.2, TP grows by 0.2
                offset_increment = offset_atr - 1.0  # How much above baseline 1.0 ATR
                sl_atr = sl_base - offset_increment
                tp_atr = tp_base + offset_increment

                # Don't let SL get too tight or TP too wide
                sl_atr = max(0.5, sl_atr)  # Min 0.5 ATR SL
                tp_atr = min(6.0, tp_atr)  # Max 6.0 ATR TP

                if prev_row['rsi'] < 35 and row['rsi'] >= 35:  # LONG signal
                    limit_price = signal_price - (atr * offset_atr)  # Buy BELOW signal
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
                    limit_price = signal_price + (atr * offset_atr)  # Sell ABOVE signal
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

    # Calculate metrics
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    total_return = ((equity - 100) / 100) * 100
    win_rate = len(winners) / len(df_t) * 100 if len(df_t) > 0 else 0
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100 if len(df_t) > 0 else 0

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    return {
        'trades': len(df_t),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

# Load all months
months_data = []
for month_name, filename in [
    ('July', 'melania_july_2025_15m_fresh.csv'),
    ('August', 'melania_august_2025_15m_fresh.csv'),
    ('September', 'melania_september_2025_15m_fresh.csv'),
    ('October', 'melania_october_2025_15m_fresh.csv'),
    ('November', 'melania_november_2025_15m_fresh.csv'),
    ('December', 'melania_december_2025_15m_fresh.csv'),
]:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    months_data.append((month_name, df))

# Combine all months for testing
df_all = pd.concat([df for _, df in months_data], ignore_index=True)
df_all = df_all.sort_values('timestamp').reset_index(drop=True)

print('=' * 120)
print('ATR-BASED OFFSET STRATEGY TEST')
print('Strategy: RSI 35/65 + ret_20 > 0, LIMIT orders with ATR offset')
print('Dynamic SL/TP: As offset ↑ by 0.2 ATR → SL ↓ by 0.2 ATR, TP ↑ by 0.2 ATR')
print('Max wait: 2 hours (8 bars on 15m)')
print('=' * 120)

print(f'\nTotal data: {len(df_all)} bars from July-December 2025')
print(f'Testing offsets: 1.0, 1.2, 1.4, 1.6, 1.8, 2.0 ATR')
print(f'Baseline: SL 2.0 ATR, TP 3.0 ATR (at 1.0 ATR offset)')

results = []

# Test different offset levels
offset_levels = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
sl_base = 2.0
tp_base = 3.0

print('\n' + '=' * 120)
print('RESULTS')
print('=' * 120)
print(f"\n{'Offset':<8} {'SL':<6} {'TP':<6} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} "
      f"{'TP%':<6} {'Avg W':<8} {'Avg L':<8} {'Return':<9} {'MaxDD':<9} {'R/DD':<8}")
print('-' * 120)

for offset_atr in offset_levels:
    # Calculate adjusted SL/TP
    offset_increment = offset_atr - 1.0
    sl_atr = max(0.5, sl_base - offset_increment)
    tp_atr = min(6.0, tp_base + offset_increment)

    result = backtest_atr_offset(df_all.copy(), offset_atr, sl_base, tp_base, max_wait_bars=8)

    if result and result['trades'] > 0:
        results.append({
            'offset_atr': offset_atr,
            'sl_atr': sl_atr,
            'tp_atr': tp_atr,
            **result
        })

        significance = '✅' if result['trades'] >= 40 else '⚠️'

        print(f"{offset_atr:.1f} ATR {sl_atr:.1f}x {tp_atr:.1f}x "
              f"{result['trades']:<8} {result['winners']:<4} {result['losers']:<4} "
              f"{result['win_rate']:>5.1f}% {result['tp_rate']:>5.1f}% "
              f"{result['avg_win']:>+7.2f}% {result['avg_loss']:>+7.2f}% "
              f"{result['total_return']:>+8.1f}% {result['max_dd']:>+8.2f}% "
              f"{result['return_dd']:>7.2f}x {significance}")
    else:
        print(f"{offset_atr:.1f} ATR {sl_atr:.1f}x {tp_atr:.1f}x NO TRADES")

# Find best config
if results:
    print('\n' + '=' * 120)
    print('ANALYSIS')
    print('=' * 120)

    # Best by return
    best_return = max(results, key=lambda x: x['total_return'])
    print(f"\n📈 BEST RETURN: {best_return['offset_atr']:.1f} ATR offset "
          f"(SL {best_return['sl_atr']:.1f}x / TP {best_return['tp_atr']:.1f}x)")
    print(f"   {best_return['trades']} trades, {best_return['win_rate']:.1f}% WR, "
          f"{best_return['total_return']:+.1f}% return, {best_return['max_dd']:+.2f}% DD")

    # Best by R/DD with significance
    significant = [r for r in results if r['trades'] >= 40]
    if significant:
        best_rdd = max(significant, key=lambda x: x['return_dd'])
        print(f"\n🎯 BEST R/DD (40+ trades): {best_rdd['offset_atr']:.1f} ATR offset "
              f"(SL {best_rdd['sl_atr']:.1f}x / TP {best_rdd['tp_atr']:.1f}x)")
        print(f"   {best_rdd['trades']} trades, {best_rdd['win_rate']:.1f}% WR, "
              f"{best_rdd['total_return']:+.1f}% return, {best_rdd['max_dd']:+.2f}% DD, "
              f"{best_rdd['return_dd']:.2f}x R/DD")

    # Trade count analysis
    print(f"\n📊 TRADE COUNT vs OFFSET:")
    for r in results:
        bar = '█' * int(r['trades'] / 5)
        sig = '✅' if r['trades'] >= 40 else '⚠️'
        print(f"   {r['offset_atr']:.1f} ATR: {r['trades']:3d} trades {bar} {sig}")

    print(f"\n💡 INSIGHTS:")
    print(f"   - Higher offset = more selective (fewer trades)")
    print(f"   - But better entry price + tighter SL + wider TP")
    print(f"   - Need to balance trade frequency vs trade quality")

    # Save
    df_results = pd.DataFrame(results)
    df_results.to_csv('atr_offset_strategy_results.csv', index=False)
    print(f'\n💾 Saved to: atr_offset_strategy_results.csv')

else:
    print('\n❌ No trades generated across all offset levels!')
