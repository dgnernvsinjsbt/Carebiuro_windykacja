"""
Optimize risk scaling for MAXIMUM R/DD
Test more aggressive downsizing after losses
Filter: SHORT + Move < 0.8%
"""
import pandas as pd
import numpy as np

def backtest_custom_scaling(df, month_name, win_mult, loss_mult, min_risk=0.05, filter_threshold=0.8):
    """Test custom risk scaling"""

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

                # Custom dynamic sizing
                if pnl_pct > 0:
                    current_risk = min(current_risk * win_mult, max_risk)
                else:
                    current_risk = max(current_risk * loss_mult, min_risk)

                trades.append({'pnl_pct': pnl_pct, 'pnl_dollar': pnl_dollar, 'exit': exit_type})
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
                # SURGICAL FILTER
                if row['avg_move_size'] < filter_threshold:
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

print('=' * 140)
print('OPTIMIZING RISK SCALING FOR MAXIMUM R/DD')
print('Filter: SHORT + Move < 0.8%')
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

# Test configurations
configs = [
    # (win_mult, loss_mult, min_risk, name)
    (1.5, 0.50, 0.05, '+50%/-50% (baseline)'),
    (1.5, 0.40, 0.05, '+50%/-60%'),
    (1.5, 0.30, 0.05, '+50%/-70%'),
    (1.5, 0.50, 0.03, '+50%/-50% floor=3%'),
    (1.5, 0.40, 0.03, '+50%/-60% floor=3%'),
    (1.5, 0.30, 0.03, '+50%/-70% floor=3%'),
    (1.5, 0.50, 0.02, '+50%/-50% floor=2%'),
    (1.5, 0.40, 0.02, '+50%/-60% floor=2%'),
    (1.5, 0.30, 0.02, '+50%/-70% floor=2%'),
    (1.6, 0.40, 0.03, '+60%/-60% floor=3%'),
    (1.6, 0.30, 0.03, '+60%/-70% floor=3%'),
    (1.7, 0.30, 0.03, '+70%/-70% floor=3%'),
]

all_results = []

for win_mult, loss_mult, min_risk, config_name in configs:
    config_results = []

    for month_name, filename in months:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        result = backtest_custom_scaling(df.copy(), month_name, win_mult, loss_mult, min_risk)
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
        'name': config_name,
        'win_mult': win_mult,
        'loss_mult': loss_mult,
        'min_risk': min_risk,
        'total_return': total_return,
        'max_dd': overall_max_dd,
        'return_dd': return_dd,
        'final_equity': cumulative_equity,
        'trades': sum(r['trades'] for r in config_results)
    })

# Sort by R/DD
all_results.sort(key=lambda x: x['return_dd'], reverse=True)

print(f"\n{'Config':<30} {'Trades':<8} {'Return':<12} {'Max DD':<10} {'R/DD':<10} {'Status'}")
print('-' * 140)

for r in all_results:
    status = '🏆' if r == all_results[0] else '⭐' if r['return_dd'] > 50 else '✅' if r['return_dd'] > 40 else ''
    print(f"{r['name']:<30} {r['trades']:<8} {r['total_return']:>+10.1f}% {r['max_dd']:>+9.2f}% "
          f"{r['return_dd']:>9.2f}x {status}")

# Show top 3 details
print('\n' + '=' * 140)
print('TOP 3 CONFIGURATIONS (by R/DD)')
print('=' * 140)

for i, r in enumerate(all_results[:3], 1):
    print(f"\n{i}. {r['name']}")
    print(f"   Win Multiplier: {r['win_mult']}x | Loss Multiplier: {r['loss_mult']}x | Min Risk Floor: {r['min_risk']*100:.0f}%")
    print(f"   Return: {r['total_return']:+.1f}% | Max DD: {r['max_dd']:+.2f}% | R/DD: {r['return_dd']:.2f}x")
    print(f"   Final Equity: ${r['final_equity']:,.2f}")

print('\n' + '=' * 140)
