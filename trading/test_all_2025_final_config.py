"""
Test Final Optimized Config on ALL of 2025 (Jan-Dec)
Offset 0.1 ATR, SL 1.2x ATR, TP 3.0x ATR
Monthly breakdown for entire year
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

def download_month(month_num, year=2025):
    """Download fresh data for a specific month"""
    exchange = ccxt.bingx({'enableRateLimit': True})

    # Calculate date range
    if month_num == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month_num + 1
        next_year = year

    start = datetime(year, month_num, 1, tzinfo=timezone.utc)
    end = datetime(next_year, next_month, 1, tzinfo=timezone.utc)

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)
        except Exception as e:
            print(f'   Error downloading: {e}')
            time.sleep(2)
            continue

    if not all_candles:
        return None

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) &
            (df['timestamp'] < end.replace(tzinfo=None))].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    return df

def backtest_month(df, month_name, offset_atr=0.1, sl_atr=1.2, tp_atr=3.0, max_wait_bars=8):
    """Backtest single month with final optimized config"""

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
            else:
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
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type, 'direction': position['direction']})
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

                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    signals += 1
                    limit_price = signal_price - (atr * offset_atr)
                    sl_price = limit_price - (atr * sl_atr)
                    tp_price = limit_price + (atr * tp_atr)
                    sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    pending_order = {
                        'direction': 'LONG', 'limit_price': limit_price,
                        'sl_price': sl_price, 'tp_price': tp_price,
                        'size': size, 'signal_bar': i
                    }
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    signals += 1
                    limit_price = signal_price + (atr * offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    pending_order = {
                        'direction': 'SHORT', 'limit_price': limit_price,
                        'sl_price': sl_price, 'tp_price': tp_price,
                        'size': size, 'signal_bar': i
                    }

    if not trades:
        return {
            'month': month_name, 'trades': 0, 'signals': signals,
            'total_return': 0, 'max_dd': 0, 'return_dd': 0
        }

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]
    losers = df_t[df_t['pnl_pct'] < 0]

    return {
        'month': month_name,
        'trades': len(df_t),
        'signals': signals,
        'fill_rate': (len(trades) / signals * 100) if signals > 0 else 0,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(df_t) * 100,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'avg_win': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loss': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'return_dd': (((equity - 100) / 100) * 100) / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity
    }

print('=' * 140)
print('FINAL CONFIG - ALL OF 2025 (JAN-DEC)')
print('Offset: 0.1 ATR | SL: 1.2x ATR | TP: 3.0x ATR')
print('=' * 140)

month_names = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

existing_files = {
    'July': 'melania_july_2025_15m_fresh.csv',
    'August': 'melania_august_2025_15m_fresh.csv',
    'September': 'melania_september_2025_15m_fresh.csv',
    'October': 'melania_october_2025_15m_fresh.csv',
    'November': 'melania_november_2025_15m_fresh.csv',
    'December': 'melania_december_2025_15m_fresh.csv',
}

results = []

for month_num, month_name in enumerate(month_names, 1):
    print(f'\nProcessing {month_name} 2025...')

    # Check if we have existing file
    if month_name in existing_files:
        df = pd.read_csv(existing_files[month_name])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f'  Loaded from file: {len(df)} bars')
    else:
        print(f'  Downloading from BingX...')
        df = download_month(month_num)
        if df is None or len(df) == 0:
            print(f'  ⚠️  No data available')
            continue
        print(f'  Downloaded: {len(df)} bars')

    result = backtest_month(df.copy(), month_name)
    if result:
        results.append(result)

# MONTHLY OVERVIEW
print('\n' + '=' * 140)
print('MONTHLY OVERVIEW - ALL 2025')
print('=' * 140)
print(f"\n{'Month':<12} {'Trades':<8} {'W':<4} {'L':<4} {'WR%':<6} {'TP%':<6} "
      f"{'Return':<10} {'MaxDD':<9} {'R/DD':<9} {'Status'}")
print('-' * 140)

for r in results:
    status = '✅' if r['total_return'] > 0 else '❌' if r['total_return'] < -10 else '➖'
    print(f"{r['month']:<12} {r['trades']:<8} {r['winners']:<4} {r['losers']:<4} "
          f"{r['win_rate']:>5.1f}% {r['tp_rate']:>5.1f}% {r['total_return']:>+9.1f}% "
          f"{r['max_dd']:>+8.2f}% {r['return_dd']:>8.2f}x {status}")

# EQUITY CURVE
print('\n' + '=' * 140)
print('EQUITY PROGRESSION THROUGH 2025')
print('=' * 140)
print(f"\n{'Month':<12} {'Starting':<12} {'Ending':<14} {'Monthly':<10} {'Cumulative':<12}")
print('-' * 140)

cumulative_equity = 100.0
for r in results:
    starting = cumulative_equity
    ending = starting * (1 + r['total_return'] / 100)
    cumulative_return = ((ending - 100) / 100) * 100

    status = '📈' if r['total_return'] > 50 else '📉' if r['total_return'] < -50 else '  '
    print(f"{r['month']:<12} ${starting:>10.2f} ${ending:>12.2f} {r['total_return']:>+9.1f}% "
          f"{cumulative_return:>+11.1f}% {status}")

    cumulative_equity = ending

# QUARTERLY BREAKDOWN
print('\n' + '=' * 140)
print('QUARTERLY BREAKDOWN')
print('=' * 140)

quarters = {
    'Q1 (Jan-Mar)': results[0:3] if len(results) >= 3 else [],
    'Q2 (Apr-Jun)': results[3:6] if len(results) >= 6 else [],
    'Q3 (Jul-Sep)': results[6:9] if len(results) >= 9 else [],
    'Q4 (Oct-Dec)': results[9:12] if len(results) >= 12 else []
}

for quarter_name, quarter_results in quarters.items():
    if quarter_results:
        total_trades = sum(r['trades'] for r in quarter_results)
        total_winners = sum(r['winners'] for r in quarter_results)
        avg_wr = (total_winners / total_trades * 100) if total_trades > 0 else 0
        print(f"\n{quarter_name}:")
        print(f"  Trades: {total_trades}, Win Rate: {avg_wr:.1f}%")
        for r in quarter_results:
            print(f"    {r['month']}: {r['total_return']:>+8.1f}%")

# SUMMARY
print('\n' + '=' * 140)
print('2025 FULL YEAR SUMMARY')
print('=' * 140)

total_trades = sum(r['trades'] for r in results)
total_winners = sum(r['winners'] for r in results)
profitable_months = len([r for r in results if r['total_return'] > 0])
losing_months = len([r for r in results if r['total_return'] < 0])

print(f"\n📊 OVERALL:")
print(f"  Final equity: ${cumulative_equity:,.2f}")
print(f"  Total return: {((cumulative_equity - 100) / 100 * 100):+.1f}%")
print(f"  Total trades: {total_trades}")
print(f"  Win rate: {(total_winners / total_trades * 100):.1f}%")
print(f"  Profitable months: {profitable_months}/{len(results)}")
print(f"  Losing months: {losing_months}/{len(results)}")

best_month = max(results, key=lambda x: x['total_return'])
worst_month = min(results, key=lambda x: x['total_return'])

print(f"\n🏆 Best month: {best_month['month']} ({best_month['total_return']:+.1f}%)")
print(f"📉 Worst month: {worst_month['month']} ({worst_month['total_return']:+.1f}%)")

# Save
df_results = pd.DataFrame(results)
df_results.to_csv('all_2025_final_config.csv', index=False)
print(f'\n💾 Saved to: all_2025_final_config.csv')
