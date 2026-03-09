# Procedure: Enforce

*Verify that charter changes have been propagated to public record flow docs. Must be run by an independent agent.*

**Invocation**: `/enforce` (or manual dispatch by independent agent)

---

## Independence Requirement

! This procedure MUST be run by a **different model entirely** than the one that made the changes. A model cannot enforce its own work — even across separate sessions, the same model carries the same biases and blind spots that produced the errors.

Recommended configurations:
- **Most common**: Primary agent is Claude Opus → enforcer calls Claude Sonnet via the Anthropic API. Inexpensive (~$0.05-0.10/run) and fast. Requires `ANTHROPIC_API_KEY` in environment variables.
- Primary agent is Claude → enforcer is Gemini or another non-Anthropic model
- Automated: hook triggers enforcer using a different model on commit

A different session of the same model does **not** qualify. The point is a genuinely different lens.

The enforcer has **read-only authority** by default. It reports findings. The human or primary agent decides whether to act on them.

---

## What This Checks

For each charter that has been modified (since last enforcement):
1. Look up dependent flow docs in `docs/architecture/propagation_map.md`
2. For each dependent flow doc, check whether claims in the flow doc are still consistent with the charter
3. Report stale claims, missing updates, and contradictions

## Process

**1. Identify changed charters**

Compare `Last verified` dates on charters, or use `git diff` to find recently modified charters:
```
git diff --name-only <since> -- docs/architecture/modules/
```

**2. Load propagation map**

Read `docs/architecture/propagation_map.md` to find dependent flow docs.

**3. For each charter → flow doc pair, dispatch a subagent**

```
You are an enforcer agent verifying propagation from [CHARTER] to [FLOW DOC].

Read both files. For each claim in the flow doc that relates to the charter's domain:
- Is the claim still accurate given the current charter?
- Are there charter changes that should be reflected in the flow doc but aren't?

Report:
- STALE: claim in flow doc contradicts current charter
- MISSING: charter documents something the flow doc should mention but doesn't
- OK: no issues found

You are NOT the agent that made the changes. Your job is independent verification.
```

**4. Compile findings**

Aggregate subagent reports. Prioritize:
1. STALE (active misinformation) — must fix
2. MISSING (incomplete but not wrong) — should fix
3. OK — no action needed

**5. Report to human**

Present findings. Do not auto-fix — the human or primary agent decides how to update the flow docs.

## Frequency

- After every charter review (`/review-charters`)
- After significant code changes that touch multiple charters
- On demand when suspicious of drift

## Cost

~$0.05-0.10 per enforcement run (depends on number of charter-flow pairs to check).
