"""
CORRECTED signal vs fill analysis
Account for immediate stop-out prevention
"""
import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0
        downval = -delta if delta < 0 else 0
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi

def calculate_atr(df, period=14):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

# Configs with SL multipliers
configs = {
    'CRV-USDT': {'file': 'bingx-trading-bot/trading/crv_usdt_90d_1h.csv', 'rsi_low': 25, 'rsi_high': 70, 'offset': 1.5, 'sl': 1.0, 'tp': 1.5},
    'MELANIA-USDT': {'file': 'bingx-trading-bot/trading/melania_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 1.5, 'sl': 1.5, 'tp': 2.0},
    'AIXBT-USDT': {'file': 'bingx-trading-bot/trading/aixbt_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'offset': 1.5, 'sl': 2.0, 'tp': 1.0},
    'TRUMPSOL-USDT': {'file': 'bingx-trading-bot/trading/trumpsol_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'offset': 1.0, 'sl': 1.0, 'tp': 0.5},
    'UNI-USDT': {'file': 'bingx-trading-bot/trading/uni_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 2.0, 'sl': 1.0, 'tp': 1.0},
    'DOGE-USDT': {'file': 'bingx-trading-bot/trading/doge_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 1.0, 'sl': 1.5, 'tp': 1.0},
    'XLM-USDT': {'file': 'bingx-trading-bot/trading/xlm_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 1.5, 'sl': 1.5, 'tp': 1.5},
    'MOODENG-USDT': {'file': 'bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 2.0, 'sl': 1.5, 'tp': 1.5},
    'PEPE-USDT': {'file': 'bingx-trading-bot/trading/1000pepe_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'offset': 1.5, 'sl': 1.0, 'tp': 1.0},
}

print('='*120)
print('🔍 CORRECTED SIGNAL ANALYSIS - Accounting for Immediate Stop-Outs')
print('='*120)
print()

total_days = 87
results = []

for coin, config in configs.items():
    df = pd.read_csv(config['file'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['atr'] = calculate_atr(df, 14)

    rsi_low = config['rsi_low']
    rsi_high = config['rsi_high']
    offset_pct = config['offset']
    sl_mult = config['sl']
    tp_mult = config['tp']

    # Count signals and fills with full logic
    rsi_signals = 0
    limit_touched = 0
    valid_entries = 0
    immediate_stopouts = 0

    for i in range(20, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            continue

        # LONG signal
        if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
            rsi_signals += 1
            signal_price = current['close']
            limit_price = signal_price * (1 - offset_pct / 100)

            # Check if limit fills in next 5 bars
            filled = False
            for j in range(i+1, min(i+6, len(df))):
                if df.iloc[j]['low'] <= limit_price:
                    limit_touched += 1
                    filled = True

                    # Check if immediate stop-out
                    entry_atr = df.iloc[j]['atr']
                    stop_loss = limit_price - (sl_mult * entry_atr)

                    if df.iloc[j]['low'] > stop_loss:
                        valid_entries += 1
                    else:
                        immediate_stopouts += 1
                    break

        # SHORT signal
        elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
            rsi_signals += 1
            signal_price = current['close']
            limit_price = signal_price * (1 + offset_pct / 100)

            # Check if limit fills in next 5 bars
            filled = False
            for j in range(i+1, min(i+6, len(df))):
                if df.iloc[j]['high'] >= limit_price:
                    limit_touched += 1
                    filled = True

                    # Check if immediate stop-out
                    entry_atr = df.iloc[j]['atr']
                    stop_loss = limit_price + (sl_mult * entry_atr)

                    if df.iloc[j]['high'] < stop_loss:
                        valid_entries += 1
                    else:
                        immediate_stopouts += 1
                    break

    results.append({
        'coin': coin,
        'rsi_signals': rsi_signals,
        'limit_touched': limit_touched,
        'immediate_stopouts': immediate_stopouts,
        'valid_entries': valid_entries,
        'signals_per_day': rsi_signals / total_days,
        'fill_rate': (limit_touched / rsi_signals * 100) if rsi_signals > 0 else 0,
        'entry_rate': (valid_entries / rsi_signals * 100) if rsi_signals > 0 else 0,
        'stopout_pct': (immediate_stopouts / limit_touched * 100) if limit_touched > 0 else 0
    })

results_df = pd.DataFrame(results).sort_values('rsi_signals', ascending=False)

print(f'{"Coin":<15} {"RSI Signals":<12} {"Limit Fills":<12} {"Stopouts":<10} {"Valid Entries":<14} {"Entry Rate"}')
print('-'*120)

for _, row in results_df.iterrows():
    print(f'{row["coin"]:<15} {row["rsi_signals"]:<12} {row["limit_touched"]:<12} '
          f'{row["immediate_stopouts"]:<10} {row["valid_entries"]:<14} {row["entry_rate"]:.1f}%')

print()
print(f'{"TOTALS:":<15} {results_df["rsi_signals"].sum():<12} {results_df["limit_touched"].sum():<12} '
      f'{results_df["immediate_stopouts"].sum():<10} {results_df["valid_entries"].sum():<14}')
print()

# Summary stats
total_signals = results_df['rsi_signals'].sum()
total_touched = results_df['limit_touched'].sum()
total_stopouts = results_df['immediate_stopouts'].sum()
total_valid = results_df['valid_entries'].sum()

print('='*120)
print('📊 SIGNAL FUNNEL BREAKDOWN')
print('='*120)
print()
print(f'Step 1: RSI Crossover Signals       {total_signals:>6} (100.0%)')
print(f'Step 2: Limit Price Touched         {total_touched:>6} ({total_touched/total_signals*100:>5.1f}%) - {total_signals - total_touched} signals expired')
print(f'Step 3: Immediate Stop-Outs         {total_stopouts:>6} ({total_stopouts/total_touched*100:>5.1f}%) - filtered by stop check')
print(f'Step 4: Valid Position Entries      {total_valid:>6} ({total_valid/total_signals*100:>5.1f}%) - actual positions opened')
print()

print('='*120)
print('🎯 COMPARISON WITH PORTFOLIO TRADES')
print('='*120)
print()

# Load actual portfolio trades
trades_df = pd.read_csv('portfolio_trades_10pct.csv')
actual_trades = len(trades_df)

print(f'Valid Entries (from signal analysis): {total_valid}')
print(f'Actual Portfolio Trades:               {actual_trades}')
print(f'Difference:                            {total_valid - actual_trades}')
print()

if total_valid != actual_trades:
    print('⚠️ DISCREPANCY DETECTED!')
    print()
    print('Possible reasons:')
    print('1. Portfolio simulation may have additional filtering (e.g., already in position)')
    print('2. Some positions may not have exited by end of backtest period')
    print('3. Portfolio simulation prevents multiple positions in same coin')
    print()

    # Check per-coin
    print('PER-COIN COMPARISON:')
    print(f'{"Coin":<15} {"Valid Entries":<15} {"Actual Trades":<15} {"Difference"}')
    print('-'*70)
    for _, row in results_df.iterrows():
        coin = row['coin']
        valid = row['valid_entries']
        actual = len(trades_df[trades_df['coin'] == coin])
        diff = valid - actual
        print(f'{coin:<15} {valid:<15} {actual:<15} {diff:+}')

print()
