"""
Regime-Level Filters: Turn Trading ON/OFF Based on Market State
Goal: Filter out entire losing periods while keeping winners
Aim for 30-40 total trades across 7 months
"""
import pandas as pd
import numpy as np

def calculate_adx(df, period=14):
    """Calculate ADX (trend strength indicator)"""
    # Directional movement
    df['high_diff'] = df['high'].diff()
    df['low_diff'] = -df['low'].diff()

    df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
    df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)

    # True range already calculated
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))

    # Smoothed indicators
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/period, adjust=False).mean() /
                            df['tr'].ewm(alpha=1/period, adjust=False).mean())
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/period, adjust=False).mean() /
                             df['tr'].ewm(alpha=1/period, adjust=False).mean())

    # ADX
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()

    return df

def backtest_with_regime_filter(df, month_name, regime_type, regime_threshold):
    """
    Test different regime filters:
    - 'atr_percentile': Only trade when ATR in top X% of last 90 days
    - 'adx': Only trade when ADX > threshold (trending market)
    - 'atr_ratio': Only trade when ATR_30d / ATR_90d > threshold
    - 'signal_quality': Only trade when recent signals have positive follow-through
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

    # Calculate regime indicators
    if regime_type == 'atr_percentile':
        df['atr_rank'] = df['atr'].rolling(576).rank(pct=True)  # 576 bars = 6 days
        df['regime_active'] = df['atr_rank'] > regime_threshold

    elif regime_type == 'adx':
        df = calculate_adx(df.copy())
        df['regime_active'] = df['adx'] > regime_threshold

    elif regime_type == 'atr_ratio':
        df['atr_30d'] = df['atr'].rolling(192).mean()  # 192 bars = 2 days
        df['atr_90d'] = df['atr'].rolling(576).mean()  # 576 bars = 6 days
        df['atr_ratio'] = df['atr_30d'] / df['atr_90d']
        df['regime_active'] = df['atr_ratio'] > regime_threshold

    elif regime_type == 'signal_quality':
        # Track forward returns after signals
        df['signal'] = 0
        df.loc[(df['rsi'].shift(1) < 35) & (df['rsi'] >= 35), 'signal'] = 1
        df.loc[(df['rsi'].shift(1) > 65) & (df['rsi'] <= 65), 'signal'] = -1

        # Calculate forward return 12 bars ahead (3 hours)
        df['fwd_ret_12'] = (df['close'].shift(-12) - df['close']) / df['close'] * 100

        # Rolling average of signal quality (last 20 signals)
        signal_quality = []
        for i in range(len(df)):
            if i < 100:
                signal_quality.append(False)
                continue

            recent_signals = df.iloc[max(0, i-384):i]  # Last 4 days
            signal_rows = recent_signals[recent_signals['signal'] != 0]

            if len(signal_rows) >= 5:
                avg_fwd = signal_rows['fwd_ret_12'].mean()
                signal_quality.append(avg_fwd > regime_threshold)
            else:
                signal_quality.append(False)

        df['regime_active'] = signal_quality

    trades = []
    signals_total = 0
    signals_filtered = 0
    equity = 100.0
    equity_curve = [100.0]
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue
        if pd.isna(row.get('regime_active')):
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
                trades.append({'pnl_pct': pnl_pct, 'exit': exit_type})
                position = None
                continue

        # Generate signals with REGIME FILTER
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= 0:
                continue
            if pd.isna(prev_row['rsi']):
                continue

            signal_triggered = False
            direction = None

            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                signal_triggered = True
                direction = 'LONG'
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                signal_triggered = True
                direction = 'SHORT'

            if signal_triggered:
                signals_total += 1

                # REGIME FILTER: Skip if regime not active
                if not row['regime_active']:
                    signals_filtered += 1
                    continue

                # Take trade
                signal_price = row['close']
                atr = row['atr']

                if direction == 'LONG':
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
                else:
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

    # Calculate time in regime
    regime_active_pct = (df['regime_active'].sum() / len(df) * 100) if len(df) > 0 else 0

    if not trades:
        return {
            'month': month_name,
            'regime_type': regime_type,
            'regime_threshold': regime_threshold,
            'trades': 0,
            'signals_total': signals_total,
            'signals_filtered': signals_filtered,
            'regime_active_pct': regime_active_pct,
            'total_return': 0,
            'final_equity': equity
        }

    df_t = pd.DataFrame(trades)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = df_t[df_t['pnl_pct'] > 0]

    return {
        'month': month_name,
        'regime_type': regime_type,
        'regime_threshold': regime_threshold,
        'trades': len(df_t),
        'signals_total': signals_total,
        'signals_filtered': signals_filtered,
        'regime_active_pct': regime_active_pct,
        'winners': len(winners),
        'win_rate': len(winners) / len(df_t) * 100,
        'total_return': ((equity - 100) / 100) * 100,
        'max_dd': max_dd,
        'final_equity': equity
    }

print('=' * 160)
print('REGIME FILTER TESTING: Turn Trading ON/OFF for Entire Periods')
print('Goal: 30-40 trades, filter out losing months')
print('=' * 160)

months = [
    ('June', 'melania_june_2025_15m.csv', 'LOSER'),
    ('July', 'melania_july_2025_15m.csv', 'LOSER'),
    ('August', 'melania_august_2025_15m.csv', 'LOSER'),
    ('September', 'melania_september_2025_15m.csv', 'LOSER'),
    ('October', 'melania_october_2025_15m.csv', 'WINNER'),
    ('November', 'melania_november_2025_15m.csv', 'WINNER'),
    ('December', 'melania_december_2025_15m.csv', 'WINNER'),
]

# Test different regime filters
test_configs = [
    ('atr_percentile', [0.5, 0.6, 0.7, 0.8]),  # Top 50%, 40%, 30%, 20%
    ('adx', [15, 20, 25, 30]),  # Trend strength threshold
    ('atr_ratio', [1.0, 1.1, 1.2, 1.3]),  # 30d ATR vs 90d ATR
    ('signal_quality', [-0.2, 0.0, 0.2, 0.3]),  # Recent signal avg return
]

all_results = []

for regime_type, thresholds in test_configs:
    print(f'\n{"="*160}')
    print(f'Testing {regime_type.upper()}')
    print('='*160)

    for threshold in thresholds:
        config_results = []

        for month_name, filename, category in months:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            result = backtest_with_regime_filter(df.copy(), month_name, regime_type, threshold)
            result['category'] = category
            config_results.append(result)

        # Aggregate
        losers = [r for r in config_results if r['category'] == 'LOSER']
        winners = [r for r in config_results if r['category'] == 'WINNER']

        loser_trades = sum(r['trades'] for r in losers)
        winner_trades = sum(r['trades'] for r in winners)
        total_trades = loser_trades + winner_trades

        # Cumulative equity
        cumulative_equity = 100.0
        for r in config_results:
            cumulative_equity = cumulative_equity * (1 + r['total_return'] / 100)

        total_return = ((cumulative_equity - 100) / 100) * 100

        summary = {
            'regime_type': regime_type,
            'threshold': threshold,
            'loser_trades': loser_trades,
            'winner_trades': winner_trades,
            'total_trades': total_trades,
            'total_return': total_return,
            'final_equity': cumulative_equity,
            'configs': config_results
        }
        all_results.append(summary)

        print(f'{regime_type} {threshold:>6.1f}: '
              f'Loser={loser_trades:3d} | Winner={winner_trades:3d} | '
              f'Total={total_trades:3d} | Return={total_return:+7.1f}%')

# Find best configs in 30-40 trade range
print('\n' + '=' * 160)
print('BEST CONFIGS WITH 30-40 TRADES')
print('=' * 160)

candidates = [r for r in all_results if 30 <= r['total_trades'] <= 50]
candidates_sorted = sorted(candidates, key=lambda x: x['total_return'], reverse=True)[:5]

print(f"\n{'Type':<18} {'Threshold':<10} {'Loser':<8} {'Winner':<8} {'Total':<8} {'Return':<10}")
print('-' * 160)

for r in candidates_sorted:
    print(f"{r['regime_type']:<18} {r['threshold']:<10.2f} {r['loser_trades']:<8} "
          f"{r['winner_trades']:<8} {r['total_trades']:<8} {r['total_return']:>+9.1f}%")

# Show monthly breakdown for best
if candidates_sorted:
    best = candidates_sorted[0]
    print('\n' + '=' * 160)
    print(f"BEST: {best['regime_type']} = {best['threshold']}")
    print('=' * 160)
    print(f"\n{'Month':<12} {'Cat':<7} {'Trades':<8} {'WR%':<6} {'Regime%':<10} {'Return':<10}")
    print('-' * 160)

    for r in best['configs']:
        wr = r.get('win_rate', 0)
        print(f"{r['month']:<12} {r['category']:<7} {r['trades']:<8} {wr:>5.1f}% "
              f"{r['regime_active_pct']:>9.1f}% {r['total_return']:>+9.1f}%")

print('\n' + '=' * 160)
