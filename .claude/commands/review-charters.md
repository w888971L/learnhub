Run a full charter review — audit all charters against the codebase for accuracy.

Read the procedure doc at `docs/procedures/full-review.md` for the full process, grouping heuristic, and subagent configuration.

Steps:
1. Create scratchpad at `docs/architecture/review_scratchpad.md`
2. Dispatch parallel subagents in batches of 2-3 related charters
3. Each subagent checks: line numbers, signatures, behaviors, access patterns, missing/stale entries
4. Write findings to scratchpad
5. Synthesize and prioritize fixes
6. Edit charters and update "Last verified" dates
