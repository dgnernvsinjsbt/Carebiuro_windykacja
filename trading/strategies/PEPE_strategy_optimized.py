"""
PEPE Optimized Strategy - Finding the Sweet Spot

Based on pattern analysis:
- Lower BB touch: 70-73% win rate (2,842 samples)
- RSI oversold: 67% win rate (3,458 samples)

Let's optimize parameters to match the discovered pattern performance.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_data(file_path: str) -> pd.DataFrame:
    """Load and prepare PEPE data"""
    df = pd.read_csv(file_path)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['time'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def calculate_indicators(df, bb_period=20, bb_std=2.0, rsi_period=14, atr_period=14):
    """Calculate indicators"""
    df = df.copy()

    # Bollinger Bands
    df['sma20'] = df['close'].rolling(bb_period).mean()
    std = df['close'].rolling(bb_period).std()
    df['bb_upper'] = df['sma20'] + (std * bb_std)
    df['bb_lower'] = df['sma20'] - (std * bb_std)

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(atr_period).mean()

    return df


def backtest_config(df, config):
    """Backtest a specific configuration"""
    # Entry conditions
    entry_signals = (
        (df['close'] <= df['bb_lower']) &
        (df['rsi'] <= config['rsi_threshold'])
    )

    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0
    sl_price = 0
    tp_price = 0

    for i in range(len(df)):
        if in_position:
            current_low = df.iloc[i]['low']
            current_high = df.iloc[i]['high']
            current_close = df.iloc[i]['close']

            # Check SL
            if current_low <= sl_price:
                pnl = (sl_price - entry_price) / entry_price
                pnl_after_fees = pnl - config['fees']
                trades.append({
                    'pnl': pnl_after_fees * 100,
                    'exit_reason': 'SL',
                    'hold_candles': i - entry_idx
                })
                in_position = False
                continue

            # Check TP
            if current_high >= tp_price:
                pnl = (tp_price - entry_price) / entry_price
                pnl_after_fees = pnl - config['fees']
                trades.append({
                    'pnl': pnl_after_fees * 100,
                    'exit_reason': 'TP',
                    'hold_candles': i - entry_idx
                })
                in_position = False
                continue

            # Check time exit
            if (i - entry_idx) >= config['time_exit']:
                pnl = (current_close - entry_price) / entry_price
                pnl_after_fees = pnl - config['fees']
                trades.append({
                    'pnl': pnl_after_fees * 100,
                    'exit_reason': 'TIME',
                    'hold_candles': i - entry_idx
                })
                in_position = False
                continue

        else:
            # Check for entry
            if entry_signals.iloc[i]:
                entry_price = df.iloc[i]['close']
                entry_idx = i
                atr = df.iloc[i]['atr']

                sl_price = entry_price - (atr * config['sl_mult'])
                tp_price = entry_price + (atr * config['tp_mult'])

                in_position = True

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['pnl'] > 0]
    losers = trades_df[trades_df['pnl'] <= 0]

    return {
        'config': config,
        'total_trades': len(trades_df),
        'win_rate': len(winners) / len(trades_df) * 100,
        'total_return': trades_df['pnl'].sum(),
        'avg_trade': trades_df['pnl'].mean(),
        'avg_win': winners['pnl'].mean() if len(winners) > 0 else 0,
        'avg_loss': losers['pnl'].mean() if len(losers) > 0 else 0,
        'max_dd': (trades_df['pnl'].cumsum().cummax() - trades_df['pnl'].cumsum()).max(),
        'tp_exits': len(trades_df[trades_df['exit_reason'] == 'TP']),
        'sl_exits': len(trades_df[trades_df['exit_reason'] == 'SL']),
        'rr_ratio': abs(winners['pnl'].mean() / losers['pnl'].mean()) if len(losers) > 0 else 0,
        'trades_df': trades_df
    }


def main():
    print("=" * 80)
    print("PEPE STRATEGY OPTIMIZATION")
    print("=" * 80)
    print()

    # Load data
    data_file = '/workspaces/Carebiuro_windykacja/trading/pepe_usdt_1m_lbank.csv'
    df = load_data(data_file)
    df = calculate_indicators(df)
    print(f"✅ Loaded {len(df):,} candles")
    print()

    # Test configurations
    configs = []

    # RSI threshold sweep
    for rsi_thresh in [25, 30, 35, 40]:
        # SL/TP ratio sweep
        for sl_mult in [1.0, 1.5, 2.0]:
            for tp_mult in [2.0, 3.0, 4.0, 5.0]:
                configs.append({
                    'rsi_threshold': rsi_thresh,
                    'sl_mult': sl_mult,
                    'tp_mult': tp_mult,
                    'time_exit': 60,
                    'fees': 0.0007
                })

    print(f"🔍 Testing {len(configs)} configurations...")
    print()

    results = []
    for i, config in enumerate(configs):
        result = backtest_config(df, config)
        if result is not None:
            results.append(result)

        if (i + 1) % 10 == 0:
            print(f"   Progress: {i + 1}/{len(configs)}")

    print()
    print(f"✅ Completed {len(results)} valid configurations")
    print()

    # Sort by total return
    results_sorted = sorted(results, key=lambda x: x['total_return'], reverse=True)

    # Display top 10
    print("=" * 80)
    print("TOP 10 CONFIGURATIONS (by Total Return)")
    print("=" * 80)
    print()

    for i, r in enumerate(results_sorted[:10], 1):
        cfg = r['config']
        print(f"#{i}")
        print(f"   RSI: {cfg['rsi_threshold']}, SL: {cfg['sl_mult']}x ATR, TP: {cfg['tp_mult']}x ATR")
        print(f"   Trades: {r['total_trades']}, Win Rate: {r['win_rate']:.1f}%")
        print(f"   Total Return: {r['total_return']:.2f}%, Avg Trade: {r['avg_trade']:.3f}%")
        print(f"   R:R: {r['rr_ratio']:.2f}, Max DD: {r['max_dd']:.2f}%")
        print(f"   TP/SL: {r['tp_exits']}/{r['sl_exits']}")
        print()

    # Save best configuration
    best = results_sorted[0]
    output_dir = '/workspaces/Carebiuro_windykacja/trading/results'

    # Save trades
    best['trades_df'].to_csv(f'{output_dir}/PEPE_strategy_optimized_results.csv', index=False)

    # Save summary
    with open(f'{output_dir}/PEPE_strategy_optimized_summary.md', 'w') as f:
        f.write("# PEPE Optimized Strategy - Performance Summary\n\n")
        f.write("## Best Configuration\n\n")
        cfg = best['config']
        f.write(f"- **RSI Threshold**: {cfg['rsi_threshold']}\n")
        f.write(f"- **Stop Loss**: {cfg['sl_mult']}x ATR\n")
        f.write(f"- **Take Profit**: {cfg['tp_mult']}x ATR\n")
        f.write(f"- **R:R Ratio**: {cfg['tp_mult'] / cfg['sl_mult']}:1\n")
        f.write(f"- **Time Exit**: {cfg['time_exit']} candles\n\n")
        f.write("## Performance Metrics\n\n")
        f.write(f"- **Total Trades**: {best['total_trades']}\n")
        f.write(f"- **Win Rate**: {best['win_rate']:.2f}%\n")
        f.write(f"- **Total Return**: {best['total_return']:.2f}%\n")
        f.write(f"- **Avg Trade**: {best['avg_trade']:.3f}%\n")
        f.write(f"- **Avg Win**: {best['avg_win']:.3f}%\n")
        f.write(f"- **Avg Loss**: {best['avg_loss']:.3f}%\n")
        f.write(f"- **R:R Ratio**: {best['rr_ratio']:.2f}:1\n")
        f.write(f"- **Max Drawdown**: {best['max_dd']:.2f}%\n")
        f.write(f"- **TP Exits**: {best['tp_exits']}\n")
        f.write(f"- **SL Exits**: {best['sl_exits']}\n")

    print(f"✅ Results saved to: {output_dir}/PEPE_strategy_optimized_*")
    print()

    # Plot equity curve
    cumulative = (1 + best['trades_df']['pnl'] / 100).cumprod()
    cumulative_pct = (cumulative - 1) * 100

    plt.figure(figsize=(14, 8))
    plt.plot(cumulative_pct.values, linewidth=2, color='#2E86AB')
    plt.fill_between(range(len(cumulative_pct)), 0, cumulative_pct.values, alpha=0.3, color='#2E86AB')
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.xlabel('Trade Number', fontsize=12, fontweight='bold')
    plt.ylabel('Cumulative Return (%)', fontsize=12, fontweight='bold')
    plt.title('PEPE Optimized Strategy - Equity Curve', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/PEPE_strategy_optimized_equity.png', dpi=300, bbox_inches='tight')
    print(f"✅ Equity curve saved to: {output_dir}/PEPE_strategy_optimized_equity.png")
    print()

    print("=" * 80)
    print("✅ OPTIMIZATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
