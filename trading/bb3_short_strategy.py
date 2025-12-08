#!/usr/bin/env python3
"""
BB3 SHORT Strategy - Mean reversion shorts when price > upper BB (3 STD)

Entry: Price > BB Upper (3 STD) → SHORT
Exit: Price < BB Mid OR Stop Loss

Limit orders ABOVE signal = better short entry (sell higher) = MAKER fees
"""
import pandas as pd
import numpy as np

# Load 1-minute ETH data
print("Loading ETH 1-minute data...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate Bollinger Bands (20 period, 3 STD)
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper_3'] = df['bb_mid'] + 3 * df['bb_std']
df['bb_lower_3'] = df['bb_mid'] - 3 * df['bb_std']

# Calculate ATR for stops
df['atr'] = (df['high'] - df['low']).rolling(14).mean()

# Drop NaN rows
df = df.dropna().reset_index(drop=True)

# FEES
MAKER_FEE = 0.0002   # 0.02%
TAKER_FEE = 0.0005   # 0.05%
STARTING_BALANCE = 10000

# Find SHORT entry signals: close > bb_upper_3
df['short_signal'] = df['close'] > df['bb_upper_3']

print(f"Total candles: {len(df)}")
print(f"Short signals found: {df['short_signal'].sum()}")

# Backtest SHORT strategy
trades = []
in_position = False
entry_price = 0
entry_time = None
stop_loss = 0
take_profit = 0

for i in range(len(df)):
    row = df.iloc[i]

    if not in_position:
        # Look for SHORT entry
        if row['short_signal']:
            in_position = True
            entry_price = row['close']
            entry_time = row['timestamp']
            atr = row['atr']

            # For SHORT: stop is ABOVE entry, target is BELOW
            stop_loss = entry_price + (atr * 2)      # 2x ATR above
            take_profit = entry_price - (atr * 4)    # 4x ATR below
    else:
        # Check exit conditions for SHORT
        high = row['high']
        low = row['low']

        # Stop loss hit (price went UP to stop)
        if high >= stop_loss:
            trades.append({
                'entry_time': entry_time,
                'exit_time': row['timestamp'],
                'entry': entry_price,
                'exit': stop_loss,
                'stop': stop_loss,
                'target': take_profit,
                'result': 'STOP',
                'pnl_pct': (entry_price - stop_loss) / entry_price * 100  # SHORT P/L
            })
            in_position = False

        # Take profit hit (price went DOWN to target)
        elif low <= take_profit:
            trades.append({
                'entry_time': entry_time,
                'exit_time': row['timestamp'],
                'entry': entry_price,
                'exit': take_profit,
                'stop': stop_loss,
                'target': take_profit,
                'result': 'TP',
                'pnl_pct': (entry_price - take_profit) / entry_price * 100  # SHORT P/L
            })
            in_position = False

trades_df = pd.DataFrame(trades)
print(f"\nTotal SHORT trades: {len(trades_df)}")

if len(trades_df) == 0:
    print("No trades found!")
    exit()

# Save raw trades
trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_short_raw_trades.csv', index=False)

# Get max price during each trade (for limit order fill check - shorts want price to go UP first)
eth_data = df.set_index('timestamp')

def get_max_price(entry_time, exit_time):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['high'].max()
    except:
        return None

def get_min_price(entry_time, exit_time):
    try:
        mask = (eth_data.index >= entry_time) & (eth_data.index <= exit_time)
        return eth_data.loc[mask]['low'].min()
    except:
        return None

trades_df['max_price'] = trades_df.apply(lambda r: get_max_price(r['entry_time'], r['exit_time']), axis=1)
trades_df['min_price'] = trades_df.apply(lambda r: get_min_price(r['entry_time'], r['exit_time']), axis=1)

# Fill missing
trades_df['max_price'] = trades_df.apply(lambda r: r['max_price'] if pd.notna(r['max_price']) else r['stop'], axis=1)
trades_df['min_price'] = trades_df.apply(lambda r: r['min_price'] if pd.notna(r['min_price']) else r['target'], axis=1)

print("\n" + "=" * 70)
print("BB3 SHORT STRATEGY RESULTS")
print("=" * 70)

# ============================================
# SCENARIO 1: MARKET ORDERS (0.10% RT)
# ============================================
balance = STARTING_BALANCE
market_results = []

for _, row in trades_df.iterrows():
    entry = row['entry']
    exit_price = row['target'] if row['result'] == 'TP' else row['stop']

    # SHORT P/L: (entry - exit) / entry
    gross_pnl_pct = (entry - exit_price) / entry * 100
    fee_pct = (TAKER_FEE + TAKER_FEE) * 100  # 0.10%
    net_pnl_pct = gross_pnl_pct - fee_pct

    pnl_dollar = balance * (net_pnl_pct / 100)
    balance += pnl_dollar

    market_results.append({
        'gross': gross_pnl_pct,
        'fee': fee_pct,
        'net': net_pnl_pct,
        'balance': balance,
        'win': gross_pnl_pct > 0
    })

market_df = pd.DataFrame(market_results)
market_final = balance

print(f"\n--- MARKET ORDERS (0.05% + 0.05% = 0.10% RT) ---")
print(f"Trades: {len(trades_df)}")
print(f"Winners: {market_df['win'].sum()}")
print(f"Losers: {len(market_df) - market_df['win'].sum()}")
print(f"Win rate: {market_df['win'].sum()/len(market_df)*100:.1f}%")
print(f"Gross return: {market_df['gross'].sum():.2f}%")
print(f"Total fees: -{market_df['fee'].sum():.2f}%")
print(f"NET RETURN: {market_df['net'].sum():.2f}%")
print(f"Final: ${market_final:,.2f} (${market_final-STARTING_BALANCE:+,.2f})")

# Calculate max drawdown for market
bal = np.array([STARTING_BALANCE] + list(market_df['balance']))
peak = np.maximum.accumulate(bal)
dd = (bal - peak) / peak * 100
print(f"Max Drawdown: {dd.min():.2f}%")

# ============================================
# SCENARIO 2: LIMIT ABOVE +0.035% (0.07% RT)
# For SHORTS: limit ABOVE signal = better entry (sell higher)
# ============================================
LIMIT_OFFSET = 0.00035
balance = STARTING_BALANCE
limit_results = []

for _, row in trades_df.iterrows():
    signal = row['entry']
    limit_price = signal * (1 + LIMIT_OFFSET)  # ABOVE for shorts
    max_price = row['max_price']

    # For shorts, limit fills if price goes UP to our limit
    filled = max_price >= limit_price

    if filled:
        entry = limit_price  # Better entry for short (sold higher)
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']

        # SHORT P/L
        gross_pnl_pct = (entry - exit_price) / entry * 100
        fee_pct = (MAKER_FEE + TAKER_FEE) * 100  # 0.07%
        net_pnl_pct = gross_pnl_pct - fee_pct

        pnl_dollar = balance * (net_pnl_pct / 100)
        balance += pnl_dollar

        limit_results.append({
            'signal': signal,
            'entry': entry,
            'exit': exit_price,
            'filled': True,
            'gross': gross_pnl_pct,
            'fee': fee_pct,
            'net': net_pnl_pct,
            'balance': balance,
            'win': gross_pnl_pct > 0,
            'result': row['result']
        })
    else:
        limit_results.append({
            'signal': signal,
            'entry': None,
            'exit': None,
            'filled': False,
            'gross': 0,
            'fee': 0,
            'net': 0,
            'balance': balance,
            'win': False,
            'result': 'SKIPPED'
        })

limit_df = pd.DataFrame(limit_results)
limit_final = balance
filled_count = limit_df['filled'].sum()
filled_df = limit_df[limit_df['filled']]

print(f"\n--- LIMIT ABOVE +0.035% (0.02% + 0.05% = 0.07% RT) ---")
print(f"Filled: {filled_count}/{len(trades_df)} ({filled_count/len(trades_df)*100:.1f}%)")
print(f"Winners: {filled_df['win'].sum()}")
print(f"Losers: {len(filled_df) - filled_df['win'].sum()}")
print(f"Win rate: {filled_df['win'].sum()/filled_count*100:.1f}%")
print(f"Gross return: {limit_df['gross'].sum():.2f}%")
print(f"Total fees: -{limit_df['fee'].sum():.2f}%")
print(f"NET RETURN: {limit_df['net'].sum():.2f}%")
print(f"Final: ${limit_final:,.2f} (${limit_final-STARTING_BALANCE:+,.2f})")

# Calculate max drawdown for limit
bal = [STARTING_BALANCE]
for r in limit_results:
    bal.append(r['balance'])
bal = np.array(bal)
peak = np.maximum.accumulate(bal)
dd = (bal - peak) / peak * 100
print(f"Max Drawdown: {dd.min():.2f}%")

# ============================================
# SUMMARY
# ============================================
print(f"\n" + "=" * 70)
print("SUMMARY - BB3 SHORT STRATEGY")
print("=" * 70)
print(f"\n{'Method':<30} {'Trades':<8} {'W/L':<10} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 70)

# Market
mdd_market = dd.min() if 'dd' in dir() else 0
bal_m = np.array([STARTING_BALANCE] + list(market_df['balance']))
peak_m = np.maximum.accumulate(bal_m)
dd_m = (bal_m - peak_m) / peak_m * 100
print(f"{'Market (0.10% RT)':<30} {len(market_df):<8} {int(market_df['win'].sum())}/{int(len(market_df)-market_df['win'].sum()):<6} {market_df['net'].sum():>+.2f}%   {dd_m.min():.2f}%    ${market_final-STARTING_BALANCE:>+,.0f}")

print(f"{'Limit +0.035% (0.07% RT)':<30} {filled_count:<8} {int(filled_df['win'].sum())}/{int(len(filled_df)-filled_df['win'].sum()):<6} {limit_df['net'].sum():>+.2f}%   {dd.min():.2f}%    ${limit_final-STARTING_BALANCE:>+,.0f}")

# Save detailed CSV
print("\nGenerating detailed CSV...")

balance = STARTING_BALANCE
detailed = []

for idx, row in trades_df.iterrows():
    signal = row['entry']
    limit_price = signal * (1 + LIMIT_OFFSET)
    max_price = row['max_price']
    filled = max_price >= limit_price

    trade = {
        'trade_num': idx + 1,
        'entry_time': row['entry_time'],
        'exit_time': row['exit_time'],
        'signal_price': signal,
        'limit_price': limit_price,
        'max_price': max_price,
        'stop': row['stop'],
        'target': row['target'],
        'filled': 'YES' if filled else 'NO',
        'result': row['result'] if filled else 'SKIPPED',
    }

    if filled:
        entry = limit_price
        exit_price = row['target'] if row['result'] == 'TP' else row['stop']
        gross = (entry - exit_price) / entry * 100
        fee = (MAKER_FEE + TAKER_FEE) * 100

        trade['actual_entry'] = entry
        trade['exit_price'] = exit_price
        trade['gross_pnl_pct'] = gross
        trade['entry_fee_pct'] = MAKER_FEE * 100
        trade['exit_fee_pct'] = TAKER_FEE * 100
        trade['total_fee_pct'] = fee
        trade['profit_after_fees_pct'] = gross - fee
        trade['winner'] = 'WIN' if gross > 0 else 'LOSS'

        pnl_dollar = balance * ((gross - fee) / 100)
        balance += pnl_dollar
        trade['profit_after_fees_dollar'] = pnl_dollar
    else:
        trade['actual_entry'] = None
        trade['exit_price'] = None
        trade['gross_pnl_pct'] = 0
        trade['entry_fee_pct'] = 0
        trade['exit_fee_pct'] = 0
        trade['total_fee_pct'] = 0
        trade['profit_after_fees_pct'] = 0
        trade['profit_after_fees_dollar'] = 0
        trade['winner'] = 'SKIP'

    trade['running_balance'] = balance
    detailed.append(trade)

detailed_df = pd.DataFrame(detailed)
detailed_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_short_with_fees.csv', index=False)

print(f"Saved: bb3_short_with_fees.csv")
print(f"Final balance: ${balance:,.2f}")
