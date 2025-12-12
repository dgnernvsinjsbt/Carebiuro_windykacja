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

## 🏆 ACTIVE STRATEGIES (10-Strategy Portfolio - 1H Candles)

**Portfolio Performance (All 10 Strategies Combined):**
- **Total Return:** +70.92% (90 days)
- **Max Drawdown:** -1.75% (extremely smooth!)
- **Return/DD Ratio:** 40.51x 🏆 EXCEPTIONAL!
- **Win Rate:** 70.8% (472 winners / 667 trades)
- **Profit Factor:** 3.31
- **Method:** Each strategy gets 10% of current equity per trade, multiple positions allowed

| Rank | Strategy | Return/DD | Win Rate | Trades | Status |
|------|----------|-----------|----------|--------|--------|
| 🥇 | **CRV RSI Swing** | 22.03x | 75.8% | 91 | ✅ LIVE |
| 🥈 | **MELANIA RSI Swing** | 21.36x | 69.4% | 98 | ✅ LIVE |
| 🥉 | **AIXBT RSI Swing** | 20.20x | 68.2% | 110 | ✅ LIVE |
| 4 | **TRUMPSOL RSI Swing** | 13.28x | 76.4% | 55 | ✅ LIVE |
| 5 | **UNI RSI Swing** | 12.38x | 75.0% | 84 | ✅ LIVE |
| 6 | **DOGE RSI Swing** | 10.66x | 42.9% | 77 | ✅ LIVE |
| 7 | **XLM RSI Swing** | 9.53x | 67.8% | 115 | ✅ LIVE |
| 8 | **MOODENG RSI Swing** | 8.38x | 74.6% | 118 | ✅ LIVE |
| 9 | **FARTCOIN ATR Limit** | 8.44x | 0.0% | 4 | ✅ LIVE |
| 10 | **PEPE RSI Swing** | 7.13x | 56.9% | 65 | ✅ LIVE |

**Code Location:** `bingx-trading-bot/strategies/`
- All RSI strategies: `{coin}_rsi_swing.py`
- FARTCOIN ATR: `fartcoin_atr_limit.py`

**Key Benefits of Portfolio Approach:**
- Diversification smooths equity curve (winners offset losers)
- 3 losing strategies (DOGE, FARTCOIN, PEPE) carried by 7 winners
- Average 4 concurrent positions spreads risk
- Individual -5% loss = only -0.5% portfolio impact

**1-Minute Strategies (Archived):** `pippin_fresh_crosses.py`, `trumpsol_contrarian.py`

---

## Strategy 1: PIPPIN Fresh Crosses + RSI/Body Filter

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **12.71x** ⭐ BEST! |
| **Return** | +21.76% (7 days BingX) |
| **Max Drawdown** | -1.71% |
| **Win Rate** | 50.0% |
| **TP Rate** | 50.0% |
| **Trades** | 10 |
| **Direction** | LONG + SHORT |
| **Timeframe** | 1-min |
| **Avg Trade Duration** | ~80 bars |

### Entry (ALL conditions must be true)

- EMA(9) crosses EMA(21) (bullish or bearish)
- **Fresh cross only**: `consecutive_ups = 0` (LONG) OR `consecutive_downs = 0` (SHORT)
- **RSI(14) >= 55** (cross has momentum conviction)
- **Body <= 0.06%** (tiny doji-like candle = calm entry, not wild spike)
- Market order (0.05% taker fee)

### Exits

- Stop Loss: **1.5x ATR(14)** from entry
- Take Profit: **10x ATR(14)** from entry (R:R = 6.67:1)
- Max Hold: 120 bars (2 hours)

### Fees

0.10% round-trip (0.05% taker x2)

### Why It Works

- Fresh crosses (`consecutive = 0`) avoid momentum chasers → cleaner reversals
- RSI >= 55 filters weak crosses → only strong conviction signals
- Tiny body (<0.06%) filters wild spikes → calm, decisive entries only
- 10x ATR TP captures PIPPIN's explosive moves when conviction is right
- Data-driven filters based on actual winner/loser analysis (not random)

### Trade-offs

- Very selective (10 trades in 7 days from 64 baseline fresh crosses)
- Lower absolute return vs baseline (+21.76% vs +39.12%)
- But **137.7% better R/DD** (12.71x vs 5.35x)
- Extremely smooth equity curve (-1.71% max DD)

### Data & Code

- **Data**: `trading/pippin_7d_bingx.csv` (11,129 candles, 7 days)
- **Analysis**: `trading/pippin_fresh_crosses_deep_analysis.py`
- **Backtest**: `trading/pippin_fresh_crosses_final_filters.py`
- **Results**: `trading/results/pippin_fresh_crosses_filtered.csv`
- **Bot**: `bingx-trading-bot/strategies/pippin_fresh_crosses.py`

### Development Process

1. Tested 29 configs → Found Fresh Crosses baseline (5.35x R/DD, 64 trades)
2. Analyzed 64 trades → Winners had tiny bodies (0.09% vs 0.21%), higher RSI (53.6 vs 47.4)
3. Tested 10 filters → RSI + Body combo = **12.71x R/DD**, 50% TP rate, 10 trades
4. Result: **137.7% improvement** in risk-adjusted returns vs baseline

---

## Strategy 2: FARTCOIN ATR Expansion (Limit Order)

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **8.44x** ⭐ |
| **Return** | +101.11% (32 days BingX) |
| **Max Drawdown** | -11.98% |
| **Win Rate** | 42.6% |
| **Trades** | 94 |
| **Direction** | LONG + SHORT |
| **Timeframe** | 1-min |
| **Avg Duration** | ~80 bars (1.3 hours) |

### Entry (ALL conditions must be true)

1. **ATR Expansion**: Current ATR(14) > 1.5x rolling 20-bar average (volatility breakout)
2. **EMA Distance Filter**: Price within 3% of EMA(20) (prevents late entries)
3. **Directional Candle**: Bullish (close > open) for LONG, Bearish for SHORT
4. **LIMIT ORDER**:
   - LONG: Place limit 1% ABOVE signal price
   - SHORT: Place limit 1% BELOW signal price
   - Wait max 3 bars for fill (filters fake breakouts)

### Exits

- **Stop Loss**: 2.0x ATR(14) from limit fill price
- **Take Profit**: 8.0x ATR(14) from limit fill price (R:R = 4:1)
- **Max Hold**: 200 bars (3.3 hours) if neither SL/TP hit

### Fees

0.10% round-trip (conservative estimate: market fills)

### Why It Works

- ATR expansion catches beginning of explosive pump/dump moves
- Limit order 1% away filters fake breakouts (only 21% of signals fill)
- EMA distance prevents overextended entries
- 8x ATR target captures full pump moves (avg winner: 4.97%)
- Tight 2x ATR stop limits downside

### Trade-offs

- High selectivity (94 trades from 444 signals = 21% fill rate)
- Lower absolute return vs market orders but 40% better Return/DD
- Requires patience - most signals won't fill

### Data & Code

- **Data**: `trading/fartcoin_30d_bingx.csv` (46,080 candles, 32 days)
- **Backtest**: `trading/fartcoin_limit_tp6x_test.py`
- **Results**: `trading/results/fartcoin_limit_order_test.csv`
- **Bot**: `bingx-trading-bot/strategies/fartcoin_atr_limit.py`

### Development Process

- Phase 1: Tested 7 entry concepts → ATR Expansion won (11.71% Top10 avg)
- Phase 2: Added filters → EMA Distance 3% improved Return/DD to 6.00x
- Phase 3: Limit orders → 1% offset + 3 bar wait → 8.44x Return/DD (final)

---

## Strategy 3: TRUMPSOL Contrarian (Mean Reversion) 🆕

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **5.17x** (with 0.1% fees) |
| **Return** | +17.49% (32 days BingX) |
| **Max Drawdown** | -3.38% |
| **Win Rate** | **68.8%** ⭐ (highest!) |
| **Trades** | 77 |
| **Direction** | LONG + SHORT |
| **Timeframe** | 1-min |
| **Avg Duration** | 12.3 minutes |

### Strategy Concept

**Fade violent moves with volume/volatility confirmation**

Buy panic, short euphoria. Entry on extreme 5-minute moves when volume and volatility confirm.

### Entry Conditions (ALL must be true - CONTRARIAN)

1. **Momentum Filter**: `abs(ret_5m) >= 1.0%` (pump or dump in 5 minutes)
2. **Volume Filter**: `volume_ratio >= 1.0` (current volume >= 30-min average)
3. **Volatility Filter**: `atr_ratio >= 1.1` (current ATR >= 110% of 30-min average)
4. **Time Filter**: `hour NOT IN {1, 5, 17}` (Europe/Warsaw timezone exclusions)

**Direction (CONTRARIAN):**
- **Pump (+1%)** → **SHORT** (fade down)
- **Dump (-1%)** → **LONG** (fade up)

### Exits

- **Stop Loss**: 1% from entry (fixed %)
- **Take Profit**: 1.5% from entry (fixed %)
- **Time Exit**: 15 bars (15 minutes) max hold

### Fees

0.10% per trade (0.05% taker x2)

### Why It Works

1. **Mean reversion** - extreme moves revert in meme coins
2. **High quality signals** - volume 3.4x + volatility 1.6x avg = real moves
3. **74% trades = time exit** - most profits from small reversals in 15 min
4. **LONG >> SHORT** - buying panic (+13.94%) better than shorting euphoria (+2.41%)
5. **High win rate** - 68.8% psychologically easy to trade

### Key Characteristics

- **Very selective**: 2.4 trades/day average
- **Best trades**: Extreme dumps (ret_5m < -3%) with vol > 5x → instant reversals
- **Worst trades**: SHORT at local tops → momentum continues
- **74% time exits**: Most trades held full 15 minutes for small gains

### Data & Code

- **Data**: `trading/trumpsol_30d_bingx.csv` (46,080 candles, 32 days)
- **Backtest**: `trading/trumpsol_contrarian_verify.py`
- **Results**: `trading/results/trumpsol_contrarian_trades.csv`
- **Report**: `trading/results/TRUMPSOL_CONTRARIAN_REPORT.md`
- **Bot**: `bingx-trading-bot/strategies/trumpsol_contrarian.py`

### Configuration

```python
{
    'min_ret_5m_pct': 1.0,        # Min 1% move in 5 minutes
    'vol_ratio_min': 1.0,         # Volume >= 30-min avg
    'atr_ratio_min': 1.1,         # ATR >= 110% of 30-min avg
    'excluded_hours': [1, 5, 17], # Europe/Warsaw time filter
    'stop_loss_pct': 1.0,         # 1% SL
    'take_profit_pct': 1.5,       # 1.5% TP
    'max_hold_bars': 15,          # 15 min max
    'vol_ma_period': 30,          # 30-bar volume MA
    'atr_ma_period': 30           # 30-bar ATR MA
}
```

### TL;DR

**One-liner:** Buy panic, sell euphoria when volume + volatility explode. 15-min mean reversion scalp.

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
