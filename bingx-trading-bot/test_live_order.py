"""
FORCED TEST TRADE - 3 USDT
Weryfikacja ATR-based TP/SL calculation i live order placement
"""

import asyncio
import pandas as pd
from config import load_config
from execution.bingx_client import BingXClient
from strategies.donchian_breakout import DonchianBreakout, COIN_PARAMS

async def test_live_order():
    """Wymuś test trade na małej kwocie"""

    # Load config
    config = load_config('config_donchian.yaml')

    # Initialize BingX client
    client = BingXClient(
        api_key=config.bingx.api_key,
        api_secret=config.bingx.api_secret,
        testnet=config.bingx.testnet
    )

    # Test coin: DOGE (wysoka płynność, TP=4.0 ATR, SL=4 ATR)
    symbol = 'DOGE-USDT'
    print(f"\n{'='*70}")
    print(f"FORCED TEST TRADE: {symbol}")
    print(f"Stake: 3 USDT")
    print(f"{'='*70}\n")

    # 1. Fetch current candles
    print("📊 Fetching 1H candles...")
    candles = await client.get_klines(symbol, '1h', limit=50)

    if not candles:
        print("❌ Failed to fetch candles")
        await client.close()
        return

    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

    print(f"✅ Loaded {len(df)} candles")
    print(f"Latest candle: {df.iloc[-1]['timestamp']}")
    print(f"Close: ${df.iloc[-1]['close']:.6f}")

    # 2. Calculate ATR
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    current_price = df.iloc[-1]['close']
    atr = df.iloc[-1]['atr']

    print(f"\n📐 ATR Calculation:")
    print(f"  ATR(14): ${atr:.6f}")
    print(f"  Current Price: ${current_price:.6f}")

    # 3. Get DOGE parameters
    params = COIN_PARAMS[symbol]
    tp_atr = params['tp_atr']  # 4.0
    sl_atr = params['sl_atr']  # 4

    print(f"\n⚙️ DOGE Parameters:")
    print(f"  TP: {tp_atr} × ATR")
    print(f"  SL: {sl_atr} × ATR")

    # 4. Force LONG position (test)
    side = 'LONG'
    entry_price = current_price
    stop_loss = entry_price - (sl_atr * atr)
    take_profit = entry_price + (tp_atr * atr)

    sl_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
    tp_distance_pct = abs(take_profit - entry_price) / entry_price * 100

    print(f"\n💡 Trade Calculation (FORCED {side}):")
    print(f"  Entry:  ${entry_price:.6f}")
    print(f"  SL:     ${stop_loss:.6f} ({sl_distance_pct:.2f}% from entry)")
    print(f"  TP:     ${take_profit:.6f} ({tp_distance_pct:.2f}% from entry)")
    print(f"  R:R:    {tp_distance_pct/sl_distance_pct:.2f}:1")

    # 5. Calculate position size for 3 USDT stake
    stake_usdt = 3.0
    leverage = 1  # Start with 1x

    # Position size in DOGE = stake_usdt / price
    position_size = stake_usdt / current_price

    print(f"\n💰 Position Sizing:")
    print(f"  Stake: ${stake_usdt:.2f} USDT")
    print(f"  Leverage: {leverage}x")
    print(f"  Position Size: {position_size:.4f} DOGE")
    print(f"  Notional Value: ${position_size * current_price:.2f}")

    # 6. Check account balance
    print(f"\n🔍 Pre-flight checks...")
    balance_data = await client.get_balance()

    if balance_data and 'balance' in balance_data:
        balance = float(balance_data['balance']['balance'])
        print(f"  Account Balance: ${balance:.2f} USDT")

        if balance < stake_usdt:
            print(f"  ❌ Insufficient balance (need ${stake_usdt}, have ${balance:.2f})")
            await client.close()
            return
    else:
        print(f"  ⚠️ Could not verify balance")

    # 7. Confirm with user
    print(f"\n{'='*70}")
    print(f"READY TO PLACE LIVE ORDER")
    print(f"{'='*70}")
    print(f"Symbol:   {symbol}")
    print(f"Side:     {side}")
    print(f"Quantity: {position_size:.4f} DOGE")
    print(f"Entry:    ${entry_price:.6f}")
    print(f"Stop:     ${stop_loss:.6f}")
    print(f"Target:   ${take_profit:.6f}")
    print(f"Risk:     ${stake_usdt * (sl_distance_pct/100):.2f} USDT")
    print(f"{'='*70}\n")

    # Auto-execute for testing
    print("⚡ AUTO-EXECUTING TEST ORDER...")
    import time
    time.sleep(1)

    # 8. Place MARKET order
    print(f"\n📤 Placing MARKET order...")

    try:
        # Set leverage
        leverage_result = await client.set_leverage(symbol, side, leverage)
        print(f"✅ Leverage set: {leverage}x {side}")

        # Place order
        order = await client.place_order(
            symbol=symbol,
            side='BUY',  # LONG = BUY
            order_type='MARKET',
            quantity=position_size,
            position_side=side
        )

        if order and 'order' in order:
            order_data = order['order']
            filled_qty = float(order_data.get('quantity', position_size))

            print(f"\n✅ ORDER EXECUTED!")
            print(f"  Order ID: {order_data.get('orderId')}")
            print(f"  Status: {order_data.get('status')}")
            print(f"  Side: {order_data.get('side')}")
            print(f"  Quantity: {filled_qty}")
            print(f"  Price: ${order_data.get('price', 'MARKET')}")

            # Get actual position to verify fill price
            print(f"\n🔍 Fetching position details...")
            positions = await client.get_positions()

            actual_entry = None
            if positions and isinstance(positions, list):
                for pos in positions:
                    if pos['symbol'] == symbol and float(pos.get('positionAmt', 0)) != 0:
                        actual_entry = float(pos['avgPrice'])
                        print(f"  Actual Entry Price: ${actual_entry:.6f}")
                        print(f"  Position Size: {pos['positionAmt']}")
                        break

            # Recalculate SL/TP based on actual entry if available
            if actual_entry:
                entry_price = actual_entry
                stop_loss = entry_price - (sl_atr * atr)
                take_profit = entry_price + (tp_atr * atr)
                print(f"  Recalculated SL: ${stop_loss:.6f}")
                print(f"  Recalculated TP: ${take_profit:.6f}")

            # Get current market price before setting SL
            latest_candles = await client.get_klines(symbol, '1m', limit=1)
            if latest_candles:
                current_market_price = float(latest_candles[0]['close'])
                print(f"  Current Market Price: ${current_market_price:.6f}")

                # Verify SL is valid
                if stop_loss >= current_market_price:
                    print(f"  ⚠️ WARNING: SL ${stop_loss:.6f} >= Current ${current_market_price:.6f}")
                    print(f"  Adjusting SL to be 0.5% below current price...")
                    stop_loss = current_market_price * 0.995

            # 9. Set TP/SL orders
            print(f"\n📤 Setting TP/SL orders...")

            # Stop Loss (STOP_MARKET)
            sl_order = await client.place_order(
                symbol=symbol,
                side='SELL',
                order_type='STOP_MARKET',
                quantity=position_size,
                position_side=side,
                stop_price=stop_loss
            )

            if sl_order:
                print(f"✅ Stop Loss set at ${stop_loss:.6f}")

            # Take Profit (TAKE_PROFIT_MARKET)
            tp_order = await client.place_order(
                symbol=symbol,
                side='SELL',
                order_type='TAKE_PROFIT_MARKET',
                quantity=position_size,
                position_side=side,
                stop_price=take_profit
            )

            if tp_order:
                print(f"✅ Take Profit set at ${take_profit:.6f}")

            print(f"\n{'='*70}")
            print(f"LIVE TRADE ACTIVE!")
            print(f"{'='*70}")

        else:
            print(f"❌ Order failed: {order}")

    except Exception as e:
        print(f"❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()
        print(f"\n✅ BingX client closed")

if __name__ == "__main__":
    asyncio.run(test_live_order())
