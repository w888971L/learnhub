# Plan: [TITLE]

**Author:** [agent name or human]
**Date:** [YYYY-MM-DD]
**Status:** draft | under-review | approved | rejected | superseded

---

## Original Request

> Paste or paraphrase the human operator's original request here, as-is. Capture the intent before it gets refined.

## Problem Statement

What needs to change and why. One paragraph max. Link to an issue or conversation if relevant.

## Scope

What this plan covers and, just as importantly, what it does NOT cover.

| In scope | Out of scope |
|----------|-------------|
| ... | ... |

## Affected Domains

Which domains are touched by this change. Reference charters where they exist.

| Domain | Charter | Impact |
|--------|---------|--------|
| e.g. Grading | `models_assignments.md` | Modifies `Grade` model |
| e.g. Analytics | `infrastructure.md` | Cache invalidation changes |

## Cross-Cutting Concerns

Which tripwires or cascading effects are relevant. If none, say "None identified" and explain why.

- [ ] Grade Cache Duality
- [ ] Late Penalty Timing
- [ ] Grade Cascade
- [ ] Enrollment State Machine
- [ ] Other: ...

For each checked item, explain how the plan accounts for it.

## Proposed Approach

Step-by-step implementation plan. Be specific about which files change and how.

### Step 1: ...

### Step 2: ...

### Step 3: ...

## Data Model Changes

Any new models, fields, or migrations. If none, write "None."

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ... | low/med/high | low/med/high | ... |

## Testing Strategy

How will you verify this works? What edge cases matter?

## Open Questions

Anything unresolved that needs human input before implementation.
