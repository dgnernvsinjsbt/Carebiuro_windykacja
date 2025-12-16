"""
Portfolio Simulation: $100 Capital, 1x Leverage, 0.07% Fees

Combines all 7 strategy trades chronologically and simulates:
- $100 starting capital
- Capital divided equally across all coins
- 1x leverage (NOT 10x)
- 0.07% round-trip fees (0.035% per entry + 0.035% per exit)
"""

import pandas as pd
import numpy as np
from pathlib import Path


def simulate_portfolio(trades_file, starting_capital=100, fee_pct=0.07):
    """
    Simulate portfolio performance with equal capital allocation

    Args:
        trades_file: Path to combined trades CSV
        starting_capital: Starting capital in USDT
        fee_pct: Round-trip fee percentage (e.g., 0.07 for 0.07%)

    Returns:
        DataFrame with equity curve and metrics dict
    """

    # Load all trades
    trades = pd.read_csv(trades_file)
    trades['entry_time'] = pd.to_datetime(trades['entry_time'])
    trades['exit_time'] = pd.to_datetime(trades['exit_time'])

    # Sort chronologically by entry time
    trades = trades.sort_values('entry_time').reset_index(drop=True)

    print(f"\n{'='*70}")
    print(f"PORTFOLIO SIMULATION")
    print(f"{'='*70}")
    print(f"Total trades: {len(trades)}")
    print(f"Symbols: {', '.join(sorted(trades['symbol'].unique()))}")
    print(f"Starting capital: ${starting_capital:.2f} USDT")
    print(f"Fee per round-trip: {fee_pct}%")
    print(f"{'='*70}\n")

    # Calculate capital per coin (equal weighting)
    num_coins = len(trades['symbol'].unique())
    capital_per_coin = starting_capital / num_coins

    print(f"Number of coins: {num_coins}")
    print(f"Capital per coin: ${capital_per_coin:.2f} USDT")
    print(f"Leverage: 1x (no leverage)")
    print()

    # Initialize portfolio tracking
    portfolio_equity = starting_capital
    equity_curve = []
    peak_equity = starting_capital
    max_drawdown = 0

    # Track per-coin allocation
    coin_allocations = {symbol: capital_per_coin for symbol in trades['symbol'].unique()}

    # Simulate each trade
    for idx, trade in trades.iterrows():
        symbol = trade['symbol']
        pnl_pct = trade['pnl_pct']

        # Get current allocation for this coin
        position_size = coin_allocations[symbol]

        # Calculate gross P/L (before fees)
        gross_pnl = position_size * (pnl_pct / 100)

        # Subtract fees (0.07% of position size = round-trip fees)
        fees = position_size * (fee_pct / 100)
        net_pnl = gross_pnl - fees

        # Update coin allocation
        coin_allocations[symbol] += net_pnl

        # Update portfolio equity
        portfolio_equity += net_pnl

        # Track peak and drawdown
        if portfolio_equity > peak_equity:
            peak_equity = portfolio_equity

        current_drawdown = ((portfolio_equity / peak_equity) - 1) * 100
        if current_drawdown < max_drawdown:
            max_drawdown = current_drawdown

        # Record equity point
        equity_curve.append({
            'timestamp': trade['exit_time'],
            'equity': portfolio_equity,
            'peak': peak_equity,
            'drawdown_pct': current_drawdown,
            'trade_num': idx + 1,
            'symbol': symbol,
            'net_pnl': net_pnl
        })

    # Convert equity curve to DataFrame
    equity_df = pd.DataFrame(equity_curve)

    # Calculate metrics
    total_return = ((portfolio_equity / starting_capital) - 1) * 100
    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown < 0 else 0

    winners = trades[trades['pnl_pct'] > 0]
    losers = trades[trades['pnl_pct'] <= 0]

    win_rate = (len(winners) / len(trades)) * 100 if len(trades) > 0 else 0
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    # Calculate profit factor (gross profit / gross loss)
    gross_profit = equity_df[equity_df['net_pnl'] > 0]['net_pnl'].sum()
    gross_loss = abs(equity_df[equity_df['net_pnl'] < 0]['net_pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    metrics = {
        'starting_capital': starting_capital,
        'ending_equity': portfolio_equity,
        'total_return_pct': total_return,
        'total_return_usd': portfolio_equity - starting_capital,
        'max_drawdown_pct': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'total_trades': len(trades),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate_pct': win_rate,
        'avg_win_pct': avg_win,
        'avg_loss_pct': avg_loss,
        'profit_factor': profit_factor,
        'total_fees_usd': trades.shape[0] * (capital_per_coin * fee_pct / 100),
        'num_coins': num_coins,
        'capital_per_coin': capital_per_coin
    }

    return equity_df, metrics


def print_metrics(metrics):
    """Print portfolio metrics in a nice format"""

    print(f"\n{'='*70}")
    print(f"PORTFOLIO PERFORMANCE METRICS")
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
    print(f"  Total Trades:      {metrics['total_trades']}")
    print(f"  Winners:           {metrics['winners']} ({metrics['win_rate_pct']:.1f}%)")
    print(f"  Losers:            {metrics['losers']} ({100 - metrics['win_rate_pct']:.1f}%)")
    print(f"  Avg Win:           {metrics['avg_win_pct']:.2f}%")
    print(f"  Avg Loss:          {metrics['avg_loss_pct']:.2f}%")
    print(f"  Profit Factor:     {metrics['profit_factor']:.2f}")
    print()

    print(f"💸 Fees:")
    print(f"  Total Fees Paid:   ${metrics['total_fees_usd']:.2f} USDT")
    print(f"  Fee Impact:        {(metrics['total_fees_usd'] / metrics['starting_capital']) * 100:.2f}% of capital")
    print()

    print(f"🪙 Allocation:")
    print(f"  Number of Coins:   {metrics['num_coins']}")
    print(f"  Capital Per Coin:  ${metrics['capital_per_coin']:.2f} USDT")
    print()

    print(f"{'='*70}")


def main():
    """Run portfolio simulation"""

    # Input file
    trades_file = Path("trading/results/all_10_strategies_trades.csv")

    if not trades_file.exists():
        print(f"❌ Error: {trades_file} not found. Run backtest_all_10_strategies.py first.")
        return

    # Run simulation
    equity_df, metrics = simulate_portfolio(
        trades_file=trades_file,
        starting_capital=100,
        fee_pct=0.07
    )

    # Print metrics
    print_metrics(metrics)

    # Save equity curve
    output_file = Path("trading/results/portfolio_100usd_equity_curve.csv")
    equity_df.to_csv(output_file, index=False)
    print(f"✅ Equity curve saved to {output_file}")

    # Save summary metrics
    summary_file = Path("trading/results/portfolio_100usd_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("PORTFOLIO SIMULATION SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Starting Capital: ${metrics['starting_capital']:.2f} USDT\n")
        f.write(f"Ending Equity: ${metrics['ending_equity']:.2f} USDT\n")
        f.write(f"Net Profit: ${metrics['total_return_usd']:.2f} USDT\n\n")
        f.write(f"Total Return: {metrics['total_return_pct']:.2f}%\n")
        f.write(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%\n")
        f.write(f"Return/DD Ratio: {metrics['return_dd_ratio']:.2f}x\n\n")
        f.write(f"Total Trades: {metrics['total_trades']}\n")
        f.write(f"Win Rate: {metrics['win_rate_pct']:.1f}%\n")
        f.write(f"Profit Factor: {metrics['profit_factor']:.2f}\n\n")
        f.write(f"Leverage: 1x\n")
        f.write(f"Fees: 0.07% round-trip\n")
        f.write(f"Allocation: Equal-weighted across {metrics['num_coins']} coins\n")

    print(f"✅ Summary saved to {summary_file}")


if __name__ == '__main__':
    main()
