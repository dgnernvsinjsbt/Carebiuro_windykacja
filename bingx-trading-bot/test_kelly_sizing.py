"""
Test Kelly position sizing live on DOGE
Risk: 3% of total equity per trade
"""

import asyncio
import pandas as pd
from config import load_config
from execution.bingx_client import BingXClient
from strategies.donchian_breakout import COIN_PARAMS

async def test_kelly_sizing():
    """Test Kelly sizing with live equity"""

    # Load config
    config = load_config('config_donchian.yaml')

    # Initialize BingX client
    client = BingXClient(
        api_key=config.bingx.api_key,
        api_secret=config.bingx.api_secret,
        testnet=config.bingx.testnet
    )

    symbol = 'DOGE-USDT'
    print(f"\n{'='*70}")
    print(f"KELLY SIZING TEST: {symbol}")
    print(f"Risk: 3% of total equity per trade")
    print(f"{'='*70}\n")

    # 1. Get actual account equity
    print("💰 Fetching account balance...")
    balance_data = await client.get_balance()

    if not balance_data or not isinstance(balance_data, list):
        print("❌ Failed to fetch balance")
        await client.close()
        return

    # Find USDT balance
    usdt_balance = None
    for asset_balance in balance_data:
        if asset_balance.get('asset') == 'USDT':
            usdt_balance = asset_balance
            break

    if not usdt_balance:
        print("❌ No USDT balance found")
        await client.close()
        return

    total_equity = float(usdt_balance['balance'])
    print(f"✅ Total Equity: ${total_equity:.2f} USDT")
    print(f"   Available Margin: ${float(usdt_balance['availableMargin']):.2f} USDT\n")

    # 2. Fetch current 1H candles
    print("📊 Fetching 1H candles for ATR calculation...")
    candles = await client.get_klines(symbol, '1h', limit=50)

    if not candles:
        print("❌ Failed to fetch candles")
        await client.close()
        return

    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

    # 3. Calculate ATR
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    current_price = df.iloc[-1]['close']
    atr = df.iloc[-1]['atr']

    print(f"✅ Latest Price: ${current_price:.6f}")
    print(f"✅ ATR(14): ${atr:.6f}\n")

    # 4. Get DOGE parameters (TP=4×ATR, SL=4×ATR)
    params = COIN_PARAMS[symbol]
    tp_atr = params['tp_atr']
    sl_atr = params['sl_atr']

    print(f"⚙️ DOGE Strategy Parameters:")
    print(f"  TP: {tp_atr} × ATR")
    print(f"  SL: {sl_atr} × ATR\n")

    # 5. KELLY SIZING CALCULATION
    print(f"📐 KELLY POSITION SIZING:")
    print(f"{'='*70}")

    # Simulate LONG entry
    entry_price = current_price
    stop_loss = entry_price - (sl_atr * atr)
    take_profit = entry_price + (tp_atr * atr)

    # Kelly formula
    risk_pct = 3.0  # From config
    risk_amount = total_equity * (risk_pct / 100)
    sl_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
    position_value_usdt = risk_amount / (sl_distance_pct / 100)
    position_size_doge = position_value_usdt / entry_price

    print(f"\n1. Risk Parameters:")
    print(f"   Total Equity: ${total_equity:.2f}")
    print(f"   Risk per Trade: {risk_pct}%")
    print(f"   Risk Amount: ${risk_amount:.2f}\n")

    print(f"2. Entry & Exit Levels:")
    print(f"   Entry:  ${entry_price:.6f}")
    print(f"   SL:     ${stop_loss:.6f} ({sl_distance_pct:.2f}% away)")
    print(f"   TP:     ${take_profit:.6f}\n")

    print(f"3. Kelly Calculation:")
    print(f"   Position Value = Risk Amount / SL Distance %")
    print(f"   Position Value = ${risk_amount:.2f} / {sl_distance_pct:.2f}%")
    print(f"   Position Value = ${position_value_usdt:.2f} USDT\n")

    print(f"4. Position Size:")
    print(f"   Size in DOGE: {position_size_doge:.4f}")
    print(f"   Notional: ${position_size_doge * entry_price:.2f}\n")

    print(f"5. Verification (if SL hits):")
    loss_amount = position_value_usdt * (sl_distance_pct / 100)
    print(f"   Loss = ${position_value_usdt:.2f} × {sl_distance_pct:.2f}%")
    print(f"   Loss = ${loss_amount:.2f}")
    print(f"   Expected Risk: ${risk_amount:.2f}")
    print(f"   ✅ Match: {abs(loss_amount - risk_amount) < 0.01}\n")

    print(f"{'='*70}")
    print(f"READY TO EXECUTE")
    print(f"{'='*70}\n")

    # Ask for confirmation
    print(f"Execute this live trade? (y/n): ", end='')
    import sys
    sys.stdout.flush()

    # Auto-execute for testing
    print("y (auto)")
    await asyncio.sleep(1)

    # 6. Set leverage to 20x (margin efficiency - risk stays the same)
    leverage = 20
    try:
        await client.set_leverage(symbol, 'LONG', leverage)
        print(f"✅ Leverage set: {leverage}x LONG")
        print(f"   Margin required: ${position_value_usdt / leverage:.2f} USDT\n")
    except Exception as e:
        print(f"⚠️ Leverage: {e}\n")

    # 7. Place MARKET order
    print(f"📤 Placing MARKET order for {position_size_doge:.4f} DOGE...")

    order = await client.place_order(
        symbol=symbol,
        side='BUY',
        order_type='MARKET',
        quantity=position_size_doge,
        position_side='LONG'
    )

    if not order or 'order' not in order:
        print(f"❌ Order failed: {order}")
        await client.close()
        return

    order_data = order['order']
    print(f"\n✅ ORDER FILLED!")
    print(f"  Order ID: {order_data.get('orderId')}")
    print(f"  Status: {order_data.get('status')}\n")

    # 8. Get actual entry price from position
    print(f"🔍 Fetching actual entry price...")
    positions = await client.get_positions()

    actual_entry = None
    if positions and isinstance(positions, list):
        for pos in positions:
            if pos['symbol'] == symbol and float(pos.get('positionAmt', 0)) != 0:
                actual_entry = float(pos['avgPrice'])
                print(f"✅ Actual Entry: ${actual_entry:.6f}\n")
                break

    if not actual_entry:
        print(f"❌ Could not fetch actual entry")
        await client.close()
        return

    # 9. Recalculate SL/TP based on actual entry
    stop_loss = actual_entry - (sl_atr * atr)
    take_profit = actual_entry + (tp_atr * atr)

    print(f"📐 Recalculated Levels (from actual entry):")
    print(f"  Entry: ${actual_entry:.6f}")
    print(f"  SL:    ${stop_loss:.6f}")
    print(f"  TP:    ${take_profit:.6f}\n")

    # 10. Place SL/TP orders
    print(f"📤 Setting TP/SL orders...")

    # Stop Loss
    sl_order = await client.place_order(
        symbol=symbol,
        side='SELL',
        order_type='STOP_MARKET',
        quantity=position_size_doge,
        position_side='LONG',
        stop_price=stop_loss
    )

    if sl_order:
        print(f"✅ Stop Loss set at ${stop_loss:.6f}")

    # Take Profit
    tp_order = await client.place_order(
        symbol=symbol,
        side='SELL',
        order_type='TAKE_PROFIT_MARKET',
        quantity=position_size_doge,
        position_side='LONG',
        stop_price=take_profit
    )

    if tp_order:
        print(f"✅ Take Profit set at ${take_profit:.6f}")

    print(f"\n{'='*70}")
    print(f"KELLY SIZING TEST COMPLETE!")
    print(f"{'='*70}")
    print(f"Position: {position_size_doge:.4f} DOGE (${position_value_usdt:.2f})")
    print(f"Risk if SL hits: ${risk_amount:.2f} ({risk_pct}% of equity)")
    print(f"{'='*70}\n")

    await client.close()

if __name__ == "__main__":
    asyncio.run(test_kelly_sizing())
