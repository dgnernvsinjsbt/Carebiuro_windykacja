#!/usr/bin/env python3
"""
MOODENG RSI Strategy - Trade Verification & Statistics
Verify SL 1.0x / TP 6.0x configuration with comprehensive stats
"""

import pandas as pd
import numpy as np
from datetime import datetime

FEE_PER_TRADE = 0.10  # BingX 0.05% x2


def load_data():
    """Load MOODENG BingX data"""
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

    # Basics
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']

    return df


def run_strategy(df, sl_mult=1.0, tp_mult=6.0, max_bars=60):
    """
    Run MOODENG RSI strategy with detailed trade logging

    Entry:
    - RSI crosses above 55
    - Bullish candle with body > 0.5%
    - Price above SMA(20)

    Exit:
    - SL: entry - (ATR * sl_mult)
    - TP: entry + (ATR * tp_mult)
    - Time: max_bars
    """
    trades = []
    in_position = False

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # Entry conditions
            rsi_cross = prev['rsi'] < 55 and row['rsi'] >= 55
            bullish_body = row['is_bullish'] and row['body_pct'] > 0.5
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                entry_atr = row['atr']
                entry_time = row['timestamp']

                stop_loss = entry_price - (entry_atr * sl_mult)
                take_profit = entry_price + (entry_atr * tp_mult)
        else:
            bars_held = i - entry_idx

            # Check SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'bars': bars_held,
                    'entry_rsi': df.iloc[entry_idx]['rsi'],
                    'entry_atr': entry_atr
                })
                in_position = False
                continue

            # Check TP
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'bars': bars_held,
                    'entry_rsi': df.iloc[entry_idx]['rsi'],
                    'entry_atr': entry_atr
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'bars': bars_held,
                    'entry_rsi': df.iloc[entry_idx]['rsi'],
                    'entry_atr': entry_atr
                })
                in_position = False

    return pd.DataFrame(trades)


def calculate_streaks(df_trades):
    """Calculate win/loss streaks"""
    df_trades['is_win'] = df_trades['pnl_pct'] > 0

    streaks = []
    current_streak = 0
    current_type = None

    for is_win in df_trades['is_win']:
        if is_win == current_type:
            current_streak += 1
        else:
            if current_type is not None:
                streaks.append({'type': 'win' if current_type else 'loss', 'length': current_streak})
            current_streak = 1
            current_type = is_win

    # Add final streak
    if current_type is not None:
        streaks.append({'type': 'win' if current_type else 'loss', 'length': current_streak})

    df_streaks = pd.DataFrame(streaks)

    win_streaks = df_streaks[df_streaks['type'] == 'win']['length']
    loss_streaks = df_streaks[df_streaks['type'] == 'loss']['length']

    return {
        'max_win_streak': win_streaks.max() if len(win_streaks) > 0 else 0,
        'avg_win_streak': win_streaks.mean() if len(win_streaks) > 0 else 0,
        'max_loss_streak': loss_streaks.max() if len(loss_streaks) > 0 else 0,
        'avg_loss_streak': loss_streaks.mean() if len(loss_streaks) > 0 else 0
    }


def analyze_trades(df_trades):
    """Comprehensive trade analysis"""

    if len(df_trades) == 0:
        return None

    # Separate winners and losers
    winners = df_trades[df_trades['pnl_pct'] > 0]
    losers = df_trades[df_trades['pnl_pct'] <= 0]

    # Basic stats
    total_trades = len(df_trades)
    win_count = len(winners)
    loss_count = len(losers)
    win_rate = win_count / total_trades * 100

    # PnL stats
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    median_win = winners['pnl_pct'].median() if len(winners) > 0 else 0
    median_loss = losers['pnl_pct'].median() if len(losers) > 0 else 0

    avg_trade = df_trades['pnl_pct'].mean()
    median_trade = df_trades['pnl_pct'].median()

    # Expectancy
    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

    # Profit factor
    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Equity curve
    equity = [100]
    for pnl in df_trades['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    # Drawdown
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    # Returns
    gross_return = equity[-1] - 100
    fee_cost = total_trades * FEE_PER_TRADE
    net_return = gross_return - fee_cost

    # Top trade concentration
    sorted_winners = winners.sort_values('pnl_pct', ascending=False)
    top_5_profit = sorted_winners.head(5)['pnl_pct'].sum() if len(sorted_winners) >= 5 else sorted_winners['pnl_pct'].sum()
    top_20pct_count = max(1, int(total_trades * 0.2))
    top_20pct = df_trades.nlargest(top_20pct_count, 'pnl_pct')
    top_20pct_profit = top_20pct['pnl_pct'].sum()

    concentration_top5 = (top_5_profit / gross_return * 100) if gross_return > 0 else 0
    concentration_top20 = (top_20pct_profit / gross_return * 100) if gross_return > 0 else 0

    # Streaks
    streak_stats = calculate_streaks(df_trades)

    # Exit breakdown
    sl_count = len(df_trades[df_trades['result'] == 'SL'])
    tp_count = len(df_trades[df_trades['result'] == 'TP'])
    time_count = len(df_trades[df_trades['result'] == 'TIME'])

    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'median_win': median_win,
        'median_loss': median_loss,
        'avg_trade': avg_trade,
        'median_trade': median_trade,
        'expectancy': expectancy,
        'profit_factor': profit_factor,
        'gross_return': gross_return,
        'fee_cost': fee_cost,
        'net_return': net_return,
        'max_dd': max_dd,
        'r_dd': net_return / max_dd if max_dd > 0 else 0,
        'concentration_top5': concentration_top5,
        'concentration_top20': concentration_top20,
        'max_win_streak': streak_stats['max_win_streak'],
        'avg_win_streak': streak_stats['avg_win_streak'],
        'max_loss_streak': streak_stats['max_loss_streak'],
        'avg_loss_streak': streak_stats['avg_loss_streak'],
        'sl_count': sl_count,
        'tp_count': tp_count,
        'time_count': time_count,
        'avg_bars_held': df_trades['bars'].mean()
    }


def main():
    print("=" * 90)
    print("MOODENG RSI STRATEGY - TRADE VERIFICATION")
    print("Configuration: SL 1.0x ATR / TP 6.0x ATR")
    print("=" * 90)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")

    # Run strategy
    df_trades = run_strategy(df, sl_mult=1.0, tp_mult=6.0, max_bars=60)

    if len(df_trades) == 0:
        print("❌ No trades generated!")
        return

    # Analyze
    stats = analyze_trades(df_trades)

    # Print comprehensive stats
    print("=" * 90)
    print("TRADE STATISTICS")
    print("=" * 90)

    print(f"\n📊 BASIC METRICS")
    print(f"   Total Trades:        {stats['total_trades']}")
    print(f"   Winners:             {stats['win_count']}")
    print(f"   Losers:              {stats['loss_count']}")
    print(f"   Win Rate:            {stats['win_rate']:.1f}%")

    print(f"\n💰 PROFIT/LOSS ANALYSIS")
    print(f"   Average Win:         +{stats['avg_win']:.2f}%")
    print(f"   Average Loss:        {stats['avg_loss']:.2f}%")
    print(f"   Median Win:          +{stats['median_win']:.2f}%")
    print(f"   Median Loss:         {stats['median_loss']:.2f}%")
    print(f"   Average Trade:       {stats['avg_trade']:+.2f}%")
    print(f"   Median Trade:        {stats['median_trade']:+.2f}%")

    print(f"\n🎯 PERFORMANCE METRICS")
    print(f"   Expectancy:          {stats['expectancy']:+.3f}%")
    print(f"   Profit Factor:       {stats['profit_factor']:.2f}x")
    print(f"   Gross Return:        {stats['gross_return']:+.2f}%")
    print(f"   Fee Cost:            -{stats['fee_cost']:.2f}%")
    print(f"   NET Return:          {stats['net_return']:+.2f}%")
    print(f"   Max Drawdown:        {stats['max_dd']:.2f}%")
    print(f"   Return/DD Ratio:     {stats['r_dd']:.2f}x")

    print(f"\n🔥 STREAK ANALYSIS")
    print(f"   Max Win Streak:      {stats['max_win_streak']:.0f} trades")
    print(f"   Avg Win Streak:      {stats['avg_win_streak']:.1f} trades")
    print(f"   Max Loss Streak:     {stats['max_loss_streak']:.0f} trades")
    print(f"   Avg Loss Streak:     {stats['avg_loss_streak']:.1f} trades")

    print(f"\n⚠️  OUTLIER DEPENDENCY")
    print(f"   Top 5 Trades:        {stats['concentration_top5']:.1f}% of profit")
    print(f"   Top 20% Trades:      {stats['concentration_top20']:.1f}% of profit")

    print(f"\n🚪 EXIT BREAKDOWN")
    print(f"   Stop Loss:           {stats['sl_count']} trades ({stats['sl_count']/stats['total_trades']*100:.1f}%)")
    print(f"   Take Profit:         {stats['tp_count']} trades ({stats['tp_count']/stats['total_trades']*100:.1f}%)")
    print(f"   Time Exit:           {stats['time_count']} trades ({stats['time_count']/stats['total_trades']*100:.1f}%)")
    print(f"   Avg Hold Time:       {stats['avg_bars_held']:.1f} bars")

    # Top 5 best trades
    print("\n" + "=" * 90)
    print("TOP 5 BEST TRADES")
    print("=" * 90)
    top5 = df_trades.nlargest(5, 'pnl_pct')
    for i, row in top5.iterrows():
        print(f"\n{i+1}. {row['entry_time'].strftime('%Y-%m-%d %H:%M')} → {row['exit_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Entry: ${row['entry_price']:.5f}, Exit: ${row['exit_price']:.5f}")
        print(f"   P&L: {row['pnl_pct']:+.2f}%, Result: {row['result']}, Held: {row['bars']} bars")

    # Top 5 worst trades
    print("\n" + "=" * 90)
    print("TOP 5 WORST TRADES")
    print("=" * 90)
    worst5 = df_trades.nsmallest(5, 'pnl_pct')
    for i, row in worst5.iterrows():
        print(f"\n{i+1}. {row['entry_time'].strftime('%Y-%m-%d %H:%M')} → {row['exit_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Entry: ${row['entry_price']:.5f}, Exit: ${row['exit_price']:.5f}")
        print(f"   P&L: {row['pnl_pct']:+.2f}%, Result: {row['result']}, Held: {row['bars']} bars")

    # Distribution analysis
    print("\n" + "=" * 90)
    print("PROFIT DISTRIBUTION")
    print("=" * 90)
    bins = [-100, -5, -2, -1, 0, 1, 2, 5, 10, 100]
    labels = ['<-5%', '-5 to -2%', '-2 to -1%', '-1 to 0%', '0 to 1%', '1 to 2%', '2 to 5%', '5 to 10%', '>10%']
    df_trades['bin'] = pd.cut(df_trades['pnl_pct'], bins=bins, labels=labels)
    dist = df_trades['bin'].value_counts().sort_index()

    for label, count in dist.items():
        pct = count / len(df_trades) * 100
        bar = '█' * int(pct / 2)
        print(f"   {label:>12}: {count:>3} trades ({pct:>5.1f}%) {bar}")

    # Save detailed trades
    output_file = '/workspaces/Carebiuro_windykacja/trading/results/moodeng_verified_trades.csv'
    df_trades.to_csv(output_file, index=False)
    print(f"\n✅ Detailed trades saved to: {output_file}")

    # Verdict
    print("\n" + "=" * 90)
    print("VERDICT")
    print("=" * 90)

    if stats['concentration_top20'] > 200:
        print("⚠️  HIGH OUTLIER DEPENDENCY")
        print(f"   Top 20% of trades contribute {stats['concentration_top20']:.0f}% of profit")
        print("   Strategy requires taking ALL signals to capture outliers")

    if stats['max_loss_streak'] > 20:
        print(f"\n⚠️  LONG LOSS STREAK: {stats['max_loss_streak']:.0f} consecutive losses")
        print("   May be psychologically challenging to trade")

    if stats['r_dd'] >= 3.0:
        print(f"\n✅ STRONG RISK-ADJUSTED RETURNS: {stats['r_dd']:.2f}x Return/DD")
        print("   Strategy meets deployment criteria")
    else:
        print(f"\n⚠️  MARGINAL RISK-ADJUSTED RETURNS: {stats['r_dd']:.2f}x Return/DD")
        print("   Consider additional filters or different configuration")


if __name__ == "__main__":
    main()
