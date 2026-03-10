# Plan: Per-Session Tool-Use Logging

**Author:** Claude (Opus 4.6)
**Date:** 2026-03-10
**Status:** under-review

---

## Original Request

> I don't want a script for tool use in a session...I want tool use logs, per session. Timestamps, charters hit, etc. A real forensic look at what the agent is doing in a session. I also don't want this logging to "weigh down" the primary agent...this should ideally be something that doesn't touch token use...let's make a formal plan for this feature, specifically for Claude Code, but with cognizance to call out what the other "team" members have to do to implement this tool-use logging per-session...

## Problem Statement

The `scripts/analyze_session.py` script works but it's a post-hoc analysis tool that parses JSONL transcripts — large files that mix tool calls with conversation content, file snapshots, and system messages. What we need is a clean, purpose-built tool-use log per session: timestamped, classified, lightweight. A forensic record of what the agent did, not what it said. This log should be produced in real-time with zero token cost to the primary agent.

## Scope

| In scope | Out of scope |
|----------|-------------|
| Real-time tool-use logging for Claude Code sessions | Codex/Gemini logging (called out for team implementation) |
| Structured JSONL log with governance classification | Replacing the existing `analyze_session.py` script |
| Async hook that doesn't touch token budget | Modifying the model's behavior or context window |
| Per-session log files in a predictable location | Log rotation, cleanup, or retention policies |
| Charter/governance file detection at log time | Full Memex scoring (stays in analysis script) |

## Affected Domains

| Domain | Charter | Impact |
|--------|---------|--------|
| Infrastructure | `infrastructure.md` | New hook configuration in `.claude/settings.json` |
| Cross-Cutting | `cross_cutting.md` | Governance file classification logic shared with analysis script |

## Cross-Cutting Concerns

- [ ] Grade Cache Duality
- [ ] Late Penalty Timing
- [ ] Grade Cascade
- [ ] Enrollment State Machine
- [x] Other: **Governance classification consistency** — the hook's file classifier must match the analysis script's classifier, or the forensic log and the post-hoc analysis will disagree on what counts as a governance read.

## Proposed Approach

### Step 1: Hook Logger Script

Create `.claude/hooks/log-tool-use.sh` (bash, works on macOS/Linux/Git Bash on Windows).

The script:
- Reads the PostToolUse JSON from stdin (provided by Claude Code's hook system)
- Extracts: `session_id`, `tool_use_id`, `tool_name`, `tool_input`, `agent_id`
- Generates a timestamp (hook JSON doesn't include one; use system clock)
- Classifies any file path as `governance`, `flow`, `experiment`, or `code` using the same patterns as `analyze_session.py`
- Extracts a human-readable summary (file name for Read/Edit, command description for Bash, pattern for Grep, etc.)
- Writes a single JSONL line to the session's log file
- Exits 0 with no stdout (zero token cost)

**Log entry schema:**
```json
{
  "timestamp": "2026-03-10T14:30:05Z",
  "session_id": "abc-123",
  "tool_use_id": "toolu_01ABC",
  "tool_name": "Read",
  "file_path": "docs/architecture/modules/cross_cutting.md",
  "file_class": "governance",
  "summary": "Read(cross_cutting.md)",
  "agent_id": null,
  "cwd": "/c/Users/curator/code2/learnhub"
}
```

**Log file location:** `.claude/logs/tool-use-{session_id}.jsonl`

This keeps logs project-local, one file per session, trivially greppable.

### Step 2: Hook Configuration

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/log-tool-use.sh",
            "async": true,
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Key choices:
- `"matcher": ".*"` — captures all tools including MCP tools
- `"async": true` — non-blocking, zero impact on agent flow
- `"timeout": 10` — safety net; logging should take <100ms

### Step 3: Session Start/End Markers

Add a `SessionStart` hook that writes a header entry to the log:
```json
{
  "timestamp": "2026-03-10T14:30:00Z",
  "session_id": "abc-123",
  "event": "session_start",
  "cwd": "/c/Users/curator/code2/learnhub"
}
```

This gives each log file a clear start marker with metadata, useful for analysis.

### Step 4: Gitignore and Cleanup

- Add `.claude/logs/` to `.gitignore` — logs are local artifacts, not committed
- The `logs/` directory is created automatically by the hook script if missing

### Step 5: Update Analysis Script

Modify `scripts/analyze_session.py` to accept the new lightweight log format as an alternative input. Add a `--tool-log` flag that reads the hook-produced JSONL instead of the full session transcript. This is faster and more precise since the log is already classified.

The governance classification patterns should be extracted into a shared module (`scripts/classify.py`) so the hook and the analysis script use identical logic.

### Step 6: Documentation

Add a section to `docs/plans/_INDEX.md` linking to this plan as the first completed example. Update the experiment README or flow docs if relevant.

## Data Model Changes

None. This is infrastructure-only — no Django models, no migrations.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hook script fails silently, no logs produced | Medium | Low | Test hook with `claude --verbose` (Ctrl+O shows hook output). Add a canary check: if log file doesn't exist after first tool call, something is wrong. |
| File classification diverges between hook and analysis script | Medium | Medium | Extract shared classification patterns into `scripts/classify.py`, import from both. |
| Windows Git Bash path handling differs from POSIX | Medium | Medium | Test on Windows with Git Bash. Use `$CLAUDE_PROJECT_DIR` env var for paths. Normalize backslashes in the hook script. |
| Log files accumulate without cleanup | Low | Low | Out of scope for now. Files are small (~10KB per session). Manual cleanup or future retention policy. |
| `jq` not installed on target system | Medium | High | Script requires `jq` for JSON parsing. Document as a prerequisite. Consider a Python fallback for environments without `jq`. |

## Testing Strategy

1. **Smoke test**: Start a Claude Code session, run a few tool calls, verify `.claude/logs/tool-use-{session_id}.jsonl` is created with correct entries.
2. **Classification test**: Read a governance file, a code file, and a flow doc. Verify each log entry has the correct `file_class`.
3. **Async verification**: Confirm the hook doesn't slow down agent responses — compare response latency with and without the hook enabled.
4. **Windows test**: Verify the bash hook works under Git Bash on Windows 10.
5. **Analysis integration**: Run `analyze_session.py --tool-log` against a hook-produced log and verify the Memex score matches (or is more accurate than) transcript-based analysis.

## Open Questions

1. **Python vs bash for the hook script?** Bash + `jq` is lighter and faster, but Python avoids the `jq` dependency and can import the shared classifier directly. The tradeoff is startup time (~200ms for Python vs ~20ms for bash). Since the hook is async, startup time doesn't block the agent.

2. **Should SubagentStart/SubagentStop be logged too?** This would give visibility into when the agent delegates to subagents, creating a more complete picture of the session's structure. Lightweight to add.

3. **Should the hook also capture PostToolUseFailure?** Failed tool calls are interesting forensically — they show where the agent hit walls. Adds one more hook entry in settings.

---

## Team Callouts

This plan is Claude Code-specific. The other team members need to implement equivalent logging for their platforms:

### Codex (AGENTS.md)
- Codex CLI may support hooks or plugins — investigate equivalent to Claude Code's `PostToolUse` hook.
- If no hook system exists, Codex should implement logging as a wrapper script that intercepts API calls and writes the same JSONL schema.
- The log entry schema (above) should be treated as the **shared contract** — all agents produce logs in this format so `analyze_session.py` can process them uniformly.
- Codex already has `scripts/analyze_codex_session.py` — this should be updated to also consume the new hook-produced logs.

### Gemini (GEMINI.md)
- Same requirement: per-session JSONL tool-use log in the shared schema.
- Gemini's implementation path depends on whether it's used via API (wrap the client) or via a CLI tool (hooks/plugins).
- The governance file classifier must match — use the same pattern list or import from `scripts/classify.py`.

### Shared contract
All agents should produce log files with this structure:
- **Location:** `.claude/logs/tool-use-{session_id}.jsonl` (or agent-equivalent directory)
- **Schema:** The JSON schema defined in Step 1 above
- **Classification:** Same governance/flow/experiment/code categories
- **One file per session**, JSONL format, one line per tool call
