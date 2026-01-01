"""
Detailed trace of every UNI signal - why 24 signals became 2 trades
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

# Load UNI data
df = pd.read_csv('bingx-trading-bot/trading/uni_usdt_90d_1h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['rsi'] = calculate_rsi(df['close'].values, 14)
df['atr'] = calculate_atr(df, 14)

# UNI config
rsi_low = 27
rsi_high = 65
offset_pct = 2.0
sl_mult = 1.0
tp_mult = 1.0

print('='*140)
print('🔍 DETAILED UNI SIGNAL TRACE - Every Signal from Start to Finish')
print('='*140)
print()
print(f'Config: RSI {rsi_low}/{rsi_high}, Offset {offset_pct}%, SL {sl_mult}x ATR, TP {tp_mult}x ATR')
print()

# Track all signals and what happened
signals = []
position = None
trade_count = 0

for i in range(20, len(df)):
    current = df.iloc[i]
    prev = df.iloc[i-1]

    if pd.isna(current['rsi']) or pd.isna(current['atr']):
        continue

    # First check exits if in position
    if position is not None:
        exit_signal = None

        # Check SL
        if position['side'] == 'LONG':
            if current['low'] <= position['stop_loss']:
                exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}
        else:
            if current['high'] >= position['stop_loss']:
                exit_signal = {'reason': 'STOP', 'price': position['stop_loss']}

        # Check TP
        if not exit_signal:
            if position['side'] == 'LONG':
                if current['high'] >= position['take_profit']:
                    exit_signal = {'reason': 'TP', 'price': position['take_profit']}
            else:
                if current['low'] <= position['take_profit']:
                    exit_signal = {'reason': 'TP', 'price': position['take_profit']}

        # Check RSI exit
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

            pnl_pct -= 0.1  # fees

            bars_held = i - position['entry_bar']
            hours_held = bars_held

            print(f'✅ TRADE #{trade_count} EXITED:')
            print(f'   Entry: {position["entry_time"].strftime("%Y-%m-%d %H:%M")} @ ${entry:.4f} ({position["side"]})')
            print(f'   Exit:  {current["timestamp"].strftime("%Y-%m-%d %H:%M")} @ ${exit_price:.4f} ({exit_signal["reason"]})')
            print(f'   Held: {hours_held}h, P&L: {pnl_pct:+.2f}%')
            print(f'   SL: ${position["stop_loss"]:.4f}, TP: ${position["take_profit"]:.4f}')
            print()

            position = None

    # Now check for new signals
    if position is None:
        # LONG signal
        if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
            signal_time = current['timestamp']
            signal_price = current['close']
            limit_price = signal_price * (1 - offset_pct / 100)

            # Check if fills in next 5 bars
            filled = False
            fill_bar = None

            for j in range(i+1, min(i+6, len(df))):
                if df.iloc[j]['low'] <= limit_price:
                    filled = True
                    fill_bar = j
                    break

            if filled:
                entry_atr = df.iloc[fill_bar]['atr']
                stop_loss = limit_price - (sl_mult * entry_atr)
                take_profit = limit_price + (tp_mult * entry_atr)

                # Check immediate stop
                if df.iloc[fill_bar]['low'] > stop_loss:
                    # Valid entry
                    trade_count += 1
                    position = {
                        'entry_bar': fill_bar,
                        'entry_time': df.iloc[fill_bar]['timestamp'],
                        'entry_price': limit_price,
                        'side': 'LONG',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }

                    print(f'🟢 SIGNAL #{len(signals)+1} - LONG @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                    print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f} (crossed above {rsi_low})')
                    print(f'   Signal: ${signal_price:.4f}, Limit: ${limit_price:.4f} ({offset_pct}% below)')
                    print(f'   ✅ FILLED at bar +{fill_bar-i} ({df.iloc[fill_bar]["timestamp"].strftime("%H:%M")})')
                    print(f'   ✅ ENTERED as TRADE #{trade_count}')
                    print(f'   SL: ${stop_loss:.4f} ({-sl_mult}x ATR), TP: ${take_profit:.4f} ({tp_mult}x ATR)')
                    print()
                else:
                    print(f'🟡 SIGNAL #{len(signals)+1} - LONG @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                    print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
                    print(f'   ✅ FILLED but ❌ IMMEDIATE STOP-OUT (fill bar low: ${df.iloc[fill_bar]["low"]:.4f} ≤ SL: ${stop_loss:.4f})')
                    print()
            else:
                print(f'🔴 SIGNAL #{len(signals)+1} - LONG @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
                print(f'   Signal: ${signal_price:.4f}, Limit: ${limit_price:.4f}')
                print(f'   ❌ NEVER FILLED (no pullback to limit in next 5 bars)')
                print()

            signals.append({
                'time': signal_time,
                'side': 'LONG',
                'filled': filled,
                'entered': filled and df.iloc[fill_bar]['low'] > stop_loss if filled else False
            })

        # SHORT signal
        elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
            signal_time = current['timestamp']
            signal_price = current['close']
            limit_price = signal_price * (1 + offset_pct / 100)

            # Check if fills
            filled = False
            fill_bar = None

            for j in range(i+1, min(i+6, len(df))):
                if df.iloc[j]['high'] >= limit_price:
                    filled = True
                    fill_bar = j
                    break

            if filled:
                entry_atr = df.iloc[fill_bar]['atr']
                stop_loss = limit_price + (sl_mult * entry_atr)
                take_profit = limit_price - (tp_mult * entry_atr)

                if df.iloc[fill_bar]['high'] < stop_loss:
                    trade_count += 1
                    position = {
                        'entry_bar': fill_bar,
                        'entry_time': df.iloc[fill_bar]['timestamp'],
                        'entry_price': limit_price,
                        'side': 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }

                    print(f'🟢 SIGNAL #{len(signals)+1} - SHORT @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                    print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f} (crossed below {rsi_high})')
                    print(f'   Signal: ${signal_price:.4f}, Limit: ${limit_price:.4f} ({offset_pct}% above)')
                    print(f'   ✅ FILLED at bar +{fill_bar-i}')
                    print(f'   ✅ ENTERED as TRADE #{trade_count}')
                    print(f'   SL: ${stop_loss:.4f}, TP: ${take_profit:.4f}')
                    print()
                else:
                    print(f'🟡 SIGNAL #{len(signals)+1} - SHORT @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                    print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
                    print(f'   ✅ FILLED but ❌ IMMEDIATE STOP-OUT')
                    print()
            else:
                print(f'🔴 SIGNAL #{len(signals)+1} - SHORT @ {signal_time.strftime("%Y-%m-%d %H:%M")}')
                print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
                print(f'   ❌ NEVER FILLED (no bounce to limit in next 5 bars)')
                print()

            signals.append({
                'time': signal_time,
                'side': 'SHORT',
                'filled': filled,
                'entered': filled and df.iloc[fill_bar]['high'] < stop_loss if filled else False
            })

    else:
        # In position, check if new signal came
        if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
            print(f'⚫ SIGNAL BLOCKED - LONG @ {current["timestamp"].strftime("%Y-%m-%d %H:%M")}')
            print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
            print(f'   ❌ ALREADY IN {position["side"]} POSITION (entered {position["entry_time"].strftime("%Y-%m-%d %H:%M")})')
            print()
        elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
            print(f'⚫ SIGNAL BLOCKED - SHORT @ {current["timestamp"].strftime("%Y-%m-%d %H:%M")}')
            print(f'   RSI: {prev["rsi"]:.1f} → {current["rsi"]:.1f}')
            print(f'   ❌ ALREADY IN {position["side"]} POSITION (entered {position["entry_time"].strftime("%Y-%m-%d %H:%M")})')
            print()

print('='*140)
print('📊 UNI SUMMARY')
print('='*140)
print()
print(f'Total RSI Crossovers: {len(signals)}')
print(f'Filled: {sum(1 for s in signals if s["filled"])}')
print(f'Valid Entries: {sum(1 for s in signals if s["entered"])}')
print(f'Actual Trades Executed: {trade_count}')
print()
