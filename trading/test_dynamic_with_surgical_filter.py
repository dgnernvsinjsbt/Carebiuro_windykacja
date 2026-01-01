"""
Combine Dynamic Position Sizing (+50%/-50%) WITH Surgical Filter
Filter: SHORT + Move < 0.9% (removes 7/20 worst, keeps 50/55 winners)
"""
import pandas as pd
import numpy as np

def backtest_dynamic_filtered(df, month_name, filter_threshold=0.9):
    """Dynamic sizing +50%/-50% WITH surgical filter"""

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

    # Move size filter
    df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
    df['ret_4h_abs'] = abs(df['ret_4h'])
    df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

    trades = []
    signals_total = 0
    signals_filtered = 0
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None
    current_risk = 0.12
    max_risk = 0.30

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

                # Dynamic sizing: +50% after win, -50% after loss
                if pnl_pct > 0:
                    current_risk = min(current_risk * 1.5, max_risk)
                else:
                    current_risk = max(current_risk * 0.5, 0.05)

                trades.append({
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit': exit_type,
                    'risk_used': current_risk,
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
                signals_total += 1

                # No filter for LONG trades
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
                signals_total += 1

                # SURGICAL FILTER: Skip SHORT if move size < threshold
                if row['avg_move_size'] < filter_threshold:
                    signals_filtered += 1
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
            'signals_total': signals_total,
            'signals_filtered': signals_filtered,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'final_equity': equity
        }

    df_t = pd.DataFrame(trades)

    # Calculate max drawdown
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Calculate metrics
    winners = df_t[df_t['pnl_dollar'] > 0]
    losers = df_t[df_t['pnl_dollar'] < 0]

    gross_profit = winners['pnl_dollar'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    total_return = ((equity - 100) / 100) * 100
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    long_trades = df_t[df_t['direction'] == 'LONG']
    short_trades = df_t[df_t['direction'] == 'SHORT']

    return {
        'month': month_name,
        'trades': len(df_t),
        'signals_total': signals_total,
        'signals_filtered': signals_filtered,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(df_t) * 100,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': equity,
        'long_trades': len(long_trades),
        'short_trades': len(short_trades)
    }

print('=' * 140)
print('DYNAMIC SIZING (+50%/-50%) WITH SURGICAL FILTER')
print('Filter: SHORT + Move Size < 0.9% (removes 7/20 worst losers, keeps 50/55 winners)')
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
    result = backtest_dynamic_filtered(df.copy(), month_name)
    results.append(result)

print(f"\n{'Month':<12} {'Trades':<8} {'L/S':<8} {'Signals':<10} {'Filtered':<10} {'W/L':<8} {'WR%':<6} "
      f"{'Gross Profit':<13} {'Gross Loss':<13} {'PF':<8} {'Return':<10} {'Max DD':<9} {'R/DD':<9}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting_eq = cumulative_equity
    ending_eq = r['final_equity'] if r['trades'] == 0 else starting_eq * (1 + r['total_return'] / 100)
    cumulative_equity = ending_eq

    wl_str = f"{r['winners']}/{r['losers']}"
    ls_str = f"{r.get('long_trades', 0)}/{r.get('short_trades', 0)}"
    status = '✅' if r['total_return'] > 0 else '❌'

    print(f"{r['month']:<12} {r['trades']:<8} {ls_str:<8} {r['signals_total']:<10} {r['signals_filtered']:<10} "
          f"{wl_str:<8} {r['win_rate']:>5.1f}% ${r['gross_profit']:>11.2f} ${r['gross_loss']:>11.2f} "
          f"{r['profit_factor']:>7.2f}x {r['total_return']:>+9.1f}% {r['max_dd']:>+8.2f}% "
          f"{r['return_dd']:>8.2f}x {status}")

# Summary
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

print(f'\n💰 FINAL: ${cumulative_equity:,.2f} ({((cumulative_equity-100)/100*100):+.1f}%)')

# Overall stats
total_trades = sum(r['trades'] for r in results)
total_signals = sum(r['signals_total'] for r in results)
total_filtered = sum(r['signals_filtered'] for r in results)
total_winners = sum(r['winners'] for r in results)
total_gross_profit = sum(r['gross_profit'] for r in results)
total_gross_loss = sum(r['gross_loss'] for r in results)
overall_pf = total_gross_profit / total_gross_loss if total_gross_loss > 0 else 0

# Calculate overall max DD
all_equity = [100.0]
eq = 100.0
for r in results:
    if r['trades'] > 0:
        eq = eq * (1 + r['total_return'] / 100)
    all_equity.append(eq)

eq_series = pd.Series(all_equity)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
overall_max_dd = drawdown.min()
overall_return_dd = ((cumulative_equity-100)/100*100) / abs(overall_max_dd) if overall_max_dd != 0 else 0

print('\\n' + '=' * 140)
print('OVERALL STATISTICS')
print('=' * 140)
print(f"Total Signals: {total_signals}")
print(f"Signals Filtered: {total_filtered} ({total_filtered/total_signals*100:.1f}%)")
print(f"Total Trades: {total_trades}")
print(f"Win Rate: {(total_winners/total_trades*100):.1f}%")
print(f"Gross Profit: ${total_gross_profit:.2f}")
print(f"Gross Loss: ${total_gross_loss:.2f}")
print(f"Profit Factor: {overall_pf:.2f}x")
print(f"Final Return: {((cumulative_equity-100)/100*100):+.1f}%")
print(f"Max Drawdown: {overall_max_dd:+.2f}%")
print(f"Return/DD Ratio: {overall_return_dd:.2f}x")

print('\n' + '=' * 140)
print('COMPARISON TO BASELINE')
print('=' * 140)
print(f"{'Strategy':<30} {'Trades':<10} {'Return':<12} {'Max DD':<12} {'R/DD':<10}")
print('-' * 140)
print(f"{'Baseline (Fixed 12% Risk)':<30} {151:<10} {'+106.6%':<12} {'-97.3%':<12} {'1.10x':<10}")
print(f"{'Dynamic +50%/-50%':<30} {151:<10} {'+2,262.7%':<12} {'-80.0%':<12} {'28.28x':<10}")
print(f"{'Dynamic + Surgical Filter':<30} {total_trades:<10} {f'+{((cumulative_equity-100)/100*100):.1f}%':<12} {f'{overall_max_dd:+.1f}%':<12} {f'{overall_return_dd:.2f}x':<10}")

print('\n' + '=' * 140)
