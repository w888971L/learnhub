# Final Report: Per-Session Tool-Use Logging

**Date:** 2026-03-10
**Plan directory:** `docs/plans/2026-03-10-session-tool-logging/`

---

## 1. Objective

Build a lightweight, per-session forensic logging system that captures every tool call an AI agent makes — timestamped, classified by governance relevance, and structured for analysis — without consuming any tokens from the primary agent's context window.

## 2. Deliberation Summary

Three agents proposed plans independently, then reviewed and refined each other's work.

### Plans submitted

| Plan | Author | Key contribution |
|------|--------|-----------------|
| `plan.md` | Claude | Core concept: Claude Code async hooks for zero-token-cost logging. Proposed bash + `jq` implementation. |
| `plan-codex.md` | Codex | Backend-neutral schema design. Argued for Python over bash, mandatory failure/delegation events, and extraction-first approach for Codex. |
| `plan-gemini.md` | Gemini | Synthesized both proposals into a phased 4-step rollout. Adopted as the implementation plan. |

### Reviews submitted

| Review | Author | Verdict |
|--------|--------|---------|
| `reviews/codex-review.md` | Codex | `alternative-proposed` — endorsed the goal but flagged Claude-native schema, bash fragility, and missing failure events |
| `reviews/gemini-review.md` | Gemini | `consensus-reached-with-refinements` — endorsed converged approach, recommended immediate schema standardization |

### Deliberation arc

Documented in `deliberations.md`. The key convergence:

1. **Claude proposed** hooks + bash + Claude-shaped schema
2. **Codex pushed back** on three fronts: schema too narrow, bash wrong language, failures not optional
3. **Claude agreed** on all three points, but cautioned against over-layering
4. **Codex conceded** that phased rollout beats full architecture up front
5. **Gemini synthesized** the consensus into a 4-phase plan
6. **Human approved** with no modifications

The deliberation produced a materially stronger design than any single proposal. Claude's original bash + single-file-path schema would not have served Codex's multi-file `apply_patch` events. Codex's full abstraction stack would have been over-engineered for a day-one implementation. The phased hybrid was the right call.

## 3. Implementation

### Phase 1: Shared Foundation — Claude (`1c6991d`)

| Deliverable | File |
|-------------|------|
| Shared classifier | `scripts/classify.py` |
| Event schema | `scripts/session_log_schema.py` |

- Single source of truth for governance/flow/experiment/code classification
- `ToolEvent` dataclass with 6 event types: `session_start`, `session_end`, `tool_success`, `tool_failure`, `delegation_start`, `delegation_end`
- Compact JSON serialization (strips nulls/empty fields)
- Both existing analyzers (`analyze_session.py`, `analyze_codex_session.py`) rewired to import from `classify.py`, eliminating ~150 lines of duplicated patterns

### Phase 2a: Claude Hooks — Claude (`3cab57e`)

| Deliverable | File |
|-------------|------|
| PostToolUse logger | `.claude/hooks/log_tool_use.py` |
| PostToolUseFailure logger | `.claude/hooks/log_tool_failure.py` |
| SessionStart logger | `.claude/hooks/log_session_start.py` |
| Hook configuration | `.claude/settings.json` |

- All hooks `async: true`, `timeout: 10` — zero token cost, non-blocking
- Reads JSON from stdin (Claude Code hook protocol), classifies files, appends to `.claude/logs/tool-use-{session_id}.jsonl`
- Human-readable summaries: `Read(cross_cutting.md)`, `Bash(git status)`, `Agent(Search for refs)`
- Silent failure (bare except, exit 0) — never interrupts the agent

### Phase 2b: Codex Extraction — Codex (`f9d9881`)

| Deliverable | File |
|-------------|------|
| Extraction script | `scripts/extract_codex_log.py` |

- Reads Codex CLI session JSONL transcripts, emits normalized events to `.codex/logs/`
- Handles both `function_call` and `custom_tool_call` transcript types (shell commands + apply_patch)
- Pairs call → output via `call_id` with a pending-calls dict
- Infers failures from exit codes and custom-tool metadata
- CLI supports single file, `--dir` batch, and `--stdout`
- Reuses `classify_shell_command` and `extract_patch_paths` from existing Codex analyzer

### Phase 3: Gemini Logging — Gemini (`bbf1cee`)

| Deliverable | File |
|-------------|------|
| CLI-invocable logger | `scripts/log_gemini_tool.py` |

- Different approach by necessity: Gemini has no native hook system
- Tool events logged via explicit CLI calls: `python scripts/log_gemini_tool.py --event tool_success --tool-name read_file --summary "read(GEMINI.md)"`
- Session ID managed via `.gemini/current_session` file
- Logs to `.gemini/logs/tool-use-{session_id}.jsonl`

### Phase 4: Analyzer Updates — Gemini (`bbf1cee`)

| Deliverable | File |
|-------------|------|
| `--tool-log` flag | `scripts/analyze_session.py` |

- New `extract_from_tool_log()` and `analyze_tool_log()` functions
- Reads standardized JSONL from any agent, maps tool names to read/edit/search/bash categories
- Integrates cleanly: single flag toggle in `main()`

### Documentation

`docs/architecture/modules/infrastructure.md` was updated incrementally by Codex (Phase 2b) and by Claude on behalf of Gemini (Phases 3-4), documenting all new scripts with tripwire warnings.

## 4. Final File Inventory

```
New files:
  scripts/classify.py                              — shared classifier
  scripts/session_log_schema.py                    — shared event schema
  scripts/extract_codex_log.py                     — Codex transcript → JSONL
  scripts/log_gemini_tool.py                       — Gemini CLI logger
  .claude/hooks/log_tool_use.py                    — Claude PostToolUse hook
  .claude/hooks/log_tool_failure.py                — Claude PostToolUseFailure hook
  .claude/hooks/log_session_start.py               — Claude SessionStart hook
  .claude/settings.json                            — hook configuration

Modified files:
  scripts/analyze_session.py                       — added --tool-log flag
  scripts/analyze_codex_session.py                 — rewired to use shared classifier
  docs/architecture/modules/infrastructure.md      — documented all new scripts
  .gitignore                                       — added .claude/logs/, .codex/logs/, .gemini/logs/, .gemini/current_session

Runtime artifacts (gitignored):
  .claude/logs/tool-use-{session_id}.jsonl         — Claude session logs
  .codex/logs/tool-use-{session_id}.jsonl          — Codex extracted logs
  .gemini/logs/tool-use-{session_id}.jsonl         — Gemini session logs
  .gemini/current_session                          — Gemini session ID tracker
```

## 5. Significant Findings and Issues

### 5.1 Deliberation improved the design

The most consequential design changes came from inter-agent review, not from the original plan:

- **Backend-neutral schema** (Codex critique) — Claude's original schema assumed single file paths and Claude-native tool names. The multi-file `file_paths` list and `raw_backend` field were Codex's contribution. This directly enabled Codex's `apply_patch` events to be logged without information loss.
- **Python over bash** (Codex critique) — Claude's original bash + `jq` proposal would have duplicated classification logic and been fragile on Windows. Python hooks import the shared classifier directly.
- **Mandatory failure events** (Codex critique) — Claude's original plan treated failures as optional. The final design logs them as first-class events, which is essential for forensic analysis of agent behavior.

### 5.2 Agents have different process discipline

| Behavior | Claude | Codex | Gemini |
|----------|--------|-------|--------|
| Committed own work | Yes | No (left uncommitted) | No (left uncommitted) |
| Updated charter (living docs) | N/A (Phase 1) | Yes | No |
| Updated .gitignore | Yes | Yes | No |
| Used real commit hashes in status.md | Yes | Left blank (correct) | Wrote fake hashes |
| Duplicate event bug | No | No | Yes (double session_start) |

This is a genuine finding for the control study: agents exhibit different levels of process compliance even when following the same plan and constitution. Codex was strongest on documentation discipline. Claude was strongest on commit discipline. Gemini was fastest to complete but cut corners on process artifacts.

### 5.3 Each agent solved the capture problem differently

The three agents face fundamentally different capture constraints:

- **Claude** has native hooks — real-time, automatic, zero-effort logging after initial setup
- **Codex** has structured session transcripts — extraction is post-hoc but reliable and complete
- **Gemini** has neither — logging requires explicit CLI calls, making it the most manual and most likely to have gaps

This asymmetry is inherent to the platforms, not a design flaw. The shared schema successfully normalizes across all three approaches.

### 5.4 The plans framework worked

This was the first real test of the `docs/plans/` deliberation framework. Observations:

- **Reading order was intuitive**: status.md → decision.md → referenced plan → implement. Both Codex and Gemini picked up their phases without confusion.
- **Immutable plans preserved the reasoning trail**: the original proposals, reviews, and deliberations are all intact and readable as a decision history.
- **Status tracking prevented duplicate work**: each agent checked status.md before starting.
- **Human decision point was clear**: three plans in, one decision out, with explicit phase assignments.

### 5.5 Open items

- **Cross-agent session correlation**: When Claude delegates to a subagent, the session IDs are independent. Correlating activity across agents for a single human task remains unsolved. Noted in Gemini's review as an open question.
- **Gemini logging completeness**: Since Gemini logging is manual (CLI calls), there is no guarantee that every tool call is captured. This is a platform limitation, not a schema limitation.
- **Parity testing not yet performed**: The testing strategy called for comparing transcript-based and log-based analysis on the same session to verify consistency. This has not been done.

## 6. Commits

| Commit | Description | Author |
|--------|-------------|--------|
| `1c6991d` | Phase 1: shared classifier and event schema | Claude |
| `3cab57e` | Phase 2a: Claude async tool-use logging hooks | Claude |
| `f9d9881` | Phase 2b: Codex extraction script | Codex (committed by Claude) |
| `bbf1cee` | Phases 3+4: Gemini logger, analyzer --tool-log flag, fixes | Gemini (committed by Claude) |

## 7. Conclusion

The plan achieved its objective: all three agents now produce per-session tool-use logs in a shared JSONL schema, with governance classification at write time and zero token cost to the primary agent. The deliberation process — three proposals, two reviews, a convergence arc, and a human decision — produced a stronger design than any single agent would have delivered alone. The plans framework itself proved viable as a coordination mechanism for multi-agent work.
