# Plans

Pre-implementation deliberation for multi-domain features and significant changes.

## How It Works

1. **A plan is proposed.** Any agent or the human operator writes a plan using `_TEMPLATES/plan.md`. It goes in a dated subdirectory: `docs/plans/YYYY-MM-DD-short-title/plan.md`.

2. **Reviews are filed.** Other agents review the plan using `_TEMPLATES/review.md`. Reviews go in `reviews/` within the same directory.

3. **The human decides.** The human operator writes `decision.md` using `_TEMPLATES/decision.md`. This is the only file that authorizes implementation.

4. **Implementation begins.** Once approved, work proceeds through normal git workflow. The plan directory becomes read-only history.

## Rules

- **Plans are immutable.** Once submitted, the original plan is not edited. If the approach changes substantially, submit a new plan.
- **Reviews are grounded.** Every concern must reference a charter, code path, or cross-cutting concern. No unsubstantiated opinions.
- **Decisions are final.** Once `decision.md` is written, deliberation ends. Implementation begins or the plan is shelved.
- **No plan branching.** If an agent has a fundamentally different approach, they submit a separate `plan-[agent].md` in the same directory — not a branch of the original.

## Directory Structure

```
docs/plans/
  _INDEX.md              # This file
  _TEMPLATES/
    plan.md              # Plan template
    review.md            # Review template
    decision.md          # Decision template
  2026-03-10-grade-forgiveness/
    plan.md              # Original plan
    plan-gemini.md       # Alternative plan (if any)
    reviews/
      claude-review.md
      codex-review.md
    decision.md          # Human's final call
```

## Plans

| Date | Title | Status | Decision |
|------|-------|--------|----------|
| 2026-03-10 | [Per-Session Tool-Use Logging](2026-03-10-session-tool-logging/plan.md) | approved | [decision.md](2026-03-10-session-tool-logging/decision.md) |
| 2026-03-11 | [Memex Architecture Refactor](2026-03-11-memex-architecture-refactor/plan.md) | draft | pending |
