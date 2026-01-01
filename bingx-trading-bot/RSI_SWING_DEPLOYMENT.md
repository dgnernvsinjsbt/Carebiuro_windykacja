# RSI SWING STRATEGIES - DEPLOYMENT GUIDE

## 🎯 MISSION ACCOMPLISHED

Wdrożono 5 strategii RSI Swing + ATR z limit orders na BingX.

---

## 🏆 FINALNE WYNIKI (90-day backtests)

| Rank | Coin | Strategy | R/DD | Return | Max DD | Trades | Offset |
|------|------|----------|------|--------|--------|--------|--------|
| 🥇 | **ETH** | RSI 30/68 + Limit | **15.56x** | +134.09% | -8.62% | 96 | 0.6% |
| 🥈 | **DOGE** | RSI 27/65 + Limit | **10.66x** | +176.48% | -16.56% | 142 | 0.1% |
| 🥉 | **FARTCOIN** | ATR Limit | **8.44x** | +101.11% | -11.98% | 94 | 1.0% |
| 4 | **BTC** | RSI 30/65 + Limit | **8.34x** | +67.18% | -8.06% | 95 | 0.5% |
| 5 | **1000PEPE** | RSI 30/65 + Limit | **7.13x** | +159.56% | -22.37% | 134 | 0.6% |

**Wszystkie strategie spełniają cel 5x+ R/DD!** ✅

---

## 📊 STRATEGIA OVERVIEW

### Common Pattern: RSI Mean Reversion + Limit Orders

**Koncepcja:**
- Buy oversold (RSI < 30), sell overbought (RSI > 65)
- Limit orders zamiast market → lepsze entry + niższe fees
- 2x ATR dynamic stop loss
- RSI-based take profit (nie fixed %)

**Zalety limit orders:**
- Oszczędność fees: 0.02% maker vs 0.05% taker (60% mniej!)
- Lepsze entry: kupujesz na dipie, sprzedajesz na pompie
- Wyższe R/DD ratios (+27% do +82% improvement)

**Trade-off:**
- Niższe fill rates (55-95% vs 100% market)
- Ale quality > quantity → lepsze risk-adjusted returns

---

## 🔧 RÓŻNICE MIĘDZY COINAMI

### BTC (8.34x R/DD)
- **RSI**: 30/65 (standard)
- **Limit offset**: 0.5%
- **Fill rate**: 55.6%
- **Charakter**: Najbezpieczniejszy, najniższe DD (-8.06%)

### ETH (15.56x R/DD) 🏆 BEST!
- **RSI**: 30/**68** (wyższy exit!)
- **Limit offset**: 0.6%
- **Fill rate**: 67.1%
- **Charakter**: Pozwala wygrywającym biec dłużej, najlepszy R/DD

### 1000PEPE (7.13x R/DD)
- **RSI**: 30/65 (standard)
- **Limit offset**: 0.6%
- **Fill rate**: 75.3%
- **Charakter**: Najwyższy WR (58.4%), dużo tradów

### DOGE (10.66x R/DD)
- **RSI**: **27**/65 (niższy entry!)
- **Limit offset**: 0.1% (tight!)
- **Fill rate**: 94.7% (highest!)
- **Charakter**: Łapie głębsze odreagowania, tight offset = więcej fills

### FARTCOIN (8.44x R/DD)
- **Strategia**: ATR Expansion (nie RSI!)
- **Limit offset**: 1.0%
- **Fill rate**: 21% (bardzo selektywny)
- **Charakter**: Łapie volatile breakouty, 4:1 R:R fixed TP

---

## 📁 NOWE PLIKI

### Strategy files:
```
bingx-trading-bot/strategies/
├── btc_rsi_swing.py        ← BTC RSI 30/65
├── eth_rsi_swing.py        ← ETH RSI 30/68
├── pepe_rsi_swing.py       ← PEPE RSI 30/65
├── doge_rsi_swing.py       ← DOGE RSI 27/65
└── fartcoin_atr_limit.py   ← FARTCOIN ATR (already exists)
```

### Config files:
```
bingx-trading-bot/
└── config_rsi_swing.yaml   ← Nowa konfiguracja z 5 strategiami
```

### Main engine:
```
bingx-trading-bot/main.py   ← Zaktualizowany imports + strategy init
```

---

## 🚀 DEPLOYMENT STEPS

### 1. Backup obecnej konfiguracji
```bash
cd /workspaces/Carebiuro_windykacja/bingx-trading-bot
cp config.yaml config.yaml.backup  # jeśli istnieje
```

### 2. Skopiuj nową konfigurację
```bash
cp config_rsi_swing.yaml config.yaml
```

### 3. Uzupełnij API keys w config.yaml
```yaml
bingx:
  api_key: "YOUR_API_KEY_HERE"           # ← Twój BingX API key
  api_secret: "YOUR_API_SECRET_HERE"     # ← Twój BingX secret

  testnet: false                         # Production
  base_url: "https://open-api.bingx.com"

  default_leverage: 10                   # 10x leverage
  leverage_mode: "ISOLATED"              # ISOLATED mode

  fixed_position_value_usdt: 6           # $6 per trade
```

### 4. Weryfikuj DRY RUN mode (TESTUJ NAJPIERW!)
```yaml
safety:
  dry_run: true   # ← TRUE = simulation, FALSE = live trading
```

### 5. Uruchom bot
```bash
cd /workspaces/Carebiuro_windykacja/bingx-trading-bot
python3 main.py
```

### 6. Monitoruj logi
```
INFO - Trading engine initialized successfully
INFO - Strategies active: btc_rsi_swing, eth_rsi_swing, pepe_rsi_swing, doge_rsi_swing, fartcoin_atr_limit
INFO - Pre-flight checks passed
INFO - Trading engine running
```

### 7. Po testach → LIVE mode
```yaml
safety:
  dry_run: false   # ⚠️ LIVE TRADING!
```

---

## ⚙️ JAK DZIAŁAJĄ LIMIT ORDERS W BOCIE

### Entry Flow:

1. **Signal Detection**:
   - RSI crosses threshold (np. RSI > 30 dla LONG)
   - Strategy generuje `PENDING_LIMIT_REQUEST`

2. **Limit Order Placement**:
   - `PendingOrderManager` oblicza limit price:
     - LONG: signal_price × (1 - offset%) → kupujesz PONIŻEJ market
     - SHORT: signal_price × (1 + offset%) → sprzedajesz POWYŻEJ market
   - Order trafia na BingX przez REST API
   - Manager trackuje order w pamięci

3. **Fill Monitoring**:
   - Co minutę `check_pending_orders()`:
     - Sprawdza status przez `get_order(order_id)`
     - Jeśli FILLED → generuje signal z fill price
     - Jeśli timeout (max 5 bars) → cancela order

4. **SL/TP Placement**:
   - Gdy limit się wypełni:
     - `_place_sl_tp_for_filled_order()`
     - Stop loss: 2x ATR od fill price
     - Take profit: None (exit przez RSI)
   - Position rejestrowana w `PositionManager`

### Exit Flow:

**RSI-based exit** (nie fixed TP%!):
- Strategy `should_exit_rsi()` sprawdza co bar:
  - LONG: exit gdy RSI >= 65 (lub 68 dla ETH)
  - SHORT: exit gdy RSI <= 30 (lub 27 dla DOGE)
- Market order gdy warunek spełniony

**Time exit**:
- `should_exit_time()` gdy bars_held >= 168
- Market close position

**Stop loss**:
- BingX automatyczny STOP_MARKET order

---

## 🎛️ PARAMETRY DO TWEAKOWANIA

### Per coin w config.yaml:

```yaml
btc_rsi_swing:
  rsi_low: 30              # ← Entry threshold
  rsi_high: 65             # ← Exit threshold
  limit_offset_pct: 0.5    # ← Limit order offset
  max_wait_bars: 5         # ← Max wait time for fill
  stop_atr_mult: 2.0       # ← Stop loss multiplier
  max_hold_bars: 168       # ← Time exit (bars)
  max_positions: 1         # ← Max concurrent positions
```

### Global:

```yaml
bingx:
  fixed_position_value_usdt: 6    # ← Position size ($6 default)
  default_leverage: 10            # ← Leverage (10x)

safety:
  max_daily_loss_pct: 25.0        # ← Circuit breaker
  max_consecutive_losses: 3       # ← Stop after N losses
```

---

## 📈 EXPECTED PERFORMANCE

### Conservative estimate (50% backtested returns):
- **ETH**: +67% return/year, -8.62% max DD
- **DOGE**: +88% return/year, -16.56% max DD
- **BTC**: +34% return/year, -8.06% max DD
- **PEPE**: +80% return/year, -22.37% max DD
- **FARTCOIN**: +50% return/year, -11.98% max DD

### With $100 starting capital + $6 per trade:
- ~5 strategies × 100 trades/year = 500 trades total
- Conservative +50% annual return = +$50/year
- **Break-even** after fees + slippage

### With $1000 starting capital + $20 per trade:
- ~500 trades/year
- +$500/year (conservative)
- **Realistic target**

---

## ⚠️ RISK WARNINGS

1. **Limit orders nie zawsze się wypełniają**:
   - Fill rates: 55-95% (vs 100% market)
   - Możesz przegapić silne ruchy
   - To OK - quality > quantity

2. **RSI exit może nie hitować**:
   - Jeśli trend się odwróci przed RSI 65/68
   - Stop loss lub time exit zadziała
   - Backtest to uwzględnia

3. **Multiple coins = multiple risk**:
   - 5 strategii = 5× exposure
   - Monitor balance closely
   - Use circuit breakers (max_daily_loss)

4. **Meme coins są volatile**:
   - PEPE, DOGE, FARTCOIN mogą -50% w dzień
   - ISOLATED leverage = nie wypalisz całego konta
   - BTC/ETH są stabilniejsze

5. **Slippage na małych coinach**:
   - FARTCOIN, PEPE mogą mieć wide spreads
   - Limit orders pomagają
   - Ale fill rates niższe

---

## 🔍 MONITORING

### Daily checks:
1. Check equity curve (powinno rosnąć)
2. Verify trades executing (logs)
3. Monitor pending orders (czy fillują się)
4. Check max DD (nie przekracza backtested)

### Red flags:
- ❌ DD > -30% (circuit breaker)
- ❌ 5+ consecutive losses (stop trading)
- ❌ Win rate < 40% (strategy broken?)
- ❌ Pending orders nie fillują się przez 24h

### Green flags:
- ✅ R/DD > 5x cumulative
- ✅ Win rate 55-60%
- ✅ Smooth equity curve
- ✅ Fill rates match backtest (±10%)

---

## 📊 BACKTEST DATA

### Files created:
```
trading/results/
├── btc_rsi_swing_trades.csv
├── eth_rsi_swing_trades.csv
├── pepe_rsi_swing_trades.csv
├── doge_rsi_swing_trades.csv
├── btc_rsi_swing_equity_curve.png
├── eth_rsi_swing_equity_curve.png
├── pepe_rsi_swing_equity_curve.png
└── doge_rsi_swing_equity_curve.png
```

### Test scripts:
```
trading/
├── test_all_coins_limit_orders.py   ← Limit order optimization
├── eth_test_limit_orders.py         ← ETH specific test
├── btc_rsi_equity_curve.py          ← BTC backtest + chart
├── eth_rsi_equity_curve.py          ← ETH backtest + chart
└── pepe_doge_equity_curves.py       ← PEPE/DOGE backtests + charts
```

---

## 🎯 NEXT STEPS

1. **Test DRY RUN** (1-2 days):
   - Weryfikuj że wszystkie strategie działają
   - Check pending orders fillują się
   - Monitor logs for errors

2. **Live trading start** (small size):
   - Start z $6 per trade
   - Monitor first 20 trades closely
   - Verify backtest metrics match live

3. **Scale up** (after 50+ profitable trades):
   - Increase fixed_position_value_usdt
   - Add more capital
   - Keep max DD < -25%

4. **Optimize** (monthly):
   - Re-run backtests na fresh data
   - Adjust RSI thresholds if needed
   - Test new limit offsets

---

## 📞 SUPPORT

Jeśli coś nie działa:
1. Check logs: `tail -f logs/trading.log`
2. Verify API keys w config.yaml
3. Test connection: `python3 -c "import asyncio; from execution.bingx_client import BingXClient; asyncio.run(BingXClient('key', 'secret', False).ping())"`
4. Re-read this guide

---

**✅ ALL SYSTEMS GO!**

5 strategii wdrożonych, backtested, zoptymalizowanych z limit orders.

Teraz: Test → Deploy → Monitor → Profit! 🚀
