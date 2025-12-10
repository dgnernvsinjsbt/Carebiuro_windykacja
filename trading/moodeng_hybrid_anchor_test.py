#!/usr/bin/env python3
"""
Test 3 SL/TP anchoring methods for limit order entries

1. Both to ENTRY: SL 11→10, TP 11→17 (R:R 1:6 from entry)
2. Both to SIGNAL: SL 11→9, TP 11→16 (R:R 1:2.3 from entry)
3. HYBRID: SL to entry 11→10, TP to signal 11→16 (R:R 1:5 from entry)
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


def run_strategy(df, limit_pct=1.25, sl_mult=1.0, tp_mult=6.0, anchor_method='both_entry'):
    """
    anchor_method options:
    - 'both_entry': SL/TP both from entry (R:R 1:6 from entry)
    - 'both_signal': SL/TP both from signal (wider stop and closer TP)
    - 'hybrid': SL from entry, TP from signal (tight stop, original target = 1:5 R:R)
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
                signal_price_ref = df.iloc[signal_idx]['close']

                if anchor_method == 'both_entry':
                    # Both anchored to entry
                    stop_loss = entry_price - (entry_atr * sl_mult)
                    take_profit = entry_price + (entry_atr * tp_mult)

                elif anchor_method == 'both_signal':
                    # Both anchored to signal
                    stop_loss = signal_price_ref - (entry_atr * sl_mult)
                    take_profit = signal_price_ref + (entry_atr * tp_mult)

                else:  # 'hybrid'
                    # SL from entry (tight), TP from signal (original target)
                    stop_loss = entry_price - (entry_atr * sl_mult)
                    take_profit = signal_price_ref + (entry_atr * tp_mult)

                # Calculate actual distances
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

    # Actual R:R
    avg_sl_dist = abs(df['sl_dist'].mean())
    avg_tp_dist = df['tp_dist'].mean()
    actual_rr = avg_tp_dist / avg_sl_dist if avg_sl_dist > 0 else 0

    # Top 20% concentration
    top_20pct_count = max(1, int(len(df) * 0.2))
    top_20pct = df.nlargest(top_20pct_count, 'pnl_pct')
    top_20pct_profit = top_20pct['pnl_pct'].sum()
    concentration = (top_20pct_profit / gross * 100) if gross > 0 else 0

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
        'avg_tp_dist': avg_tp_dist,
        'top20_conc': concentration
    }


def main():
    print("=" * 100)
    print("SL/TP ANCHORING COMPARISON - 3 Methods")
    print("Limit Order Entry at +1.25% above signal")
    print("=" * 100)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles\n")

    # Test all 3 methods
    methods = [
        ('both_entry', 'Both to ENTRY'),
        ('both_signal', 'Both to SIGNAL'),
        ('hybrid', 'HYBRID (SL→entry, TP→signal)')
    ]

    results = []

    for method, label in methods:
        trades = run_strategy(df, limit_pct=1.25, anchor_method=method)
        r = analyze(trades, label)
        results.append(r)

    # Display results
    print(f"{'Method':<35} {'Trades':<8} {'NET':<10} {'R/DD':<8} {'WR':<7} {'Exp':<9} {'DD':<8} {'R:R':<10} {'Top20%'}")
    print("-" * 100)

    for r in results:
        rr_str = f"1:{r['actual_rr']:.1f}"
        print(f"{r['label']:<35} {r['trades']:<8} {r['net']:>+8.2f}% {r['rdd']:>7.2f}x "
              f"{r['wr']:>6.1f}% {r['expectancy']:>+7.3f}% {r['dd']:>7.2f}% {rr_str:<10} {r['top20_conc']:>6.1f}%")

    # Detailed comparison
    print("\n" + "=" * 100)
    print("DETAILED COMPARISON")
    print("=" * 100)

    for i, r in enumerate(results, 1):
        print(f"\n{i}️⃣  {r['label']}")
        print(f"   NET Return: {r['net']:+.2f}%")
        print(f"   Return/DD: {r['rdd']:.2f}x")
        print(f"   Win Rate: {r['wr']:.1f}%")
        print(f"   Avg Win: {r['avg_win']:+.2f}% | Avg Loss: {r['avg_loss']:+.2f}%")
        print(f"   Expectancy: {r['expectancy']:+.3f}%")
        print(f"   Max DD: {r['dd']:.2f}%")
        print(f"   Exits: {r['sl_count']} SL / {r['tp_count']} TP")
        print(f"   Actual R:R: 1:{r['actual_rr']:.1f} (SL {r['avg_sl_dist']:.2f}%, TP {r['avg_tp_dist']:.2f}%)")
        print(f"   Top 20% Concentration: {r['top20_conc']:.1f}%")

    # Example calculation
    print("\n" + "=" * 100)
    print("EXAMPLE: Signal at $10, ATR = $1, Limit fills at $11 (+1.25%)")
    print("=" * 100)

    examples = [
        ("Both to ENTRY", 10, 17, "11 - 1 = $10", "11 + 6 = $17", 1, 6),
        ("Both to SIGNAL", 9, 16, "10 - 1 = $9", "10 + 6 = $16", 2, 5),
        ("HYBRID", 10, 16, "11 - 1 = $10", "10 + 6 = $16", 1, 5),
    ]

    for name, sl, tp, sl_calc, tp_calc, sl_atr, tp_atr in examples:
        sl_pct = (11 - sl) / 11 * 100
        tp_pct = (tp - 11) / 11 * 100
        rr = tp_pct / sl_pct

        print(f"\n{name}:")
        print(f"   Entry: $11")
        print(f"   SL: ${sl} ({sl_calc}) = {sl_pct:.1f}% from entry")
        print(f"   TP: ${tp} ({tp_calc}) = +{tp_pct:.1f}% from entry")
        print(f"   R:R from entry: 1:{rr:.1f}")

    # Recommendation
    print("\n" + "=" * 100)
    print("RECOMMENDATION")
    print("=" * 100)

    # Sort by R/DD
    sorted_results = sorted(results, key=lambda x: x['rdd'], reverse=True)
    best = sorted_results[0]

    print(f"\n🏆 WINNER: {best['label']}")
    print(f"   NET: {best['net']:+.2f}%")
    print(f"   R/DD: {best['rdd']:.2f}x")
    print(f"   Expectancy: {best['expectancy']:+.3f}%")
    print(f"   Win Rate: {best['wr']:.1f}%")
    print(f"   Actual R:R: 1:{best['actual_rr']:.1f}")

    # Trade-offs
    print(f"\n📊 KEY TRADE-OFFS:")

    for r in sorted_results:
        if r == best:
            continue
        print(f"\n   vs {r['label']}:")
        print(f"   - NET: {best['net'] - r['net']:+.2f}% better")
        print(f"   - R/DD: {(best['rdd'] / r['rdd'] - 1)*100:+.1f}% better" if r['rdd'] > 0 else "")
        print(f"   - Win Rate: {best['wr'] - r['wr']:+.1f}%")
        print(f"   - Expectancy: {best['expectancy'] - r['expectancy']:+.3f}%")


if __name__ == "__main__":
    main()
