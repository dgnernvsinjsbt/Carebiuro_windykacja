"""
RISK-BASED POSITION SIZING - Risk 1% per trade
Position size calculated based on stop loss distance
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

def backtest_with_stop_info(df, coin_name, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, fee_pct=0.05):
    """Backtest that includes stop loss % for risk calculation"""
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['atr'] = calculate_atr(df, 14)

    trades = []
    position = None

    i = 20
    while i < len(df):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            i += 1
            continue

        # Exit logic
        if position is not None:
            exit_signal = None

            # Stop loss
            if position['side'] == 'LONG':
                if current['low'] <= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}
            else:
                if current['high'] >= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}

            # Take profit
            if not exit_signal:
                if position['side'] == 'LONG':
                    if current['high'] >= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'price': position['take_profit']}
                else:
                    if current['low'] <= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'price': position['take_profit']}

            # RSI exit
            if not exit_signal:
                if position['side'] == 'LONG':
                    if current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                        exit_signal = {'reason': 'RSI', 'price': current['close']}
                else:
                    if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                        exit_signal = {'reason': 'RSI', 'price': current['close']}

            if exit_signal:
                entry = position['entry_price']
                exit_price = exit_signal['price']

                if position['side'] == 'LONG':
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100

                pnl_pct -= (2 * fee_pct)

                trades.append({
                    'coin': coin_name,
                    'entry_time': position['entry_time'],
                    'exit_time': current['timestamp'],
                    'side': position['side'],
                    'entry_price': entry,
                    'exit_price': exit_price,
                    'stop_loss_pct': position['stop_loss_pct'],  # ADD THIS
                    'take_profit_pct': position['take_profit_pct'],  # ADD THIS
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_signal['reason']
                })
                position = None

        # Entry logic
        if position is None:
            # LONG signal
            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                filled = False
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_atr = df.iloc[j]['atr']
                        stop_loss = limit_price - (stop_atr_mult * entry_atr)
                        take_profit = limit_price + (tp_atr_mult * entry_atr)

                        if df.iloc[j]['low'] > stop_loss:
                            # Calculate stop/TP as % from entry
                            stop_loss_pct = abs((stop_loss - limit_price) / limit_price) * 100
                            take_profit_pct = abs((take_profit - limit_price) / limit_price) * 100

                            position = {
                                'entry_time': df.iloc[j]['timestamp'],
                                'side': 'LONG',
                                'entry_price': limit_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'stop_loss_pct': stop_loss_pct,
                                'take_profit_pct': take_profit_pct
                            }
                            i = j
                            filled = True
                        break

                if not filled:
                    i += 1
                    continue

            # SHORT signal
            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                filled = False
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        entry_atr = df.iloc[j]['atr']
                        stop_loss = limit_price + (stop_atr_mult * entry_atr)
                        take_profit = limit_price - (tp_atr_mult * entry_atr)

                        if df.iloc[j]['high'] < stop_loss:
                            stop_loss_pct = abs((stop_loss - limit_price) / limit_price) * 100
                            take_profit_pct = abs((take_profit - limit_price) / limit_price) * 100

                            position = {
                                'entry_time': df.iloc[j]['timestamp'],
                                'side': 'SHORT',
                                'entry_price': limit_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'stop_loss_pct': stop_loss_pct,
                                'take_profit_pct': take_profit_pct
                            }
                            i = j
                            filled = True
                        break

                if not filled:
                    i += 1
                    continue

        i += 1

    return pd.DataFrame(trades)

# Configs
COINS = {
    'CRV-USDT': {'file': 'bingx-trading-bot/trading/crv_usdt_90d_1h.csv', 'rsi_low': 25, 'rsi_high': 70, 'sl': 1.0, 'tp': 1.5, 'offset': 1.5},
    'MELANIA-USDT': {'file': 'bingx-trading-bot/trading/melania_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.5, 'tp': 2.0, 'offset': 1.5},
    'AIXBT-USDT': {'file': 'bingx-trading-bot/trading/aixbt_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'sl': 2.0, 'tp': 1.0, 'offset': 1.5},
    'TRUMPSOL-USDT': {'file': 'bingx-trading-bot/trading/trumpsol_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'sl': 1.0, 'tp': 0.5, 'offset': 1.0},
    'UNI-USDT': {'file': 'bingx-trading-bot/trading/uni_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.0, 'tp': 1.0, 'offset': 2.0},
    'DOGE-USDT': {'file': 'bingx-trading-bot/trading/doge_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.5, 'tp': 1.0, 'offset': 1.0},
    'XLM-USDT': {'file': 'bingx-trading-bot/trading/xlm_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.5, 'tp': 1.5, 'offset': 1.5},
    'MOODENG-USDT': {'file': 'bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.5, 'tp': 1.5, 'offset': 2.0},
    'PEPE-USDT': {'file': 'bingx-trading-bot/trading/1000pepe_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'sl': 1.0, 'tp': 1.0, 'offset': 1.5},
}

print('='*100)
print('💼 RISK-BASED POSITION SIZING - 1% Risk Per Trade')
print('='*100)
print()

# Collect all trades
all_trades = []
for coin, config in COINS.items():
    df = pd.read_csv(config['file'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    trades = backtest_with_stop_info(
        df, coin,
        rsi_low=config['rsi_low'],
        rsi_high=config['rsi_high'],
        limit_offset_pct=config['offset'],
        stop_atr_mult=config['sl'],
        tp_atr_mult=config['tp']
    )

    if len(trades) > 0:
        all_trades.append(trades)
        print(f'✅ {coin}: {len(trades)} trades')

combined = pd.concat(all_trades, ignore_index=True)
combined = combined.sort_values('exit_time').reset_index(drop=True)

print()
print(f'Total trades: {len(combined)}')
print()

# Risk-based simulation
RISK_PER_TRADE = 0.01  # 1% risk

equity = 1000.0
results = []

for idx, trade in combined.iterrows():
    # Calculate position size based on stop loss
    # Risk = Position Size * Stop Loss %
    # Position Size = Risk / Stop Loss %

    risk_amount = equity * RISK_PER_TRADE  # $10 if equity is $1000
    position_size = risk_amount / (trade['stop_loss_pct'] / 100)

    # Cap position size at 50% of equity (safety limit)
    max_position = equity * 0.50
    if position_size > max_position:
        position_size = max_position

    # Calculate actual P&L
    dollar_pnl = position_size * (trade['pnl_pct'] / 100)

    # Update equity
    equity += dollar_pnl

    # Record
    results.append({
        'exit_time': trade['exit_time'],
        'coin': trade['coin'],
        'side': trade['side'],
        'pnl_pct': trade['pnl_pct'],
        'stop_loss_pct': trade['stop_loss_pct'],
        'position_size': position_size,
        'position_pct': (position_size / (equity - dollar_pnl)) * 100,
        'dollar_pnl': dollar_pnl,
        'portfolio_impact': (dollar_pnl / (equity - dollar_pnl)) * 100,
        'equity': equity,
        'exit_reason': trade['exit_reason']
    })

results_df = pd.DataFrame(results)

# Calculate drawdown
results_df['peak'] = results_df['equity'].cummax()
results_df['drawdown'] = results_df['equity'] - results_df['peak']
results_df['drawdown_pct'] = (results_df['drawdown'] / results_df['peak']) * 100

# Stats
final_equity = results_df['equity'].iloc[-1]
total_return = ((final_equity - 1000) / 1000) * 100
max_dd = results_df['drawdown_pct'].min()
winners = len(results_df[results_df['pnl_pct'] > 0])
losers = len(results_df[results_df['pnl_pct'] < 0])

print('='*100)
print('📊 RISK-BASED RESULTS')
print('='*100)
print()
print(f'Starting: $1,000.00')
print(f'Final: ${final_equity:,.2f}')
print(f'Return: {total_return:+.2f}%')
print(f'Max DD: {max_dd:.2f}%')
print(f'Return/DD: {abs(total_return/max_dd):.2f}x')
print()
print(f'Trades: {len(results_df)}')
print(f'Winners: {winners} ({winners/len(results_df)*100:.1f}%)')
print(f'Losers: {losers} ({losers/len(results_df)*100:.1f}%)')
print()

# Compare to 10% fixed sizing
print('='*100)
print('📊 COMPARISON: Risk-Based vs Fixed 10%')
print('='*100)
print()

fixed_10_return = 35.19
fixed_10_dd = -1.69

print(f'{"Metric":<20} {"Fixed 10%":<15} {"Risk-Based 1%":<15} {"Difference"}')
print('-'*100)
print(f'{"Return":<20} {fixed_10_return:>13.2f}% {total_return:>13.2f}% {total_return-fixed_10_return:>+13.2f}%')
print(f'{"Max DD":<20} {fixed_10_dd:>13.2f}% {max_dd:>13.2f}% {max_dd-fixed_10_dd:>+13.2f}%')
print(f'{"Return/DD":<20} {abs(fixed_10_return/fixed_10_dd):>13.2f}x {abs(total_return/max_dd):>13.2f}x')
print()

# Show max loss examples
print('='*100)
print('🔍 LARGEST LOSSES - Risk-Based vs Fixed')
print('='*100)
print()

losers_df = results_df[results_df['pnl_pct'] < 0].sort_values('dollar_pnl')
print(f'{"Date":<20} {"Coin":<15} {"Trade Loss":<12} {"Position %":<12} {"Portfolio Impact"}')
print('-'*100)
for idx, row in losers_df.head(10).iterrows():
    print(f'{row["exit_time"].strftime("%Y-%m-%d %H:%M"):<20} {row["coin"]:<15} {row["pnl_pct"]:>10.2f}% {row["position_pct"]:>10.2f}% {row["portfolio_impact"]:>10.2f}%')

print()
print('With FIXED 10% sizing, those same trades would have been:')
print(f'{"Date":<20} {"Coin":<15} {"Trade Loss":<12} {"Fixed Impact"}')
print('-'*100)
for idx, row in losers_df.head(10).iterrows():
    fixed_impact = 0.10 * row['pnl_pct']
    print(f'{row["exit_time"].strftime("%Y-%m-%d %H:%M"):<20} {row["coin"]:<15} {row["pnl_pct"]:>10.2f}% {fixed_impact:>10.2f}%')

print()
results_df.to_csv('portfolio_RISK_BASED.csv', index=False)
print('💾 Saved: portfolio_RISK_BASED.csv')
