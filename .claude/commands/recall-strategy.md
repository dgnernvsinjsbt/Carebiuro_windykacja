---
description: "Recall a memorized trading strategy by name, R:R ratio, or keyword (e.g., /recall-strategy 8.88 or /recall-strategy short)"
---

Read the trading strategies section from CLAUDE.md (the section titled "BINGX TRADING BOT - FARTCOIN STRATEGIES").

User is looking for: $ARGUMENTS

If $ARGUMENTS is empty, list ALL memorized strategies with their key metrics (R:R, return, direction).

If $ARGUMENTS contains a number (like "8.88" or "7.14"), find the strategy with that R:R ratio.

If $ARGUMENTS contains a keyword (like "short", "long", "trend"), find strategies matching that keyword.

Display the FULL strategy details including:
- All metrics (R:R, Return, Max Drawdown, Direction, Timeframe)
- Complete entry rules
- Complete exit rules (SL/TP)
- Code location and data source files

If the user seems to want to continue working on the strategy, also read the relevant code files mentioned in the strategy.
