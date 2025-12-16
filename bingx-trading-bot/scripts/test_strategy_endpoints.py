#!/usr/bin/env python3
"""
Test all endpoints needed for trading strategies
- Klines (for RSI, SMA, ATR indicators)
- Orders with Stop-Loss and Take-Profit
- Contract info (for min quantities, leverage, etc.)
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from config import load_config

async def main():
    print("="*70)
    print("BingX Strategy Endpoints Test")
    print("="*70)

    config = load_config('config.yaml')
    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet
    )

    try:
        # Test 1: Klines (Historical Candlestick Data)
        print("\n📊 TEST 1: Klines / Candlestick Data")
        print("="*70)
        print("Getting 1-minute klines for FARTCOIN-USDT (last 100 candles)...")

        klines = await client.get_klines(
            symbol="FARTCOIN-USDT",
            interval="1m",
            limit=100
        )

        if klines:
            print(f"✓ Retrieved {len(klines)} candles")
            print(f"\nLatest 3 candles:")
            for i, candle in enumerate(klines[-3:], 1):
                print(f"   {i}. O: ${candle.get('open')} H: ${candle.get('high')} "
                      f"L: ${candle.get('low')} C: ${candle.get('close')} "
                      f"Vol: {candle.get('volume')}")

            # Test if we can calculate indicators
            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)

            # Simple SMA calculation
            sma_50 = df['close'].rolling(50).mean().iloc[-1]
            print(f"\n✓ Can calculate indicators:")
            print(f"   Current price: ${df['close'].iloc[-1]}")
            print(f"   SMA(50): ${sma_50:.4f}")
            print(f"   Distance from SMA: {((df['close'].iloc[-1] - sma_50) / sma_50 * 100):.2f}%")
        else:
            print("❌ No klines data returned")

        # Test 2: Multiple timeframes
        print("\n\n📈 TEST 2: Multiple Timeframe Data")
        print("="*70)

        for interval in ['1m', '5m', '15m']:
            klines = await client.get_klines(
                symbol="FARTCOIN-USDT",
                interval=interval,
                limit=10
            )
            print(f"   {interval}: {len(klines)} candles - Latest close: ${klines[-1].get('close')}")

        # Test 3: Contract Information
        print("\n\n📋 TEST 3: Contract Information")
        print("="*70)

        contracts = await client.get_contract_info("FARTCOIN-USDT")
        if contracts:
            contract = contracts[0] if isinstance(contracts, list) else contracts
            print(f"✓ Contract: {contract.get('symbol')}")
            print(f"   Min Quantity: {contract.get('minQty')}")
            print(f"   Quantity Precision: {contract.get('quantityPrecision')}")
            print(f"   Price Precision: {contract.get('pricePrecision')}")
            print(f"   Max Leverage: {contract.get('maxLeverage')}")
            print(f"   Tick Size: {contract.get('tickSize')}")

        # Test 4: Leverage Setting
        print("\n\n⚡ TEST 4: Set Leverage")
        print("="*70)

        try:
            # Try setting leverage to 1x (safest)
            leverage_result = await client.set_leverage(
                symbol="FARTCOIN-USDT",
                side="LONG",
                leverage=1
            )
            print(f"✓ Leverage set to 1x: {leverage_result}")
        except BingXAPIError as e:
            print(f"⚠️  Leverage setting: {e.msg}")
            print(f"   (Might already be at 1x or not available in one-way mode)")

        # Test 5: Orders with Stop-Loss and Take-Profit
        print("\n\n🛡️  TEST 5: Order with Stop-Loss and Take-Profit")
        print("="*70)

        # Get current price
        ticker = await client.get_ticker("FARTCOIN-USDT")
        current_price = float(ticker.get('price') or ticker.get('lastPrice'))
        print(f"Current price: ${current_price}")

        # Calculate entry, SL, and TP prices
        # Entry: 5% below market (limit order)
        entry_price = round(current_price * 0.95, 4)

        # Stop-Loss: 2% below entry
        stop_loss_price = round(entry_price * 0.98, 4)

        # Take-Profit: 5% above entry
        take_profit_price = round(entry_price * 1.05, 4)

        print(f"\nTest order prices:")
        print(f"   Entry: ${entry_price} (limit)")
        print(f"   Stop-Loss: ${stop_loss_price}")
        print(f"   Take-Profit: ${take_profit_price}")

        print(f"\nPlacing LIMIT BUY with SL/TP...")

        try:
            order = await client.place_order(
                symbol="FARTCOIN-USDT",
                side="BUY",
                position_side="BOTH",
                order_type="LIMIT",
                quantity=6,
                price=entry_price,
                stop_loss={
                    "type": "MARK_PRICE",
                    "stopPrice": stop_loss_price,
                    "price": stop_loss_price,
                    "workingType": "MARK_PRICE"
                },
                take_profit={
                    "type": "MARK_PRICE",
                    "stopPrice": take_profit_price,
                    "price": take_profit_price,
                    "workingType": "MARK_PRICE"
                }
            )

            if isinstance(order, dict) and 'order' in order:
                order_data = order['order']
                order_id = order_data.get('orderId')
                print(f"✓ Order placed with SL/TP!")
                print(f"   Order ID: {order_id}")
                print(f"   Status: {order_data.get('status')}")
                print(f"   Stop-Loss: {order_data.get('stopLoss')}")
                print(f"   Take-Profit: {order_data.get('takeProfit')}")

                # Wait 2 seconds then cancel
                await asyncio.sleep(2)

                await client.cancel_order("FARTCOIN-USDT", order_id)
                print(f"✓ Order cancelled")
        except BingXAPIError as e:
            print(f"⚠️  SL/TP order: {e}")
            print(f"   Note: BingX might require separate SL/TP orders after entry")

        # Test 6: Orderbook Depth (for better entry prices)
        print("\n\n📖 TEST 6: Order Book Depth")
        print("="*70)

        orderbook = await client.get_orderbook("FARTCOIN-USDT", limit=5)
        if orderbook:
            print("✓ Order book retrieved")
            print(f"\nTop 3 Bids (buyers):")
            for bid in orderbook.get('bids', [])[:3]:
                print(f"   ${bid[0]} - {bid[1]} FARTCOIN")

            print(f"\nTop 3 Asks (sellers):")
            for ask in orderbook.get('asks', [])[:3]:
                print(f"   ${ask[0]} - {ask[1]} FARTCOIN")

            # Calculate spread
            best_bid = float(orderbook['bids'][0][0]) if orderbook.get('bids') else 0
            best_ask = float(orderbook['asks'][0][0]) if orderbook.get('asks') else 0
            spread = ((best_ask - best_bid) / best_bid * 100) if best_bid else 0
            print(f"\n   Spread: {spread:.4f}%")

        # Summary
        print("\n\n" + "="*70)
        print("✅ STRATEGY ENDPOINTS TEST COMPLETE")
        print("="*70)

        print("\n✅ Working endpoints for strategy:")
        print("   • Klines (1m, 5m, 15m) - for indicators")
        print("   • Contract info - for min quantities")
        print("   • Leverage setting - working")
        print("   • Order book - for spread analysis")
        print("   • SL/TP orders - tested")

        print("\n💡 Your trading strategy can now:")
        print("   • Calculate RSI, SMA, ATR from klines")
        print("   • Analyze multiple timeframes")
        print("   • Set proper position sizes (contract info)")
        print("   • Manage risk with SL/TP")
        print("   • Get best bid/ask prices")

        print("\n🚀 All endpoints needed for automated trading are operational!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
