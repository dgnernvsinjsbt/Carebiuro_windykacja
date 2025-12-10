#!/usr/bin/env python3
"""
MOODENG RSI - Limit Order Entry Filter Test
Test different limit order levels above signal to filter false breakouts
"""

import pandas as pd
import numpy as np

FEE_PER_TRADE = 0.10


def load_data():
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 0.0001)
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMA20
    df['sma_20'] = df['close'].rolling(20).mean()
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']

    return df


def run_strategy(df, limit_pct=0.0, sl_mult=1.0, tp_mult=6.0, max_bars=60, fill_timeout=10):
    """
    Strategy with limit order entry above signal

    limit_pct: % above signal price to place limit order (0 = market order)
    fill_timeout: max bars to wait for limit fill before canceling
    """
    trades = []
    in_position = False
    waiting_for_fill = False
    limit_price = signal_idx = signal_price = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position and not waiting_for_fill:
            # SIGNAL CHECK
            rsi_cross = prev['rsi'] < 55 and row['rsi'] >= 55
            bullish_body = row['is_bullish'] and row['body_pct'] > 0.5
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                signal_price = row['close']
                signal_idx = i
                signal_atr = row['atr']

                if limit_pct == 0:
                    # MARKET ORDER - immediate fill
                    in_position = True
                    entry_price = signal_price
                    entry_idx = i
                    entry_atr = signal_atr
                    stop_loss = entry_price - (entry_atr * sl_mult)
                    take_profit = entry_price + (entry_atr * tp_mult)
                else:
                    # LIMIT ORDER - wait for fill
                    waiting_for_fill = True
                    limit_price = signal_price * (1 + limit_pct/100)

        elif waiting_for_fill:
            # Check if limit filled
            if row['high'] >= limit_price:
                # FILLED
                in_position = True
                waiting_for_fill = False
                entry_price = limit_price
                entry_idx = i
                # Use SIGNAL candle's ATR (not current candle)
                entry_atr = df.iloc[signal_idx]['atr']

                # SL based on limit entry, TP based on original signal ATR
                stop_loss = entry_price - (entry_atr * sl_mult)
                take_profit = entry_price + (entry_atr * tp_mult)

            # Cancel if timeout
            elif i - signal_idx >= fill_timeout:
                waiting_for_fill = False
                # Trade never entered - no record

        elif in_position:
            bars_held = i - entry_idx

            # Check SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'bars': bars_held,
                    'signal_price': signal_price
                })
                in_position = False
                continue

            # Check TP
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'bars': bars_held,
                    'signal_price': signal_price
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'bars': bars_held,
                    'signal_price': signal_price
                })
                in_position = False

    return trades


def analyze(trades, label=''):
    if not trades:
        return {
            'label': label,
            'trades': 0,
            'net': 0,
            'wr': 0,
            'dd': 0,
            'rdd': 0,
            'avg_trade': 0,
            'median_trade': 0,
            'expectancy': 0,
            'pf': 0,
            'max_loss_streak': 0,
            'sl_count': 0,
            'tp_count': 0
        }

    df = pd.DataFrame(trades)

    # Winners/losers
    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]

    win_rate = len(winners) / len(df) * 100
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    avg_trade = df['pnl_pct'].mean()
    median_trade = df['pnl_pct'].median()

    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

    # PF
    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

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

    # Loss streaks
    df['is_loss'] = df['pnl_pct'] <= 0
    streaks = []
    current = 0
    for is_loss in df['is_loss']:
        if is_loss:
            current += 1
        else:
            if current > 0:
                streaks.append(current)
            current = 0
    if current > 0:
        streaks.append(current)

    max_loss_streak = max(streaks) if streaks else 0

    # Exit breakdown
    sl_count = len(df[df['result'] == 'SL'])
    tp_count = len(df[df['result'] == 'TP'])

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
        'avg_trade': avg_trade,
        'median_trade': median_trade,
        'expectancy': expectancy,
        'pf': pf,
        'max_loss_streak': max_loss_streak,
        'sl_count': sl_count,
        'tp_count': tp_count,
        'top20_conc': concentration
    }


def main():
    print("=" * 100)
    print("MOODENG RSI - LIMIT ORDER ENTRY FILTER TEST")
    print("=" * 100)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles\n")

    results = []

    # Test different limit order levels
    limit_levels = [
        0.0,    # Market order (baseline)
        0.25,   # +0.25% above signal
        0.5,    # +0.5% above signal
        0.75,   # +0.75% above signal
        1.0,    # +1% above signal
        1.25,   # +1.25% above signal
        1.5,    # +1.5% above signal
        2.0,    # +2% above signal
    ]

    print("Testing limit order levels from 0% (market) to 2.0% above signal...\n")
    print(f"{'Limit':<8} {'Trades':<8} {'NET':<10} {'WR':<7} {'DD':<8} {'R/DD':<8} {'Avg':<9} {'Exp':<9} {'MaxLS':<7} {'SL/TP':<10} {'Top20%'}")
    print("-" * 100)

    for limit_pct in limit_levels:
        trades = run_strategy(df, limit_pct=limit_pct, sl_mult=1.0, tp_mult=6.0)
        label = f"Market" if limit_pct == 0 else f"+{limit_pct}%"
        r = analyze(trades, label)
        results.append(r)

        sl_tp = f"{r['sl_count']}/{r['tp_count']}"
        print(f"{r['label']:<8} {r['trades']:<8} {r['net']:>+8.2f}% {r['wr']:>6.1f}% "
              f"{r['dd']:>7.2f}% {r['rdd']:>7.2f}x {r['avg_trade']:>+7.3f}% "
              f"{r['expectancy']:>+7.3f}% {r['max_loss_streak']:>6.0f} {sl_tp:<10} {r['top20_conc']:>6.1f}%")

    # Best by different criteria
    print("\n" + "=" * 100)
    print("BEST CONFIGURATIONS")
    print("=" * 100)

    df_results = pd.DataFrame(results)

    best_rdd = df_results.nlargest(1, 'rdd').iloc[0]
    best_net = df_results.nlargest(1, 'net').iloc[0]
    best_wr = df_results.nlargest(1, 'wr').iloc[0]
    best_exp = df_results.nlargest(1, 'expectancy').iloc[0]
    min_streak = df_results.nsmallest(1, 'max_loss_streak').iloc[0]

    print(f"\n🏆 BEST RETURN/DD: {best_rdd['label']}")
    print(f"   NET: {best_rdd['net']:+.2f}%, R/DD: {best_rdd['rdd']:.2f}x, Trades: {best_rdd['trades']}, "
          f"WR: {best_rdd['wr']:.1f}%, Max Loss Streak: {best_rdd['max_loss_streak']:.0f}")

    print(f"\n💰 HIGHEST NET RETURN: {best_net['label']}")
    print(f"   NET: {best_net['net']:+.2f}%, R/DD: {best_net['rdd']:.2f}x, Trades: {best_net['trades']}, "
          f"WR: {best_net['wr']:.1f}%, Max Loss Streak: {best_net['max_loss_streak']:.0f}")

    print(f"\n🎯 HIGHEST WIN RATE: {best_wr['label']}")
    print(f"   WR: {best_wr['wr']:.1f}%, NET: {best_wr['net']:+.2f}%, R/DD: {best_wr['rdd']:.2f}x, "
          f"Trades: {best_wr['trades']}, Max Loss Streak: {best_wr['max_loss_streak']:.0f}")

    print(f"\n📈 BEST EXPECTANCY: {best_exp['label']}")
    print(f"   Exp: {best_exp['expectancy']:+.3f}%, NET: {best_exp['net']:+.2f}%, R/DD: {best_exp['rdd']:.2f}x, "
          f"WR: {best_exp['wr']:.1f}%, Trades: {best_exp['trades']}")

    print(f"\n🛡️  SHORTEST LOSS STREAK: {min_streak['label']}")
    print(f"   Max Loss Streak: {min_streak['max_loss_streak']:.0f}, NET: {min_streak['net']:+.2f}%, "
          f"R/DD: {min_streak['rdd']:.2f}x, WR: {min_streak['wr']:.1f}%, Trades: {min_streak['trades']}")

    # Trade-off analysis
    print("\n" + "=" * 100)
    print("LIMIT ORDER TRADE-OFFS")
    print("=" * 100)

    baseline = results[0]  # Market order
    for r in results[1:]:
        trade_reduction = (1 - r['trades']/baseline['trades']) * 100
        net_change = r['net'] - baseline['net']
        wr_change = r['wr'] - baseline['wr']
        streak_change = baseline['max_loss_streak'] - r['max_loss_streak']

        print(f"\n{r['label']} vs Market:")
        print(f"   Trades: {r['trades']} ({trade_reduction:+.0f}% reduction)")
        print(f"   NET: {r['net']:+.2f}% ({net_change:+.2f}%)")
        print(f"   Win Rate: {r['wr']:.1f}% ({wr_change:+.1f}%)")
        print(f"   Max Loss Streak: {r['max_loss_streak']:.0f} ({streak_change:+.0f} fewer)")
        print(f"   Expectancy: {r['expectancy']:+.3f}%")

        if r['rdd'] > baseline['rdd']:
            improvement = (r['rdd'] / baseline['rdd'] - 1) * 100
            print(f"   ✅ R/DD improved by {improvement:+.1f}%")

    # Recommendation
    print("\n" + "=" * 100)
    print("RECOMMENDATION")
    print("=" * 100)

    # Find best balance: high R/DD, decent trade count, low loss streaks
    df_results['score'] = (
        df_results['rdd'] * 2 +  # Prioritize R/DD
        (df_results['trades'] / df_results['trades'].max()) * 0.5 +  # Keep enough trades
        (1 - df_results['max_loss_streak'] / df_results['max_loss_streak'].max()) * 1  # Reduce streaks
    )

    recommended = df_results.nlargest(1, 'score').iloc[0]

    print(f"\n🎯 RECOMMENDED: {recommended['label']}")
    print(f"   NET Return: {recommended['net']:+.2f}%")
    print(f"   Return/DD: {recommended['rdd']:.2f}x")
    print(f"   Win Rate: {recommended['wr']:.1f}%")
    print(f"   Trades: {recommended['trades']}")
    print(f"   Max Loss Streak: {recommended['max_loss_streak']:.0f}")
    print(f"   Expectancy: {recommended['expectancy']:+.3f}%")
    print(f"   Top 20% Concentration: {recommended['top20_conc']:.1f}%")

    if recommended['label'] != 'Market':
        print(f"\n✅ Using limit orders filters out weak signals and improves risk-adjusted returns!")
    else:
        print(f"\n⚠️  Market orders still perform best on this data")


if __name__ == "__main__":
    main()
