"""
Monthly breakdown in clean table format
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
    min_risk = 0.02

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
                        'size': pending_order['size'],
                        'risk_pct': current_risk
                    }
                    pending_order = None
            else:
                if row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size'],
                        'risk_pct': current_risk
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

                trades.append({
                    'direction': position['direction'],
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit': exit_type,
                    'risk_pct': position['risk_pct'] * 100,
                    'winner': pnl_pct > 0
                })

                if pnl_pct > 0:
                    current_risk = min(current_risk * 1.5, max_risk)
                else:
                    current_risk = max(current_risk * 0.5, min_risk)

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

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['winner']]
    losers = df_t[~df_t['winner']]

    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0

    for winner in df_t['winner']:
        if winner:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        else:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)

    return {
        'month': month_name,
        'trades': len(df_t),
        'long': len(df_t[df_t['direction'] == 'LONG']),
        'short': len(df_t[df_t['direction'] == 'SHORT']),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'avg_risk': df_t['risk_pct'].mean(),
        'min_risk': df_t['risk_pct'].min(),
        'max_risk': df_t['risk_pct'].max(),
        'gross_profit': winners['pnl_dollar'].sum() if len(winners) > 0 else 0,
        'gross_loss': abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0,
        'profit_factor': (winners['pnl_dollar'].sum() / abs(losers['pnl_dollar'].sum())) if len(losers) > 0 and losers['pnl_dollar'].sum() != 0 else 0,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity
    }

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
cumulative_equity = 100.0

for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    result = backtest_winner(df.copy(), month_name)
    if result:
        result['starting_equity'] = cumulative_equity
        ending_equity = cumulative_equity * (1 + result['total_return'] / 100)
        result['ending_equity'] = ending_equity
        result['cumulative_return'] = ((ending_equity - 100) / 100) * 100
        result['return_dd'] = abs(result['total_return'] / result['max_dd']) if result['max_dd'] != 0 else 0
        cumulative_equity = ending_equity
        results.append(result)

print('\n' + '=' * 180)
print('MONTHLY PERFORMANCE TABLE')
print('Config: +50%/-50% Dynamic Sizing | 2% Floor | 0.8% Surgical Filter')
print('=' * 180)

print(f"\n{'Month':<10} {'Trades':<7} {'L/S':<7} {'W/L':<7} {'WR%':<6} {'TP%':<6} {'MaxW':<5} {'MaxL':<5} "
      f"{'AvgR%':<7} {'MinR%':<7} {'MaxR%':<7} {'GP':<10} {'GL':<10} {'PF':<7} "
      f"{'Return':<9} {'MaxDD':<9} {'R/DD':<7} {'Start$':<10} {'End$':<11} {'Cum%':<10}")
print('-' * 180)

for r in results:
    ls_str = f"{r['long']}/{r['short']}"
    wl_str = f"{r['winners']}/{r['losers']}"

    print(f"{r['month']:<10} {r['trades']:<7} {ls_str:<7} {wl_str:<7} "
          f"{r['win_rate']:>5.1f} {r['tp_rate']:>5.1f} {r['max_win_streak']:>4} {r['max_loss_streak']:>4} "
          f"{r['avg_risk']:>6.1f} {r['min_risk']:>6.1f} {r['max_risk']:>6.1f} "
          f"${r['gross_profit']:>8.2f} ${r['gross_loss']:>8.2f} {r['profit_factor']:>6.2f} "
          f"{r['total_return']:>+8.1f}% {r['max_dd']:>+8.2f}% {r['return_dd']:>6.2f} "
          f"${r['starting_equity']:>8.2f} ${r['ending_equity']:>9.2f} {r['cumulative_return']:>+9.1f}%")

# Calculate overall stats
all_equity = [results[0]['starting_equity']]
for r in results:
    all_equity.append(r['ending_equity'])

eq_series = pd.Series(all_equity)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
overall_max_dd = drawdown.min()

total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
total_losers = sum(r['losers'] for r in results)
total_gp = sum(r['gross_profit'] for r in results)
total_gl = sum(r['gross_loss'] for r in results)
overall_pf = total_gp / total_gl if total_gl > 0 else 0
final_equity = results[-1]['ending_equity']
final_return = results[-1]['cumulative_return']
overall_rdd = final_return / abs(overall_max_dd) if overall_max_dd != 0 else 0

print('-' * 180)
print(f"{'TOTAL':<10} {total_trades:<7} {'':<7} {f'{total_winners}/{total_losers}':<7} "
      f"{(total_winners/total_trades*100):>5.1f} {'':<6} {'':<5} {'':<5} "
      f"{'':<7} {'':<7} {'':<7} "
      f"${total_gp:>8.2f} ${total_gl:>8.2f} {overall_pf:>6.2f} "
      f"{final_return:>+8.1f}% {overall_max_dd:>+8.2f}% {overall_rdd:>6.2f} "
      f"$   100.00 ${final_equity:>9.2f} {final_return:>+9.1f}%")

print('\n' + '=' * 180)
print('LEGEND')
print('=' * 180)
print('Trades = Total trades | L/S = Long/Short | W/L = Winners/Losers | WR% = Win Rate | TP% = Take Profit Rate')
print('MaxW = Max Win Streak | MaxL = Max Loss Streak')
print('AvgR% = Avg Risk % | MinR% = Min Risk % | MaxR% = Max Risk %')
print('GP = Gross Profit | GL = Gross Loss | PF = Profit Factor')
print('Return = Monthly Return % | MaxDD = Max Drawdown % | R/DD = Return/DD Ratio')
print('Start$ = Starting Equity | End$ = Ending Equity | Cum% = Cumulative Return %')
print('=' * 180)

# Summary stats
print('\n' + '=' * 180)
print('KEY INSIGHTS')
print('=' * 180)

loser_months = [r for r in results if r['total_return'] < 0]
winner_months = [r for r in results if r['total_return'] > 0]

print(f"\nLOSER MONTHS (Jun, Aug): {len(loser_months)} months")
print(f"  • Avg Risk: {sum(r['avg_risk'] for r in loser_months)/len(loser_months):.1f}%")
print(f"  • Min Risk Hit: {min(r['min_risk'] for r in loser_months):.1f}% (TURTLE MODE 🐢)")
print(f"  • Total Loss: {sum(r['total_return'] for r in loser_months):.1f}%")

print(f"\nWINNER MONTHS (Jul, Sep, Oct, Nov, Dec): {len(winner_months)} months")
print(f"  • Avg Risk: {sum(r['avg_risk'] for r in winner_months)/len(winner_months):.1f}%")
print(f"  • Max Risk Hit: {max(r['max_risk'] for r in winner_months):.1f}% (AGGRESSIVE 🚀)")
print(f"  • Total Gain: {sum(r['total_return'] for r in winner_months):.1f}%")

print(f"\nOVERALL:")
print(f"  • Final Return: {final_return:+.1f}%")
print(f"  • Max Drawdown: {overall_max_dd:+.2f}%")
print(f"  • Return/DD Ratio: {overall_rdd:.2f}x 🏆")
print(f"  • Final Equity: ${final_equity:,.2f}")

print('\n' + '=' * 180)
