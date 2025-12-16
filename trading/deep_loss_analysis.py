"""
DEEP ANALYSIS: Why do bad months fail?
- Are we hitting SL too often?
- Do we need wider SL or tighter TP?
- Is it the signal quality or the exit strategy?
- What's fundamentally different about price action?
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jun 2025', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc), 'BAD'),
    ('Jul-Aug 2025', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc), 'BAD'),
    ('Oct 2025', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc), 'GOOD'),
    ('Nov 2025', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc), 'GOOD'),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc), 'GOOD'),
]

def backtest_with_detail(df, sl_mult=2.0, tp_mult=3.0):
    """Backtest with detailed exit tracking"""
    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        if position:
            bars_held = i - position['entry_idx']
            bar = row

            if position['direction'] == 'LONG':
                # Check SL first
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'LONG',
                        'entry': position['entry'],
                        'exit': position['sl_price'],
                        'pnl_pct': pnl_pct,
                        'equity': equity,
                        'exit_type': 'SL',
                        'bars_held': bars_held,
                        'entry_atr': position['entry_atr'],
                        'entry_ret_20': position['entry_ret_20'],
                        'sl_mult': sl_mult,
                        'tp_mult': tp_mult
                    })
                    position = None
                    continue
                # Then check TP
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'LONG',
                        'entry': position['entry'],
                        'exit': position['tp_price'],
                        'pnl_pct': pnl_pct,
                        'equity': equity,
                        'exit_type': 'TP',
                        'bars_held': bars_held,
                        'entry_atr': position['entry_atr'],
                        'entry_ret_20': position['entry_ret_20'],
                        'sl_mult': sl_mult,
                        'tp_mult': tp_mult
                    })
                    position = None
                    continue
            else:  # SHORT
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'SHORT',
                        'entry': position['entry'],
                        'exit': position['sl_price'],
                        'pnl_pct': pnl_pct,
                        'equity': equity,
                        'exit_type': 'SL',
                        'bars_held': bars_held,
                        'entry_atr': position['entry_atr'],
                        'entry_ret_20': position['entry_ret_20'],
                        'sl_mult': sl_mult,
                        'tp_mult': tp_mult
                    })
                    position = None
                    continue
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({
                        'direction': 'SHORT',
                        'entry': position['entry'],
                        'exit': position['tp_price'],
                        'pnl_pct': pnl_pct,
                        'equity': equity,
                        'exit_type': 'TP',
                        'bars_held': bars_held,
                        'entry_atr': position['entry_atr'],
                        'entry_ret_20': position['entry_ret_20'],
                        'sl_mult': sl_mult,
                        'tp_mult': tp_mult
                    })
                    position = None
                    continue

        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                # RSI 35 cross (LONG)
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry = row['close']
                    sl = entry - (row['atr'] * sl_mult)
                    tp = entry + (row['atr'] * tp_mult)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {
                        'direction': 'LONG',
                        'entry': entry,
                        'sl_price': sl,
                        'tp_price': tp,
                        'size': size,
                        'entry_idx': i,
                        'entry_atr': row['atr'],
                        'entry_ret_20': row['ret_20']
                    }
                # RSI 65 cross (SHORT)
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry = row['close']
                    sl = entry + (row['atr'] * sl_mult)
                    tp = entry - (row['atr'] * tp_mult)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {
                        'direction': 'SHORT',
                        'entry': entry,
                        'sl_price': sl,
                        'tp_price': tp,
                        'size': size,
                        'entry_idx': i,
                        'entry_atr': row['atr'],
                        'entry_ret_20': row['ret_20']
                    }

    return pd.DataFrame(trades) if trades else None

all_trades = []

print('=' * 80)
print('DEEP ANALYSIS: Good vs Bad Months - Exit Pattern Analysis')
print('=' * 80)

for name, start, end, quality in months:
    print(f'\n{name} ({quality}):')

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

    # Backtest with current params (2.0 SL, 3.0 TP)
    trades = backtest_with_detail(df, sl_mult=2.0, tp_mult=3.0)

    if trades is not None and len(trades) > 0:
        trades['month'] = name
        trades['quality'] = quality

        tp_rate = (trades['exit_type'] == 'TP').sum() / len(trades) * 100
        sl_rate = (trades['exit_type'] == 'SL').sum() / len(trades) * 100
        win_rate = (trades['pnl_pct'] > 0).sum() / len(trades) * 100

        print(f'  Total trades: {len(trades)}')
        print(f'  Win rate: {win_rate:.1f}%')
        print(f'  TP rate: {tp_rate:.1f}% | SL rate: {sl_rate:.1f}%')
        print(f'  Avg winner: {trades[trades["pnl_pct"] > 0]["pnl_pct"].mean():.2f}%')
        print(f'  Avg loser: {trades[trades["pnl_pct"] < 0]["pnl_pct"].mean():.2f}%')
        print(f'  Avg bars held (winners): {trades[trades["pnl_pct"] > 0]["bars_held"].mean():.1f}')
        print(f'  Avg bars held (losers): {trades[trades["pnl_pct"] < 0]["bars_held"].mean():.1f}')

        all_trades.append(trades)

print('\n' + '=' * 80)
print('COMPARISON: BAD vs GOOD months')
print('=' * 80)

df_all = pd.concat(all_trades, ignore_index=True)
bad = df_all[df_all['quality'] == 'BAD']
good = df_all[df_all['quality'] == 'GOOD']

print(f'\nBAD MONTHS ({len(bad)} trades):')
print(f'  TP exits: {(bad["exit_type"] == "TP").sum()} ({(bad["exit_type"] == "TP").sum()/len(bad)*100:.1f}%)')
print(f'  SL exits: {(bad["exit_type"] == "SL").sum()} ({(bad["exit_type"] == "SL").sum()/len(bad)*100:.1f}%)')
print(f'  Win rate: {(bad["pnl_pct"] > 0).sum()/len(bad)*100:.1f}%')
print(f'  Avg winner: {bad[bad["pnl_pct"] > 0]["pnl_pct"].mean():.2f}%')
print(f'  Avg loser: {bad[bad["pnl_pct"] < 0]["pnl_pct"].mean():.2f}%')
print(f'  Avg bars to SL: {bad[bad["exit_type"] == "SL"]["bars_held"].mean():.1f}')
print(f'  Avg bars to TP: {bad[bad["exit_type"] == "TP"]["bars_held"].mean():.1f}')

print(f'\nGOOD MONTHS ({len(good)} trades):')
print(f'  TP exits: {(good["exit_type"] == "TP").sum()} ({(good["exit_type"] == "TP").sum()/len(good)*100:.1f}%)')
print(f'  SL exits: {(good["exit_type"] == "SL").sum()} ({(good["exit_type"] == "SL").sum()/len(good)*100:.1f}%)')
print(f'  Win rate: {(good["pnl_pct"] > 0).sum()/len(good)*100:.1f}%')
print(f'  Avg winner: {good[good["pnl_pct"] > 0]["pnl_pct"].mean():.2f}%')
print(f'  Avg loser: {good[good["pnl_pct"] < 0]["pnl_pct"].mean():.2f}%')
print(f'  Avg bars to SL: {good[good["exit_type"] == "SL"]["bars_held"].mean():.1f}')
print(f'  Avg bars to TP: {good[good["exit_type"] == "TP"]["bars_held"].mean():.1f}')

print('\n' + '=' * 80)
print('KEY DIFFERENCES:')
print('=' * 80)

bad_tp_rate = (bad["exit_type"] == "TP").sum()/len(bad)*100
good_tp_rate = (good["exit_type"] == "TP").sum()/len(good)*100

bad_sl_rate = (bad["exit_type"] == "SL").sum()/len(bad)*100
good_sl_rate = (good["exit_type"] == "SL").sum()/len(good)*100

print(f'\nTP Rate: BAD {bad_tp_rate:.1f}% vs GOOD {good_tp_rate:.1f}% ({good_tp_rate - bad_tp_rate:+.1f}% diff)')
print(f'SL Rate: BAD {bad_sl_rate:.1f}% vs GOOD {good_sl_rate:.1f}% ({good_sl_rate - bad_sl_rate:+.1f}% diff)')

if bad_tp_rate < good_tp_rate * 0.6:
    print(f'\n⚠️  BAD months hit TP {((1 - bad_tp_rate/good_tp_rate) * 100):.0f}% LESS often!')
    print('   → Maybe we need TIGHTER TP (price doesn\'t move far enough)?')
    print('   → Or WIDER SL (getting stopped too early)?')

# Test alternative params on bad months only
print('\n' + '=' * 80)
print('TESTING ALTERNATIVE PARAMS ON BAD MONTHS:')
print('=' * 80)

param_tests = [
    (1.5, 2.0, 'Tighter exits'),
    (2.5, 4.0, 'Wider exits'),
    (3.0, 3.0, 'Equal SL/TP'),
    (1.5, 4.0, 'Tight SL, Wide TP'),
]

for name, start, end, quality in months:
    if quality == 'BAD':
        print(f'\n{name}:')

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

        for sl, tp, desc in param_tests:
            trades = backtest_with_detail(df, sl_mult=sl, tp_mult=tp)
            if trades is not None and len(trades) > 0:
                ret = ((trades['equity'].iloc[-1] - 100) / 100) * 100
                win_rate = (trades['pnl_pct'] > 0).sum() / len(trades) * 100
                print(f'  SL {sl}x / TP {tp}x ({desc}): {len(trades)} trades, {win_rate:.1f}% win, {ret:+.1f}% return')

df_all.to_csv('detailed_trade_analysis.csv', index=False)
print(f'\n💾 Saved: detailed_trade_analysis.csv')