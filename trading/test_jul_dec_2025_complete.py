"""
Final Config - Complete Jul-Dec 2025 Breakdown
Offset 0.1 ATR, SL 1.2x ATR, TP 3.0x ATR
"""
import pandas as pd
import numpy as np

def backtest_month(df, month_name, offset_atr=0.1, sl_atr=1.2, tp_atr=3.0, max_wait_bars=8):
    """Backtest single month"""
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

    trades, signals, equity, equity_curve = [], 0, 100.0, [100.0]
    position, pending_order = None, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        if pending_order:
            if i - pending_order['signal_bar'] > max_wait_bars:
                pending_order = None
                continue
            if pending_order['direction'] == 'LONG' and row['low'] <= pending_order['limit_price']:
                position = {'direction': 'LONG', 'entry': pending_order['limit_price'],
                           'sl_price': pending_order['sl_price'], 'tp_price': pending_order['tp_price'],
                           'size': pending_order['size']}
                pending_order = None
            elif pending_order['direction'] == 'SHORT' and row['high'] >= pending_order['limit_price']:
                position = {'direction': 'SHORT', 'entry': pending_order['limit_price'],
                           'sl_price': pending_order['sl_price'], 'tp_price': pending_order['tp_price'],
                           'size': pending_order['size']}
                pending_order = None

        if position:
            pnl_pct, exit_type = None, None
            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'TP'
            else:
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    exit_type = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type, 'direction': position['direction']})
                position = None
                continue

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0 or pd.isna(prev_row['rsi']):
                continue

            signal_price, atr = row['close'], row['atr']
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                signals += 1
                limit_price = signal_price - (atr * offset_atr)
                pending_order = {
                    'direction': 'LONG', 'limit_price': limit_price,
                    'sl_price': limit_price - (atr * sl_atr),
                    'tp_price': limit_price + (atr * tp_atr),
                    'size': (equity * 0.12) / (abs((limit_price - (limit_price - (atr * sl_atr))) / limit_price) * 100 / 100),
                    'signal_bar': i
                }
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                signals += 1
                limit_price = signal_price + (atr * offset_atr)
                pending_order = {
                    'direction': 'SHORT', 'limit_price': limit_price,
                    'sl_price': limit_price + (atr * sl_atr),
                    'tp_price': limit_price - (atr * tp_atr),
                    'size': (equity * 0.12) / (abs((limit_price + (atr * sl_atr) - limit_price) / limit_price) * 100 / 100),
                    'signal_bar': i
                }

    if not trades:
        return {'month': month_name, 'trades': 0}

    df_t = pd.DataFrame(trades)
    eq_s = pd.Series(equity_curve)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()

    return {
        'month': month_name, 'trades': len(df_t), 'signals': signals,
        'winners': (df_t['pnl_pct'] > 0).sum(), 'losers': (df_t['pnl_pct'] < 0).sum(),
        'win_rate': (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'avg_win': df_t[df_t['pnl_pct'] > 0]['pnl_pct'].mean() if (df_t['pnl_pct'] > 0).sum() > 0 else 0,
        'avg_loss': df_t[df_t['pnl_pct'] < 0]['pnl_pct'].mean() if (df_t['pnl_pct'] < 0).sum() > 0 else 0,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'return_dd': (((equity - 100) / 100) * 100) / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

print('='*140)
print('FINAL CONFIG - JULY-DECEMBER 2025 COMPLETE BREAKDOWN')
print('Offset: 0.1 ATR | SL: 1.2x ATR | TP: 3.0x ATR | Max wait: 2h')
print('='*140)

months = [
    ('July', 'melania_july_2025_15m_fresh.csv'),
    ('August', 'melania_august_2025_15m_fresh.csv'),
    ('September', 'melania_september_2025_15m_fresh.csv'),
    ('October', 'melania_october_2025_15m_fresh.csv'),
    ('November', 'melania_november_2025_15m_fresh.csv'),
    ('December', 'melania_december_2025_15m_fresh.csv'),
]

results = []
for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_month(df.copy(), month_name)
    if result['trades'] > 0:
        results.append(result)

print(f"\n{'Month':<12} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} {'Return':<10} {'MaxDD':<9} {'R/DD':<9} {'Status'}")
print('-'*140)

for r in results:
    status = '✅' if r['total_return'] > 0 else '❌'
    print(f"{r['month']:<12} {r['trades']:<8} {r['winners']:<4} {r['losers']:<4} {r['win_rate']:>5.1f}% "
          f"{r['tp_rate']:>5.1f}% {r['total_return']:>+9.1f}% {r['max_dd']:>+8.2f}% {r['return_dd']:>8.2f}x {status}")

print('\n' + '='*140)
print('EQUITY PROGRESSION')
print('='*140)
print(f"\n{'Month':<12} {'Start':<12} {'End':<14} {'Monthly':<10} {'Cumulative':<14}")
print('-'*140)

equity = 100.0
for r in results:
    start_eq = equity
    end_eq = start_eq * (1 + r['total_return'] / 100)
    cum_ret = ((end_eq - 100) / 100) * 100
    marker = '🚀' if r['total_return'] > 100 else '📈' if r['total_return'] > 0 else '📉'
    print(f"{r['month']:<12} ${start_eq:>10.2f} ${end_eq:>12.2f} {r['total_return']:>+9.1f}% {cum_ret:>+13.1f}% {marker}")
    equity = end_eq

print('\n' + '='*140)
print('SUMMARY')
print('='*140)

print(f"\n📊 6-MONTH PERFORMANCE (Jul-Dec 2025):")
print(f"   Starting capital: $100.00")
print(f"   Ending capital: ${equity:,.2f}")
print(f"   Total return: {((equity - 100) / 100) * 100:+.1f}%")
print(f"   Total trades: {sum(r['trades'] for r in results)}")
print(f"   Overall win rate: {(sum(r['winners'] for r in results) / sum(r['trades'] for r in results) * 100):.1f}%")
print(f"   Profitable months: {len([r for r in results if r['total_return'] > 0])}/6")

best = max(results, key=lambda x: x['total_return'])
worst = min(results, key=lambda x: x['total_return'])
print(f"\n🏆 Best month: {best['month']} ({best['total_return']:+.1f}%)")
print(f"📉 Worst month: {worst['month']} ({worst['total_return']:+.1f}%)")

df_r = pd.DataFrame(results)
df_r.to_csv('jul_dec_2025_complete.csv', index=False)
print(f'\n💾 Saved: jul_dec_2025_complete.csv')
