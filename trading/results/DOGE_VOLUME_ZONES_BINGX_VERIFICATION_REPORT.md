
================================================================================
DATA CORRUPTION DETECTION REPORT
================================================================================
Total Trades: 32
Winners: 13 | Losers: 19
Total P&L: 2.12%

WINNER DISTRIBUTION:
  Median winner: +0.785%
  Max winner:    +1.731%
  Best trade is: 2.2x the median winner
  Std dev:       0.446%

MARKET CONTEXT:
  Median ATR:    0.11% per candle

CORRUPTION ANALYSIS:
  Trades > 10x median winner: 0
  P&L without suspicious trades: +2.12%

✅ NO SUSPICIOUS TRADES FOUND

Winner distribution appears normal:
- No trades >10x median winner
- P&L comes from consistent edge, not outliers

✅ DATA INTEGRITY VERIFIED


================================================================================
TRADE CALCULATION VERIFICATION
================================================================================
Trades Sampled: 5
Issues Found: 0

SAMPLE VERIFICATION RESULTS:
   trade_idx  entry_price  exit_price  claimed_pnl  expected_pnl  pnl_match
0         26      0.14985    0.150297    -0.003975     -0.003975       True
1          5      0.16245    0.164256     0.010116      0.010116       True
2         12      0.14286    0.141234    -0.012380     -0.012380       True
3         11      0.16080    0.160499    -0.002875     -0.002875       True
4          8      0.15554    0.156734     0.006678      0.006678       True

✅ ALL SAMPLED TRADES VERIFIED CORRECTLY


================================================================================
OUTLIER TRADE INVESTIGATION
================================================================================
Threshold: Trades contributing >5.0% of total profit
Outliers Found: 12
Total Profit: 2.12%

OUTLIER DETAILS:

--------------------------------------------------------------------------------
Trade at 2025-11-12 02:36:00
  Entry: 0.171030 → Exit: 0.171976
  P&L: +0.453% | Contribution: 21.4% of total profit
  Move: 0.55%
  ⚠️  SUSPICIOUS: Single trade = 21.4% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-14 04:43:00
  Entry: 0.161650 → Exit: 0.163350
  P&L: +0.952% | Contribution: 44.9% of total profit
  Move: 1.05%
  ⚠️  SUSPICIOUS: Single trade = 44.9% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-14 06:52:00
  Entry: 0.162450 → Exit: 0.164256
  P&L: +1.012% | Contribution: 47.7% of total profit
  Move: 1.11%
  ⚠️  SUSPICIOUS: Single trade = 47.7% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-14 23:08:00
  Entry: 0.155260 → Exit: 0.158103
  P&L: +1.731% | Contribution: 81.6% of total profit
  Move: 1.83%
  ⚠️  SUSPICIOUS: Single trade = 81.6% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-16 21:12:00
  Entry: 0.155540 → Exit: 0.156734
  P&L: +0.668% | Contribution: 31.5% of total profit
  Move: 0.77%
  ⚠️  SUSPICIOUS: Single trade = 31.5% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-18 03:05:00
  Entry: 0.151730 → Exit: 0.153647
  P&L: +1.164% | Contribution: 54.8% of total profit
  Move: 1.26%
  ⚠️  SUSPICIOUS: Single trade = 54.8% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-09 23:06:00
  Entry: 0.180350 → Exit: 0.178767
  P&L: +0.785% | Contribution: 37.0% of total profit
  Move: 0.88%
  ⚠️  SUSPICIOUS: Single trade = 37.0% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-11 01:21:00
  Entry: 0.185330 → Exit: 0.182833
  P&L: +1.266% | Contribution: 59.7% of total profit
  Move: 1.35%
  ⚠️  SUSPICIOUS: Single trade = 59.7% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-22 22:56:00
  Entry: 0.141580 → Exit: 0.140246
  P&L: +0.851% | Contribution: 40.1% of total profit
  Move: 0.94%
  ⚠️  SUSPICIOUS: Single trade = 40.1% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-11-23 04:24:00
  Entry: 0.143820 → Exit: 0.142903
  P&L: +0.542% | Contribution: 25.5% of total profit
  Move: 0.64%
  ⚠️  SUSPICIOUS: Single trade = 25.5% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-12-03 22:02:00
  Entry: 0.152270 → Exit: 0.151436
  P&L: +0.451% | Contribution: 21.3% of total profit
  Move: 0.55%
  ⚠️  SUSPICIOUS: Single trade = 21.3% of ALL profits

--------------------------------------------------------------------------------
Trade at 2025-12-06 03:10:00
  Entry: 0.140040 → Exit: 0.139523
  P&L: +0.271% | Contribution: 12.8% of total profit
  Move: 0.37%
  ✅ Trade appears legitimate

================================================================================
🚨 ACTION REQUIRED:
11 suspicious outlier trade(s) detected.

For each suspicious trade:
1. Check raw price data around that timestamp
2. Look for news/events that day
3. Verify the move actually happened on exchange

DO NOT GO LIVE until outliers are investigated!
================================================================================


================================================================================
TIME PERIOD CONSISTENCY CHECK
================================================================================
Total Trades: 32
Total Profit: 2.12%
Date Range: 2025-11-07 to 2025-12-09

WEEKLY DISTRIBUTION:
           sum  count  pct_of_total
week                               
45    0.003969      2     18.706172
46    0.049008     10    231.002077
47    0.003480      7     16.404612
48   -0.006721      2    -31.677470
49   -0.025227     10   -118.908280
50   -0.003294      1    -15.527112

Profitable Weeks: 3/6 (50%)
Max Week Contribution: 231.0%

DAY OF WEEK DISTRIBUTION:
                  sum  count  pct_of_total
day_of_week                               
Friday       0.033057      4    155.813523
Monday      -0.015931      2    -75.091548
Saturday    -0.000125      5     -0.590159
Sunday       0.018855      5     88.875271
Thursday    -0.008292      2    -39.083140
Tuesday      0.001773      8      8.355406
Wednesday   -0.008121      6    -38.279353

Max Day Contribution: Friday = 155.8%

HOURLY DISTRIBUTION (Top 5):
           sum  count  pct_of_total
hour                               
23    0.021279      3    100.298734
4     0.011640      3     54.867027
3     0.008646      4     40.751468
6     0.005426      2     25.573243
1     0.004366      3     20.580983

Max Hour Contribution: 23:00 UTC = 100.3%

============================================================
⚠️  RED FLAGS:
  🚨 Single week = 231.0% of profit
  ⚠️  Friday = 155.8% of profit
  ⚠️  Hour 23:00 UTC = 100.3% of profit

🛑 Profits may be concentrated in specific time periods!


################################################################################
                        VERIFICATION SUMMARY
################################################################################

| Check                    | Status |
|--------------------------|--------|
| Data Corruption          | ✅ PASS |
| Trade Calculations       | ✅ PASS |
| Outlier Investigation    | ❌ FAIL |
| Time Consistency         | ❌ FAIL |
|--------------------------|--------|
| OVERALL                  | ❌ CHECKS FAILED |

================================================================================
BASELINE STRATEGY PERFORMANCE ON BINGX DATA
================================================================================
Total Trades: 32
Total Return: +2.12%
Max Drawdown: -1.97%
Return/DD Ratio: 1.08x
Win Rate: 40.6%

COMPARISON TO LBANK BASELINE:
- Return: +2.12% vs +8.14% (-6.02% difference)
- Return/DD: 1.08x vs 7.15x (-6.07x difference)

================================================================================
