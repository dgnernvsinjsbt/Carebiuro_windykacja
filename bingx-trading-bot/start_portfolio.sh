#!/bin/bash
# Start the 9-coin RSI portfolio bot with LIVE TRADING

echo "=========================================="
echo "🚀 STARTING 9-COIN RSI PORTFOLIO BOT"
echo "=========================================="
echo ""
echo "⚠️  LIVE TRADING MODE - REAL MONEY!"
echo ""
echo "Config: config_portfolio_fixed10.yaml"
echo "Position Sizing: 10% of equity per trade"
echo "Leverage: 1x (no leverage)"
echo "Strategies: 9 coins (CRV, MELANIA, AIXBT, TRUMPSOL, UNI, DOGE, XLM, MOODENG, PEPE)"
echo ""
echo "Expected Performance (based on 90-day backtest):"
echo "  Return: +35.19%"
echo "  Max DD: -1.69%"
echo "  Win Rate: 75.5%"
echo ""
echo "Press Ctrl+C to stop the bot"
echo "Create file 'STOP' to gracefully shutdown"
echo ""
echo "=========================================="
echo ""

# Load environment variables
export $(cat .env | xargs)

# Start the bot
python main.py --config config_portfolio_fixed10.yaml
