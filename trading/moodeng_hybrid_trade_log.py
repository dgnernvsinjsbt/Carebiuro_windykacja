#!/usr/bin/env python3
"""
MOODENG HYBRID Strategy - Complete Trade Log
Chronological trade list with running statistics
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


def run_hybrid_strategy(df, limit_pct=1.25, sl_mult=1.0, tp_mult=6.0):
    """
    HYBRID Strategy:
    - SL anchored to entry (tight stop)
    - TP anchored to signal (original target)
    - Results in R:R ~1:5 from entry
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
                signal_time = row['timestamp']
                signal_idx = i
                signal_atr = row['atr']
                signal_rsi = row['rsi']
                waiting_for_fill = True
                limit_price = signal_price * (1 + limit_pct/100)

        elif waiting_for_fill:
            # Check if limit filled
            if row['high'] >= limit_price:
                in_position = True
                waiting_for_fill = False
                entry_price = limit_price
                entry_time = row['timestamp']
                entry_idx = i
                entry_atr = df.iloc[signal_idx]['atr']
                signal_price_ref = df.iloc[signal_idx]['close']

                # HYBRID: SL from entry, TP from signal
                stop_loss = entry_price - (entry_atr * sl_mult)
                take_profit = signal_price_ref + (entry_atr * tp_mult)

                sl_dist_pct = (entry_price - stop_loss) / entry_price * 100
                tp_dist_pct = (take_profit - entry_price) / entry_price * 100

            # Cancel if timeout
            elif i - signal_idx >= 10:
                waiting_for_fill = False

        elif in_position:
            bars_held = i - entry_idx

            # Check SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'trade_num': len(trades) + 1,
                    'signal_time': signal_time,
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'signal_price': signal_price_ref,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'bars_held': bars_held,
                    'signal_rsi': signal_rsi,
                    'sl_dist_pct': sl_dist_pct,
                    'tp_dist_pct': tp_dist_pct
                })
                in_position = False
                continue

            # Check TP
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'trade_num': len(trades) + 1,
                    'signal_time': signal_time,
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'signal_price': signal_price_ref,
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'bars_held': bars_held,
                    'signal_rsi': signal_rsi,
                    'sl_dist_pct': sl_dist_pct,
                    'tp_dist_pct': tp_dist_pct
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= 60:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'trade_num': len(trades) + 1,
                    'signal_time': signal_time,
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'signal_price': signal_price_ref,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'bars_held': bars_held,
                    'signal_rsi': signal_rsi,
                    'sl_dist_pct': sl_dist_pct,
                    'tp_dist_pct': tp_dist_pct
                })
                in_position = False

    return pd.DataFrame(trades)


def add_running_stats(df_trades):
    """Add running statistics to trade log"""

    # Running equity
    equity = 100
    df_trades['equity_before'] = 0.0
    df_trades['equity_after'] = 0.0
    df_trades['running_pnl'] = 0.0

    # Running DD
    peak = 100
    df_trades['peak_equity'] = 0.0
    df_trades['dd_pct'] = 0.0
    df_trades['max_dd_so_far'] = 0.0

    # Win/loss streaks
    df_trades['consecutive_losses'] = 0
    df_trades['consecutive_wins'] = 0
    current_loss_streak = 0
    current_win_streak = 0

    # Running stats
    df_trades['cumulative_wins'] = 0
    df_trades['cumulative_losses'] = 0
    df_trades['running_win_rate'] = 0.0

    wins = 0
    losses = 0
    max_dd_overall = 0

    for i, row in df_trades.iterrows():
        # Equity before trade
        df_trades.at[i, 'equity_before'] = equity

        # Execute trade (subtract fee)
        pnl_with_fee = row['pnl_pct'] - FEE_PER_TRADE
        equity = equity * (1 + pnl_with_fee / 100)

        # Equity after trade
        df_trades.at[i, 'equity_after'] = equity
        df_trades.at[i, 'running_pnl'] = equity - 100

        # Update peak and DD
        if equity > peak:
            peak = equity

        dd = (peak - equity) / peak * 100
        max_dd_overall = max(max_dd_overall, dd)

        df_trades.at[i, 'peak_equity'] = peak
        df_trades.at[i, 'dd_pct'] = dd
        df_trades.at[i, 'max_dd_so_far'] = max_dd_overall

        # Win/loss tracking
        is_win = row['pnl_pct'] > 0

        if is_win:
            wins += 1
            current_win_streak += 1
            current_loss_streak = 0
        else:
            losses += 1
            current_loss_streak += 1
            current_win_streak = 0

        df_trades.at[i, 'consecutive_losses'] = current_loss_streak
        df_trades.at[i, 'consecutive_wins'] = current_win_streak
        df_trades.at[i, 'cumulative_wins'] = wins
        df_trades.at[i, 'cumulative_losses'] = losses
        df_trades.at[i, 'running_win_rate'] = wins / (wins + losses) * 100

    return df_trades


def main():
    print("=" * 120)
    print("MOODENG HYBRID STRATEGY - COMPLETE TRADE LOG")
    print("Configuration: Limit +1.25%, SL→entry (1x ATR), TP→signal (6x ATR)")
    print("=" * 120)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")

    # Run strategy
    df_trades = run_hybrid_strategy(df)

    if len(df_trades) == 0:
        print("No trades generated!")
        return

    # Add running statistics
    df_trades = add_running_stats(df_trades)

    # Print summary first
    final_equity = df_trades.iloc[-1]['equity_after']
    total_return = final_equity - 100
    max_dd = df_trades['max_dd_so_far'].max()
    win_rate = df_trades.iloc[-1]['running_win_rate']

    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)
    print(f"Total Trades: {len(df_trades)}")
    print(f"Final Equity: ${final_equity:.2f} (started at $100)")
    print(f"NET Return: {total_return:+.2f}%")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Return/DD: {total_return/max_dd:.2f}x")
    print(f"Final Win Rate: {win_rate:.1f}%")
    print(f"Wins: {df_trades.iloc[-1]['cumulative_wins']:.0f} | Losses: {df_trades.iloc[-1]['cumulative_losses']:.0f}")
    print(f"Max Consecutive Losses: {df_trades['consecutive_losses'].max():.0f}")
    print(f"Max Consecutive Wins: {df_trades['consecutive_wins'].max():.0f}")

    # Complete trade log
    print("\n" + "=" * 120)
    print("CHRONOLOGICAL TRADE LOG")
    print("=" * 120)
    print()

    for _, trade in df_trades.iterrows():
        trade_num = int(trade['trade_num'])

        # Header
        marker = "🟢" if trade['pnl_pct'] > 0 else "🔴"
        print(f"{marker} TRADE #{trade_num} - {trade['result']}")
        print("-" * 120)

        # Timing
        print(f"Signal:  {trade['signal_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['signal_price']:.5f} (RSI {trade['signal_rsi']:.1f})")
        print(f"Entry:   {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['entry_price']:.5f} (+{((trade['entry_price']/trade['signal_price'])-1)*100:.2f}% from signal)")
        print(f"Exit:    {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ ${trade['exit_price']:.5f} ({int(trade['bars_held'])} bars held)")

        # P&L
        gross_pnl = trade['pnl_pct']
        net_pnl = gross_pnl - FEE_PER_TRADE
        print(f"\nP&L:     {gross_pnl:+.2f}% (gross) | {net_pnl:+.2f}% (net after 0.10% fee)")
        print(f"R:R:     SL {trade['sl_dist_pct']:.2f}% / TP {trade['tp_dist_pct']:.2f}% = 1:{trade['tp_dist_pct']/trade['sl_dist_pct']:.1f}")

        # Account status
        print(f"\nAccount: ${trade['equity_before']:.2f} → ${trade['equity_after']:.2f} (Running P&L: {trade['running_pnl']:+.2f}%)")
        print(f"Peak:    ${trade['peak_equity']:.2f} | Current DD: {trade['dd_pct']:.2f}% | Max DD so far: {trade['max_dd_so_far']:.2f}%")

        # Streaks & Stats
        if trade['consecutive_losses'] > 0:
            print(f"Streak:  🔴 {int(trade['consecutive_losses'])} consecutive losses")
        elif trade['consecutive_wins'] > 0:
            print(f"Streak:  🟢 {int(trade['consecutive_wins'])} consecutive wins")

        print(f"Stats:   W/L: {int(trade['cumulative_wins'])}/{int(trade['cumulative_losses'])} | Win Rate: {trade['running_win_rate']:.1f}%")
        print()

    # Save to CSV
    output_file = '/workspaces/Carebiuro_windykacja/trading/results/moodeng_hybrid_complete_log.csv'
    df_trades.to_csv(output_file, index=False)
    print(f"\n✅ Complete trade log saved to: {output_file}")

    # Additional analysis
    print("\n" + "=" * 120)
    print("ADDITIONAL ANALYSIS")
    print("=" * 120)

    # Best/worst trades
    best_trade = df_trades.nlargest(1, 'pnl_pct').iloc[0]
    worst_trade = df_trades.nsmallest(1, 'pnl_pct').iloc[0]

    print(f"\n🏆 BEST TRADE: #{int(best_trade['trade_num'])}")
    print(f"   {best_trade['entry_time'].strftime('%Y-%m-%d %H:%M')} → {best_trade['exit_time'].strftime('%Y-%m-%d %H:%M')}")
    print(f"   Entry: ${best_trade['entry_price']:.5f} | Exit: ${best_trade['exit_price']:.5f}")
    print(f"   P&L: {best_trade['pnl_pct']:+.2f}% | Result: {best_trade['result']}")

    print(f"\n💀 WORST TRADE: #{int(worst_trade['trade_num'])}")
    print(f"   {worst_trade['entry_time'].strftime('%Y-%m-%d %H:%M')} → {worst_trade['exit_time'].strftime('%Y-%m-%d %H:%M')}")
    print(f"   Entry: ${worst_trade['entry_price']:.5f} | Exit: ${worst_trade['exit_price']:.5f}")
    print(f"   P&L: {worst_trade['pnl_pct']:+.2f}% | Result: {worst_trade['result']}")

    # Monthly breakdown
    print(f"\n📅 MONTHLY BREAKDOWN")
    df_trades['month'] = pd.to_datetime(df_trades['exit_time']).dt.to_period('M')
    monthly = df_trades.groupby('month').agg({
        'pnl_pct': ['count', 'sum', 'mean'],
        'result': lambda x: (x == 'TP').sum()
    })

    for month, row in monthly.iterrows():
        trades_count = int(row['pnl_pct']['count'])
        total_pnl = row['pnl_pct']['sum']
        avg_pnl = row['pnl_pct']['mean']
        tp_count = int(row['result']['<lambda>'])
        wr = tp_count / trades_count * 100 if trades_count > 0 else 0

        print(f"   {month}: {trades_count} trades | Total: {total_pnl:+.2f}% | Avg: {avg_pnl:+.2f}% | WR: {wr:.0f}%")


if __name__ == "__main__":
    main()
