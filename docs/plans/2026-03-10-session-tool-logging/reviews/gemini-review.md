# Review: Per-Session Tool-Use Logging

**Reviewer:** Gemini CLI
**Date:** 2026-03-10
**Plans reviewed:** `plan.md` (Claude), `plan-codex.md` (Codex)

---

## Verdict

**consensus-reached-with-refinements**

## Summary

This review synthesizes the feedback on both initial proposals. Claude's original plan correctly identified the need for hooks and real-time capture but suffered from a Claude-centric tool model and a bash/`jq` implementation that would be fragile on Windows and duplicate classification logic. Codex's alternative correctly identified the need for a backend-neutral schema, Python-based loggers, and the inclusion of failures and delegation as mandatory forensic events.

The deliberation has successfully converged on a hybrid approach:
1.  **Shared Python-based classifier** to prevent logic drift.
2.  **Phased rollout** to manage architectural complexity.
3.  **Mandatory failure/delegation tracking** for forensic completeness.

I fully endorse this converged path and have codified it in `plan-gemini.md`.

## Section-by-Section Analysis

### Problem Statement
- [x] Agree with framing
- Comments: The core issue is that post-hoc transcript parsing is noisy and token-heavy for analysis. Purpose-built, lightweight event logs are the correct solution.

### Scope
- [x] Scope is appropriate
- Comments: The shift from "Claude-only" to "shared agent-local logs" is a critical improvement. This allows for forensic analysis across the entire team (Claude, Codex, Gemini) using a unified schema.

### Affected Domains
- [x] Charter references are correct
- Comments: The impact on `infrastructure.md` and `cross_cutting.md` (classification) is properly identified.

### Proposed Approach
- [x] Steps are in the right order
- [x] Approach is the simplest that works
- Comments: The convergence on a Python-based hook for Claude is a major win for portability and maintainability on this codebase. The Codex extraction path is a pragmatic "first implementation" that avoids unproven interception wrappers.

### Risk Assessment
- [x] Risks are realistic
- Comments: Path normalization (Windows vs POSIX) remains the most likely operational hurdle; using `pathlib` in all new Python modules is a necessary mitigation.

### Testing Strategy
- [x] Covers the critical paths
- Comments: Parity testing (transcript vs log) is the definitive way to prove the new system's accuracy.

## Charter Verification

| Charter | Contradiction or Concern |
|---------|------------------------|
| `infrastructure.md` | No direct contradiction. The addition of logging hooks is a standard infrastructure expansion. |
| `cross_cutting.md` | No direct contradiction. The focus on classification consistency directly supports the governance goals defined here. |

## Final Recommendations

1.  **Implement `scripts/classify.py` first.** This is the bedrock of the entire system.
2.  **Standardize the `session_id`.** To ensure logs from different agents (e.g., Claude calling a sub-agent) can be correlated, we should investigate if a project-root `SESSION_ID` environment variable can be used.
3.  **Adopt the unified schema immediately.** Do not wait for a "Phase 2" to define the schema; start with the neutral, failure-inclusive schema from the first log entry.
