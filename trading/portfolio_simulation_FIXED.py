"""
FIXED PORTFOLIO SIMULATION - Correct chronological execution
Bug fix: Skip bars between signal and fill to prevent checking exits before entry
"""
import pandas as pd
import numpy as np
from datetime import datetime

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

def backtest_coin_FIXED(df, coin_name, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, fee_pct=0.05):
    """FIXED: Properly handle chronological execution"""
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
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss'], 'exit_time': current['timestamp']}
            else:
                if current['high'] >= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss'], 'exit_time': current['timestamp']}

            # Take profit
            if not exit_signal:
                if position['side'] == 'LONG':
                    if current['high'] >= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'exit_price': position['take_profit'], 'exit_time': current['timestamp']}
                else:
                    if current['low'] <= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'exit_price': position['take_profit'], 'exit_time': current['timestamp']}

            # RSI exit
            if not exit_signal:
                if position['side'] == 'LONG':
                    if current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                        exit_signal = {'reason': 'RSI', 'exit_price': current['close'], 'exit_time': current['timestamp']}
                else:
                    if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                        exit_signal = {'reason': 'RSI', 'exit_price': current['close'], 'exit_time': current['timestamp']}

            if exit_signal:
                entry = position['entry_price']
                exit_price = exit_signal['exit_price']

                if position['side'] == 'LONG':
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100

                pnl_pct -= (2 * fee_pct)

                trades.append({
                    'coin': coin_name,
                    'entry_time': position['entry_time'],
                    'exit_time': exit_signal['exit_time'],
                    'side': position['side'],
                    'entry_price': entry,
                    'exit_price': exit_price,
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

                # Check if fills in next 5 bars
                filled = False
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_atr = df.iloc[j]['atr']
                        stop_loss = limit_price - (stop_atr_mult * entry_atr)
                        take_profit = limit_price + (tp_atr_mult * entry_atr)

                        # Check immediate stop
                        if df.iloc[j]['low'] > stop_loss:
                            position = {
                                'entry_time': df.iloc[j]['timestamp'],
                                'side': 'LONG',
                                'entry_price': limit_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                            # CRITICAL FIX: Jump to fill bar to start checking exits from there
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
                            position = {
                                'entry_time': df.iloc[j]['timestamp'],
                                'side': 'SHORT',
                                'entry_price': limit_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                            # CRITICAL FIX: Jump to fill bar
                            i = j
                            filled = True
                        break

                if not filled:
                    i += 1
                    continue

        i += 1

    return pd.DataFrame(trades)

# Coin configurations (OPTIMIZED)
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

print('='*120)
print('💼 FIXED PORTFOLIO SIMULATION')
print('='*120)
print()

# Collect all trades
all_trades = []
for coin, config in COINS.items():
    df = pd.read_csv(config['file'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    trades = backtest_coin_FIXED(
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
combined = combined.sort_values('entry_time').reset_index(drop=True)

print()
print(f'Total trades: {len(combined)}')
print()

# Verify no time travel
time_issues = combined[combined['exit_time'] < combined['entry_time']]
if len(time_issues) > 0:
    print(f'❌ ERROR: {len(time_issues)} trades with exit BEFORE entry!')
    print(time_issues[['coin', 'entry_time', 'exit_time']])
    exit()
else:
    print('✅ Time verification passed (all exits after entries)')
    print()

# Portfolio simulation with 10% sizing
STARTING_EQUITY = 1000.0
equity = STARTING_EQUITY
portfolio_trades = []
open_positions = {}

for idx, trade in combined.iterrows():
    coin = trade['coin']

    # Can only have 1 position per coin
    if coin in open_positions:
        continue

    # Enter position
    position_size = equity * 0.10
    dollar_pnl = position_size * (trade['pnl_pct'] / 100)
    equity += dollar_pnl

    portfolio_trades.append({
        'time': trade['exit_time'],
        'coin': coin,
        'entry_time': trade['entry_time'],
        'exit_time': trade['exit_time'],
        'side': trade['side'],
        'pnl_pct': trade['pnl_pct'],
        'dollar_pnl': dollar_pnl,
        'equity': equity,
        'exit_reason': trade['exit_reason']
    })

    # Mark as having traded this coin (reset on next entry opportunity)
    open_positions[coin] = trade['exit_time']

    # Clear position tracking for coins whose positions have closed
    open_positions = {c: t for c, t in open_positions.items() if t > trade['entry_time']}

trades_df = pd.DataFrame(portfolio_trades)
trades_df['cumulative'] = trades_df['dollar_pnl'].cumsum()
trades_df['peak'] = trades_df['equity'].cummax()
trades_df['drawdown'] = trades_df['equity'] - trades_df['peak']
trades_df['dd_pct'] = (trades_df['drawdown'] / trades_df['peak']) * 100

print('='*120)
print('📊 REAL RESULTS')
print('='*120)
print()
print(f'Starting: ${STARTING_EQUITY:.2f}')
print(f'Final: ${equity:.2f}')
print(f'Return: {((equity/STARTING_EQUITY - 1)*100):+.2f}%')
print(f'Max DD: {trades_df["dd_pct"].min():.2f}%')
print(f'Return/DD: {abs((equity/STARTING_EQUITY - 1)*100 / trades_df["dd_pct"].min()):.2f}x')
print()
print(f'Trades: {len(trades_df)}')
print(f'Winners: {len(trades_df[trades_df["pnl_pct"] > 0])} ({len(trades_df[trades_df["pnl_pct"] > 0])/len(trades_df)*100:.1f}%)')
print(f'Losers: {len(trades_df[trades_df["pnl_pct"] < 0])} ({len(trades_df[trades_df["pnl_pct"] < 0])/len(trades_df)*100:.1f}%)')
print()

# Per coin
print('PER COIN:')
print(f'{"Coin":<15} {"Trades":<8} {"Win%":<8} {"Total P&L"}')
print('-'*60)
for coin in sorted(COINS.keys()):
    coin_trades = trades_df[trades_df['coin'] == coin]
    if len(coin_trades) > 0:
        wins = len(coin_trades[coin_trades['pnl_pct'] > 0])
        win_pct = wins / len(coin_trades) * 100
        total_pnl = coin_trades['dollar_pnl'].sum()
        print(f'{coin:<15} {len(coin_trades):<8} {win_pct:<8.1f} ${total_pnl:+.2f}')

print()
trades_df.to_csv('portfolio_FIXED.csv', index=False)
print('💾 Saved: portfolio_FIXED.csv')
