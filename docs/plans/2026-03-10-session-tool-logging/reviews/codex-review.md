# Review: Per-Session Tool-Use Logging

**Reviewer:** Codex
**Date:** 2026-03-10
**Plan reviewed:** `plan.md`

---

## Verdict

**alternative-proposed**

## Summary

The plan is directionally strong for Claude Code itself: real-time, per-session, purpose-built tool logs are a better forensic substrate than transcript-only analysis. The main issue is that the proposed shared contract is too Claude-native to serve cleanly across Claude, Codex, and Gemini. I support the goal, but I recommend the alternative approach in `plan-codex.md`: shared schema at the event level, shared Python classification logic, Claude hook capture as one backend, and Codex transcript extraction as the initial Codex implementation path.

## Section-by-Section

### Problem Statement
- [x] Agree with framing
- Comments: The core framing is correct. Transcript parsing is useful but noisy, and lightweight per-session logs are the right direction for forensic questions like "which charters were hit?" and "what failed during the session?"

### Scope
- [ ] Scope is appropriate (not too broad, not too narrow)
- Comments: Scope is appropriate for Claude Code, but slightly under-specifies the cross-agent requirement implied by the original request. The plan says Codex/Gemini are out of scope while also defining a cross-team "shared contract." That contract needs to be designed with non-Claude tool models in mind up front.

### Affected Domains
- [ ] All affected domains identified
- [x] Charter references are correct
- Missing domains: Agent-local operational config is implicated more concretely than the plan states. The repo currently has `.claude/settings.local.json`, not `.claude/settings.json`, so the implementation target is ambiguous for this codebase.

### Cross-Cutting Concerns
- [ ] All relevant tripwires identified
- [ ] Mitigations are adequate
- Missed concerns: The plan correctly identifies governance-classification consistency, but it misses forensic completeness of failure paths and delegation events. A tool-use log that records only successful calls is incomplete for operational review.

### Proposed Approach
- [ ] Steps are in the right order
- [ ] No missing steps
- [ ] Approach is the simplest that works
- Concerns: The hook idea is good, but the bash + `jq` implementation is the wrong abstraction if shared Python classification is also required. That creates duplicate logic or an awkward boundary. The proposed shared schema is also too Claude-shaped: single `file_path`, Claude-native tool names, and `tool_use_id` do not map cleanly to Codex's `shell_command` and multi-file `apply_patch` events. Finally, the Codex callout is too speculative; extraction from existing `.codex/sessions` files is a lower-risk initial path than wrappers.

### Data Model Changes
- [x] Migration strategy is sound
- [x] No unnecessary schema changes
- Concerns: None. This is correctly scoped as infrastructure-only.

### Risk Assessment
- [ ] Risks are realistic (not understated)
- [ ] Mitigations are actionable
- Additional risks: The largest understated risk is schema mismatch across agents. If the shared contract is Claude-native, later Codex/Gemini adapters will either lose detail or fork the format. Another understated risk is that optionalizing failures and subagent events materially reduces the forensic value of the logs.

### Testing Strategy
- [ ] Covers the critical paths
- [ ] Edge cases addressed
- Missing coverage: The plan should explicitly test whether the resulting log can answer the operator's actual questions, not just whether a file is written. It should also test multi-file edits, failed tool calls, and cross-backend normalization.

## Charter Verification

Did you read the referenced charters? List any contradictions between the plan and current charter content.

| Charter | Contradiction or Concern |
|---------|------------------------|
| `infrastructure.md` | No direct contradiction. Concern: the plan targets `.claude/settings.json`, but this repo currently contains `.claude/settings.local.json`, so the concrete config path should be clarified before implementation. |
| `cross_cutting.md` | No direct contradiction. Concern: classification-consistency risk is real and correctly identified, but the plan's bash-based hook path makes consistency harder to guarantee than a shared Python module would. |

## Alternative Approach (if applicable)

Use a backend-neutral JSONL event schema with required core fields and optional backend-specific payloads. Centralize path classification in Python and import it from both analyzers and any logger/extractor code. Keep Claude hook capture, but implement it in Python. For Codex, start by extracting compact per-session logs from the existing `.codex/sessions` artifacts rather than designing wrappers before a native hook surface is confirmed. Treat failed calls and delegation as required event classes, not later enhancements.
