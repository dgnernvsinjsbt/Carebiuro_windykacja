"""
Optimize risk floor for maximum R/DD
Test: 1%, 1.5%, 2%, 2.5%, 3% floors
Config: +50%/-50%, 0.8% filter, 30% max
"""
import pandas as pd
import numpy as np

def backtest_with_floor(df, month_name, min_risk_pct):
    """Test with specific floor"""

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
    min_risk = min_risk_pct / 100

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

                if pnl_pct > 0:
                    current_risk = min(current_risk * 1.5, max_risk)
                else:
                    current_risk = max(current_risk * 0.5, min_risk)

                trades.append({'pnl_pct': pnl_pct, 'pnl_dollar': pnl_dollar})
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
        return None

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return {
        'month': month_name,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity,
        'trades': len(trades)
    }

print('=' * 120)
print('OPTIMIZING RISK FLOOR FOR MAXIMUM R/DD')
print('Config: +50%/-50% Dynamic Sizing | 0.8% Surgical Filter | 30% Max Risk')
print('=' * 120)

months = [
    ('June', 'melania_june_2025_15m.csv'),
    ('July', 'melania_july_2025_15m.csv'),
    ('August', 'melania_august_2025_15m.csv'),
    ('September', 'melania_september_2025_15m.csv'),
    ('October', 'melania_october_2025_15m.csv'),
    ('November', 'melania_november_2025_15m.csv'),
    ('December', 'melania_december_2025_15m.csv'),
]

floors = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
all_results = []

for floor_pct in floors:
    config_results = []

    for month_name, filename in months:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        result = backtest_with_floor(df.copy(), month_name, floor_pct)
        if result:
            config_results.append(result)

    if not config_results:
        continue

    # Calculate cumulative
    cumulative_equity = 100.0
    for r in config_results:
        cumulative_equity = cumulative_equity * (1 + r['total_return'] / 100)

    # Calculate overall max DD
    all_equity = [100.0]
    eq = 100.0
    for r in config_results:
        eq = eq * (1 + r['total_return'] / 100)
        all_equity.append(eq)

    eq_series = pd.Series(all_equity)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    overall_max_dd = drawdown.min()

    total_return = ((cumulative_equity - 100) / 100) * 100
    return_dd = total_return / abs(overall_max_dd) if overall_max_dd != 0 else 0

    all_results.append({
        'floor': floor_pct,
        'total_return': total_return,
        'max_dd': overall_max_dd,
        'return_dd': return_dd,
        'final_equity': cumulative_equity,
        'trades': sum(r['trades'] for r in config_results),
        'results': config_results
    })

# Sort by R/DD
all_results.sort(key=lambda x: x['return_dd'], reverse=True)

print(f"\n{'Floor %':<10} {'Trades':<8} {'Return':<12} {'Max DD':<10} {'R/DD':<10} {'Final $':<12} {'Status'}")
print('-' * 120)

for r in all_results:
    status = '🏆' if r == all_results[0] else '⭐' if r['return_dd'] > 100 else '✅' if r['return_dd'] > 50 else ''
    print(f"{r['floor']:<10.1f} {r['trades']:<8} {r['total_return']:>+10.1f}% {r['max_dd']:>+9.2f}% "
          f"{r['return_dd']:>9.2f}x ${r['final_equity']:>10.2f} {status}")

# Show top 3 with monthly detail
print('\n' + '=' * 120)
print('TOP 3 CONFIGURATIONS')
print('=' * 120)

for i, config in enumerate(all_results[:3], 1):
    print(f"\n{i}. FLOOR = {config['floor']:.1f}% | R/DD = {config['return_dd']:.2f}x | Return = {config['total_return']:+.1f}% | Max DD = {config['max_dd']:+.2f}%")
    print('-' * 120)
    print(f"{'Month':<12} {'Return':<10} {'Max DD':<10} {'R/DD':<8} {'Equity':<12}")
    print('-' * 120)

    cumulative_equity = 100.0
    for r in config['results']:
        starting = cumulative_equity
        ending = starting * (1 + r['total_return'] / 100)
        monthly_rdd = abs(r['total_return'] / r['max_dd']) if r['max_dd'] != 0 else 0

        status = '✅' if r['total_return'] > 0 else '❌'
        print(f"{r['month']:<12} {r['total_return']:>+8.1f}% {r['max_dd']:>+9.2f}% {monthly_rdd:>7.2f} ${ending:>10.2f} {status}")

        cumulative_equity = ending

print('\n' + '=' * 120)
