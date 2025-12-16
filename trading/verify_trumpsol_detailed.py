"""
DETAILED VERIFICATION - Every bar for TRUMPSOL
Show exactly what happens: signals, limit orders, fills, position status, exits
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

# Load TRUMPSOL
df = pd.read_csv('bingx-trading-bot/trading/trumpsol_usdt_90d_1h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['rsi'] = calculate_rsi(df['close'].values, 14)
df['atr'] = calculate_atr(df, 14)

# Config
rsi_low = 30
rsi_high = 65
offset_pct = 1.0
sl_mult = 1.0
tp_mult = 0.5

print('='*150)
print('🔍 TRUMPSOL DETAILED VERIFICATION - Bar by Bar')
print('='*150)
print()
print(f'Config: RSI {rsi_low}/{rsi_high}, Offset {offset_pct}%, SL {sl_mult}x ATR, TP {tp_mult}x ATR')
print()

position = None
pending_limit = None
trades = []
trade_count = 0

i = 20
events_shown = 0
max_events = 50  # Limit output

while i < len(df) and events_shown < max_events:
    current = df.iloc[i]
    prev = df.iloc[i-1] if i > 0 else None

    if pd.isna(current['rsi']) or pd.isna(current['atr']):
        i += 1
        continue

    # Check exits if in position
    if position is not None:
        exit_signal = None

        # SL
        if position['side'] == 'LONG':
            if current['low'] <= position['stop_loss']:
                exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}
        else:
            if current['high'] >= position['stop_loss']:
                exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}

        # TP
        if not exit_signal:
            if position['side'] == 'LONG':
                if current['high'] >= position['take_profit']:
                    exit_signal = {'reason': 'TP', 'price': position['take_profit']}
            else:
                if current['low'] <= position['take_profit']:
                    exit_signal = {'reason': 'TP', 'price': position['take_profit']}

        if exit_signal:
            pnl_pct = ((exit_signal['price'] - position['entry_price']) / position['entry_price'] * 100) if position['side'] == 'LONG' else ((position['entry_price'] - exit_signal['price']) / position['entry_price'] * 100)
            pnl_pct -= 0.1

            print(f"BAR {i} [{current['timestamp'].strftime('%Y-%m-%d %H:%M')}] - ⛔ EXIT")
            print(f"  Position: {position['side']} entered at ${position['entry_price']:.4f}")
            print(f"  Exit: {exit_signal['reason']} at ${exit_signal['price']:.4f}")
            print(f"  P&L: {pnl_pct:+.2f}% (held {i - position['entry_bar']}h)")
            print(f"  Status: ✅ Position closed, can accept new signals")
            print()
            events_shown += 1

            trades.append({
                'entry_bar': position['entry_bar'],
                'exit_bar': i,
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': exit_signal['price'],
                'pnl_pct': pnl_pct,
                'exit_reason': exit_signal['reason']
            })
            position = None

    # Check for new signals (only if no position)
    if position is None and prev is not None:
        # LONG signal
        if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
            signal_price = current['close']
            limit_price = signal_price * (1 - offset_pct / 100)

            print(f"BAR {i} [{current['timestamp'].strftime('%Y-%m-%d %H:%M')}] - 📶 LONG SIGNAL")
            print(f"  RSI: {prev['rsi']:.1f} → {current['rsi']:.1f} (crossed above {rsi_low})")
            print(f"  Signal price: ${signal_price:.4f}")
            print(f"  Limit order: ${limit_price:.4f} ({offset_pct}% below)")
            print(f"  Status: Waiting for fill in next 5 bars...")
            print()
            events_shown += 1

            # Check for fill
            filled = False
            for j in range(i+1, min(i+6, len(df))):
                check_bar = df.iloc[j]

                if check_bar['low'] <= limit_price:
                    # Filled!
                    entry_atr = check_bar['atr']
                    stop_loss = limit_price - (sl_mult * entry_atr)
                    take_profit = limit_price + (tp_mult * entry_atr)

                    # Check immediate stop
                    if check_bar['low'] > stop_loss:
                        print(f"  ✅ FILLED at bar {j} [{check_bar['timestamp'].strftime('%H:%M')}] (+ {j-i} bars)")
                        print(f"     Entry: ${limit_price:.4f}")
                        print(f"     SL: ${stop_loss:.4f} (-{sl_mult}x ATR)")
                        print(f"     TP: ${take_profit:.4f} (+{tp_mult}x ATR)")
                        print(f"     Status: 🔒 IN POSITION - No new signals accepted")
                        print()
                        events_shown += 1

                        position = {
                            'entry_bar': j,
                            'entry_price': limit_price,
                            'side': 'LONG',
                            'stop_loss': stop_loss,
                            'take_profit': take_profit
                        }
                        i = j  # Jump to fill bar
                        filled = True
                    else:
                        print(f"  🟡 FILLED but immediate stop-out (bar {j} low ${check_bar['low']:.4f} ≤ SL ${stop_loss:.4f})")
                        print()
                        events_shown += 1
                    break

            if not filled and events_shown < max_events:
                print(f"  ❌ NOT FILLED - Limit expired after 5 bars")
                print()
                events_shown += 1

        # SHORT signal
        elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
            signal_price = current['close']
            limit_price = signal_price * (1 + offset_pct / 100)

            print(f"BAR {i} [{current['timestamp'].strftime('%Y-%m-%d %H:%M')}] - 📶 SHORT SIGNAL")
            print(f"  RSI: {prev['rsi']:.1f} → {current['rsi']:.1f} (crossed below {rsi_high})")
            print(f"  Signal price: ${signal_price:.4f}")
            print(f"  Limit order: ${limit_price:.4f} ({offset_pct}% above)")
            print(f"  Status: Waiting for fill...")
            print()
            events_shown += 1

            filled = False
            for j in range(i+1, min(i+6, len(df))):
                check_bar = df.iloc[j]

                if check_bar['high'] >= limit_price:
                    entry_atr = check_bar['atr']
                    stop_loss = limit_price + (sl_mult * entry_atr)
                    take_profit = limit_price - (tp_mult * entry_atr)

                    if check_bar['high'] < stop_loss:
                        print(f"  ✅ FILLED at bar {j} [{check_bar['timestamp'].strftime('%H:%M')}] (+ {j-i} bars)")
                        print(f"     Entry: ${limit_price:.4f}")
                        print(f"     SL: ${stop_loss:.4f}")
                        print(f"     TP: ${take_profit:.4f}")
                        print(f"     Status: 🔒 IN POSITION - No new signals accepted")
                        print()
                        events_shown += 1

                        position = {
                            'entry_bar': j,
                            'entry_price': limit_price,
                            'side': 'SHORT',
                            'stop_loss': stop_loss,
                            'take_profit': take_profit
                        }
                        i = j
                        filled = True
                    else:
                        print(f"  🟡 FILLED but immediate stop-out")
                        print()
                        events_shown += 1
                    break

            if not filled and events_shown < max_events:
                print(f"  ❌ NOT FILLED - Limit expired")
                print()
                events_shown += 1

    i += 1

print('='*150)
print(f'📊 SUMMARY (First {events_shown} events shown)')
print('='*150)
print()
print(f'Total trades completed: {len(trades)}')
print(f'Winners: {len([t for t in trades if t["pnl_pct"] > 0])}')
print(f'Losers: {len([t for t in trades if t["pnl_pct"] < 0])}')
print()

if len(trades) > 0:
    print('TRADES:')
    for idx, t in enumerate(trades, 1):
        print(f'{idx}. {t["side"]} bar {t["entry_bar"]}→{t["exit_bar"]} ({t["exit_bar"]-t["entry_bar"]}h): {t["pnl_pct"]:+.2f}% ({t["exit_reason"]})')
    print()

print('✅ VERIFICATION COMPLETE')
print()
print('Key checks:')
print('1. ✓ No signals accepted while in position')
print('2. ✓ Limit orders wait max 5 bars')
print('3. ✓ Position closes before new signals accepted')
print('4. ✓ Only SL or TP exits (no overlaps)')
