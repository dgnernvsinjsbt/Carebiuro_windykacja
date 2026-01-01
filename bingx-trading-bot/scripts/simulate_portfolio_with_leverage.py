"""
Portfolio Simulation with Leverage - NEVER SKIP TRADES

- Start with $100 total
- Use leverage so we can ALWAYS take every signal (never skip due to lack of capital)
- Each trade gets allocated: current_equity / 10 (since 10 strategies)
- Reinvest all profits
- 1x leverage base, but leverage allows multiple positions
- 0.07% round-trip fees
"""

import pandas as pd
import numpy as np
from pathlib import Path


def simulate_with_leverage(trades_file, starting_capital=100, fee_pct=0.07, num_strategies=10):
    """
    Portfolio simulation where we NEVER skip trades (using leverage)

    Each trade gets: current_equity / num_strategies
    This way each strategy effectively gets 10% of current equity
    """

    # Load all trades
    trades = pd.read_csv(trades_file)
    trades['entry_time'] = pd.to_datetime(trades['entry_time'])
    trades['exit_time'] = pd.to_datetime(trades['exit_time'])

    # Sort chronologically
    trades = trades.sort_values('entry_time').reset_index(drop=True)

    print(f"\n{'='*70}")
    print(f"PORTFOLIO SIMULATION WITH LEVERAGE")
    print(f"{'='*70}")
    print(f"Total signals: {len(trades)}")
    print(f"Symbols: {', '.join(sorted(trades['symbol'].unique()))}")
    print(f"Starting capital: ${starting_capital:.2f} USDT")
    print(f"Allocation per trade: current_equity / {num_strategies}")
    print(f"Leverage: YES (never skip trades)")
    print(f"Fees: {fee_pct}% round-trip")
    print(f"{'='*70}\n")

    # Portfolio state
    current_equity = starting_capital
    open_positions = {}  # {trade_idx: {'capital': ..., 'pnl_pct': ...}}
    equity_curve = []
    peak_equity = starting_capital
    max_drawdown = 0

    # Create timeline of events
    events = []
    for idx, trade in trades.iterrows():
        events.append({
            'timestamp': trade['entry_time'],
            'type': 'entry',
            'trade_idx': idx,
            'symbol': trade['symbol'],
            'pnl_pct': trade['pnl_pct']
        })
        events.append({
            'timestamp': trade['exit_time'],
            'type': 'exit',
            'trade_idx': idx,
            'symbol': trade['symbol'],
            'pnl_pct': trade['pnl_pct']
        })

    # Sort events
    events = sorted(events, key=lambda x: (x['timestamp'], x['type'] == 'entry'))

    # Track equity at each point
    equity_at_time = {}

    # Process events
    for event in events:
        timestamp = event['timestamp']

        if event['type'] == 'entry':
            # Allocate portion of CURRENT equity to this trade
            # Each strategy gets 1/10th of current equity
            position_capital = current_equity / num_strategies

            # Open position
            open_positions[event['trade_idx']] = {
                'symbol': event['symbol'],
                'capital': position_capital,
                'entry_time': timestamp,
                'pnl_pct': event['pnl_pct']
            }

        elif event['type'] == 'exit':
            # Close position
            if event['trade_idx'] in open_positions:
                pos = open_positions[event['trade_idx']]

                # Calculate P/L
                gross_pnl = pos['capital'] * (pos['pnl_pct'] / 100)
                fees = pos['capital'] * (fee_pct / 100)
                net_pnl = gross_pnl - fees

                # Update equity
                current_equity += net_pnl

                # Remove position
                del open_positions[event['trade_idx']]

                # Update peak and drawdown
                if current_equity > peak_equity:
                    peak_equity = current_equity

                current_drawdown = ((current_equity / peak_equity) - 1) * 100
                if current_drawdown < max_drawdown:
                    max_drawdown = current_drawdown

                # Record equity point
                equity_curve.append({
                    'timestamp': timestamp,
                    'equity': current_equity,
                    'peak': peak_equity,
                    'drawdown_pct': current_drawdown,
                    'open_positions': len(open_positions),
                    'net_pnl': net_pnl,
                    'symbol': pos['symbol'],
                    'position_capital': pos['capital']
                })

    # Convert to DataFrame
    equity_df = pd.DataFrame(equity_curve)

    # Calculate metrics
    total_return = ((current_equity / starting_capital) - 1) * 100
    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown < 0 else 0

    # Winners/Losers
    winners = equity_df[equity_df['net_pnl'] > 0]
    losers = equity_df[equity_df['net_pnl'] <= 0]

    win_rate = (len(winners) / len(equity_df)) * 100 if len(equity_df) > 0 else 0

    # Profit factor
    gross_profit = winners['net_pnl'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Average position size
    avg_position_size = equity_df['position_capital'].mean() if len(equity_df) > 0 else 0

    # Concurrent positions
    avg_concurrent = equity_df['open_positions'].mean() if len(equity_df) > 0 else 0
    max_concurrent = equity_df['open_positions'].max() if len(equity_df) > 0 else 0

    metrics = {
        'starting_capital': starting_capital,
        'ending_equity': current_equity,
        'total_return_pct': total_return,
        'total_return_usd': current_equity - starting_capital,
        'max_drawdown_pct': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'total_signals': len(trades),
        'filled_trades': len(equity_df),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate_pct': win_rate,
        'profit_factor': profit_factor,
        'avg_position_size': avg_position_size,
        'avg_concurrent_positions': avg_concurrent,
        'max_concurrent_positions': max_concurrent
    }

    return equity_df, metrics


def print_metrics(metrics):
    """Print metrics"""

    print(f"\n{'='*70}")
    print(f"PORTFOLIO PERFORMANCE (WITH LEVERAGE)")
    print(f"{'='*70}\n")

    print(f"💰 Capital:")
    print(f"  Starting:          ${metrics['starting_capital']:.2f} USDT")
    print(f"  Ending:            ${metrics['ending_equity']:.2f} USDT")
    print(f"  Net Profit:        ${metrics['total_return_usd']:.2f} USDT")
    print()

    print(f"📊 Returns:")
    print(f"  Total Return:      {metrics['total_return_pct']:.2f}%")
    print(f"  Max Drawdown:      {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Return/DD Ratio:   {metrics['return_dd_ratio']:.2f}x")
    print()

    print(f"🎯 Trading Stats:")
    print(f"  Total Signals:     {metrics['total_signals']}")
    print(f"  Filled Trades:     {metrics['filled_trades']} (ALL SIGNALS FILLED!)")
    print(f"  Winners:           {metrics['winners']} ({metrics['win_rate_pct']:.1f}%)")
    print(f"  Losers:            {metrics['losers']} ({100 - metrics['win_rate_pct']:.1f}%)")
    print(f"  Profit Factor:     {metrics['profit_factor']:.2f}")
    print()

    print(f"📈 Position Management:")
    print(f"  Avg Position Size: ${metrics['avg_position_size']:.2f} USDT")
    print(f"  Avg Concurrent:    {metrics['avg_concurrent_positions']:.1f} positions")
    print(f"  Max Concurrent:    {int(metrics['max_concurrent_positions'])} positions")
    print()

    print(f"{'='*70}")


def main():
    """Run simulation with leverage"""

    trades_file = Path("trading/results/all_10_strategies_trades.csv")

    if not trades_file.exists():
        print(f"❌ Error: {trades_file} not found")
        return

    # Run simulation
    equity_df, metrics = simulate_with_leverage(
        trades_file=trades_file,
        starting_capital=100,
        fee_pct=0.07,
        num_strategies=10
    )

    # Print results
    print_metrics(metrics)

    # Save results
    equity_df.to_csv("trading/results/portfolio_leverage_equity_curve.csv", index=False)
    print(f"✅ Equity curve saved to trading/results/portfolio_leverage_equity_curve.csv")

    # Save summary
    with open("trading/results/portfolio_leverage_summary.txt", 'w') as f:
        f.write("PORTFOLIO WITH LEVERAGE - FINAL RESULTS\n")
        f.write("="*70 + "\n\n")
        f.write(f"Starting Capital: ${metrics['starting_capital']:.2f} USDT\n")
        f.write(f"Ending Equity: ${metrics['ending_equity']:.2f} USDT\n")
        f.write(f"Net Profit: ${metrics['total_return_usd']:.2f} USDT\n\n")
        f.write(f"Total Return: {metrics['total_return_pct']:.2f}%\n")
        f.write(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%\n")
        f.write(f"Return/DD Ratio: {metrics['return_dd_ratio']:.2f}x\n\n")
        f.write(f"Total Signals: {metrics['total_signals']}\n")
        f.write(f"Filled Trades: {metrics['filled_trades']} (100%)\n")
        f.write(f"Win Rate: {metrics['win_rate_pct']:.1f}%\n")
        f.write(f"Profit Factor: {metrics['profit_factor']:.2f}\n\n")
        f.write(f"Method: Each trade gets current_equity / 10\n")
        f.write(f"Leverage: YES (never skip trades)\n")
        f.write(f"Fees: 0.07% round-trip\n")

    print(f"✅ Summary saved to trading/results/portfolio_leverage_summary.txt")


if __name__ == '__main__':
    main()
