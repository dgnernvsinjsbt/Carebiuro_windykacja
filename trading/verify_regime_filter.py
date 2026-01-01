"""
Test: Does range_288 > 23.76% regime filter actually work?
Backtest with filter ON vs OFF to verify it prevents bad month trading
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jun 2025', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc)),
    ('Jul-Aug 2025', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc)),
    ('Sep 2025', datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc)),
    ('Oct 2025', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc)),
    ('Nov 2025', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc)),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc)),
]

REGIME_THRESHOLD = 23.76  # range_288 threshold from analysis

def backtest_with_regime(df, use_regime_filter=True):
    """Backtest RSI 35/65 + ret_20 > 0% with optional regime filter"""
    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Regime filter check
        if use_regime_filter and pd.notna(row['range_288']):
            if row['range_288'] < REGIME_THRESHOLD:
                # Close any open position if regime becomes unfavorable
                if position is not None:
                    pnl_pct = ((row['close'] - position['entry']) / position['entry']) * 100 if position['direction'] == 'LONG' else ((position['entry'] - row['close']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'equity': equity, 'exit': 'REGIME'})
                    position = None
                continue  # Don't trade in bad regime

        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL'})
                    position = None
                    continue
                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP'})
                    position = None
                    continue
            else:
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'SL'})
                    position = None
                    continue
                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100, 'equity': equity, 'exit': 'TP'})
                    position = None
                    continue

        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry = row['close']
                    sl = entry - (row['atr'] * 2.0)
                    tp = entry + (row['atr'] * 3.0)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry = row['close']
                    sl = entry + (row['atr'] * 2.0)
                    tp = entry - (row['atr'] * 3.0)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity - 100) / 100) * 100
    eq = [100.0] + df_t['equity'].tolist()
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100

    return {
        'trades': len(df_t),
        'win_rate': win_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0,
        'equity': equity
    }

print('=' * 80)
print('REGIME FILTER VERIFICATION')
print(f'Filter: range_288 > {REGIME_THRESHOLD:.2f}%')
print('=' * 80)

results_no_filter = []
results_with_filter = []

for name, start, end in months:
    print(f'\nProcessing {name}...')

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles: break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)
        except:
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) & (df['timestamp'] <= end.replace(tzinfo=None))].sort_values('timestamp').reset_index(drop=True)

    # Calculate indicators
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    # Regime indicator
    df['range_288'] = ((df['high'].rolling(288).max() - df['low'].rolling(288).min()) / df['low'].rolling(288).min()) * 100

    avg_range_288 = df['range_288'].mean()

    # Backtest without filter
    result_no = backtest_with_regime(df, use_regime_filter=False)
    # Backtest with filter
    result_with = backtest_with_regime(df, use_regime_filter=True)

    if result_no:
        result_no['month'] = name
        result_no['avg_range_288'] = avg_range_288
        results_no_filter.append(result_no)

    if result_with:
        result_with['month'] = name
        result_with['avg_range_288'] = avg_range_288
        results_with_filter.append(result_with)

    print(f'  Avg Range288: {avg_range_288:.2f}% {"✅ GOOD" if avg_range_288 > REGIME_THRESHOLD else "❌ BAD"}')
    if result_no:
        print(f'  NO FILTER:   {result_no["trades"]} trades, {result_no["win_rate"]:.1f}% win, {result_no["return"]:+.0f}%, {result_no["return_dd"]:.2f}x R/DD')
    if result_with:
        print(f'  WITH FILTER: {result_with["trades"]} trades, {result_with["win_rate"]:.1f}% win, {result_with["return"]:+.0f}%, {result_with["return_dd"]:.2f}x R/DD')

print('\n' + '=' * 80)
print('SUMMARY - NO FILTER:')
print('=' * 80)

df_no = pd.DataFrame(results_no_filter)
total_trades_no = df_no['trades'].sum()
overall_equity_no = df_no['equity'].iloc[-1] if len(df_no) > 0 else 100
overall_return_no = ((overall_equity_no - 100) / 100) * 100

print(f'\nTotal trades: {total_trades_no}')
print(f'Final equity: ${overall_equity_no:.2f}')
print(f'Total return: {overall_return_no:+.2f}%')

print('\n' + '=' * 80)
print('SUMMARY - WITH REGIME FILTER:')
print('=' * 80)

df_with = pd.DataFrame(results_with_filter)
total_trades_with = df_with['trades'].sum()
overall_equity_with = df_with['equity'].iloc[-1] if len(df_with) > 0 else 100
overall_return_with = ((overall_equity_with - 100) / 100) * 100

print(f'\nTotal trades: {total_trades_with}')
print(f'Final equity: ${overall_equity_with:.2f}')
print(f'Total return: {overall_return_with:+.2f}%')

if total_trades_no > 0 and total_trades_with > 0:
    print('\n' + '=' * 80)
    print('FILTER EFFECTIVENESS:')
    print('=' * 80)

    print(f'\nTrades filtered out: {total_trades_no - total_trades_with} ({(1 - total_trades_with/total_trades_no)*100:.0f}%)')
    print(f'Return improvement: {overall_return_no:+.2f}% → {overall_return_with:+.2f}% ({overall_return_with - overall_return_no:+.2f}% points)')

    if overall_return_with > overall_return_no * 1.5:
        print(f'\n✅ FILTER WORKS! Return improved by {((overall_return_with / overall_return_no) - 1) * 100:+.0f}%')
    elif overall_return_with > overall_return_no:
        print(f'\n⚠️  Small improvement ({overall_return_with - overall_return_no:+.1f}%) - may need more data')
    else:
        print(f'\n❌ FILTER HURTS! Return decreased by {overall_return_no - overall_return_with:.1f}%')

df_no.to_csv('regime_test_no_filter.csv', index=False)
df_with.to_csv('regime_test_with_filter.csv', index=False)
print(f'\n💾 Saved: regime_test_no_filter.csv, regime_test_with_filter.csv')
