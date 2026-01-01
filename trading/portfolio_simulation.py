"""
PORTFOLIO SIMULATION - All 9 coins combined
10% position sizing per trade, compounding, chronological execution
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

def backtest_coin(df, coin_name, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, fee_pct=0.05):
    """Generate all trades for a coin"""
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['atr'] = calculate_atr(df, 14)

    trades = []
    position = None

    for i in range(20, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            continue

        # Exit logic
        if position is not None:
            bars_held = i - position['entry_bar']
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
                    'exit_reason': exit_signal['reason'],
                    'bars_held': bars_held
                })
                position = None

        # Entry logic
        if position is None:
            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']
                        entry_time = df.iloc[entry_bar]['timestamp']

                        stop_loss = entry_price - (stop_atr_mult * entry_atr)
                        take_profit = entry_price + (tp_atr_mult * entry_atr)

                        if df.iloc[entry_bar]['low'] > stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'entry_time': entry_time,
                                'side': 'LONG',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        break

            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']
                        entry_time = df.iloc[entry_bar]['timestamp']

                        stop_loss = entry_price + (stop_atr_mult * entry_atr)
                        take_profit = entry_price - (tp_atr_mult * entry_atr)

                        if df.iloc[entry_bar]['high'] < stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'entry_time': entry_time,
                                'side': 'SHORT',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        break

    return pd.DataFrame(trades)

# Coin configurations (OPTIMIZED from 90-day data)
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
print('💼 PORTFOLIO SIMULATION - 9 Coins with 10% Position Sizing')
print('='*120)
print()
print('Setup:')
print('  - Starting equity: $1,000')
print('  - Position size: 10% of CURRENT equity per trade')
print('  - Multiple positions allowed (different coins)')
print('  - Compounding: YES (reinvest all profits)')
print('  - Fees: 0.1% per trade (included in P&L)')
print()

# Collect all trades from all coins
all_trades = []

for coin, config in COINS.items():
    try:
        df = pd.read_csv(config['file'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        trades = backtest_coin(
            df, coin,
            rsi_low=27, rsi_high=65,
            limit_offset_pct=config['offset'],
            stop_atr_mult=config['sl'],
            tp_atr_mult=config['tp']
        )

        if len(trades) > 0:
            all_trades.append(trades)
            print(f'✅ {coin}: {len(trades)} trades')
    except Exception as e:
        print(f'❌ {coin}: {e}')

# Combine and sort chronologically
if len(all_trades) == 0:
    print('❌ No trades generated!')
    exit()

combined = pd.concat(all_trades, ignore_index=True)
combined = combined.sort_values('entry_time').reset_index(drop=True)

print()
print(f'Total trades collected: {len(combined)}')
print(f'Date range: {combined["entry_time"].min()} to {combined["exit_time"].max()}')
print()

# Simulate portfolio with 10% position sizing and compounding
STARTING_EQUITY = 1000.0
equity = STARTING_EQUITY
equity_curve = [{'time': combined['entry_time'].min(), 'equity': equity, 'positions_open': 0}]

open_positions = []
portfolio_trades = []

print('='*120)
print('🔄 SIMULATING PORTFOLIO EXECUTION...')
print('='*120)
print()

# Create timeline of all events (entries and exits)
events = []
for idx, trade in combined.iterrows():
    events.append({'time': trade['entry_time'], 'type': 'ENTRY', 'trade_idx': idx})
    events.append({'time': trade['exit_time'], 'type': 'EXIT', 'trade_idx': idx})

events_df = pd.DataFrame(events).sort_values('time').reset_index(drop=True)

# Process events chronologically
for _, event in events_df.iterrows():
    trade = combined.iloc[event['trade_idx']]

    if event['type'] == 'ENTRY':
        # Open new position with 10% of CURRENT equity
        position_size_pct = 0.10
        position_equity = equity * position_size_pct

        open_positions.append({
            'trade_idx': event['trade_idx'],
            'coin': trade['coin'],
            'entry_time': trade['entry_time'],
            'position_equity': position_equity,
            'pnl_pct': trade['pnl_pct']
        })

    elif event['type'] == 'EXIT':
        # Close position and update equity
        position = next((p for p in open_positions if p['trade_idx'] == event['trade_idx']), None)

        if position:
            # Calculate dollar P&L from position
            dollar_pnl = position['position_equity'] * (position['pnl_pct'] / 100)
            equity += dollar_pnl

            # Record trade result
            portfolio_trades.append({
                'time': trade['exit_time'],
                'coin': position['coin'],
                'position_size': position['position_equity'],
                'pnl_pct': position['pnl_pct'],
                'dollar_pnl': dollar_pnl,
                'equity_after': equity,
                'exit_reason': trade['exit_reason']
            })

            # Record equity curve point
            equity_curve.append({
                'time': trade['exit_time'],
                'equity': equity,
                'positions_open': len(open_positions) - 1
            })

            # Remove from open positions
            open_positions = [p for p in open_positions if p['trade_idx'] != event['trade_idx']]

# Convert to dataframes
portfolio_trades_df = pd.DataFrame(portfolio_trades)
equity_curve_df = pd.DataFrame(equity_curve)

# Calculate metrics
portfolio_trades_df['portfolio_pnl_pct'] = (portfolio_trades_df['dollar_pnl'] / STARTING_EQUITY) * 100
portfolio_trades_df['cumulative_pnl'] = portfolio_trades_df['portfolio_pnl_pct'].cumsum()

final_equity = equity_curve_df['equity'].iloc[-1]
total_return_pct = ((final_equity - STARTING_EQUITY) / STARTING_EQUITY) * 100

# Max drawdown calculation
equity_curve_df['peak'] = equity_curve_df['equity'].cummax()
equity_curve_df['drawdown'] = equity_curve_df['equity'] - equity_curve_df['peak']
equity_curve_df['drawdown_pct'] = (equity_curve_df['drawdown'] / equity_curve_df['peak']) * 100

max_dd_pct = equity_curve_df['drawdown_pct'].min()
max_dd_dollar = equity_curve_df['drawdown'].min()

# Win rate and profit factor
winners = portfolio_trades_df[portfolio_trades_df['dollar_pnl'] > 0]
losers = portfolio_trades_df[portfolio_trades_df['dollar_pnl'] < 0]

win_rate = len(winners) / len(portfolio_trades_df) * 100
avg_win = winners['dollar_pnl'].mean() if len(winners) > 0 else 0
avg_loss = abs(losers['dollar_pnl'].mean()) if len(losers) > 0 else 0
profit_factor = winners['dollar_pnl'].sum() / abs(losers['dollar_pnl'].sum()) if len(losers) > 0 else float('inf')

# Sharpe ratio (simplified - assuming daily)
returns = portfolio_trades_df['portfolio_pnl_pct'].values
sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

# Max positions open at once
max_positions = equity_curve_df['positions_open'].max()

# Print results
print('='*120)
print('📊 PORTFOLIO RESULTS')
print('='*120)
print()
print(f'Starting Equity: ${STARTING_EQUITY:,.2f}')
print(f'Final Equity: ${final_equity:,.2f}')
print(f'Total Return: {total_return_pct:+.2f}%')
print(f'Total Profit: ${final_equity - STARTING_EQUITY:+,.2f}')
print()
print(f'Max Drawdown: {max_dd_pct:.2f}% (${max_dd_dollar:.2f})')
print(f'Return/DD Ratio: {abs(total_return_pct / max_dd_pct):.2f}x')
print()
print(f'Total Trades: {len(portfolio_trades_df)}')
print(f'Winners: {len(winners)} ({win_rate:.1f}%)')
print(f'Losers: {len(losers)} ({100-win_rate:.1f}%)')
print()
print(f'Avg Winner: ${avg_win:.2f} ({winners["portfolio_pnl_pct"].mean():.2f}% of portfolio)')
print(f'Avg Loser: ${avg_loss:.2f} ({abs(losers["portfolio_pnl_pct"].mean()):.2f}% of portfolio)')
print(f'Largest Win: ${winners["dollar_pnl"].max():.2f}' if len(winners) > 0 else 'N/A')
print(f'Largest Loss: ${losers["dollar_pnl"].min():.2f}' if len(losers) > 0 else 'N/A')
print()
print(f'Profit Factor: {profit_factor:.2f}x')
print(f'Sharpe Ratio: {sharpe:.2f}')
print()
print(f'Max Concurrent Positions: {max_positions}')
print(f'Avg Position Size: ${portfolio_trades_df["position_size"].mean():.2f}')
print()

# Exit reason breakdown
print('Exit Reasons:')
for reason, count in portfolio_trades_df['exit_reason'].value_counts().items():
    pct = count / len(portfolio_trades_df) * 100
    avg_pnl = portfolio_trades_df[portfolio_trades_df['exit_reason'] == reason]['dollar_pnl'].mean()
    print(f'  {reason}: {count} ({pct:.1f}%) - Avg: ${avg_pnl:+.2f}')
print()

# Coin performance breakdown
print('='*120)
print('📈 PERFORMANCE BY COIN')
print('='*120)
print()
print(f'{"Coin":<15} {"Trades":<8} {"Win%":<8} {"Profit":<12} {"Avg P&L":<12}')
print('-'*120)

for coin in COINS.keys():
    coin_trades = portfolio_trades_df[portfolio_trades_df['coin'] == coin]
    if len(coin_trades) > 0:
        coin_win_rate = (coin_trades['dollar_pnl'] > 0).sum() / len(coin_trades) * 100
        coin_profit = coin_trades['dollar_pnl'].sum()
        coin_avg = coin_trades['dollar_pnl'].mean()
        print(f'{coin:<15} {len(coin_trades):<8} {coin_win_rate:>6.1f}% ${coin_profit:>10.2f} ${coin_avg:>10.2f}')

print()
print('='*120)
print('💾 SAVING RESULTS...')
print('='*120)
print()

portfolio_trades_df.to_csv('portfolio_trades_10pct.csv', index=False)
equity_curve_df.to_csv('portfolio_equity_curve_10pct.csv', index=False)

print('✅ Saved: portfolio_trades_10pct.csv')
print('✅ Saved: portfolio_equity_curve_10pct.csv')
print()
print('='*120)
