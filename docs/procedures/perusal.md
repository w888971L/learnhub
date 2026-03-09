# Procedure: Informed Perusal

*Walk through a small pocket of code with architectural context loaded, looking for mismatches between intent and reality.*

**Invocation**: `/peruse <file-or-domain>` (e.g., `/peruse core/utils/grading.py`, `/peruse assignments`)

---

## What This Finds

| Tool | Question | Finds |
|------|----------|-------|
| **Enforcer** (independent agent) | Did this diff break the docs? | Staleness from recent changes |
| **Full review** | Does the charter match the code? | Authoring errors, stale anchors |
| **Perusal** | Does the code match the architectural intent? | Drift, misplacement, creep, inconsistency |

Perusal catches **architectural drift** — the slow process by which code migrates away from its intended design one reasonable commit at a time.

## What to Look For

1. **Responsibility creep** — a view doing business logic that belongs in a utility
2. **Pattern inconsistency** — five endpoints validate one way, a sixth does it differently
3. **Vestigial code** — commented blocks, unused imports, dead feature flags
4. **Undocumented patterns** — behavior the charter doesn't mention
5. **Misplaced responsibilities** — code that works but lives in the wrong module

## Agent Configuration

Dispatch a Haiku agent (cheapest, fast, sufficient for pattern recognition):

```
You are performing an informed perusal of [FILE/DOMAIN].

Context loaded:
- Charter: [relevant charter]
- Cross-cutting concerns: cross_cutting.md

Read the source file(s). For each function or class, ask:
"Given what the charter says this domain should look like, does this code belong?"

Report:
- Findings (drift, misplacement, undocumented patterns, vestigial code)
- For each finding: file, line, what you found, why it matters
- "No issues found" is a valid result

Do NOT check charter accuracy (that's a full review).
Do NOT look for bugs (that's testing).
Look for architectural fit.
```

## Frequency

Weekly, one file at a time. Spaced over days/weeks for fresh eyes. Not a marathon — a practice.

## Cost

~$0.005 per perusal (Haiku). The cheapest practice in the toolkit.
