import pandas as pd
import numpy as np

# Load historical data
df = pd.read_csv('bot_data_last_8h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter FARTCOIN
fart = df[df['symbol'] == 'FARTCOIN-USDT'].sort_values('timestamp').copy()

# Calculate ATR expansion
fart['atr_ma_20'] = fart['atr'].rolling(20).mean()
fart['atr_expansion'] = fart['atr'] / fart['atr_ma_20']

# Calculate EMA distance (using SMA as proxy)
fart['ema_distance_pct'] = abs(fart['close'] - fart['sma_20']) / fart['close'] * 100

# Determine candle direction
fart['is_bullish'] = fart['close'] > fart['open']
fart['is_bearish'] = fart['close'] < fart['open']

# Find signals
fart_signals = fart[
    (fart['atr_expansion'] > 1.5) &
    (fart['ema_distance_pct'] <= 3.0) &
    ((fart['is_bullish']) | (fart['is_bearish']))
].copy()

print("=" * 80)
print(f"FARTCOIN MISSED TRADES SIMULATION")
print("=" * 80)
print(f"Total signals found: {len(fart_signals)}")
print()

if len(fart_signals) == 0:
    print("No signals to simulate")
    exit()

# Strategy parameters from config
LIMIT_OFFSET_PCT = 1.0  # Place limit 1% away from signal
MAX_WAIT_BARS = 3       # Wait max 3 bars for fill
STOP_ATR_MULT = 2.0     # Stop loss 2x ATR
TARGET_ATR_MULT = 8.0   # Take profit 8x ATR
MAX_HOLD_BARS = 200     # Max 200 bars (3.3 hours)
POSITION_SIZE_USDT = 6.0  # Flat $6 USDT per trade
FEES_PCT = 0.10         # 0.10% round-trip fees

trades = []

for idx, signal_row in fart_signals.iterrows():
    signal_time = signal_row['timestamp']
    signal_price = signal_row['close']
    signal_atr = signal_row['atr']
    direction = 'LONG' if signal_row['is_bullish'] else 'SHORT'

    # Calculate limit price (1% away from signal)
    if direction == 'LONG':
        limit_price = signal_price * (1 + LIMIT_OFFSET_PCT / 100)
    else:  # SHORT
        limit_price = signal_price * (1 - LIMIT_OFFSET_PCT / 100)

    # Check if limit fills within next 3 bars
    signal_idx = fart[fart['timestamp'] == signal_time].index[0]
    next_3_bars = fart.iloc[signal_idx+1:signal_idx+4] if signal_idx+4 < len(fart) else fart.iloc[signal_idx+1:]

    filled = False
    fill_price = None
    fill_time = None

    for _, bar in next_3_bars.iterrows():
        if direction == 'LONG':
            # LONG limit: price must drop to limit_price or below
            if bar['low'] <= limit_price:
                filled = True
                fill_price = limit_price
                fill_time = bar['timestamp']
                break
        else:  # SHORT
            # SHORT limit: price must rise to limit_price or above
            if bar['high'] >= limit_price:
                filled = True
                fill_price = limit_price
                fill_time = bar['timestamp']
                break

    if not filled:
        # Limit didn't fill - skip this trade
        trades.append({
            'signal_time': signal_time,
            'direction': direction,
            'signal_price': signal_price,
            'limit_price': limit_price,
            'filled': False,
            'reason': 'Limit not filled within 3 bars'
        })
        continue

    # Calculate SL/TP from fill price
    if direction == 'LONG':
        stop_loss = fill_price - (STOP_ATR_MULT * signal_atr)
        take_profit = fill_price + (TARGET_ATR_MULT * signal_atr)
    else:  # SHORT
        stop_loss = fill_price + (STOP_ATR_MULT * signal_atr)
        take_profit = fill_price - (TARGET_ATR_MULT * signal_atr)

    # Simulate trade execution from fill_time onwards
    fill_idx = fart[fart['timestamp'] == fill_time].index[0]
    future_bars = fart.iloc[fill_idx+1:fill_idx+MAX_HOLD_BARS+1]

    exit_price = None
    exit_time = None
    exit_reason = None
    bars_held = 0

    for _, bar in future_bars.iterrows():
        bars_held += 1

        if direction == 'LONG':
            # Check SL hit
            if bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_time = bar['timestamp']
                exit_reason = 'Stop Loss'
                break
            # Check TP hit
            if bar['high'] >= take_profit:
                exit_price = take_profit
                exit_time = bar['timestamp']
                exit_reason = 'Take Profit'
                break
        else:  # SHORT
            # Check SL hit
            if bar['high'] >= stop_loss:
                exit_price = stop_loss
                exit_time = bar['timestamp']
                exit_reason = 'Stop Loss'
                break
            # Check TP hit
            if bar['low'] <= take_profit:
                exit_price = take_profit
                exit_time = bar['timestamp']
                exit_reason = 'Take Profit'
                break

    # If no exit yet, time exit at max hold
    if exit_price is None:
        if len(future_bars) > 0:
            exit_price = future_bars.iloc[-1]['close']
            exit_time = future_bars.iloc[-1]['timestamp']
            exit_reason = 'Time Exit (max hold)'
        else:
            exit_price = fill_price
            exit_time = fill_time
            exit_reason = 'No data (use fill price)'

    # Calculate P/L
    if direction == 'LONG':
        pnl_pct = (exit_price - fill_price) / fill_price * 100
    else:  # SHORT
        pnl_pct = (fill_price - exit_price) / fill_price * 100

    # Subtract fees
    pnl_pct -= FEES_PCT

    # Calculate dollar P/L
    pnl_usd = POSITION_SIZE_USDT * (pnl_pct / 100)

    trades.append({
        'signal_time': signal_time,
        'fill_time': fill_time,
        'exit_time': exit_time,
        'direction': direction,
        'signal_price': signal_price,
        'limit_price': limit_price,
        'fill_price': fill_price,
        'exit_price': exit_price,
        'filled': True,
        'exit_reason': exit_reason,
        'bars_held': bars_held,
        'pnl_pct': pnl_pct,
        'pnl_usd': pnl_usd
    })

# Create DataFrame
trades_df = pd.DataFrame(trades)

# Print results
print("TRADE-BY-TRADE RESULTS:")
print("=" * 80)

for i, trade in trades_df.iterrows():
    if not trade['filled']:
        print(f"\n#{i+1} - {trade['signal_time']} - {trade['direction']}")
        print(f"  Signal: ${trade['signal_price']:.6f} → Limit: ${trade['limit_price']:.6f}")
        print(f"  ❌ NOT FILLED: {trade['reason']}")
    else:
        pnl_symbol = '✅' if trade['pnl_usd'] > 0 else '❌'
        print(f"\n#{i+1} - {trade['signal_time']} - {trade['direction']} {pnl_symbol}")
        print(f"  Fill: ${trade['fill_price']:.6f} @ {trade['fill_time']}")
        print(f"  Exit: ${trade['exit_price']:.6f} @ {trade['exit_time']}")
        print(f"  Reason: {trade['exit_reason']} ({trade['bars_held']} bars)")
        print(f"  P/L: {trade['pnl_pct']:+.2f}% = ${trade['pnl_usd']:+.2f} USD")

# Calculate overall stats
filled_trades = trades_df[trades_df['filled'] == True]

if len(filled_trades) > 0:
    total_pnl = filled_trades['pnl_usd'].sum()
    total_pnl_pct = filled_trades['pnl_pct'].sum()
    avg_pnl = filled_trades['pnl_usd'].mean()
    winners = filled_trades[filled_trades['pnl_usd'] > 0]
    losers = filled_trades[filled_trades['pnl_usd'] <= 0]
    win_rate = len(winners) / len(filled_trades) * 100 if len(filled_trades) > 0 else 0

    # Calculate max drawdown
    cumulative_pnl = filled_trades['pnl_usd'].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - running_max
    max_dd = drawdown.min()
    max_dd_pct = (max_dd / 12.38) * 100  # As % of $12.38 balance

    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total Signals: {len(trades_df)}")
    print(f"Limit Fills: {len(filled_trades)} ({len(filled_trades)/len(trades_df)*100:.1f}% fill rate)")
    print(f"Unfilled: {len(trades_df) - len(filled_trades)}")
    print()
    print(f"Total P/L: ${total_pnl:+.2f} USD ({total_pnl_pct:+.2f}%)")
    print(f"Average per trade: ${avg_pnl:+.2f} USD")
    print(f"Win Rate: {win_rate:.1f}% ({len(winners)}W / {len(losers)}L)")
    print()
    print(f"Winners: ${winners['pnl_usd'].sum():+.2f} USD (avg ${winners['pnl_usd'].mean():+.2f})")
    print(f"Losers: ${losers['pnl_usd'].sum():+.2f} USD (avg ${losers['pnl_usd'].mean():+.2f})")
    print()
    print(f"Max Drawdown: ${max_dd:.2f} USD ({max_dd_pct:.2f}% of account)")
    print(f"Starting Balance: $12.38 USD")
    print(f"Ending Balance: ${12.38 + total_pnl:.2f} USD")
    print(f"Return: {(total_pnl / 12.38 * 100):+.2f}%")

    if max_dd != 0:
        return_dd_ratio = abs(total_pnl / max_dd)
        print(f"Return/DD Ratio: {return_dd_ratio:.2f}x")

    print()
    print("Equity Curve:")
    print("-" * 80)
    equity = 12.38
    for i, trade in filled_trades.iterrows():
        equity += trade['pnl_usd']
        print(f"  After trade {i+1}: ${equity:.2f} ({trade['pnl_usd']:+.2f})")
else:
    print("\nNo trades filled")
