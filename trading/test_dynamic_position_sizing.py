"""
Dynamic Position Sizing Based on Win/Loss Streaks
- Increase size after wins
- Decrease size after losses
- Naturally scales up in hot streaks, down in cold streaks
"""
import pandas as pd
import numpy as np

def analyze_streaks(df, month_name):
    """Analyze win/loss streaks in a month"""

    # Basic indicators
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
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Check pending limit order
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

        # Manage active position
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
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type, 'winner': pnl_pct > 0})
                position = None
                continue

        # Generate signals
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
                size = (equity * 0.12) / (sl_dist / 100)

                pending_order = {
                    'direction': 'LONG',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                limit_price = signal_price + (atr * 0.1)
                sl_price = limit_price + (atr * 1.2)
                tp_price = limit_price - (atr * 3.0)
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

    # Analyze streaks
    df_t = pd.DataFrame(trades)

    # Calculate streaks
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    streaks = []

    for winner in df_t['winner']:
        if winner:
            if current_streak >= 0:
                current_streak += 1
            else:
                streaks.append(current_streak)
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            if current_streak <= 0:
                current_streak -= 1
            else:
                streaks.append(current_streak)
                current_streak = -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))

    if current_streak != 0:
        streaks.append(current_streak)

    # Calculate average streaks
    win_streaks = [s for s in streaks if s > 0]
    loss_streaks = [abs(s) for s in streaks if s < 0]

    avg_win_streak = np.mean(win_streaks) if win_streaks else 0
    avg_loss_streak = np.mean(loss_streaks) if loss_streaks else 0

    return {
        'month': month_name,
        'trades': len(df_t),
        'winners': (df_t['winner']).sum(),
        'win_rate': (df_t['winner']).sum() / len(df_t) * 100,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'avg_win_streak': avg_win_streak,
        'avg_loss_streak': avg_loss_streak,
        'total_return': ((equity - 100) / 100) * 100
    }

def backtest_dynamic_sizing(df, month_name, win_multiplier=1.2, loss_multiplier=0.8, max_risk=0.30):
    """
    Dynamic position sizing:
    - After win: multiply risk by win_multiplier
    - After loss: multiply risk by loss_multiplier
    - Cap at max_risk
    """

    # Basic indicators
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
    current_risk = 0.12  # Start at 12%

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Check pending limit order
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

        # Manage active position
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

                # DYNAMIC SIZING: Adjust risk based on outcome
                if pnl_pct > 0:  # Winner
                    current_risk = min(current_risk * win_multiplier, max_risk)
                else:  # Loser
                    current_risk = max(current_risk * loss_multiplier, 0.05)  # Min 5%

                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type, 'risk_used': current_risk})
                position = None
                continue

        # Generate signals with DYNAMIC RISK
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
                size = (equity * current_risk) / (sl_dist / 100)  # Use dynamic risk

                pending_order = {
                    'direction': 'LONG',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                limit_price = signal_price + (atr * 0.1)
                sl_price = limit_price + (atr * 1.2)
                tp_price = limit_price - (atr * 3.0)
                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)  # Use dynamic risk

                pending_order = {
                    'direction': 'SHORT',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

    if not trades:
        return {'month': month_name, 'trades': 0, 'total_return': 0, 'final_equity': equity}

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]

    return {
        'month': month_name,
        'trades': len(df_t),
        'winners': len(winners),
        'win_rate': len(winners) / len(df_t) * 100,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity
    }

print('=' * 140)
print('PART 1: WIN/LOSS STREAK ANALYSIS')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv', 'LOSER'),
    ('July', 'melania_july_2025_15m.csv', 'LOSER'),
    ('August', 'melania_august_2025_15m.csv', 'LOSER'),
    ('September', 'melania_september_2025_15m.csv', 'LOSER'),
    ('October', 'melania_october_2025_15m.csv', 'WINNER'),
    ('November', 'melania_november_2025_15m.csv', 'WINNER'),
    ('December', 'melania_december_2025_15m.csv', 'WINNER'),
]

streak_results = []

for month_name, filename, category in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = analyze_streaks(df.copy(), month_name)
    if result:
        result['category'] = category
        streak_results.append(result)

print(f"\n{'Month':<12} {'Cat':<7} {'Trades':<8} {'WR%':<6} {'Max W':<7} {'Max L':<7} "
      f"{'Avg W':<7} {'Avg L':<7} {'Return':<10}")
print('-' * 140)

for r in streak_results:
    print(f"{r['month']:<12} {r['category']:<7} {r['trades']:<8} {r['win_rate']:>5.1f}% "
          f"{r['max_win_streak']:<7} {r['max_loss_streak']:<7} {r['avg_win_streak']:<7.2f} "
          f"{r['avg_loss_streak']:<7.2f} {r['total_return']:>+9.1f}%")

# Summary
losers = [r for r in streak_results if r['category'] == 'LOSER']
winners = [r for r in streak_results if r['category'] == 'WINNER']

print('\n' + '=' * 140)
print('SUMMARY')
print('=' * 140)
print(f"\nLOSER MONTHS (Jun-Sep):")
print(f"  Avg max win streak: {np.mean([r['max_win_streak'] for r in losers]):.1f}")
print(f"  Avg max loss streak: {np.mean([r['max_loss_streak'] for r in losers]):.1f}")
print(f"  Avg win streak length: {np.mean([r['avg_win_streak'] for r in losers]):.2f}")
print(f"  Avg loss streak length: {np.mean([r['avg_loss_streak'] for r in losers]):.2f}")

print(f"\nWINNER MONTHS (Oct-Dec):")
print(f"  Avg max win streak: {np.mean([r['max_win_streak'] for r in winners]):.1f}")
print(f"  Avg max loss streak: {np.mean([r['max_loss_streak'] for r in winners]):.1f}")
print(f"  Avg win streak length: {np.mean([r['avg_win_streak'] for r in winners]):.2f}")
print(f"  Avg loss streak length: {np.mean([r['avg_loss_streak'] for r in winners]):.2f}")

# Test dynamic sizing
print('\n' + '=' * 140)
print('PART 2: DYNAMIC POSITION SIZING TEST')
print('=' * 140)

configs = [
    (1.1, 0.9, 'Conservative (+10%/-10%)'),
    (1.2, 0.8, 'Moderate (+20%/-20%)'),
    (1.3, 0.7, 'Aggressive (+30%/-30%)'),
    (1.5, 0.5, 'Very Aggressive (+50%/-50%)'),
]

for win_mult, loss_mult, label in configs:
    print(f'\n{label}:')

    cumulative_equity = 100.0
    for month_name, filename, category in months:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        result = backtest_dynamic_sizing(df.copy(), month_name, win_mult, loss_mult)

        starting = cumulative_equity
        cumulative_equity = starting * (1 + result['total_return'] / 100)

        print(f"  {month_name}: {result['trades']} trades, {result['total_return']:+.1f}% "
              f"(${starting:.2f} → ${cumulative_equity:.2f})")

    total_return = ((cumulative_equity - 100) / 100) * 100
    print(f"  FINAL: ${cumulative_equity:.2f} ({total_return:+.1f}%)")

print('\n' + '=' * 140)
