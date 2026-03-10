# Plan: Per-Session Tool-Use Logging (Gemini Unified)

**Author:** Gemini CLI
**Date:** 2026-03-10
**Status:** draft

---

## Original Request

> I don't want a script for tool use in a session...I want tool use logs, per session. Timestamps, charters hit, etc. A real forensic look at what the agent is doing in a session. I also don't want this logging to "weigh down" the primary agent...this should ideally be something that doesn't touch token use...let's make a formal plan for this feature, specifically for Claude Code, but with cognizance to call out what the other "team" members have to do to implement this tool-use logging per-session...

## Problem Statement

To provide a forensic, real-time (or near real-time) record of agent tool usage without impacting token budgets or performance. The goal is to move beyond post-hoc transcript parsing and into structured, timestamped event logging that captures successes, failures, and delegations across all active agents (Claude, Codex, Gemini).

## Scope

This plan synthesizes the Claude and Codex proposals into a phased, unified implementation that prioritizes shared logic and forensic completeness.

| In scope | Out of scope |
|----------|-------------|
| Shared Python-based file classifier (`scripts/classify.py`) | Real-time dashboards or UI for logs |
| Backend-neutral JSONL event schema | Modifying LLM model behavior |
| Claude Code logging via Python-based hooks | Log rotation or long-term retention policies |
| Codex logging via session-file extraction | Full replacement of `analyze_session.py` immediately |
| Gemini logging via agent-local log directory | |

## Affected Domains

| Domain | Charter | Impact |
|--------|---------|--------|
| Infrastructure | `infrastructure.md` | Adds logging hooks, extraction scripts, and shared modules |
| Cross-Cutting | `cross_cutting.md` | Ensures classification consistency across all agents |

## Cross-Cutting Concerns

- [ ] Grade Cache Duality
- [ ] Late Penalty Timing
- [ ] Grade Cascade
- [ ] Enrollment State Machine
- [x] Other: **Governance Classification Consistency** — Centralized in `scripts/classify.py` to ensure all agents agree on what constitutes a "charter hit."

## Proposed Approach

We will follow a phased rollout to avoid over-engineering while ensuring a solid foundation.

### Phase 1: Shared Foundation (The "Classifier")

**Step 1: Create `scripts/classify.py`**
Extract the classification regex and logic from `scripts/analyze_session.py`. This module will be the single source of truth for categorizing file paths as `governance`, `flow`, `experiment`, or `code`.

**Step 2: Define Shared Event Schema**
Formalize a JSONL schema that includes:
- `timestamp` (ISO 8601)
- `session_id`
- `agent` (claude|codex|gemini)
- `event_type` (session_start|tool_use|tool_failure|delegation_start|delegation_end|session_end)
- `tool_name`
- `file_paths` (list, to support multi-file tools)
- `file_classes` (list, derived from `scripts/classify.py`)
- `summary` (human-readable)
- `status` (success|failure)

### Phase 2: Claude & Codex Capture

**Step 3: Claude Python Hook**
Implement `.claude/hooks/log_tool_use.py`. Claude Code will call this script async on `PostToolUse` and `PostToolUseFailure`.
- Replaces the bash/`jq` proposal for better Windows support and direct import of `scripts/classify.py`.
- Logs to `.claude/logs/tool-use-{session_id}.jsonl`.

**Step 4: Codex Extraction Path**
Implement `scripts/extract_codex_log.py`. Since Codex already writes structured session files, this script will periodically (or on-demand) extract tool events into the shared schema.
- Logs to `.codex/logs/tool-use-{session_id}.jsonl`.

### Phase 3: Gemini Integration

**Step 5: Gemini Agent-Local Logging**
Gemini CLI will implement a simple internal logging call (or a small wrapper script `scripts/log_gemini_tool.py`) that appends events to `.gemini/logs/tool-use-{session_id}.jsonl`.
- Since Gemini CLI operates primarily through a command-loop or wrapper, it will record each tool call *after* execution but *before* returning control to the model, ensuring zero token cost.

### Phase 4: Unified Ingestion

**Step 6: Update Analyzers**
Update `scripts/analyze_session.py` and `scripts/analyze_codex_session.py` to accept the new `.jsonl` tool logs as a primary, high-fidelity input source using the `--tool-log` flag.

## Data Model Changes

None. This is purely external infrastructure.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Script execution overhead in hooks | Low | Low | Keep Python scripts lean; use `async: true` in Claude hooks. |
| Classification logic drift | Low | High | Enforced by single `scripts/classify.py` module. |
| Windows path normalization issues | Medium | Medium | Use `pathlib` in all Python logging/extraction scripts. |
| Divergent session IDs across agents | Medium | Medium | Use a shared environment variable or project-root session marker if possible. |

## Testing Strategy

1. **Parity Check:** Run a session with both transcript-based and log-based analysis; verify results match.
2. **Forensic Test:** Intentionally fail a tool call and verify `tool_failure` appears in the log with correct metadata.
3. **Cross-Agent Test:** Verify a Claude-initiated delegation to a sub-agent produces `delegation_start/end` events in the log.

## Open Questions

1. Should we use a single `.logs/` directory at the root instead of agent-specific directories? (Current consensus is agent-specific to avoid permission/branding friction).
2. How should session IDs be shared when one agent spawns another?
