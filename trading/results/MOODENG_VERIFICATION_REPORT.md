# MOODENG BINGX DATA VERIFICATION REPORT

**Date**: 2025-12-09 16:17:49
**Data File**: trading/moodeng_30d_bingx.csv
**Total Candles**: 46,080
**Date Range**: 2025-11-07 14:40:00 to 2025-12-09 14:39:00

## Verification Results

### DATA GAPS: PASS ✅

- **gaps_count**: 0
- **total_missing_minutes**: 0
- **largest_gap_minutes**: 0

### DUPLICATES: PASS ✅

- **duplicate_count**: 0

### OUTLIERS: FAIL/WARNING ⚠️

- **body_outliers**: 11
- **range_outliers**: 9
- **volume_outliers**: 47
- **max_body_pct**: 53.09573858207529
- **max_range_pct**: 125.7391304347826

### CONCENTRATION: FAIL/WARNING ⚠️

- **trades**: 127
- **total_pnl**: 18.7753694546389
- **top_20_concentration**: 361.18810838126853
- **best_trade_contrib**: 56.46809915752791
- **max_loss_streak**: 97
- **winner_cv**: 0.8597332764153243

### TIME CONSISTENCY: PASS ✅

- **is_sorted**: True
- **backwards_jumps**: 0
- **missing_hours**: 0
- **min_candles_per_day**: 560
- **max_candles_per_day**: 1440


## Conclusion

Some checks raised warnings. Review the detailed results above before proceeding with optimization.