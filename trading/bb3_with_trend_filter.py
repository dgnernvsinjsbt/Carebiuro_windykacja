#!/usr/bin/env python3
"""
BB3 Strategy with Trend Filter
- LONG only in bullish regime
- SHORT only in bearish regime

Test different trend detection methods:
1. Price vs 200 EMA
2. 50 EMA vs 200 EMA (Golden/Death Cross)
3. Higher timeframe trend (1H)
4. ADX + DI for trend direction
"""
import pandas as pd
import numpy as np

# Load 1-minute ETH data
print("Loading ETH 1-minute data...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
print("Calculating indicators...")

# Bollinger Bands (20 period, 3 STD)
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper_3'] = df['bb_mid'] + 3 * df['bb_std']
df['bb_lower_3'] = df['bb_mid'] - 3 * df['bb_std']

# ATR for stops
df['atr'] = (df['high'] - df['low']).rolling(14).mean()

# TREND FILTERS
# 1. EMA 200
df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['trend_ema200'] = np.where(df['close'] > df['ema_200'], 'BULL', 'BEAR')

# 2. EMA 50 vs EMA 200
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['trend_ema_cross'] = np.where(df['ema_50'] > df['ema_200'], 'BULL', 'BEAR')

# 3. Higher timeframe (resample to 1H)
df_1h = df.set_index('timestamp').resample('1H').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

# Map 1H trend back to 1m data
df['timestamp_1h'] = df['timestamp'].dt.floor('1H')
trend_1h_map = df_1h['trend_1h'].to_dict()
df['trend_1h'] = df['timestamp_1h'].map(trend_1h_map)

# 4. Slope of EMA 200 (rising = bull, falling = bear)
df['ema_200_slope'] = df['ema_200'].diff(20)  # Change over 20 periods
df['trend_slope'] = np.where(df['ema_200_slope'] > 0, 'BULL', 'BEAR')

# Drop NaN
df = df.dropna().reset_index(drop=True)

# Entry signals
df['long_signal'] = df['close'] < df['bb_lower_3']
df['short_signal'] = df['close'] > df['bb_upper_3']

# FEES
MAKER_FEE = 0.0002   # 0.02%
TAKER_FEE = 0.0005   # 0.05%
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def backtest_with_filter(df, trend_col, use_limit=True):
    """
    Backtest BB3 with trend filter:
    - LONG when trend_col == 'BULL' and long_signal
    - SHORT when trend_col == 'BEAR' and short_signal
    """
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    entry_time = None
    stop_loss = 0
    take_profit = 0

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row[trend_col]

        if not in_position:
            # LONG entry in BULL trend
            if trend == 'BULL' and row['long_signal']:
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 4)

            # SHORT entry in BEAR trend
            elif trend == 'BEAR' and row['short_signal']:
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * 2)
                take_profit = entry_price - (atr * 4)

        else:
            high = row['high']
            low = row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'exit': stop_loss,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif high >= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'exit': take_profit,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

            elif position_type == 'SHORT':
                if high >= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'exit': stop_loss,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif low <= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'exit': take_profit,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)

    # Get max/min prices during trades for limit order simulation
    eth_data = df.set_index('timestamp')

    def get_extremes(row):
        try:
            mask = (eth_data.index >= row['entry_time']) & (eth_data.index <= row['exit_time'])
            data = eth_data.loc[mask]
            return pd.Series({'max_price': data['high'].max(), 'min_price': data['low'].min()})
        except:
            return pd.Series({'max_price': row['stop'], 'min_price': row['target']})

    extremes = trades_df.apply(get_extremes, axis=1)
    trades_df['max_price'] = extremes['max_price']
    trades_df['min_price'] = extremes['min_price']

    # Simulate with limit orders
    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit_price = signal * (1 - LIMIT_OFFSET)  # Below for longs
            filled = row['min_price'] <= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
        else:  # SHORT
            limit_price = signal * (1 + LIMIT_OFFSET)  # Above for shorts
            filled = row['max_price'] >= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_price) / entry * 100

        if not use_limit:
            filled = True
            entry = signal
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']
            if row['type'] == 'LONG':
                gross = (exit_price - entry) / entry * 100
            else:
                gross = (entry - exit_price) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100 if use_limit else (TAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results.append({
                'type': row['type'], 'filled': True, 'gross': gross,
                'fee': fee, 'net': net, 'balance': balance, 'win': gross > 0
            })
        else:
            results.append({
                'type': row['type'], 'filled': False, 'gross': 0,
                'fee': 0, 'net': 0, 'balance': balance, 'win': False
            })

    results_df = pd.DataFrame(results)
    filled_df = results_df[results_df['filled']]

    # Calculate stats
    bal = np.array([STARTING_BALANCE] + list(results_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    longs = filled_df[filled_df['type'] == 'LONG']
    shorts = filled_df[filled_df['type'] == 'SHORT']

    return {
        'total': len(trades_df),
        'filled': len(filled_df),
        'longs': len(longs),
        'shorts': len(shorts),
        'wins': filled_df['win'].sum(),
        'losses': len(filled_df) - filled_df['win'].sum(),
        'win_rate': filled_df['win'].sum() / len(filled_df) * 100 if len(filled_df) > 0 else 0,
        'long_wins': longs['win'].sum() if len(longs) > 0 else 0,
        'short_wins': shorts['win'].sum() if len(shorts) > 0 else 0,
        'gross': filled_df['gross'].sum(),
        'fees': filled_df['fee'].sum(),
        'net': filled_df['net'].sum(),
        'max_dd': dd.min(),
        'final_balance': balance,
        'profit': balance - STARTING_BALANCE
    }

# Test all filters
print("\n" + "=" * 90)
print("BB3 WITH TREND FILTERS - COMPARISON")
print("=" * 90)

filters = {
    'No Filter (Long only)': None,
    'EMA 200': 'trend_ema200',
    'EMA 50/200 Cross': 'trend_ema_cross',
    '1H Timeframe': 'trend_1h',
    'EMA 200 Slope': 'trend_slope'
}

results_summary = []

for name, trend_col in filters.items():
    if trend_col is None:
        # Long only baseline
        trades = []
        in_position = False

        for i in range(len(df)):
            row = df.iloc[i]
            if not in_position and row['long_signal']:
                in_position = True
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 4)
            elif in_position:
                if df.iloc[i]['low'] <= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'LONG', 'entry': entry_price, 'exit': stop_loss,
                                   'stop': stop_loss, 'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif df.iloc[i]['high'] >= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'LONG', 'entry': entry_price, 'exit': take_profit,
                                   'stop': stop_loss, 'target': take_profit, 'result': 'TP'})
                    in_position = False

        trades_df = pd.DataFrame(trades)
        eth_data = df.set_index('timestamp')

        balance = STARTING_BALANCE
        results = []
        for _, row in trades_df.iterrows():
            try:
                mask = (eth_data.index >= row['entry_time']) & (eth_data.index <= row['exit_time'])
                min_price = eth_data.loc[mask]['low'].min()
            except:
                min_price = row['stop']

            signal = row['entry']
            limit_price = signal * (1 - LIMIT_OFFSET)
            filled = min_price <= limit_price

            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
                fee = (MAKER_FEE + TAKER_FEE) * 100
                net = gross - fee
                pnl = balance * (net / 100)
                balance += pnl
                results.append({'filled': True, 'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0})
            else:
                results.append({'filled': False, 'gross': 0, 'net': 0, 'balance': balance, 'win': False})

        results_df = pd.DataFrame(results)
        filled_df = results_df[results_df['filled']]
        bal = np.array([STARTING_BALANCE] + list(results_df['balance']))
        peak = np.maximum.accumulate(bal)
        dd = (bal - peak) / peak * 100

        stats = {
            'name': name,
            'total': len(trades_df),
            'filled': len(filled_df),
            'longs': len(filled_df),
            'shorts': 0,
            'wins': int(filled_df['win'].sum()),
            'losses': int(len(filled_df) - filled_df['win'].sum()),
            'win_rate': filled_df['win'].sum() / len(filled_df) * 100,
            'net': filled_df['net'].sum(),
            'max_dd': dd.min(),
            'profit': balance - STARTING_BALANCE
        }
    else:
        result = backtest_with_filter(df, trend_col, use_limit=True)
        if result:
            stats = {
                'name': name,
                'total': result['total'],
                'filled': result['filled'],
                'longs': result['longs'],
                'shorts': result['shorts'],
                'wins': int(result['wins']),
                'losses': int(result['losses']),
                'win_rate': result['win_rate'],
                'net': result['net'],
                'max_dd': result['max_dd'],
                'profit': result['profit']
            }
        else:
            stats = {'name': name, 'total': 0, 'filled': 0, 'longs': 0, 'shorts': 0,
                     'wins': 0, 'losses': 0, 'win_rate': 0, 'net': 0, 'max_dd': 0, 'profit': 0}

    results_summary.append(stats)

# Print results
print(f"\n{'Filter':<22} {'Trades':<8} {'L/S':<10} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 90)

for s in results_summary:
    ls = f"{s['longs']}/{s['shorts']}"
    wl = f"{s['wins']}/{s['losses']}"
    print(f"{s['name']:<22} {s['filled']:<8} {ls:<10} {wl:<10} {s['win_rate']:.1f}%    {s['net']:>+.2f}%   {s['max_dd']:.2f}%    ${s['profit']:>+,.0f}")

# Find best filter
best = max(results_summary, key=lambda x: x['profit'])
print(f"\n{'='*90}")
print(f"BEST FILTER: {best['name']} → Net: {best['net']:.2f}%, Profit: ${best['profit']:+,.0f}")
print(f"{'='*90}")

# Generate detailed CSV for best filter
if best['name'] != 'No Filter (Long only)':
    best_col = filters[best['name']]
    print(f"\nGenerating detailed CSV for {best['name']}...")

    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row[best_col]

        if not in_position:
            if trend == 'BULL' and row['long_signal']:
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 4)
                entry_trend = trend

            elif trend == 'BEAR' and row['short_signal']:
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * 2)
                take_profit = entry_price - (atr * 4)
                entry_trend = trend

        else:
            high = row['high']
            low = row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'trend': entry_trend, 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif high >= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'trend': entry_trend, 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

            elif position_type == 'SHORT':
                if high >= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'trend': entry_trend, 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif low <= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'trend': entry_trend, 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

    trades_df = pd.DataFrame(trades)
    trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_trend_filter_best.csv', index=False)
    print(f"Saved: bb3_trend_filter_best.csv")
