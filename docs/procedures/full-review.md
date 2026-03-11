# Procedure: Full Charter Review

*Periodic accuracy audit of all charters against the codebase. The most thorough verification practice.*

**Invocation**: `/review-charters` (or manual dispatch)

---

## What This Checks

For each charter, verify:
- Line number anchors (within ~20 lines?)
- Function signatures (exist? correct?)
- Behavioral descriptions (still accurate?)
- Model access patterns (R/W/RW correct?)
- Missing entries (public functions not in charter?)
- Stale entries (charter mentions things that no longer exist?)
- Cross-references (point to valid charters?)

## Process

**1. Create a scratchpad** at `docs/architecture/review_scratchpad.md` — tracking table for intermediate results.

**2. Dispatch parallel subagents** in batches of 2-3. Each subagent reviews related charters against source code.

**3. Write findings to scratchpad** as each subagent completes. This preserves detail that would otherwise be lost to context compression.

**4. Synthesize** — read scratchpad, prioritize fixes (functional errors > stale line numbers > missing entries > cosmetic).

**5. Fix and update** — edit charters, update "Last verified" dates.

**6. Close out the scratchpad** — after all fixes land, truncate the scratchpad to a dated one-line summary (e.g., "2026-03-08: Full review complete. 9 charters reviewed, 76+ issues found and fixed. See git history for details."). The full review detail lives in git history, not in the working tree. A stale scratchpad with resolved findings is a governance hazard — future agents may mistake historical issues for current drift.

## Grouping Heuristic

Batch by data proximity:
- Model charters together (they share `core/models.py`)
- Tightly-coupled view charters together
- Infrastructure and cross-cutting alone

## Why Subagents

Each subagent gets a fresh context window focused on its charter subset. The scratchpad acts as externalized memory — surviving context compression in the main agent.

## Frequency

Monthly or quarterly. After major refactors.

## Cost

~$0.50-1.00 per full review (depends on charter count and codebase size).
