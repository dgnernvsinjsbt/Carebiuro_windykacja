"""
Analyze REAL intrabar drawdown during 3-hour hold period
vs final exit price
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

def backtest_3h_with_intrabar_dd(df):
    """Backtest 3-hour exit WITH intrabar drawdown tracking"""
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'].values, 14)

    trades = []
    position = None

    for i in range(20, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']):
            continue

        # Exit logic (after 3 bars)
        if position is not None:
            bars_held = i - position['entry_bar']

            if bars_held >= 3:
                # Calculate final exit
                exit_price = current['close']

                if position['side'] == 'LONG':
                    final_pnl = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                else:
                    final_pnl = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                trades.append({
                    **position,
                    'exit_bar': i,
                    'exit_price': exit_price,
                    'final_pnl': final_pnl,
                    'bars_held': bars_held
                })
                position = None

        # Entry logic
        if position is None:
            signal = None

            # LONG signal
            if current['rsi'] > 27 and prev['rsi'] <= 27:
                signal_price = current['close']
                limit_price = signal_price * 0.99  # 1% better

                # Check if limit fills
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_bar = j
                        entry_price = limit_price

                        # Calculate intrabar drawdown for next 3 bars
                        position_bars = df.iloc[entry_bar:min(entry_bar+4, len(df))]
                        worst_price = position_bars['low'].min()
                        worst_dd = ((worst_price - entry_price) / entry_price) * 100

                        position = {
                            'entry_bar': entry_bar,
                            'side': 'LONG',
                            'entry_price': entry_price,
                            'intrabar_worst': worst_price,
                            'intrabar_dd': worst_dd
                        }
                        break

            # SHORT signal
            elif current['rsi'] < 65 and prev['rsi'] >= 65:
                signal_price = current['close']
                limit_price = signal_price * 1.01  # 1% better

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        entry_bar = j
                        entry_price = limit_price

                        # Calculate intrabar drawdown for next 3 bars
                        position_bars = df.iloc[entry_bar:min(entry_bar+4, len(df))]
                        worst_price = position_bars['high'].max()
                        worst_dd = ((entry_price - worst_price) / entry_price) * 100

                        position = {
                            'entry_bar': entry_bar,
                            'side': 'SHORT',
                            'entry_price': entry_price,
                            'intrabar_worst': worst_price,
                            'intrabar_dd': worst_dd
                        }
                        break

    return pd.DataFrame(trades)

def main():
    df = pd.read_csv('bingx-trading-bot/trading/crv_usdt_90d_1h.csv')
    df['time'] = pd.to_datetime(df['timestamp'])

    print('='*120)
    print('🔍 3-HOUR STRATEGY: INTRABAR DRAWDOWN vs FINAL EXIT PRICE')
    print('='*120)
    print()

    trades = backtest_3h_with_intrabar_dd(df)
    trades['cumulative'] = trades['final_pnl'].cumsum()

    # Calculate statistics
    total_return = trades['cumulative'].iloc[-1]
    max_dd_cumulative = (trades['cumulative'] - trades['cumulative'].cummax()).min()
    win_rate = (trades['final_pnl'] > 0).sum() / len(trades) * 100

    print(f'Total Trades: {len(trades)}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Total Return: +{total_return:.2f}%')
    print(f'Max Cumulative DD: {max_dd_cumulative:.2f}%')
    print()

    # Analyze intrabar vs final
    print('='*120)
    print('📊 INTRABAR DRAWDOWN ANALYSIS')
    print('='*120)
    print()

    worst_intrabar_dd = trades['intrabar_dd'].min()
    avg_intrabar_dd = trades[trades['intrabar_dd'] < 0]['intrabar_dd'].mean()

    print(f'Worst intrabar DD: {worst_intrabar_dd:.2f}% (during the trade)')
    print(f'Average intrabar DD (losers): {avg_intrabar_dd:.2f}%')
    print(f'Worst final P&L: {trades["final_pnl"].min():.2f}% (at exit)')
    print()

    # Show trades where intrabar DD was much worse than final P&L
    print('='*120)
    print('🎢 TRADES WITH BIG RECOVERIES (Intrabar DD >> Final Loss)')
    print('='*120)
    print()

    trades['recovery'] = trades['intrabar_dd'] - trades['final_pnl']
    big_recoveries = trades[trades['recovery'] < -2].sort_values('recovery')

    if len(big_recoveries) > 0:
        print(f'{"Trade":<7} {"Side":<6} {"Entry":<10} {"Worst DD":<12} {"Final P&L":<12} {"Recovery":<12}')
        print('-'*120)

        for idx, trade in big_recoveries.head(15).iterrows():
            print(f'#{idx+1:<6} {trade["side"]:<6} ${trade["entry_price"]:<9.4f} {trade["intrabar_dd"]:>10.2f}% {trade["final_pnl"]:>10.2f}% {trade["recovery"]:>10.2f}%')

        print()
        print(f'Found {len(big_recoveries)} trades that recovered >2% from worst point')
        print(f'Largest recovery: {big_recoveries["recovery"].min():.2f}% (went from {big_recoveries.iloc[0]["intrabar_dd"]:.2f}% to {big_recoveries.iloc[0]["final_pnl"]:.2f}%)')
    else:
        print('No significant recoveries found')

    # Show truly bad trades
    print()
    print('='*120)
    print('💀 WORST TRADES (Scary Intrabar Drawdowns)')
    print('='*120)
    print()

    worst_trades = trades.nsmallest(10, 'intrabar_dd')
    print(f'{"Trade":<7} {"Side":<6} {"Entry":<10} {"Worst Price":<12} {"Intrabar DD":<12} {"Exit Price":<12} {"Final P&L":<12}')
    print('-'*120)

    for idx, trade in worst_trades.iterrows():
        print(f'#{idx+1:<6} {trade["side"]:<6} ${trade["entry_price"]:<9.4f} ${trade["intrabar_worst"]:<11.4f} {trade["intrabar_dd"]:>10.2f}% ${trade["exit_price"]:<11.4f} {trade["final_pnl"]:>10.2f}%')

    # Summary comparison
    print()
    print('='*120)
    print('📊 REALITY CHECK')
    print('='*120)
    print()

    print('What the backtest shows (close prices only):')
    print(f'  - Max DD: {max_dd_cumulative:.2f}%')
    print(f'  - Worst trade: {trades["final_pnl"].min():.2f}%')
    print(f'  - R/R Ratio: {abs(total_return / max_dd_cumulative):.2f}x')

    print()
    print('What you ACTUALLY experience (intrabar reality):')
    print(f'  - Worst unrealized DD: {worst_intrabar_dd:.2f}% (during trade)')
    print(f'  - Average unrealized DD: {avg_intrabar_dd:.2f}%')
    print(f'  - # Trades with >5% intrabar DD: {(trades["intrabar_dd"] < -5).sum()}')
    print(f'  - # Trades with >10% intrabar DD: {(trades["intrabar_dd"] < -10).sum()}')

    print()
    print('💡 CONCLUSION:')
    if worst_intrabar_dd < -5:
        print(f'  ⚠️  You WILL experience drawdowns up to {worst_intrabar_dd:.2f}% during the 3 hours!')
        print(f'  Even though many recover by exit, you have to STOMACH the unrealized loss')
        print(f'  This is the hidden cost of the "wait 3 hours" strategy')
    else:
        print('  ✅ Intrabar drawdowns are manageable (<5%)')

    print()
    print('='*120)

    # Save detailed results
    trades.to_csv('3h_strategy_intrabar_analysis.csv', index=False)
    print('\n💾 Saved: 3h_strategy_intrabar_analysis.csv')

if __name__ == '__main__':
    main()
