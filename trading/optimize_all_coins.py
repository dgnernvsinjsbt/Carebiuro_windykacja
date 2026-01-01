"""
COMPREHENSIVE OPTIMIZATION - All 10 coins
Test: SL/TP multipliers, limit offset %
Find optimal config per coin
"""
import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')

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

def backtest(df, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, fee_pct=0.05):
    """Fast backtest with all parameters"""
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

            # Stop loss (intrabar)
            if position['side'] == 'LONG':
                if current['low'] <= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss']}
            else:
                if current['high'] >= position['stop_loss']:
                    exit_signal = {'reason': 'STOP', 'exit_price': position['stop_loss']}

            # Take profit (intrabar)
            if not exit_signal:
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

            if exit_signal:
                entry = position['entry_price']
                exit_price = exit_signal['exit_price']

                if position['side'] == 'LONG':
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100

                pnl_pct -= (2 * fee_pct)  # Fees

                trades.append({
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_signal['reason']
                })
                position = None

        # Entry logic
        if position is None:
            # LONG signal
            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']

                        stop_loss = entry_price - (stop_atr_mult * entry_atr)
                        take_profit = entry_price + (tp_atr_mult * entry_atr)

                        if df.iloc[entry_bar]['low'] > stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'side': 'LONG',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        break

            # SHORT signal
            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        entry_bar = j
                        entry_price = limit_price
                        entry_atr = df.iloc[entry_bar]['atr']

                        stop_loss = entry_price + (stop_atr_mult * entry_atr)
                        take_profit = entry_price - (tp_atr_mult * entry_atr)

                        if df.iloc[entry_bar]['high'] < stop_loss:
                            position = {
                                'entry_bar': entry_bar,
                                'side': 'SHORT',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            }
                        break

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['peak'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['peak']

    total_return = trades_df['cumulative'].iloc[-1]
    max_dd = trades_df['drawdown'].min()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df) * 100
    rr_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'win_rate': win_rate,
        'tp_rate': (trades_df['exit_reason'] == 'TP').sum() / len(trades_df) * 100,
        'stop_rate': (trades_df['exit_reason'] == 'STOP').sum() / len(trades_df) * 100,
        'rsi_rate': (trades_df['exit_reason'] == 'RSI').sum() / len(trades_df) * 100
    }

# Coin configurations (all RSI swing strategies)
COINS = {
    'CRV-USDT': {'file': 'bingx-trading-bot/trading/crv_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'MELANIA-USDT': {'file': 'bingx-trading-bot/trading/melania_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'AIXBT-USDT': {'file': 'bingx-trading-bot/trading/aixbt_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'TRUMPSOL-USDT': {'file': 'bingx-trading-bot/trading/trumpsol_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'UNI-USDT': {'file': 'bingx-trading-bot/trading/uni_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'DOGE-USDT': {'file': 'bingx-trading-bot/trading/doge_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'XLM-USDT': {'file': 'bingx-trading-bot/trading/xlm_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'MOODENG-USDT': {'file': 'bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
    'PEPE-USDT': {'file': 'bingx-trading-bot/trading/1000pepe_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65},
}

# Test parameters
SL_MULTS = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_MULTS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
LIMIT_OFFSETS = [0.5, 1.0, 1.5, 2.0]

print('='*120)
print('🔍 COMPREHENSIVE OPTIMIZATION - All Coins')
print('='*120)
print()
print(f'Testing {len(SL_MULTS)} stop loss multipliers')
print(f'Testing {len(TP_MULTS)} take profit multipliers')
print(f'Testing {len(LIMIT_OFFSETS)} limit offset %')
print(f'Total combinations per coin: {len(SL_MULTS) * len(TP_MULTS) * len(LIMIT_OFFSETS)}')
print()

all_results = []

for coin, config in COINS.items():
    print('='*120)
    print(f'💰 {coin}')
    print('='*120)
    print()

    try:
        df = pd.read_csv(config['file'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        print(f'❌ Could not load {coin}: {e}')
        print()
        continue

    print(f'Data: {len(df)} candles, {config["rsi_low"]}/{config["rsi_high"]} RSI levels')
    print(f'Testing {len(SL_MULTS) * len(TP_MULTS) * len(LIMIT_OFFSETS)} configurations...')
    print()

    best_config = None
    best_rr = 0

    # Test all combinations
    for sl, tp, offset in product(SL_MULTS, TP_MULTS, LIMIT_OFFSETS):
        result = backtest(
            df,
            rsi_low=config['rsi_low'],
            rsi_high=config['rsi_high'],
            limit_offset_pct=offset,
            stop_atr_mult=sl,
            tp_atr_mult=tp,
            fee_pct=0.05
        )

        if result and result['rr_ratio'] > best_rr and result['trades'] >= 20:
            best_rr = result['rr_ratio']
            best_config = {
                'coin': coin,
                'sl_mult': sl,
                'tp_mult': tp,
                'limit_offset': offset,
                **result
            }

    if best_config:
        all_results.append(best_config)
        print(f'🏆 OPTIMAL CONFIG:')
        print(f'   SL: {best_config["sl_mult"]}x ATR')
        print(f'   TP: {best_config["tp_mult"]}x ATR')
        print(f'   Limit offset: {best_config["limit_offset"]}%')
        print()
        print(f'   Return: {best_config["return"]:+.2f}%')
        print(f'   Max DD: {best_config["max_dd"]:.2f}%')
        print(f'   R/R: {best_config["rr_ratio"]:.2f}x')
        print(f'   Win rate: {best_config["win_rate"]:.1f}%')
        print(f'   Trades: {best_config["trades"]}')
        print(f'   Exit breakdown: {best_config["tp_rate"]:.1f}% TP / {best_config["stop_rate"]:.1f}% SL / {best_config["rsi_rate"]:.1f}% RSI')
    else:
        print(f'❌ No valid configuration found')

    print()

# Summary
print('='*120)
print('📊 OPTIMIZATION SUMMARY - Top Configurations')
print('='*120)
print()

if len(all_results) > 0:
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    print(f'{"Coin":<12} {"SL":<6} {"TP":<6} {"Offset":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"Trades":<8}')
    print('-'*120)

    for _, row in results_df.iterrows():
        print(f'{row["coin"]:<12} {row["sl_mult"]:.1f}x   {row["tp_mult"]:.1f}x   {row["limit_offset"]:.1f}%     {row["return"]:>7.1f}%  {row["max_dd"]:>8.2f}%  {row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% {row["trades"]:>7}')

    print()
    print('='*120)
    print('💡 KEY INSIGHTS')
    print('='*120)
    print()

    # Analyze patterns
    avg_sl = results_df['sl_mult'].mean()
    avg_tp = results_df['tp_mult'].mean()
    avg_offset = results_df['limit_offset'].mean()

    print(f'Average optimal SL: {avg_sl:.1f}x ATR')
    print(f'Average optimal TP: {avg_tp:.1f}x ATR')
    print(f'Average optimal offset: {avg_offset:.1f}%')
    print()

    # Check if tighter or looser is better
    tight_tp = len(results_df[results_df['tp_mult'] <= 1.0])
    loose_tp = len(results_df[results_df['tp_mult'] > 2.0])

    if tight_tp > loose_tp:
        print('✅ TIGHTER take profits (≤1.0x ATR) are more profitable')
    else:
        print('✅ LOOSER take profits (>2.0x ATR) are more profitable')

    tight_sl = len(results_df[results_df['sl_mult'] <= 1.5])
    loose_sl = len(results_df[results_df['sl_mult'] > 2.0])

    if tight_sl > loose_sl:
        print('✅ TIGHTER stop losses (≤1.5x ATR) are more profitable')
    else:
        print('✅ LOOSER stop losses (>2.0x ATR) are more profitable')

    # Save results
    results_df.to_csv('all_coins_optimization_results.csv', index=False)
    print()
    print('💾 Saved: all_coins_optimization_results.csv')

else:
    print('❌ No results to display')

print()
print('='*120)
