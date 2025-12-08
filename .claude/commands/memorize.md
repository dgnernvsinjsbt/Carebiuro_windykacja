---
name: memorize
description: Save currently discussed trading strategy to CLAUDE.md with all metrics, config, and analysis data for quick recall
argument-hint: [token-name] (optional - inferred from context if omitted)
---

<objective>
Document the trading strategy from the current conversation into CLAUDE.md for permanent reference and quick recall.

This creates a complete strategy entry with:
- Performance metrics (Return, Max DD, Win Rate, R:R, Return/DD ratio)
- Entry/exit rules with all conditions and filters
- Configuration parameters (code block format)
- Why it works (market edge explanation)
- Trading requirements and psychological considerations
- Key discoveries and failed approach comparisons
- Links to all code files, data files, and analysis results

$ARGUMENTS specifies the token/strategy name (e.g., "TRUMP", "MOODENG"). If omitted, Claude infers from conversation context.
</objective>

<context>
Current documentation: @CLAUDE.md
</context>

<process>
1. **Extract strategy details from current conversation**:
   - Token/strategy name (from $ARGUMENTS or infer from discussion)
   - All performance metrics:
     * Return/DD ratio (PRIMARY METRIC - determines ranking)
     * Return percentage
     * Max Drawdown percentage
     * Win Rate
     * Number of trades
     * Actual R:R ratio
   - Entry conditions (ALL filters, thresholds, session filters)
   - Exit conditions (SL, TP, time exits, max hold bars)
   - Fees structure
   - Configuration parameters (volume thresholds, ATR multipliers, etc.)
   - Why It Works section (market edge, validation)
   - Trading Requirements (discipline, psychological factors)
   - Special considerations (outlier dependency, consistency metrics)
   - File references:
     * Data file path (CSV with candle data)
     * Code files (backtest, optimization, analysis scripts)
     * Result files (trade logs, summary CSVs)

2. **Determine insertion point and strategy number**:
   - Count existing strategies (Strategy 1, Strategy 2, etc.)
   - If updating existing strategy: Keep same number, update content
   - If new strategy: Assign next number in sequence
   - Place before "UNTRADEABLE" or "FAILED APPROACHES" sections

3. **Format strategy documentation following exact CLAUDE.md structure**:
   ```markdown
   ## Strategy N: [TOKEN] [STRATEGY_NAME] [⚠️ if outlier-dependent]
   | Metric | Value |
   |--------|-------|
   | **Return/DD Ratio** | **X.XXx** |
   | **Return** | +X.XX% (30 days) |
   | **Max Drawdown** | -X.XX% |
   | **Win Rate** | XX.X% |
   | **Trades** | NN |
   | **Actual R:R** | X.XX:1 |
   | Direction | LONG/SHORT/BOTH |
   | Timeframe | 1-min |

   **Entry (...):**
   - Condition 1
   - Condition 2

   **Exits:**
   - Stop Loss: ...
   - Take Profit: ...

   **Fees:** 0.10% per trade (...)

   **Why It Works:**
   - Explanation

   **Configuration:**
   ```python
   {
       'param': value,
   }
   ```

   **Data File:** `path/to/file.csv`
   **Code:**
   - `path/to/script.py`
   **Analysis:**
   - `path/to/analysis.py`
   ```

4. **Update Quick Reference Table**:
   - Extract all strategies with Return/DD ratios
   - Sort by Return/DD ratio (descending)
   - Assign ranks: 🥇 (1st), 🥈 (2nd), 🥉 (3rd), numbers for rest
   - Add ⚠️ icon if outlier-dependent (concentration >80%)
   - Regenerate entire table with correct rankings

5. **Write updated CLAUDE.md**:
   - Preserve all existing strategies
   - Insert/update new strategy section
   - Update Quick Reference Table rankings
   - Maintain exact formatting and structure

</process>

<output>
- `CLAUDE.md` - Updated with new/modified strategy section and re-ranked Quick Reference Table
</output>

<verification>
Before completing, verify:
- Strategy section has all required components:
  * Metrics table with Return/DD as first row (bold)
  * Entry conditions (all filters documented)
  * Exit conditions (SL/TP/time exits)
  * Configuration code block (valid Python dict syntax)
  * File references (valid paths)
- Quick Reference Table:
  * Sorted correctly by Return/DD ratio (highest first)
  * Ranks assigned correctly (🥇🥈🥉 for top 3)
  * ⚠️ icon present if strategy is outlier-dependent
  * All columns populated (Return/DD, Return, Max DD, R:R, Token)
- Markdown formatting:
  * Tables aligned properly
  * Code blocks have correct syntax highlighting
  * All links use relative paths from project root
- No duplicate strategy sections
- Existing strategies preserved unchanged
</verification>

<success_criteria>
- Strategy fully documented with all performance metrics
- Quick Reference Table updated and correctly ranked by Return/DD
- All file references point to actual files in the project
- Documentation format matches existing strategies exactly
- Strategy can be recalled instantly by reading CLAUDE.md
- No information lost from conversation (metrics, config, insights)
</success_criteria>