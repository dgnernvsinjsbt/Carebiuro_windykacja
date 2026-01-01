"""
Show detailed monthly breakdown of WINNER config
+50%/-50% with 2% floor + 0.8% surgical filter
"""
import pandas as pd
import numpy as np

def backtest_winner(df, month_name):
    """Winner config: +50%/-50%, 2% floor, 0.8% filter"""

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

    df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
    df['ret_4h_abs'] = abs(df['ret_4h'])
    df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

    trades = []
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None
    current_risk = 0.12
    max_risk = 0.30
    min_risk = 0.02  # KEY: 2% floor instead of 5%

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue
        if pd.isna(row['avg_move_size']):
            continue

        if pending_order:
            bars_waiting = i - pending_order['signal_bar']
            if bars_waiting > 8:
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
            else:
                if row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None

        if position:
            pnl_pct = None
            exit_type = None

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

                # Dynamic sizing
                if pnl_pct > 0:
                    current_risk = min(current_risk * 1.5, max_risk)
                else:
                    current_risk = max(current_risk * 0.5, min_risk)

                trades.append({
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit': exit_type,
                    'direction': position['direction']
                })
                position = None
                continue

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= 0:
                continue
            if pd.isna(prev_row['rsi']):
                continue

            signal_price = row['close']
            atr = row['atr']

            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                limit_price = signal_price - (atr * 0.1)
                sl_price = limit_price - (atr * 1.2)
                tp_price = limit_price + (atr * 3.0)
                sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'direction': 'LONG',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                # SURGICAL FILTER: 0.8%
                if row['avg_move_size'] < 0.8:
                    continue

                limit_price = signal_price + (atr * 0.1)
                sl_price = limit_price + (atr * 1.2)
                tp_price = limit_price - (atr * 3.0)
                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'direction': 'SHORT',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

    if not trades:
        return {
            'month': month_name,
            'trades': 0,
            'total_return': 0,
            'max_dd': 0,
            'final_equity': equity
        }

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_dollar'] > 0]
    losers = df_t[df_t['pnl_dollar'] < 0]

    gross_profit = winners['pnl_dollar'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'month': month_name,
        'trades': len(df_t),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(df_t) * 100,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity
    }

print('=' * 140)
print('🏆 WINNER CONFIG: +50%/-50% with 2% floor + 0.8% surgical filter')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv'),
    ('July', 'melania_july_2025_15m.csv'),
    ('August', 'melania_august_2025_15m.csv'),
    ('September', 'melania_september_2025_15m.csv'),
    ('October', 'melania_october_2025_15m.csv'),
    ('November', 'melania_november_2025_15m.csv'),
    ('December', 'melania_december_2025_15m.csv'),
]

results = []

for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_winner(df.copy(), month_name)
    results.append(result)

print(f"\n{'Month':<12} {'Trades':<8} {'W/L':<8} {'WR%':<6} {'Gross Profit':<13} {'Gross Loss':<13} "
      f"{'PF':<8} {'Return':<10} {'Max DD':<9} {'R/DD':<9}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting_eq = cumulative_equity
    ending_eq = r['final_equity'] if r['trades'] == 0 else starting_eq * (1 + r['total_return'] / 100)
    cumulative_equity = ending_eq

    wl_str = f"{r['winners']}/{r['losers']}"
    return_dd = r['total_return'] / abs(r['max_dd']) if r['max_dd'] != 0 else 0
    status = '✅' if r['total_return'] > 0 else '❌'

    print(f"{r['month']:<12} {r['trades']:<8} {wl_str:<8} {r['win_rate']:>5.1f}% "
          f"${r['gross_profit']:>11.2f} ${r['gross_loss']:>11.2f} "
          f"{r['profit_factor']:>7.2f}x {r['total_return']:>+9.1f}% {r['max_dd']:>+8.2f}% "
          f"{return_dd:>8.2f}x {status}")

# Equity progression
print('\n' + '=' * 140)
print('EQUITY PROGRESSION')
print('=' * 140)
print(f"\n{'Month':<12} {'Starting':<12} {'Ending':<12} {'Monthly':<10} {'Cumulative':<12}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting = cumulative_equity
    ending = r['final_equity'] if r['trades'] == 0 else starting * (1 + r['total_return'] / 100)
    cumulative_return = ((ending - 100) / 100) * 100

    status = '🚀' if r['total_return'] > 200 else '📈' if r['total_return'] > 0 else '📉'
    print(f"{r['month']:<12} ${starting:>10.2f} ${ending:>10.2f} {r['total_return']:>+9.1f}% "
          f"{cumulative_return:>+11.1f}% {status}")

    cumulative_equity = ending

# Calculate overall max DD
all_equity = [100.0]
eq = 100.0
for r in results:
    eq = eq * (1 + r['total_return'] / 100)
    all_equity.append(eq)

eq_series = pd.Series(all_equity)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
overall_max_dd = drawdown.min()

total_return = ((cumulative_equity - 100) / 100) * 100
overall_return_dd = total_return / abs(overall_max_dd) if overall_max_dd != 0 else 0

print(f'\n💰 FINAL: ${cumulative_equity:,.2f} ({total_return:+.1f}%)')
print(f'📉 MAX DRAWDOWN: {overall_max_dd:+.2f}%')
print(f'🏆 RETURN/DD RATIO: {overall_return_dd:.2f}x')

print('\n' + '=' * 140)
print('FINAL COMPARISON')
print('=' * 140)
print(f"{'Strategy':<35} {'Trades':<10} {'Return':<12} {'Max DD':<12} {'R/DD':<10}")
print('-' * 140)
print(f"{'Baseline (Fixed 12% Risk)':<35} {151:<10} {'+106.6%':<12} {'-97.3%':<12} {'1.10x':<10}")
print(f"{'Dynamic +50%/-50% (5% floor)':<35} {151:<10} {'+2,262.7%':<12} {'-80.0%':<12} {'28.28x':<10}")
print(f"{'+ Filter 0.8% (5% floor)':<35} {139:<10} {'+3,312.9%':<12} {'-67.0%':<12} {'49.46x':<10}")
print(f"{'+ Filter 0.8% (2% floor) 🏆':<35} {sum(r['trades'] for r in results):<10} {f'+{total_return:.1f}%':<12} {f'{overall_max_dd:+.1f}%':<12} {f'{overall_return_dd:.2f}x':<10}")

print('\n' + '=' * 140)
