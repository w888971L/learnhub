# Plan: Per-Session Tool-Use Logging (Codex Alternative)

**Author:** Codex
**Date:** 2026-03-10
**Status:** under-review

---

## Original Request

> I don't want a script for tool use in a session...I want tool use logs, per session. Timestamps, charters hit, etc. A real forensic look at what the agent is doing in a session. I also don't want this logging to "weigh down" the primary agent...this should ideally be something that doesn't touch token use...let's make a formal plan for this feature, specifically for Claude Code, but with cognizance to call out what the other "team" members have to do to implement this tool-use logging per-session...

## Problem Statement

The current analyzers are useful but post-hoc: they infer behavior by parsing full session transcripts after the fact. What is missing is a lightweight, per-session forensic event log that captures tool activity directly, with timestamps and governance classification, while preserving enough backend-specific detail to be reliable across Claude Code, Codex, and Gemini.

## Scope

This plan proposes a shared logging architecture with a Codex-first interpretation of the cross-agent problem. It preserves Claude Code hook logging as one capture path, but avoids forcing all agents into a Claude-native event model.

| In scope | Out of scope |
|----------|-------------|
| Shared event schema for per-session tool-use logs across agents | Replacing the existing transcript analyzers immediately |
| Claude Code capture via hooks | Django model changes or migrations |
| Codex capture via transcript extraction first, hook/plugin later if available | Retention policy automation |
| Python shared classifier and parser module | Memex scoring redesign |
| Success, failure, and delegation event capture | Real-time UI dashboards |
| Agent-local log directories with analyzer normalization | Logging arbitrary conversational text |

## Affected Domains

| Domain | Charter | Impact |
|--------|---------|--------|
| Infrastructure | `infrastructure.md` | Adds agent-local logging config/scripts and shared parser/classifier modules |
| Cross-Cutting | `cross_cutting.md` | Requires classification consistency between capture and analysis layers |
| Procedures | `docs/procedures/briefing.md` (adjacent process only) | No direct behavioral change, but logs improve later briefings/reviews |

## Cross-Cutting Concerns

- [ ] Grade Cache Duality
- [ ] Late Penalty Timing
- [ ] Grade Cascade
- [ ] Enrollment State Machine
- [x] Other: **Governance classification consistency**
- [x] Other: **Forensic completeness of failure paths**
- [x] Other: **Backend-specific event fidelity**

No grading or enrollment tripwires are directly modified because this is tooling infrastructure outside the Django application path.

Governance classification consistency matters because the same session should not be counted as "governance-aware" by one analyzer and "code-only" by another. The classifier must be shared, not reimplemented ad hoc per tool.

Failure-path completeness matters because the most revealing forensic events are often failed tool calls, retries, approval denials, and delegation. A "tool-use log" that records only successful calls is incomplete.

Backend-specific fidelity matters because Claude Code, Codex, and Gemini do not expose identical tool models. A shared schema must normalize the common fields without collapsing away important native detail.

## Proposed Approach

### Step 1: Define a backend-neutral event schema

Create a shared schema module, e.g. `scripts/session_log_schema.py`, that defines a canonical JSONL event shape. Required fields:

- `timestamp`
- `session_id`
- `agent`
- `event_type`
- `tool_name`
- `status`
- `cwd`
- `summary`

Optional fields:

- `file_paths`
- `file_classes`
- `command`
- `tool_input`
- `tool_output_meta`
- `error`
- `agent_id`
- `delegated_to`
- `raw_backend`

Rationale: Claude's proposed schema assumes a single `file_path`, `tool_use_id`, and Claude-native tool names. That is too narrow for Codex, where a single `apply_patch` may touch multiple files and `shell_command` often wraps file access heuristically.

### Step 2: Extract classification logic into a shared Python module

Move governance/flow/experiment/code path classification into a shared Python module, e.g. `scripts/classify.py`, then import it from:

- `scripts/analyze_session.py`
- `scripts/analyze_codex_session.py`
- any new capture or extraction scripts

This removes duplication and prevents drift. The current Claude and Codex analyzers already duplicate core classification rules.

### Step 3: Claude Code capture path uses hook-based event logging

For Claude Code specifically, keep the hook idea, but implement the logger in Python rather than bash + `jq`.

Proposed files:

- `.claude/hooks/log_tool_use.py`
- `.claude/hooks/log_session_event.py` if start/end/failure hooks need separate entry points

Why Python instead of bash:

- direct reuse of shared classifier/schema code
- no `jq` dependency
- less quoting/path fragility on Windows
- easier support for multi-file events and structured payloads

Claude-specific behavior:

- `PostToolUse` writes `tool_success` events
- if supported, `PostToolUseFailure` writes `tool_failure` events
- if supported, session/subagent hooks write `session_start`, `session_end`, `delegation_start`, `delegation_end`

Claude log location:

- `.claude/logs/tool-use-{session_id}.jsonl`

### Step 4: Codex capture path starts with transcript extraction, not wrappers

For Codex, do not begin with an interception wrapper unless a native hook/plugin API is confirmed and stable.

Instead, add a compact extractor that reads Codex's existing structured session files from `.codex/sessions/...jsonl` and emits the shared event schema into agent-local log files.

Proposed files:

- `scripts/extract_codex_tool_log.py`
- `.codex/logs/tool-use-{session_id}.jsonl` as normalized output

Why this is the preferred first step:

- zero impact on the primary agent
- zero dependency on undocumented interception points
- uses data Codex is already emitting
- lower operational risk than API-call wrapping

If Codex later exposes a reliable hook/plugin surface, add a direct real-time logger as a second capture mode, not as the initial requirement.

### Step 5: Treat failures and delegation as required event classes

The forensic minimum should include:

- `session_start`
- `tool_success`
- `tool_failure`
- `delegation_start`
- `delegation_end`
- `session_end`

This is a deliberate divergence from the original Claude plan, which treats failures and delegation as optional follow-ons. Forensic usefulness depends on showing where the agent hit walls, retried, escalated, or split work.

### Step 6: Keep agent-local storage, normalize at analysis time

Do not require all agents to write into `.claude/logs/`. That path is Claude-branded and repo-local.

Preferred locations:

- Claude Code: `.claude/logs/`
- Codex: `.codex/logs/`
- Gemini: agent-local equivalent

The shared contract is the event schema, not the directory name. Analysis tools should accept any agent-local path and normalize across them.

### Step 7: Add a unified analyzer input layer

Rather than bolting `--tool-log` only onto `scripts/analyze_session.py`, add a small shared ingestion layer that can read:

- full Claude transcripts
- full Codex transcripts
- normalized compact tool logs

Then keep backend-specific extraction separate from shared scoring/reporting. This reduces the risk of the Claude analyzer becoming the accidental global parser for all agent logs.

### Step 8: Validation is question-driven, not just smoke-driven

The log design should be tested against the actual forensic questions the human operator wants to answer:

- Which charters were hit in this session?
- Did governance reads happen before edits?
- Which tool calls failed, and how often?
- When did delegation happen?
- Which sessions touched `cross_cutting.md` or other tripwire-heavy docs?
- Which edits followed no governance reads at all?

If the schema cannot answer those directly, it is not yet a sufficient forensic log.

## Data Model Changes

None.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shared schema is too Claude-specific and loses Codex/Gemini detail | Medium | High | Define required core fields plus backend-specific optional fields from the start |
| Classification logic drifts across logger and analyzer implementations | Medium | High | Centralize classification in one Python module imported everywhere |
| Bash hook path handling and `jq` availability break Claude logging on Windows | Medium | Medium | Use Python hook scripts instead of bash + `jq` |
| Codex wrapper/interception approach proves brittle or unsupported | Medium | Medium | Start with transcript extraction from existing `.codex/sessions` artifacts |
| Logs omit failed calls and delegation, weakening forensic value | High | High | Make failure/delegation required event classes |
| Agent-local log directories create fragmentation | Low | Medium | Normalize at analysis time; keep schema shared |
| Full-session extraction for Codex is not strictly real-time | Medium | Low | Accept extraction-first as phase 1; add direct hooks later if platform support appears |

## Testing Strategy

1. Schema test: validate that Claude and Codex events can both serialize into the same canonical schema without dropping important fields.
2. Classification test: verify a governance file, flow doc, experiment doc, and code file produce consistent `file_classes` across logger and analyzer paths.
3. Claude capture test: run a Claude session with hooks enabled and confirm success, failure, and delegation events append correctly.
4. Codex extraction test: run the extractor against real `.codex/sessions` files and confirm the resulting compact log preserves timestamps, summaries, and multi-file edits.
5. Parity test: compare transcript-based analysis versus compact-log analysis on the same session and confirm material conclusions match.
6. Windows test: verify Python hook/extractor behavior on this machine, including path normalization.
7. Forensic question test: confirm the produced logs can answer the operator-facing questions listed in Step 8 without re-reading the full transcript.

## Open Questions

1. For Claude Code, which hook events are actually available in the current installed version: `PostToolUse`, failure hooks, subagent hooks, session hooks?
2. For Codex, is near-real-time extraction from `.codex/sessions` sufficient, or is true append-time logging a hard requirement?
3. Should compact logs store raw tool input in full, or only a summarized/redacted subset to reduce sensitivity and file size?
4. Should analyzer output remain split by backend (`analyze_session.py`, `analyze_codex_session.py`) or converge on one unified entry point after shared ingestion exists?

---

## Comparison To Original Claude Plan

This alternative agrees with the original plan on the core objective: lightweight, per-session, purpose-built tool logs are better than transcript-only forensics.

It differs in four material ways:

1. The shared contract should be schema-level, not Claude-tool-level.
2. Python is preferred over bash + `jq` because shared classification and Windows robustness matter more than minimal startup overhead.
3. Codex should start with extraction from existing session artifacts, not speculative wrappers.
4. Failure and delegation logging should be mandatory, not future enhancements.
