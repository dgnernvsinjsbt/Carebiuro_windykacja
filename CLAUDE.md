CLAUDE.md — Best Practices for Fiscal Development

---

# 🤖 BINGX TRADING BOT - ACTIVE STRATEGIES (Dec 2025)

## 🚀 INSTANT STARTUP - NO 4-HOUR WAIT

**Historical Data Warmup**

The bot downloads the last 300 candles on startup instead of waiting 4 hours:

- **Before**: 4-hour warmup required (250+ candles from live WebSocket)
- **After**: <10 seconds warmup (300 candles from BingX REST API)
- **Method**: `MultiTimeframeCandleManager.warmup_from_history()`
- **Location**: [data/candle_builder.py:320](bingx-trading-bot/data/candle_builder.py#L320)

Benefits:
- ✅ Restarts/rebuilds no longer wipe progress
- ✅ Can deploy updates without losing 4 hours
- ✅ Indicators calculated immediately from historical data
- ✅ Bot starts trading within seconds of launch

---

## 📐 KEY METRIC DEFINITION

**R:R Ratio = Total Return ÷ Max Drawdown**

This is the PRIMARY metric for ranking strategies. It measures how much profit you make relative to the worst loss you experienced.

```
Example: FARTCOIN ATR
- Return: +101.11%
- Max Drawdown: -11.98%
- R:R = 101.11 ÷ 11.98 = 8.44x
```

**ALWAYS use this definition when discussing R:R.** Do NOT confuse with trade-level TP/SL ratios.

Higher R:R = Better risk-adjusted performance.

---

## 🐛 CRITICAL BUG FIXES (Dec 2025)

**Four critical bugs were discovered and fixed on Dec 15, 2025:**

### Bug #1: RSI Calculation (CRITICAL - Invalidated All Previous Results)

**Problem**: Bot was using Simple Moving Average (SMA) instead of Wilder's EMA for RSI calculation.

**Impact**: RSI values differed by 5-20 points from BingX/TradingView. Bot showed RSI 66.87 when actual was 58.23.

**Fix**: Replaced `gain.rolling(window=period).mean()` with proper Wilder's smoothing:
- First value: SMA of first 14 periods
- Subsequent values: `new_avg = (prev_avg * 13 + current_value) / 14`

**File**: `bingx-trading-bot/data/indicators.py:40-75`

**Verification**: RSI values now match BingX exactly.

### Bug #2: Symbol Matching

**Problem**: Strategy symbols ('1000PEPE') didn't match config symbols ('1000PEPE-USDT'), causing all strategies to be filtered out.

**Impact**: No signals generated despite RSI crossovers occurring.

**Fix**: Added symbol base extraction in signal_generator.py:
```python
symbol_base = symbol.split('-')[0]  # Extract "1000PEPE" from "1000PEPE-USDT"
if strategy.symbol != symbol and strategy.symbol != symbol_base:
    continue
```

**File**: `bingx-trading-bot/execution/signal_generator.py:20-23`

### Bug #3: Field Name Mismatch

**Problem**: Strategies return 'side' field but main.py expects 'direction', causing KeyError.

**Impact**: Bot would crash when trying to access signal['direction'].

**Fix**: Normalize field names in signal_generator.py:
```python
if 'side' in signal and 'direction' not in signal:
    signal['direction'] = signal['side']
```

**File**: `bingx-trading-bot/execution/signal_generator.py:31-32`

### Bug #4: Type Mismatch

**Problem**: Strategies return type='LIMIT' but main.py checks for 'PENDING_LIMIT_REQUEST'.

**Impact**: Limit orders skipped pending order flow and went to wrong execution path.

**Fix**: Normalize type in signal_generator.py:
```python
if signal.get('type') == 'LIMIT':
    signal['type'] = 'PENDING_LIMIT_REQUEST'
```

**File**: `bingx-trading-bot/execution/signal_generator.py:34-35`

### Re-optimization Results

After fixing these bugs, ALL strategies were re-optimized with corrected RSI:
- Tested 432 parameter combinations per coin (9 coins total)
- Parameter grid: 3 RSI_low × 3 RSI_high × 4 limit_offset × 3 SL_ATR × 4 TP_ATR
- All 9 strategy files updated with new optimal parameters
- Portfolio results improved significantly with proper RSI calculation

**⚠️ IMPORTANT**: All results shown below use CORRECTED RSI (Wilder's EMA method).

---

# 🎯 4-COIN SHORT REVERSAL PORTFOLIO (15m timeframe)

**Portfolio Performance (Jun-Dec 2025):**
- **Total Return:** +5,204,473% ($100 → $5.2M)
- **Max Drawdown:** -65.9%
- **Return/DD Ratio:** 78,973x 🏆 EXCEPTIONAL!
- **Timeframe:** 15-minute candles
- **Position Sizing:** 5% risk per trade
- **Method:** Limit orders with swing-based entries

---

## 📊 STRATEGY PARAMETERS COMPARISON

| Coin | RSI Trigger | Limit Offset | TP % | File |
|------|-------------|--------------|------|------|
| **FARTCOIN** | 70 | 1.0 ATR | 10.0% | `fartcoin_short_reversal.py` |
| **MELANIA** | 72 | 0.8 ATR | 10.0% | `melania_short_reversal.py` |
| **DOGE** | 72 | 0.6 ATR | 6.0% | `doge_short_reversal.py` |
| **MOODENG** | 70 | 0.8 ATR | 8.0% | `moodeng_short_reversal.py` |

**Common Parameters (all 4 strategies):**
- `lookback = 5` (swing low lookback period)
- `max_wait_bars = 20` (5 hours timeout for limit orders)
- `max_sl_pct = 10.0%` (skip if SL distance > 10%)
- `risk_pct = 5.0%` (risk 5% of equity per trade)

---

## 🔄 UNIVERSAL STRATEGY LOGIC

All 4 strategies follow the same core logic with different parameters:

1. **ARM Signal:** RSI(14) > trigger (overbought, ready for reversal)
2. **Calculate Swing Low:** Min low of last 5 candles
3. **Wait for Break:** Price breaks below swing low (resistance→support failure)
4. **Place Limit Order:** `swing_low + (limit_offset × ATR)`
5. **Stop Loss:** Swing high from signal bar to break bar (dynamic)
6. **Take Profit:** Fixed % below entry price
7. **Timeout:** Cancel limit if not filled within 20 bars (5 hours)

**Position Sizing:** Risk 5% of equity per trade based on SL distance

---

## 💎 MELANIA-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Total Return** | +1,330.4% |
| **Max Drawdown** | -24.66% |
| **Return/DD Ratio** | **53.96x** 🏆 |
| **Total Trades** | 45 |
| **Win Rate** | 42.2% (19W / 26L) |
| **Avg SL Distance** | 3.02% |
| **Max Consecutive Losses** | ~8-9 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 72           # ARM when RSI > 72
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.8     # Limit order offset above swing low
tp_pct = 10.0              # Take profit 10% below entry
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Monthly Performance
| Month | P&L | Status |
|-------|-----|--------|
| Jun 2025 | +$62.15 | ✅ |
| Jul 2025 | +$58.53 | ✅ |
| Aug 2025 | +$162.49 | ✅ |
| Sep 2025 | -$41.25 | ❌ ONLY LOSING MONTH |
| Oct 2025 | +$230.49 | ✅ |
| Nov 2025 | +$149.27 | ✅ |
| Dec 2025 | +$708.74 | 🚀 BEST MONTH |

### Key Insights
- **December dominance:** $708.74 profit (53% of total return) in one month
- **September drawdown:** Only losing month at -$41.25
- **High R/R:** 53.96x return/drawdown ratio is exceptional
- **Moderate win rate:** 42.2% but winners are much larger than losers
- **Tight stops:** 3.02% avg SL distance keeps losses small

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/melania_short_reversal.py`
- **Backtest Script:** `trading/test_melania_sl_methods.py`
- **Data File:** `trading/melania_6months_bingx.csv` (15m candles)

---

## 🚀 FARTCOIN-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | ~30% of total |
| **Total Trades** | 86 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 70           # ARM when RSI > 70 (lower threshold)
lookback = 5               # Swing low lookback period
limit_atr_offset = 1.0     # WIDER offset for FARTCOIN (more volatile)
tp_pct = 10.0              # Take profit 10% below entry
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **Lower RSI trigger (70):** FARTCOIN more volatile, reverses earlier
- **Wider limit offset (1.0 ATR):** Allows for larger pullback before entry
- **Same TP (10%):** Keeps consistent target across coins

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/fartcoin_short_reversal.py`
- **Data File:** `trading/fartcoin_6months_bingx.csv` (15m candles)

---

## 🐕 DOGE-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | $2,993,404 (57.5% of total!) 🏆 |
| **Total Trades** | 79 |
| **Profitable Months** | 5/7 |
| **Best Trade** | +$998,362 (Dec 9) |

### Parameters
```python
rsi_trigger = 72           # ARM when RSI > 72
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.6     # TIGHTER offset for DOGE
tp_pct = 6.0               # TIGHTER TP target (higher win rate)
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **STAR PERFORMER:** 57.5% of portfolio returns!
- **Tightest limit offset (0.6 ATR):** DOGE has cleaner reversals
- **Lowest TP (6%):** Optimized for higher fill rate and win rate
- **Best single trade:** +$998k in December

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/doge_short_reversal.py`
- **Data File:** `trading/doge_6months_bingx.csv` (15m candles)

---

## 🦛 MOODENG-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | ~10% of total |
| **Total Trades** | 78 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 70           # ARM when RSI > 70 (lower threshold)
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.8     # Mid-range offset
tp_pct = 8.0               # Mid-range TP (balance between DOGE 6% and MELANIA 10%)
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **Balanced approach:** Mid-range offset and TP
- **Lower RSI trigger (70):** Similar to FARTCOIN
- **Consistent performer:** 6/7 profitable months

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/moodeng_short_reversal.py`
- **Data File:** `trading/moodeng_6months_bingx.csv` (15m candles)

---

## 🎯 PARAMETER OPTIMIZATION INSIGHTS

### RSI Triggers
- **70:** FARTCOIN, MOODENG (more volatile, reverse earlier)
- **72:** MELANIA, DOGE (higher threshold for cleaner signals)

### Limit Offsets
- **0.6 ATR:** DOGE (tightest - cleanest reversals)
- **0.8 ATR:** MELANIA, MOODENG (mid-range)
- **1.0 ATR:** FARTCOIN (widest - most volatile)

### Take Profit Targets
- **6%:** DOGE (tightest - highest win rate)
- **8%:** MOODENG (balanced)
- **10%:** MELANIA, FARTCOIN (wider targets for larger moves)

**General Rule:** More volatile coins (FARTCOIN) need wider offsets and can support wider TPs. Cleaner reversals (DOGE) work better with tighter parameters.

---

## 🚨 IMPORTANT NOTES

1. **All strategies use corrected RSI (Wilder's EMA method)** - see Bug Fixes section
2. **5% risk per trade** - position size calculated from SL distance
3. **Limit orders only** - no market orders (reduces slippage, filters fake breakouts)
4. **20-bar timeout** - prevents stale orders in ranging markets
5. **Dynamic stop loss** - based on swing high, adapts to market structure

---

## 📁 CODE STRUCTURE

```
bingx-trading-bot/
├── strategies/
│   ├── base_strategy.py           # Base class
│   ├── fartcoin_short_reversal.py # FARTCOIN strategy
│   ├── melania_short_reversal.py  # MELANIA strategy
│   ├── doge_short_reversal.py     # DOGE strategy
│   └── moodeng_short_reversal.py  # MOODENG strategy
├── data/
│   ├── indicators.py              # RSI (Wilder's EMA), ATR
│   └── candle_builder.py          # 15m candle aggregation
└── execution/
    ├── signal_generator.py        # Strategy signal routing
    └── bingx_client.py            # BingX API client

trading/
├── melania_6months_bingx.csv      # MELANIA historical data
├── fartcoin_6months_bingx.csv     # FARTCOIN historical data
├── doge_6months_bingx.csv         # DOGE historical data
└── moodeng_6months_bingx.csv      # MOODENG historical data
```

---

## 🔥 PORTFOLIO SUMMARY

**Why These 4 Coins Work Together:**

1. **DOGE:** 57.5% contributor - star performer, cleanest reversals
2. **FARTCOIN:** 30% contributor - volatile, wider targets capture big moves
3. **MELANIA:** Exceptional R/DD (53.96x), highest quality trades
4. **MOODENG:** Consistent diversifier, balanced approach

**Combined Effect:**
- Diversification smooths equity curve
- Different volatility profiles = trades don't overlap perfectly
- $100 → $5.2M in 6 months (backtest with 5% risk)
- Return/DD: 78,973x (indicates exceptional risk-adjusted returns)

**⚠️ Backtest Disclaimer:** These results are from historical backtesting with 5% risk per trade and full compounding. Live trading results may vary due to slippage, API latency, and market conditions.

---

## ⚡ CRITICAL: Supabase Database Management

**ZAWSZE używaj Supabase CLI do zarządzania bazą danych, NIE proś użytkownika o wklejanie SQL.**

Dostępne komendy:
- `SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase gen types typescript --linked` - generuj TypeScript types
- `SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase inspect db table-stats --linked` - statystyki tabel
- `SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase migration new nazwa_migracji` - stwórz migrację
- `SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase db push` - wypchnij migracje

Workflow:
1. Sprawdź strukturę bazy przez `gen types` lub `table-stats`
2. Stwórz migrację przez `migration new`
3. Napisz SQL w pliku migracji
4. Użytkownik wykonuje `npx supabase db push`

**NIE pytaj użytkownika o strukturę - sam ją sprawdź przez CLI!**

---

## 🎯 Core Principles

1. **Plan First, Code Second**
   - Przeczytaj cały opis funkcji przed kodowaniem
   - Podziel pracę na najmniejsze logiczne kroki
   - Zapisz pseudokod lub szkic przepływu danych

2. **Small Steps, Frequent Checks**
   - Implementuj jedną funkcję na raz
   - Testuj natychmiast po każdej zmianie
   - Nie przechodź dalej, dopóki obecny etap nie działa

3. **Think Like a Product Engineer**
   - Zawsze pytaj „po co", zanim coś dodasz
   - Myśl o przypadkach brzegowych
   - Dbaj o doświadczenie użytkownika
   - Kod powinien tłumaczyć się sam przez nazwy

4. **Communication is Key**
   - Jeśli coś jest niejasne → pytaj, nie zakładaj
   - Wyjaśnij swój plan przed implementacją
   - Dziel się postępami po każdym większym kroku

---

## 🔄 Development Workflow

### Stage 1: Planning
1. Przeczytaj wymagania funkcji
2. Zrób listę plików do utworzenia/modyfikacji
3. Zanotuj potencjalne problemy
4. Zadaj pytania przed kodowaniem
5. Potwierdź plan

### Stage 2: Implementation
1. Stwórz strukturę folderów i plików
2. Zaimplementuj najmniejszy element
3. Przetestuj w izolacji
4. Zintegruj z resztą systemu
5. Testuj ponownie
6. Utwórz checkpoint commit

### Stage 3: Validation
1. Uruchom aplikację lokalnie
2. Sprawdź konsolę (brak błędów)
3. Przetestuj happy path + edge cases
4. Popraw błędy natychmiast
5. Zapisz co działa

### Stage 4: Checkpoint
1. Podsumuj co zostało wdrożone
2. Wypisz co działa, a co nie
3. Zapisz dług techniczny
4. Potwierdź gotowość do następnego modułu

---

## 🛠️ Technical Best Practices

### File Organization

✅ **DO:**
- Jeden komponent / plik
- Grupy po funkcjonalności
- Nazwy opisowe: `UpdateCommentNode.ts`, `InvoiceParser.ts`

❌ **DON'T:**
- Jeden plik z dziesiątkami funkcji
- Nazwy generyczne jak `utils.ts` z 500 liniami
- Głębokie zagnieżdżenia (max 3-4 poziomy)

### Code Style

✅ **DO:**
```typescript
async function syncInvoiceComment(invoiceId: string, field: string, value: boolean) {
  const invoice = await getInvoice(invoiceId);
  const updatedComment = updateFiscalSync(invoice.comment, field, value);
  await fakturownia.put(`/invoices/${invoiceId}`, { invoice: { comment: updatedComment } });
}
```

❌ **DON'T:**
```typescript
async function doSync(id, f, v) {
  const x = await api(id);
  await send(x, f, v);
}
```

### Error Handling

```typescript
try {
  const res = await supabase.from('invoices').select('*');
  if (!res.data) throw new Error('No data returned');
} catch (err) {
  console.error('Fetch error:', err);
  toast.error('Nie udało się pobrać danych z bazy');
}
```

---

## 📋 Checkpoint System

Po każdej większej funkcji dodaj notatkę:

```markdown
## Checkpoint: Strategia TRUMPSOL — 2025-12-09

### ✅ Completed
- Dodano strategię TRUMPSOL Contrarian
- Implementacja mean reversion z filtrami vol/atr
- Testy backtestowe: +17.49% z fees

### 🐛 Known Issues
- Brak

### 📝 Next Steps
- Monitorować live performance
- Rozważyć LONG-only version (70% profits)
```

---

## ✅ Definition of Done

Feature jest gotowy, gdy:

- ✅ Działa poprawnie (happy + edge cases)
- ✅ Brak błędów w konsoli
- ✅ UI spójny z resztą aplikacji
- ✅ Kod czysty, bez TODO
- ✅ Typy uzupełnione, brak `any`
- ✅ Testy ręczne zakończone sukcesem
- ✅ Checkpoint utworzony

---

## 🚨 Red Flags

**Zatrzymaj się i zapytaj, jeśli:**
- Utknąłeś na > 30 min
- Masz pomysł „obejścia" trzeciego błędu
- Nie wiesz jak coś powinno działać
- Masz zamiar „tymczasowo" dodać hardkodowane dane

---

## 📖 Remember

**Make it work → Make it right → Make it fast.**

1. Najpierw zrób, żeby działało
2. Potem zadbaj o jakość i bezpieczeństwo
3. Na końcu optymalizuj

**Perfect is the enemy of shipped.**

Nie potrzebujesz perfekcji, tylko działającego systemu.

**✅ Sukces =**
- Funkcja działa i jest stabilna
- Kod jest zrozumiały tydzień później
- Klient widzi efekt
- Ty rozumiesz każdy element

---

**Now go build Fiscal the smart way. 🧠⚡**
Plan → Test → Document → Ship.
