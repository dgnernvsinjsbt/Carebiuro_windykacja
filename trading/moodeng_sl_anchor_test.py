#!/usr/bin/env python3
"""
Test SL/TP anchoring methods for limit order entries
1. Anchor to ENTRY price (maintain 1:6 R:R from entry)
2. Anchor to SIGNAL price (wider SL, maintains original invalidation level)
"""

import pandas as pd
import numpy as np

FEE_PER_TRADE = 0.10


def load_data():
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 0.0001)
    df['rsi'] = 100 - (100 / (1 + rs))

    df['sma_20'] = df['close'].rolling(20).mean()
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']

    return df


def run_strategy(df, limit_pct=1.25, sl_mult=1.0, tp_mult=6.0, anchor_to='entry'):
    """
    anchor_to options:
    - 'entry': SL/TP based on entry price (maintains R:R ratio)
    - 'signal': SL/TP based on signal price (wider stops, original invalidation)
    """
    trades = []
    in_position = False
    waiting_for_fill = False

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position and not waiting_for_fill:
            # Signal check
            rsi_cross = prev['rsi'] < 55 and row['rsi'] >= 55
            bullish_body = row['is_bullish'] and row['body_pct'] > 0.5
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                signal_price = row['close']
                signal_idx = i
                signal_atr = row['atr']
                waiting_for_fill = True
                limit_price = signal_price * (1 + limit_pct/100)

        elif waiting_for_fill:
            # Check if limit filled
            if row['high'] >= limit_price:
                in_position = True
                waiting_for_fill = False
                entry_price = limit_price
                entry_idx = i
                entry_atr = df.iloc[signal_idx]['atr']

                if anchor_to == 'entry':
                    # Anchor to entry price - maintains R:R
                    stop_loss = entry_price - (entry_atr * sl_mult)
                    take_profit = entry_price + (entry_atr * tp_mult)
                    actual_sl_dist = (entry_price - stop_loss) / entry_price * 100
                    actual_tp_dist = (take_profit - entry_price) / entry_price * 100

                else:  # anchor_to == 'signal'
                    # Anchor to signal price - wider stop from entry
                    signal_price_ref = df.iloc[signal_idx]['close']
                    stop_loss = signal_price_ref - (entry_atr * sl_mult)
                    take_profit = signal_price_ref + (entry_atr * tp_mult)
                    actual_sl_dist = (entry_price - stop_loss) / entry_price * 100
                    actual_tp_dist = (take_profit - entry_price) / entry_price * 100

            # Cancel if timeout
            elif i - signal_idx >= 10:
                waiting_for_fill = False

        elif in_position:
            bars_held = i - entry_idx

            # Check SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'sl_dist': actual_sl_dist,
                    'tp_dist': actual_tp_dist
                })
                in_position = False
                continue

            # Check TP
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'sl_dist': actual_sl_dist,
                    'tp_dist': actual_tp_dist
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= 60:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'sl_dist': actual_sl_dist,
                    'tp_dist': actual_tp_dist
                })
                in_position = False

    return trades


def analyze(trades, label=''):
    if not trades:
        return None

    df = pd.DataFrame(trades)

    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]

    win_rate = len(winners) / len(df) * 100
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    # Equity
    equity = [100]
    for pnl in df['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    # DD
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    gross = equity[-1] - 100
    fees = len(df) * FEE_PER_TRADE
    net = gross - fees

    rdd = net / max_dd if max_dd > 0 else 0

    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

    # Actual R:R from distance
    avg_sl_dist = abs(df['sl_dist'].mean())
    avg_tp_dist = df['tp_dist'].mean()
    actual_rr = avg_tp_dist / avg_sl_dist if avg_sl_dist > 0 else 0

    return {
        'label': label,
        'trades': len(df),
        'net': net,
        'wr': win_rate,
        'dd': max_dd,
        'rdd': rdd,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'sl_count': len(df[df['result'] == 'SL']),
        'tp_count': len(df[df['result'] == 'TP']),
        'actual_rr': actual_rr,
        'avg_sl_dist': avg_sl_dist,
        'avg_tp_dist': avg_tp_dist
    }


def main():
    print("=" * 90)
    print("SL/TP ANCHORING TEST - Limit Order +1.25%")
    print("=" * 90)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles\n")

    print("Testing two SL/TP anchoring methods:\n")
    print("1. ANCHOR TO ENTRY: SL/TP from entry price (maintains 1:6 R:R)")
    print("2. ANCHOR TO SIGNAL: SL/TP from signal price (wider stop, original invalidation)\n")

    # Test both methods
    print("=" * 90)

    # Method 1: Anchor to entry
    trades_entry = run_strategy(df, limit_pct=1.25, anchor_to='entry')
    r1 = analyze(trades_entry, 'Anchor to ENTRY')

    print(f"1️⃣  ANCHOR TO ENTRY PRICE")
    print(f"   Trades: {r1['trades']}")
    print(f"   NET Return: {r1['net']:+.2f}%")
    print(f"   Return/DD: {r1['rdd']:.2f}x")
    print(f"   Win Rate: {r1['wr']:.1f}%")
    print(f"   Avg Win: {r1['avg_win']:+.2f}%")
    print(f"   Avg Loss: {r1['avg_loss']:+.2f}%")
    print(f"   Expectancy: {r1['expectancy']:+.3f}%")
    print(f"   Max DD: {r1['dd']:.2f}%")
    print(f"   Exits: {r1['sl_count']} SL / {r1['tp_count']} TP")
    print(f"   Actual R:R: 1:{r1['actual_rr']:.1f} (Avg SL: {r1['avg_sl_dist']:.2f}%, Avg TP: {r1['avg_tp_dist']:.2f}%)")

    print(f"\n2️⃣  ANCHOR TO SIGNAL PRICE")

    # Method 2: Anchor to signal
    trades_signal = run_strategy(df, limit_pct=1.25, anchor_to='signal')
    r2 = analyze(trades_signal, 'Anchor to SIGNAL')

    print(f"   Trades: {r2['trades']}")
    print(f"   NET Return: {r2['net']:+.2f}%")
    print(f"   Return/DD: {r2['rdd']:.2f}x")
    print(f"   Win Rate: {r2['wr']:.1f}%")
    print(f"   Avg Win: {r2['avg_win']:+.2f}%")
    print(f"   Avg Loss: {r2['avg_loss']:+.2f}%")
    print(f"   Expectancy: {r2['expectancy']:+.3f}%")
    print(f"   Max DD: {r2['dd']:.2f}%")
    print(f"   Exits: {r2['sl_count']} SL / {r2['tp_count']} TP")
    print(f"   Actual R:R: 1:{r2['actual_rr']:.1f} (Avg SL: {r2['avg_sl_dist']:.2f}%, Avg TP: {r2['avg_tp_dist']:.2f}%)")

    # Comparison
    print("\n" + "=" * 90)
    print("COMPARISON")
    print("=" * 90)

    print(f"\n{'Metric':<20} {'Anchor to Entry':<20} {'Anchor to Signal':<20} {'Difference'}")
    print("-" * 90)

    metrics = [
        ('NET Return', 'net', '%'),
        ('Return/DD', 'rdd', 'x'),
        ('Win Rate', 'wr', '%'),
        ('Expectancy', 'expectancy', '%'),
        ('Max DD', 'dd', '%'),
        ('Avg Win', 'avg_win', '%'),
        ('Avg Loss', 'avg_loss', '%'),
    ]

    for name, key, unit in metrics:
        v1 = r1[key]
        v2 = r2[key]
        diff = v2 - v1
        sign = '+' if diff > 0 else ''

        if unit == '%':
            print(f"{name:<20} {v1:>+8.2f}%{' '*11} {v2:>+8.2f}%{' '*11} {sign}{diff:.2f}%")
        else:
            print(f"{name:<20} {v1:>8.2f}{unit}{' '*11} {v2:>8.2f}{unit}{' '*11} {sign}{diff:.2f}{unit}")

    # Recommendation
    print("\n" + "=" * 90)
    print("RECOMMENDATION")
    print("=" * 90)

    if r1['rdd'] > r2['rdd']:
        print(f"\n✅ ANCHOR TO ENTRY is BETTER")
        print(f"   Higher R/DD: {r1['rdd']:.2f}x vs {r2['rdd']:.2f}x")
        print(f"   NET: {r1['net']:+.2f}% vs {r2['net']:+.2f}%")
        print(f"\n   Maintains consistent 1:6 R:R from actual entry price")
        print(f"   Simpler logic: entry - 1 ATR, entry + 6 ATR")
    else:
        print(f"\n✅ ANCHOR TO SIGNAL is BETTER")
        print(f"   Higher R/DD: {r2['rdd']:.2f}x vs {r1['rdd']:.2f}x")
        print(f"   NET: {r2['net']:+.2f}% vs {r1['net']:+.2f}%")
        print(f"\n   Wider stop absorbs entry slippage")
        print(f"   Preserves original signal invalidation level")

    print(f"\n📊 PRACTICAL IMPLICATIONS:")
    print(f"\n   Example: Signal at $10, ATR = $1, Limit fills at $11 (+10%)")
    print(f"\n   Anchor to ENTRY:")
    print(f"   - Entry: $11")
    print(f"   - SL: $10 (11 - 1 ATR) = -9.1% from entry")
    print(f"   - TP: $17 (11 + 6 ATR) = +54.5% from entry")
    print(f"   - R:R: 1:6 ✅")
    print(f"\n   Anchor to SIGNAL:")
    print(f"   - Entry: $11")
    print(f"   - SL: $9 (10 - 1 ATR) = -18.2% from entry ⚠️ WIDER")
    print(f"   - TP: $16 (10 + 6 ATR) = +45.5% from entry")
    print(f"   - R:R: 1:2.5 (worse)")


if __name__ == "__main__":
    main()
