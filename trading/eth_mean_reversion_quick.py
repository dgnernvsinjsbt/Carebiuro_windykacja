"""
ETH/USDT Mean Reversion - QUICK TEST
Tests only the most promising parameter combinations
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def prepare_data(df):
    """Calculate all indicators"""
    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df

def backtest(df, config):
    """Row-by-row backtest"""
    capital = 1000.0
    equity = capital
    peak = capital
    max_dd = 0.0

    in_pos = False
    pos_type = None
    entry_price = 0.0
    sl = 0.0
    tp = 0.0
    entry_time = None
    last_trade = -999

    trades = []
    lev = config['lev']
    fee = 0.00005

    for i in range(250, len(df)):
        row = df.iloc[i]

        # Track drawdown
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

        # Exit
        if in_pos:
            exit_price = None
            reason = None

            if pos_type == 'long':
                if row['low'] <= sl:
                    exit_price = sl
                    reason = 'SL'
                elif row['high'] >= tp:
                    exit_price = tp
                    reason = 'TP'
            else:
                if row['high'] >= sl:
                    exit_price = sl
                    reason = 'SL'
                elif row['low'] <= tp:
                    exit_price = tp
                    reason = 'TP'

            if exit_price:
                if pos_type == 'long':
                    pct = (exit_price - entry_price) / entry_price
                else:
                    pct = (entry_price - exit_price) / entry_price

                pnl_pct = pct * lev - (2 * fee * lev)
                pnl = equity * pnl_pct
                equity += pnl

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'type': pos_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': reason,
                    'pnl_pct': pnl_pct * 100,
                    'equity': equity
                })

                in_pos = False
                last_trade = i

        # Entry
        if not in_pos and (i - last_trade) >= config['spacing']:
            long_sig = False
            short_sig = False

            if config['type'] == 'rsi':
                long_sig = row['rsi'] < config['os']
                short_sig = row['rsi'] > config['ob']

            elif config['type'] == 'bb':
                if row['bb_width'] < config['max_width']:
                    dist_lower = (row['close'] - row['bb_lower']) / row['close']
                    dist_upper = (row['bb_upper'] - row['close']) / row['close']
                    long_sig = dist_lower < config['thresh']
                    short_sig = dist_upper < config['thresh']

            elif config['type'] == 'combo':
                rsi_long = row['rsi'] < config['os']
                rsi_short = row['rsi'] > config['ob']

                dist_lower = (row['close'] - row['bb_lower']) / row['close']
                dist_upper = (row['bb_upper'] - row['close']) / row['close']

                bb_long = dist_lower < config['thresh']
                bb_short = dist_upper < config['thresh']
                ranging = row['bb_width'] < config['max_width']

                long_sig = rsi_long and bb_long and ranging
                short_sig = rsi_short and bb_short and ranging

            if long_sig:
                pos_type = 'long'
                entry_price = row['close']
                sl = entry_price - (row['atr'] * config['sl'])
                tp = entry_price + (row['atr'] * config['tp'])
                entry_time = row['timestamp']
                in_pos = True

            elif short_sig:
                pos_type = 'short'
                entry_price = row['close']
                sl = entry_price + (row['atr'] * config['sl'])
                tp = entry_price - (row['atr'] * config['tp'])
                entry_time = row['timestamp']
                in_pos = True

    return {'trades': trades, 'equity': equity, 'max_dd': max_dd}

def main():
    print("="*80)
    print("ETH/USDT MEAN REVERSION - QUICK TEST")
    print("="*80)

    # Load
    print("\nLoading data...")
    df = pd.read_csv('eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = prepare_data(df)

    print(f"Dataset: {len(df):,} candles")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Quick stats
    print(f"\nQuick Stats:")
    print(f"  Avg ATR: ${df['atr'].mean():.2f}")
    print(f"  Avg BB width: {df['bb_width'].mean():.2f}%")
    print(f"  Avg RSI: {df['rsi'].mean():.1f}")
    print(f"  RSI <30: {(df['rsi']<30).sum()} times ({(df['rsi']<30).sum()/len(df)*100:.1f}%)")
    print(f"  RSI >70: {(df['rsi']>70).sum()} times ({(df['rsi']>70).sum()/len(df)*100:.1f}%)")

    # Test configs (small focused set)
    configs = []

    # RSI only
    for os in [25, 30]:
        for ob in [70, 75]:
            for sl, tp in [(2.0, 4.0), (2.0, 5.0), (2.5, 5.0), (2.0, 6.0)]:
                for lev in [10, 15, 20]:
                    configs.append({
                        'type': 'rsi',
                        'os': os,
                        'ob': ob,
                        'thresh': 0.002,
                        'max_width': 2.0,
                        'sl': sl,
                        'tp': tp,
                        'lev': lev,
                        'spacing': 10,
                        'name': f"RSI_OS{os}_OB{ob}_SL{sl}_TP{tp}_LEV{lev}"
                    })

    # BB only
    for thresh in [0.001, 0.002, 0.003]:
        for width in [1.5, 2.0]:
            for sl, tp in [(2.0, 4.0), (2.0, 5.0), (2.5, 5.0)]:
                for lev in [10, 15, 20]:
                    configs.append({
                        'type': 'bb',
                        'os': 30,
                        'ob': 70,
                        'thresh': thresh,
                        'max_width': width,
                        'sl': sl,
                        'tp': tp,
                        'lev': lev,
                        'spacing': 10,
                        'name': f"BB_T{thresh*1000:.0f}_W{width}_SL{sl}_TP{tp}_LEV{lev}"
                    })

    # Combo
    for os, ob in [(25, 75), (30, 70)]:
        for thresh in [0.002, 0.003]:
            for width in [1.5, 2.0]:
                for sl, tp in [(2.0, 5.0), (2.5, 5.0), (2.0, 6.0)]:
                    for lev in [15, 20]:
                        configs.append({
                            'type': 'combo',
                            'os': os,
                            'ob': ob,
                            'thresh': thresh,
                            'max_width': width,
                            'sl': sl,
                            'tp': tp,
                            'lev': lev,
                            'spacing': 10,
                            'name': f"COMBO_OS{os}_OB{ob}_T{thresh*1000:.0f}_W{width}_SL{sl}_TP{tp}_LEV{lev}"
                        })

    print(f"\nTesting {len(configs)} configurations...")

    results = []
    for i, cfg in enumerate(configs):
        res = backtest(df, cfg)

        if len(res['trades']) >= 10:
            trades_df = pd.DataFrame(res['trades'])
            wins = trades_df[trades_df['pnl_pct'] > 0]

            total_ret = (res['equity'] - 1000) / 1000 * 100
            dd_pct = res['max_dd'] * 100

            results.append({
                'name': cfg['name'],
                'type': cfg['type'],
                'leverage': cfg['lev'],
                'num_trades': len(trades_df),
                'win_rate': len(wins) / len(trades_df) * 100,
                'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
                'total_return': total_ret,
                'max_dd': dd_pct,
                'profit_dd': abs(total_ret) / max(dd_pct, 0.01),
                'final_equity': res['equity'],
                'trades_df': trades_df,
                'config': cfg
            })

        if (i+1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(configs)}")

    print(f"\nCompleted {len(results)} successful strategies")

    # Sort by profit/DD
    results.sort(key=lambda x: x['profit_dd'], reverse=True)

    # Filter profitable
    profitable = [r for r in results if r['total_return'] > 0]

    print(f"Profitable strategies: {len(profitable)}")
    print(f"Strategies with profit/DD >= 4.0: {len([r for r in profitable if r['profit_dd'] >= 4.0])}")

    # Save summary
    summary = []
    for r in profitable[:20]:
        summary.append({
            'name': r['name'],
            'type': r['type'],
            'leverage': r['leverage'],
            'trades': r['num_trades'],
            'win_rate': round(r['win_rate'], 1),
            'avg_win': round(r['avg_win'], 2),
            'total_return': round(r['total_return'], 2),
            'max_dd': round(r['max_dd'], 2),
            'profit_dd': round(r['profit_dd'], 2)
        })

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv('eth_mean_reversion_summary.csv', index=False)

    # Show top 10
    print("\n" + "="*80)
    print("TOP 10 STRATEGIES")
    print("="*80)
    print(f"\n{summary_df.head(10).to_string(index=False)}")

    # Best details
    if len(profitable) > 0:
        best = profitable[0]
        print("\n" + "="*80)
        print("BEST STRATEGY")
        print("="*80)
        print(f"\nName: {best['name']}")
        print(f"Type: {best['type'].upper()}")
        print(f"Leverage: {best['leverage']}x")

        cfg = best['config']
        print(f"\nParameters:")
        print(f"  RSI Oversold: {cfg['os']}")
        print(f"  RSI Overbought: {cfg['ob']}")
        print(f"  BB Threshold: {cfg['thresh']*100:.2f}%")
        print(f"  Max BB Width: {cfg['max_width']}%")
        print(f"  Stop Loss: {cfg['sl']}x ATR")
        print(f"  Take Profit: {cfg['tp']}x ATR")

        print(f"\nPerformance:")
        print(f"  Total Return: {best['total_return']:.2f}%")
        print(f"  Max Drawdown: {best['max_dd']:.2f}%")
        print(f"  Profit/DD Ratio: {best['profit_dd']:.2f}")
        print(f"  Trades: {best['num_trades']}")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Avg Win: {best['avg_win']:.2f}%")
        print(f"  Final Equity: ${best['final_equity']:.2f}")

        # Save best trades
        best['trades_df'].to_csv('eth_mean_reversion_best_trades.csv', index=False)
        print(f"\nSaved best trades to: eth_mean_reversion_best_trades.csv")

        # Exit breakdown
        print(f"\nExit Reasons:")
        print(best['trades_df']['exit_reason'].value_counts())

    print("\n" + "="*80)
    print("DONE!")
    print("="*80)

if __name__ == "__main__":
    main()
