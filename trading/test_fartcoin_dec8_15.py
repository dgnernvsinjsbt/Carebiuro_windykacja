"""
Test FARTCOIN ATR Expansion strategy on Dec 8-15 period
to see if momentum strategies handled that week better than RSI mean reversion.
"""

import pandas as pd
import numpy as np

# Load FARTCOIN 1-minute data
df = pd.read_csv('trading/fartcoin_30d_bingx.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Total data: {len(df)} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")

# Filter to Dec 8-15
df_dec = df[(df['timestamp'] >= '2025-12-08') & (df['timestamp'] < '2025-12-16')].reset_index(drop=True)
print(f"\nDec 8-15 data: {len(df_dec)} bars ({df_dec['timestamp'].min()} to {df_dec['timestamp'].max()})")

# Calculate indicators
def calculate_indicators(df):
    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']

    # EMA(20)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_dist_pct'] = abs(df['close'] - df['ema20']) / df['ema20'] * 100

    return df

df_dec = calculate_indicators(df_dec)

# Baseline parameters (from FARTCOIN ATR strategy)
PARAMS = {
    'atr_expansion_threshold': 1.5,  # Current ATR > 1.5x 20-bar MA
    'ema_distance_max': 3.0,          # Within 3% of EMA(20)
    'limit_offset_pct': 1.0,          # 1% limit order offset
    'max_wait_bars': 3,               # Wait max 3 bars for fill
    'sl_mult': 2.0,                   # 2.0x ATR stop loss
    'tp_mult': 8.0,                   # 8.0x ATR take profit
    'max_hold_bars': 200              # 200 bars max hold (~3.3 hours)
}

def backtest_atr_strategy(df, params):
    """Run FARTCOIN ATR Expansion backtest"""
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 20  # Start after indicators valid
    while i < len(df):
        row = df.iloc[i]

        # Skip if indicators not ready
        if pd.isna(row['atr']) or pd.isna(row['atr_ratio']) or pd.isna(row['ema_dist_pct']):
            i += 1
            continue

        # Entry conditions
        atr_expanding = row['atr_ratio'] > params['atr_expansion_threshold']
        ema_close = row['ema_dist_pct'] < params['ema_distance_max']

        direction = None
        if atr_expanding and ema_close:
            # Bullish candle -> LONG
            if row['close'] > row['open']:
                direction = 'LONG'
            # Bearish candle -> SHORT
            elif row['close'] < row['open']:
                direction = 'SHORT'

        if direction is None:
            i += 1
            continue

        # LONG signal
        if direction == 'LONG':
            signal_price = row['close']
            entry_price = signal_price * (1 + params['limit_offset_pct'] / 100)  # 1% above
            sl_price = entry_price - (row['atr'] * params['sl_mult'])
            tp_price = entry_price + (row['atr'] * params['tp_mult'])

            # Wait for fill (max 3 bars)
            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + params['max_wait_bars'] + 1, len(df))):
                if df.iloc[j]['low'] <= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            # Look for exit
            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold_bars'] + 1, len(df))):
                bar = df.iloc[k]

                # Check SL
                if bar['low'] <= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break

                # Check TP
                if bar['high'] >= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            # Time exit
            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold_bars'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            # Calculate P&L
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl_pct -= 0.10  # Fees

            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'entry_time': df.iloc[fill_idx]['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'],
                'direction': 'LONG',
                'signal_price': signal_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity,
                'atr_ratio': row['atr_ratio'],
                'ema_dist': row['ema_dist_pct']
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        # SHORT signal
        elif direction == 'SHORT':
            signal_price = row['close']
            entry_price = signal_price * (1 - params['limit_offset_pct'] / 100)  # 1% below
            sl_price = entry_price + (row['atr'] * params['sl_mult'])
            tp_price = entry_price - (row['atr'] * params['tp_mult'])

            # Wait for fill
            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + params['max_wait_bars'] + 1, len(df))):
                if df.iloc[j]['high'] >= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            # Look for exit
            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold_bars'] + 1, len(df))):
                bar = df.iloc[k]

                # Check SL
                if bar['high'] >= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break

                # Check TP
                if bar['low'] <= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            # Time exit
            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold_bars'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            # Calculate P&L (SHORT)
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl_pct -= 0.10  # Fees

            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'entry_time': df.iloc[fill_idx]['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'],
                'direction': 'SHORT',
                'signal_price': signal_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity,
                'atr_ratio': row['atr_ratio'],
                'ema_dist': row['ema_dist_pct']
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        i += 1

    return trades, equity_curve

# Run backtest
trades, equity_curve = backtest_atr_strategy(df_dec, PARAMS)

if len(trades) == 0:
    print("\n❌ NO TRADES GENERATED on Dec 8-15")
    print("   Either no ATR expansion signals or no fills")
else:
    df_trades = pd.DataFrame(trades)

    # Calculate metrics
    total_return = ((equity_curve[-1] - 100) / 100) * 100

    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = (df_trades['pnl_pct'] > 0).sum()
    win_rate = (winners / len(df_trades)) * 100

    tp_count = (df_trades['exit_type'] == 'TP').sum()
    sl_count = (df_trades['exit_type'] == 'SL').sum()
    time_count = (df_trades['exit_type'] == 'TIME').sum()

    tp_rate = (tp_count / len(df_trades)) * 100
    sl_rate = (sl_count / len(df_trades)) * 100
    time_rate = (time_count / len(df_trades)) * 100

    avg_winner = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if winners > 0 else 0
    avg_loser = df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean() if (len(df_trades) - winners) > 0 else 0

    # Print results
    print("\n" + "=" * 80)
    print("FARTCOIN ATR EXPANSION - DEC 8-15 PERFORMANCE")
    print("=" * 80)

    print(f"\n📊 Overall Metrics:")
    print(f"  Total Return: {total_return:+.2f}%")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Return/DD Ratio: {total_return / abs(max_dd):.2f}x" if max_dd != 0 else "  Return/DD Ratio: N/A")
    print(f"  Final Equity: ${equity_curve[-1]:.2f}")

    print(f"\n📈 Trade Statistics:")
    print(f"  Total Trades: {len(df_trades)}")
    print(f"  Winners: {winners} ({win_rate:.1f}%)")
    print(f"  Losers: {len(df_trades) - winners} ({100-win_rate:.1f}%)")
    print(f"  Avg Winner: {avg_winner:+.2f}%")
    print(f"  Avg Loser: {avg_loser:+.2f}%")

    print(f"\n🎯 Exit Breakdown:")
    print(f"  Take Profit: {tp_count} ({tp_rate:.1f}%)")
    print(f"  Stop Loss: {sl_count} ({sl_rate:.1f}%)")
    print(f"  Time Exit: {time_count} ({time_rate:.1f}%)")

    # Compare to baseline (from CLAUDE.md)
    print("\n" + "=" * 80)
    print("COMPARISON TO BASELINE (Oct 29 - Nov 29, 32 days)")
    print("=" * 80)

    baseline = {
        'return': 101.11,
        'max_dd': -11.98,
        'return_dd': 8.44,
        'trades': 94,
        'win_rate': 42.6,
        'avg_winner': 4.97,
        'avg_loser': -2.89
    }

    print(f"\nBaseline:")
    print(f"  Return: +{baseline['return']:.2f}% | MaxDD: {baseline['max_dd']:.2f}% | R/DD: {baseline['return_dd']:.2f}x")
    print(f"  Trades: {baseline['trades']} | Win: {baseline['win_rate']:.1f}%")
    print(f"  Avg Win: +{baseline['avg_winner']:.2f}% | Avg Loss: {baseline['avg_loser']:.2f}%")

    print(f"\nDec 8-15:")
    print(f"  Return: {total_return:+.2f}% | MaxDD: {max_dd:.2f}% | R/DD: {total_return/abs(max_dd):.2f}x" if max_dd != 0 else f"  Return: {total_return:+.2f}% | MaxDD: {max_dd:.2f}%")
    print(f"  Trades: {len(df_trades)} | Win: {win_rate:.1f}%")
    print(f"  Avg Win: {avg_winner:+.2f}% | Avg Loss: {avg_loser:+.2f}%")

    # Verdict
    print("\n" + "=" * 80)
    print("🔍 VERDICT:")
    print("=" * 80)

    if total_return > 0:
        print("✅ PROFITABLE on Dec 8-15!")
        print(f"   ATR momentum strategy made {total_return:+.2f}% during the week that")
        print("   killed RSI mean reversion strategies.")
        print("\n   This suggests:")
        print("   - Dec 8-15 was a TRENDING market (momentum worked, mean reversion failed)")
        print("   - Diversifying between RSI and ATR strategies could smooth equity curve")
        print("   - Consider running both strategy types in parallel")
    else:
        print("❌ ALSO UNPROFITABLE on Dec 8-15")
        print(f"   Even ATR momentum strategy lost {total_return:.2f}%")
        print("\n   This confirms:")
        print("   - Dec 8-15 was genuinely difficult for ALL strategies")
        print("   - Not just a mean reversion problem, but market-wide volatility")
        print("   - Bad variance affects multiple strategy types")

    # Show trades
    print("\n" + "=" * 80)
    print("TRADE LOG:")
    print("=" * 80)

    for idx, trade in df_trades.iterrows():
        print(f"\n{trade['entry_time'].strftime('%Y-%m-%d %H:%M')} - {trade['exit_time'].strftime('%H:%M')}")
        print(f"  {trade['direction']} | Entry: ${trade['entry_price']:.6f} | Exit: ${trade['exit_price']:.6f}")
        print(f"  P&L: {trade['pnl_pct']:+.2f}% | Exit: {trade['exit_type']} | ATR Ratio: {trade['atr_ratio']:.2f}x")

print("\n" + "=" * 80)
print("Analysis complete.")
