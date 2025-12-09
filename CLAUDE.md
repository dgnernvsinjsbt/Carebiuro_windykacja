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

## 🏆 ACTIVE STRATEGIES (3 Total)

| Rank | Strategy | Return/DD | Return | Max DD | Trades | Token | Status |
|------|----------|-----------|--------|--------|--------|-------|--------|
| 🥇 | **FARTCOIN ATR Limit** | **8.44x** | **+101.11%** | -11.98% | 94 | FARTCOIN | ✅ LIVE |
| 🥈 | **DOGE Volume Zones** ⚠️ | **10.75x** | **+5.15%** | -0.48% | 22 | DOGE | ✅ LIVE |
| 🥉 | **TRUMPSOL Contrarian** 🆕 | **5.17x** | **+17.49%** | -3.38% | 77 | TRUMPSOL | ✅ LIVE |

**Legend:**
- ⚠️ = Outlier-dependent (requires discipline to take all signals)
- 🆕 = New strategy (Dec 2025)
- ✅ = Active in production

**Code Location:** `bingx-trading-bot/strategies/`
- `fartcoin_atr_limit.py`
- `doge_volume_zones.py`
- `trumpsol_contrarian.py`

**Archived Strategies:** See [ARCHIVUM_STRATEGII.md](ARCHIVUM_STRATEGII.md) for MOODENG, PEPE, TRUMP, UNI, ETH, PENGU strategies.

---

## Strategy 1: FARTCOIN ATR Expansion (Limit Order)

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

## Strategy 2: DOGE Volume Zones (BingX Optimized - Outlier Harvester)

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **10.75x** ⭐ |
| **Return** | +5.15% (32 days BingX) |
| **Max Drawdown** | **-0.48%** (shallowest!) |
| **Win Rate** | 63.6% |
| **Trades** | 22 |
| **Actual R:R** | 4.0x ATR TP / 1.5x ATR SL |
| **Direction** | LONG + SHORT |
| **Timeframe** | 1-min |
| **⚠️ Outlier Dependency** | **95.3%** from top 5 trades |

### Entry - Accumulation Zones (LONG)

- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local low (20-bar lookback)
- Enter **Asia/EU session (07:00-14:00 UTC) ONLY** ⚠️
- Market order (0.05% taker fee)

### Entry - Distribution Zones (SHORT)

- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local high (20-bar lookback)
- Enter **Asia/EU session (07:00-14:00 UTC) ONLY** ⚠️
- Market order (0.05% taker fee)

### Exits

- **Stop Loss**: 1.5x ATR(14) (tighter for lower volatility session)
- **Take Profit**: 4.0x ATR (absolute ATR target, not R:R)
- **Max Hold**: 90 bars (90 minutes)

### Fees

0.10% per trade (0.05% taker x2)

### Why It Works (But Differently)

- **CRITICAL:** This is an outlier-harvesting strategy like TRUMP Volume Zones
- Top 5 trades = 95.3% of all profits (remaining 17 = +0.24%)
- Must take EVERY signal - cannot cherry-pick
- Asia/EU session has cleaner volume zone follow-through on BingX
- ATR-based TP (4.0x) captures explosive moves better than R:R
- LONGs contribute 88.5% of profits (keep SHORTs for 11.5%)

### Session Analysis (BingX vs LBank)

| Exchange | Session | Return/DD | Notes |
|----------|---------|-----------|-------|
| **BingX** | **Asia/EU (07-14)** | **10.75x** | ⭐ OPTIMAL |
| BingX | Overnight (21-07) | 1.08x | Fails on BingX |
| LBank | Overnight (21-07) | 7.15x | Optimal on LBank |

**⚠️ Exchange-Specific Behavior:** Parameters don't transfer between exchanges!

### Configuration (BingX Optimized)

```python
{
    'volume_threshold': 1.5,      # 1.5x average volume
    'min_zone_bars': 5,           # 5+ consecutive bars
    'sl_type': 'atr',
    'sl_value': 1.5,              # 1.5x ATR stop (tighter)
    'tp_type': 'atr_multiple',    # ATR-based (not R:R!)
    'tp_value': 4.0,              # 4.0x ATR target
    'session': 'asia_eu',         # 07:00-14:00 UTC ONLY
    'max_hold_bars': 90           # 90 minute max hold
}
```

### Data & Code

- **Data**: `trading/doge_30d_bingx.csv` (46,080 candles, 32 days)
- **Optimizer**: `trading/doge_bingx_comprehensive_optimizer.py` (567 configs tested)
- **Report**: `trading/strategies/DOGE_BINGX_VOLUME_ZONES_FINAL.md`
- **Trades**: `trading/results/doge_bingx_optimized_trades.csv` (22 trades)
- **Bot**: `bingx-trading-bot/strategies/doge_volume_zones.py`

### Key Discovery

- Comprehensive re-optimization with ATR-based TP + relaxed filters
- NO configuration with Return/DD > 5.0x has Top5 < 80% (fundamental to DOGE)
- Strategy works by catching 3-5 explosive moves per month
- Remaining trades tread water (+0.24% from 17 trades)

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
