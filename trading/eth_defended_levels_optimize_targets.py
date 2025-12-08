import pandas as pd
import numpy as np

def backtest_with_targets(signals_df, df, sl_pct, tp_pct, max_hold_hours=48):
    """Backtest with different SL/TP targets"""

    trades = []

    for idx, signal in signals_df.iterrows():
        entry_idx = df[df['timestamp'] == signal['entry_time']].index[0]
        entry_price = signal['entry_price']
        direction = 1 if signal['type'] == 'ACCUMULATION' else -1

        # Calculate stop and target
        if direction == 1:
            stop_price = entry_price * (1 - sl_pct/100)
            target_price = entry_price * (1 + tp_pct/100)
        else:
            stop_price = entry_price * (1 + sl_pct/100)
            target_price = entry_price * (1 - tp_pct/100)

        # Simulate trade
        exit_idx = min(entry_idx + max_hold_hours*60, len(df)-1)
        exit_price = None
        exit_reason = 'TIME'

        for i in range(entry_idx+1, exit_idx+1):
            if direction == 1:
                if df['low'].iloc[i] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['high'].iloc[i] >= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break
            else:
                if df['high'].iloc[i] >= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['low'].iloc[i] <= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df['close'].iloc[exit_idx]

        # Calculate P&L
        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_pct -= 0.10  # Fees

        trades.append({
            'entry_time': signal['entry_time'],
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
        })

    trades_df = pd.DataFrame(trades)

    if len(trades_df) == 0:
        return None

    total_return = trades_df['pnl_pct'].sum()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df)

    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    return {
        'sl': sl_pct,
        'tp': tp_pct,
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'ratio': abs(total_return/max_dd) if max_dd != 0 else 0,
        'win_rate': win_rate,
        'tp_count': (trades_df['exit_reason'] == 'TP').sum(),
        'sl_count': (trades_df['exit_reason'] == 'SL').sum(),
    }


if __name__ == '__main__':
    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    signals_df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_signals.csv')
    signals_df['entry_time'] = pd.to_datetime(signals_df['entry_time'])
    signals_df['extreme_time'] = pd.to_datetime(signals_df['extreme_time'])

    print(f"Testing {len(signals_df)} defended level signals")
    print(f"Looking at signals: {signals_df['entry_time'].tolist()}")
    print(f"\n{'='*80}")
    print("STOP LOSS / TAKE PROFIT OPTIMIZATION")
    print(f"{'='*80}")

    results = []

    # Test various SL/TP combinations
    stop_losses = [1.0, 1.5, 2.0, 2.5]
    take_profits = [3.0, 4.0, 5.0, 6.0, 8.0, 10.0]

    for sl in stop_losses:
        for tp in take_profits:
            result = backtest_with_targets(signals_df, df, sl, tp)
            if result:
                results.append(result)
                print(f"SL {sl:.1f}% / TP {tp:.1f}% → Return: {result['return']:+.2f}% | "
                      f"DD: {result['max_dd']:.2f}% | R/DD: {result['ratio']:.2f}x | "
                      f"WR: {result['win_rate']*100:.0f}% | TP: {result['tp_count']}/{result['trades']}")

    # Find best configs
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('ratio', ascending=False)

    print(f"\n{'='*80}")
    print("TOP 10 CONFIGS BY RETURN/DD RATIO:")
    print(f"{'='*80}")
    print(results_df.head(10).to_string(index=False))

    print(f"\n{'='*80}")
    print("TOP 5 BY TOTAL RETURN:")
    print(f"{'='*80}")
    print(results_df.nlargest(5, 'return').to_string(index=False))

    # Save results
    results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimization.csv', index=False)
    print(f"\nSaved optimization results to trading/results/eth_defended_levels_optimization.csv")
