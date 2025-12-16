"""
Optimize Stop Loss and Take Profit ATR multipliers for CRV strategy
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

def backtest_with_params(df, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult=None, max_hold_bars=999):
    """Backtest with specific SL/TP parameters"""
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['atr'] = calculate_atr(df, 14)

    trades = []
    position = None

    for i in range(20, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            continue

        # Exit logic
        if position is not None:
            bars_held = i - position['entry_bar']
            exit_signal = None

            # Check stop loss (using high/low)
            if position['side'] == 'LONG':
                if current['low'] <= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss']}
            else:
                if current['high'] >= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss']}

            # Check take profit
            if not exit_signal and tp_atr_mult is not None:
                if position['side'] == 'LONG':
                    if current['high'] >= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'exit_price': position['take_profit']}
                else:
                    if current['low'] <= position['take_profit']:
                        exit_signal = {'reason': 'TP', 'exit_price': position['take_profit']}

            # RSI exit
            if not exit_signal:
                if position['side'] == 'LONG':
                    if current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                        exit_signal = {'reason': 'RSI', 'exit_price': current['close']}
                else:
                    if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                        exit_signal = {'reason': 'RSI', 'exit_price': current['close']}

            # Time exit
            if not exit_signal and bars_held >= max_hold_bars:
                exit_signal = {'reason': 'TIME', 'exit_price': current['close']}

            if exit_signal:
                entry = position['entry_price']
                exit_price = exit_signal['exit_price']

                if position['side'] == 'LONG':
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100

                trades.append({
                    'entry_bar': position['entry_bar'],
                    'exit_bar': i,
                    'side': position['side'],
                    'entry_price': entry,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_signal['reason'],
                    'bars_held': bars_held
                })
                position = None

        # Entry logic
        if position is None:
            signal = None

            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                # Check if limit fills
                filled = False
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']

                        stop_loss = entry_price - (stop_atr_mult * entry_atr)
                        take_profit = entry_price + (tp_atr_mult * entry_atr) if tp_atr_mult else None

                        # Check immediate stop
                        if df.iloc[entry_bar]['low'] > stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'side': 'LONG',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        filled = True
                        break

            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                filled = False
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']

                        stop_loss = entry_price + (stop_atr_mult * entry_atr)
                        take_profit = entry_price - (tp_atr_mult * entry_atr) if tp_atr_mult else None

                        if df.iloc[entry_bar]['high'] < stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'side': 'SHORT',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        filled = True
                        break

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()

    total_return = trades_df['cumulative'].iloc[-1]
    max_dd = (trades_df['cumulative'] - trades_df['cumulative'].cummax()).min()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df) * 100
    rr_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'win_rate': win_rate,
        'avg_winner': trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] > 0).any() else 0,
        'avg_loser': trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if (trades_df['pnl_pct'] < 0).any() else 0,
        'worst_trade': trades_df['pnl_pct'].min(),
        'exit_reasons': trades_df['exit_reason'].value_counts().to_dict()
    }

def main():
    df = pd.read_csv('bingx-trading-bot/trading/crv_usdt_90d_1h.csv')
    df['time'] = pd.to_datetime(df['timestamp'])

    print('='*100)
    print('🔍 STOP LOSS OPTIMIZATION (No TP, No Time Limit)')
    print('='*100)
    print()

    # Test different stop loss multipliers
    sl_results = []
    for sl_mult in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
        result = backtest_with_params(
            df,
            rsi_low=27,
            rsi_high=65,
            limit_offset_pct=1.0,
            stop_atr_mult=sl_mult,
            tp_atr_mult=None,  # No TP yet
            max_hold_bars=999
        )

        if result:
            sl_results.append({'sl_mult': sl_mult, **result})

    # Display results
    print(f'{"SL":<6} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"Avg W":<8} {"Avg L":<8} {"Worst":<8}')
    print('-'*100)

    for r in sl_results:
        print(f'{r["sl_mult"]}x ATR {r["trades"]:<8} {r["return"]:>8.1f}% {r["max_dd"]:>8.2f}% {r["rr_ratio"]:>7.2f}x {r["win_rate"]:>6.1f}% {r["avg_winner"]:>6.2f}% {r["avg_loser"]:>6.2f}% {r["worst_trade"]:>6.2f}%')

    # Find best SL by R/R ratio
    best_sl = max(sl_results, key=lambda x: x['rr_ratio'])
    print()
    print(f'🏆 Best Stop Loss: {best_sl["sl_mult"]}x ATR (R/R: {best_sl["rr_ratio"]:.2f}x)')

    # Now test Take Profits with best SL
    print()
    print('='*100)
    print(f'🎯 TAKE PROFIT OPTIMIZATION (SL = {best_sl["sl_mult"]}x ATR)')
    print('='*100)
    print()

    tp_results = []
    for tp_mult in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, None]:  # None = no TP (RSI exit only)
        result = backtest_with_params(
            df,
            rsi_low=27,
            rsi_high=65,
            limit_offset_pct=1.0,
            stop_atr_mult=best_sl['sl_mult'],
            tp_atr_mult=tp_mult,
            max_hold_bars=999
        )

        if result:
            tp_results.append({'tp_mult': tp_mult if tp_mult else 'RSI', **result})

    print(f'{"TP":<8} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"Avg W":<8} {"Avg L":<8}')
    print('-'*100)

    for r in tp_results:
        tp_label = f'{r["tp_mult"]}x ATR' if isinstance(r["tp_mult"], float) else 'RSI only'
        print(f'{tp_label:<8} {r["trades"]:<8} {r["return"]:>8.1f}% {r["max_dd"]:>8.2f}% {r["rr_ratio"]:>7.2f}x {r["win_rate"]:>6.1f}% {r["avg_winner"]:>6.2f}% {r["avg_loser"]:>6.2f}%')

    best_tp = max(tp_results, key=lambda x: x['rr_ratio'])
    tp_label = f'{best_tp["tp_mult"]}x ATR' if isinstance(best_tp["tp_mult"], float) else 'RSI only'

    print()
    print(f'🏆 Best Take Profit: {tp_label} (R/R: {best_tp["rr_ratio"]:.2f}x)')

    # Final recommendation
    print()
    print('='*100)
    print('✅ OPTIMAL CONFIGURATION')
    print('='*100)
    print(f'\nStop Loss: {best_sl["sl_mult"]}x ATR')
    print(f'Take Profit: {tp_label}')
    print(f'\nExpected Performance:')
    print(f'  - Trades: {best_tp["trades"]}')
    print(f'  - Return: +{best_tp["return"]:.1f}%')
    print(f'  - Max DD: {best_tp["max_dd"]:.2f}%')
    print(f'  - R/R Ratio: {best_tp["rr_ratio"]:.2f}x')
    print(f'  - Win Rate: {best_tp["win_rate"]:.1f}%')
    print(f'  - Avg Winner: +{best_tp["avg_winner"]:.2f}%')
    print(f'  - Avg Loser: {best_tp["avg_loser"]:.2f}%')
    print(f'  - Worst Trade: {best_tp["worst_trade"]:.2f}%')

    print(f'\n💰 Portfolio Impact (10% position sizing):')
    print(f'  - Worst trade impact: {best_tp["worst_trade"] * 0.1:.3f}% of portfolio')
    print(f'  - Max DD impact: {best_tp["max_dd"] * 0.1:.3f}% of portfolio')

    print('\n' + '='*100)

if __name__ == '__main__':
    main()
