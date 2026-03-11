# Development Log

Daily summaries of development activity, newest first. For the full commit history, see `git log`.

---

## 2026-03-11

### Memex Architecture Refactor Plan

Codex proposed a formal plan to evolve the constitutional architecture's Memex layer ([plan](../docs/plans/2026-03-11-memex-architecture-refactor/plan.md)). Key ideas: split `cross_cutting.md` into an index + focused invariant docs, introduce typed references (`→ invariant:`, `→ triggers:`, `→ depends on:`), and create a lightweight invariant registry for faster agent orientation. Gemini filed a [review](../docs/plans/2026-03-11-memex-architecture-refactor/reviews/gemini-review.md) (approve-with-concerns: merge registry with propagation map, add parseable reference grammar). Codex filed a [follow-up review](../docs/plans/2026-03-11-memex-architecture-refactor/reviews/codex-review.md) incorporating a scratchpad lifecycle finding.

### Control Study — Round 1 Data Collection

Ran the first round of the Memex vs Memory control study. Three agents (Claude, Codex, Gemini) each completed planning challenges under two conditions: **constitutional** (with governance docs) and **raw** (scrubbed codebase, no charters).

Results — governance doc engagement:

| Agent | Raw | Constitutional |
|-------|-----|----------------|
| Claude | 0.0 | 4.0, 4.0, 4.0 |
| Codex | 0.0 | 2.0, 2.0, 2.0 |
| Gemini | 0.0 | 2.0, 2.0, 1.3 |

Zero overlap between conditions. Constitutional agents read governance docs first in every session. Raw agents never touched governance files (none existed to read). Qualitative plan grading is next.

Plans collected from all sessions are saved in `C:/tmp/analysis-*.json` for the grading phase.

### Claude Transcript Extractor

Built [`scripts/extract_claude_log.py`](../scripts/extract_claude_log.py) — parses native Claude Code session transcripts from `~/.claude/projects/`, including subagent tool calls from progress records, into the shared JSONL schema. Updated [`scripts/analyze_latest.py`](../scripts/analyze_latest.py) with `--project` support for Claude (paralleling existing Gemini support).

### Scratchpad Lifecycle Fix

Human operator noticed stale line numbers Codex kept referencing — traced to the review scratchpad (`docs/architecture/review_scratchpad.md`) retaining resolved findings from a previous charter review. All 76+ issues were marked FIXED but the body still read like active findings. Fixed by adding a close-out step to the [`/review-charters` procedure](../docs/procedures/full-review.md) and truncating the scratchpad to a one-line summary.

### Grading Bug Fixes (from previous session, now on all branches)

Two HIGH bugs found by Codex's audit, fixed in [`core/utils/grading.py`](../core/utils/grading.py) and [`core/views_lib/assignments/grade.py`](../core/views_lib/assignments/grade.py):
1. `apply_grade()` now accepts `is_final` parameter (previously always created as final, then overwritten)
2. Cross-version grade demotion — finalizing a grade now demotes previous final grades across all submission versions, preventing double-counting

---

## 2026-03-10

### Session Tool-Use Logging — Plan Completed

First multi-agent plan executed end-to-end. Three agents (Claude, Codex, Gemini) collaboratively designed and implemented per-session tool-use logging across all three agent platforms.

Key deliverables:
- Shared event schema ([`scripts/session_log_schema.py`](../scripts/session_log_schema.py))
- File classifier ([`scripts/classify.py`](../scripts/classify.py)) — governance/flow/experiment/code classification + constitutional terminology detection
- Session analyzer ([`scripts/analyze_session.py`](../scripts/analyze_session.py)) — Memex scoring, trail detection, tripwire coverage
- Codex transcript extractor ([`scripts/extract_codex_log.py`](../scripts/extract_codex_log.py))
- Gemini transcript extractor ([`scripts/extract_gemini_log.py`](../scripts/extract_gemini_log.py))
- Convenience analyzer ([`scripts/analyze_latest.py`](../scripts/analyze_latest.py))

Final report: [`docs/plans/2026-03-10-session-tool-logging/report.md`](../docs/plans/2026-03-10-session-tool-logging/report.md)

### Constitutional Architecture — Initial Build

Full constitutional architecture created for the LearnHub codebase:
- 3 agent constitutions (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`)
- 9 charter documents in `docs/architecture/modules/`
- Cross-cutting concerns with 4 tripwires in `cross_cutting.md`
- 3 flow docs in `docs/flows/`
- Procedures, reference notes, plan templates
- Enforcer framework for independent verification

### Django Application — Initial Commit

LearnHub Django LMS: 16 models, 30 URL patterns, 6 domains (accounts, courses, assignments, discussions, notifications, analytics). Tailwind CSS templates, role-based permissions, late penalty grading engine, enrollment state machine.

---

## 2026-03-09

### Multi-Agent Constitutional Setup

Added `AGENTS.md` (Codex constitution) alongside existing `CLAUDE.md` and `GEMINI.md`. Reorganized experiment docs into `docs/experiments/`. Built initial session analysis scripts ([`scripts/analyze_session.py`](../scripts/analyze_session.py)) for the Memex vs Memory experiment — scoring tool-use logs for governance engagement, trail-following, and tripwire coverage.

### Runtime Fixes

Fixed runtime crashes from template/URL drift and settings wiring issues discovered during first `runserver` test.

---

## 2026-03-08

### Initial Commit

LearnHub created with full constitutional architecture: Django LMS application + 9 charter documents, cross-cutting concerns, flow docs, procedures, reference notes, and enforcer framework. Built as a reference implementation for the constitutional architecture governance pattern.
