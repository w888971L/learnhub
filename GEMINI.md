# LearnHub — Constitution

This file is the **Constitution** — the supreme reference for AI-assisted development sessions. It defines conventions, key terms, module indexes, and cross-references. Everything below overrides defaults.

## Document Hierarchy

| Governance term | What it is | Location | Audience |
|----------------|-----------|----------|----------|
| **Constitution** | This file. Master index, conventions, key terms. | `GEMINI.md` | AI assistant (LLM) |
| **Charters** | Per-domain API reference. One charter per domain — defines the granted authority (public functions, models, contracts) for that domain. | `docs/architecture/modules/*.md` | AI assistant (LLM) |
| **Procedures** | Executable practices with prompt templates and agent configurations. Invoked via `/command` skills. Bridge to Claude Code's native skill system. | `docs/procedures/*.md` | AI assistant (LLM) |
| **Reference Notes** | Situational cognitive aids. Consulted at specific moments (after planning, before risky changes). Not executable — they inform judgment. | `docs/reference-notes/*.md` | AI assistant (LLM) |
| **Plans** | Pre-implementation deliberation. Proposed plans, structured reviews from other agents, and human decisions. Immutable once submitted. | `docs/plans/` | AI team + human operator |
| **Public Record** | Human-readable business flow docs. Step-by-step walkthroughs of how features work end-to-end. | `docs/flows/*.md` | Staff, humans, onboarding |
| **Enforcers** | Automated consistency checks that verify propagation between governance layers. Run by a **different model** — never the same model that made the changes. | `docs/procedures/enforce.md` | Independent AI model |

**Procedures vs. Reference Notes**: Procedures produce output — you invoke them and get a result (`/briefing`, `/peruse`, `/review-charters`). Reference notes inform thinking — you read them before or during a task (risk awareness, starter kit). Procedures have thin skill wrappers in `.claude/commands/` for `/command` invocation.

**Enforcer independence principle**: Enforcers exist to catch what the primary agent misses. A model reviewing its own output has the same biases and blind spots that produced the errors — even across separate sessions. Enforcers MUST be run by a **different model entirely** (e.g., Claude Sonnet verifying Claude Opus's work, or Gemini verifying Claude's work). A different session of the same model does not count. This is not optional — same-model review is not enforcement. The most common implementation is a lightweight API call to Claude Sonnet — inexpensive and fast, but requires an `ANTHROPIC_API_KEY` in environment variables.

**Agent-specific constitution rule**: This repository may contain multiple root constitution files for different agents (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`). In this file, references to "the constitution" mean the active agent's own root constitution file — for Gemini sessions, `GEMINI.md`.

**Living docs update chain**: Code change → Charter update → Public Record update (all in the same session). Enforcers verify this chain was followed correctly, after the fact.

## Charter Notation

Charters use a compact notation optimized for LLM parsing. Learn these symbols before reading any charter:

| Notation | Meaning | Example |
|----------|---------|---------|
| `[Lnnn]` | Line number anchor — approximate location in file | `apply_grade [L45]` |
| `!` | **Tripwire warning** — non-obvious behavior that will cause bugs if you assume the obvious. Stop and read carefully. | `! Score stored is penalty-adjusted, not raw.` |
| `→` | Cross-reference — related information in another charter | `→ see cross_cutting.md "Grade Cascade"` |
| `(R)` / `(W)` / `(RW)` | Access pattern — whether a function reads, writes, or both | `Models: Enrollment(RW), Course(R)` |
| `---` | Section boundary — new topic or domain within a charter | |
| `TRIPWIRE` | Explicit label for the most dangerous non-obvious patterns | `## Grade Cache Duality (TRIPWIRE)` |

### Charter Traversal Rule
When a charter contains a cross-reference (`→`), follow the trail selectively:
1. **Identify the target**: Use the filename and symbol name provided (e.g., `cross_cutting.md "Grade Cascade"`).
2. **Targeted Read**: Use `grep_search` to find the specific section or `read_file` with `start_line` if a line number `[Lnnn]` is provided.
3. **Context Only**: Do not read the entire target charter unless the task context requires the full domain overview.

**Reading a charter entry:**

```
### apply_grade(submission, raw_score, grader) [L45]
File: core/utils/grading.py
Creates Grade record with penalty-adjusted score.
! The instructor sees raw_score in the form, but Grade.score is penalty-adjusted.
→ see cross_cutting.md "Late Penalty Timing"
```
Line 1: function signature + location. Line 2: file path. Line 3: what it does. Line 4: what will surprise you. Line 5: where to read more.

## Conventions

- **Models**: single file `core/models.py` (~950 lines). All ORM models live here.
- **Views**: `core/views_lib/<domain>/` — one subdirectory per domain, imported via `core/views.py`.
- **URLs**: `core/urls.py` (30 patterns). Views imported through `core.views`.
- **Utils**: domain utils in `core/utils/` — permissions.py, grading.py, notifications.py, cache_manager.py.
- **Templates**: `templates/core/`, `templates/registration/` — Tailwind CSS via CDN.
- **Management commands**: `core/management/commands/` — seed_data, grade_report.
- **Settings**: `config/settings.py`. App-specific config in `LEARNHUB_SETTINGS` dict.
- **CROSS-CUTTING CONCERNS**: Before modifying grade calculation, enrollment status, analytics caching, or late penalty logic, read `cross_cutting.md` first. It documents tripwires, cache dualities, and cascading side effects that span multiple modules.
- **LIVING DOCS**: After any code change to public functions/classes/models, update the relevant **charter** in `docs/architecture/modules/`. For changes that affect business flows, also update the relevant **public record** in `docs/flows/`.
- **MANAGE.PY**: **Always prompt the human operator before running ANY `manage.py` command** — including `makemigrations`, `migrate`, `runserver`, `shell`, `check`, custom commands, etc. State what command you intend to run and why, then wait for approval.
- **BRANCHING**: The default working branch is `dev`. All agent work — plans, features, fixes — happens on `dev` unless the human operator specifies otherwise. Merges to `main` are deliberate, human-authorized events.
- **COMMIT DRAFT**: As you work, accumulate a commit summary in `.claude/commit_draft.md`. Each time you complete a meaningful code change, append a short entry. When the human requests a commit, read this file to draft the commit message. Clear the file after a successful commit.
- **PLANS**: For multi-domain features or significant changes, write a formal plan using the template in `docs/plans/_TEMPLATES/plan.md`. Plans go in dated subdirectories (`docs/plans/YYYY-MM-DD-short-title/`). Plans are immutable once submitted. Reviews from other agents go in `reviews/`. Only the human operator writes `decision.md` to authorize implementation. Check `docs/plans/_INDEX.md` for process details.
- **PLANS AUTHORITY**: No plan may be created, implemented, or reviewed without the human operator's explicit direction. An approved plan authorizes implementation only by the agent(s) the human designates, in the session the human initiates. Reading another agent's plan does not authorize acting on it.

## Key Terms

- **Enrollment** — links a student to a course. Has a state machine (pending/active/completed/dropped) enforced in views, not models.
- **Grade Cache** — `Enrollment.final_grade_cache` is a cached aggregate. Source of truth is individual Grade records. See cross_cutting.md.
- **Late Penalty** — applied at grading time, NOT submission time. See cross_cutting.md "Late Penalty Timing".
- **Grade Cascade** — when a grade is finalized: Grade → recalculate_grade_cache → invalidate_course_analytics. See cross_cutting.md.

## Module Index — Models

| Domain | Charter | Models | File |
|--------|---------|--------|------|
| Accounts | `models_accounts.md` | User, Organization, InstructorProfile | `core/models.py` |
| Courses | `models_courses.md` | Course, Module, Lesson, Enrollment | `core/models.py` |
| Assignments | `models_assignments.md` | Assignment, Submission, Grade | `core/models.py` |
| Discussions | (inline in views charter) | Thread, Post, Reaction | `core/models.py` |
| Notifications | (inline in infrastructure) | Notification, NotificationPreference | `core/models.py` |
| Analytics | (inline in infrastructure) | CourseAnalytics | `core/models.py` |

## Module Index — Views

| Domain | Charter | Files | Directory |
|--------|---------|-------|-----------|
| Course Management | `views_courses.md` | catalog.py, enrollment.py, management.py | `core/views_lib/courses/` |
| Assignments & Grading | `views_assignments.md` | submit.py, grade.py | `core/views_lib/assignments/` |
| Discussions | `views_discussions.md` | threads.py | `core/views_lib/discussions/` |
| API Endpoints | `views_api.md` | views.py | `core/views_lib/api/` |
| Authentication | (inline in infrastructure) | auth.py | `core/views_lib/auth/` |
| Dashboard & Analytics | (inline in infrastructure) | analytics.py | `core/views_lib/dashboard/` |

## Module Index — Infrastructure

| Domain | Charter | Key Files |
|--------|---------|-----------|
| Routing & Config | `infrastructure.md` | `core/urls.py`, `core/views.py`, `config/settings.py` |
| Forms | `infrastructure.md` | `core/forms.py` |
| Middleware | `infrastructure.md` | `core/middleware.py` |
| Permissions | `infrastructure.md` | `core/utils/permissions.py` |
| Grading Engine | `infrastructure.md` | `core/utils/grading.py` |
| Notifications | `infrastructure.md` | `core/utils/notifications.py` |
| Cache Manager | `infrastructure.md` | `core/utils/cache_manager.py` |
| Template Tags | `infrastructure.md` | `core/templatetags/core_tags.py` |
| Management Commands | `infrastructure.md` | `core/management/commands/` |
| Cross-Cutting Concerns | `cross_cutting.md` | (spans all modules) |

## Cross-References — Multi-Module Tasks

When a task spans multiple domains, read these charters together:

| Task Pattern | Read These Docs |
|-------------|----------------|
| Grading flow (submit → grade → cascade) | `views_assignments.md` + `models_assignments.md` + `cross_cutting.md` |
| Enrollment lifecycle | `views_courses.md` + `models_courses.md` + `cross_cutting.md` |
| Analytics changes | `views_api.md` + `infrastructure.md` (cache_manager) + `cross_cutting.md` |
| Adding new assignment types | `models_assignments.md` + `views_assignments.md` + `infrastructure.md` (forms) |
| Permission changes | `infrastructure.md` (permissions) + all view charters |
| Notification changes | `infrastructure.md` (notifications) + view charters that trigger them |
| Refactoring / code health | `cross_cutting.md` + relevant per-module docs |

## Approval Protocol (MANDATORY)

Before modifying any files (except for creating a plan document), you MUST follow this sequence:

1. **Research & Plan**: Analyze the codebase and draft a plan (e.g., in `docs/`).
2. **Consult Risk Awareness**: Read `docs/reference-notes/risk-awareness.md` and append a "Risk Assessment" section to your plan.
3. **Obtain Approval**: Present the final plan to the human operator and wait for an explicit Directive (e.g., "Proceed with the plan") before executing any code changes.

## Procedures & Reference Notes — Dispatch Table

Procedures and reference notes are **not** loaded by default. Consult them when the situation matches.

| When | Type | Read this | File |
|------|------|-----------|------|
| Cold-start orientation — what is this codebase? | Procedure | About | `docs/procedures/about.md` |
| Producing a synthesized explanation of a domain or flow | Procedure | Briefing | `docs/procedures/briefing.md` |
| Architectural drift discovery (weekly, one file at a time) | Procedure | Informed Perusal | `docs/procedures/perusal.md` |
| Periodic charter accuracy audit | Procedure | Full Charter Review | `docs/procedures/full-review.md` |
| Planning a multi-domain feature or significant change | Deliberation | Plans | `docs/plans/_INDEX.md` |
| Reviewing another agent's plan | Deliberation | Plan Review | `docs/plans/_TEMPLATES/review.md` |
| After completing a plan, before presenting to human | Reference Note | Risk Awareness | `docs/reference-notes/risk-awareness.md` |
| Bootstrapping constitutional architecture on a new codebase | Reference Note | Starter Kit | `docs/reference-notes/starter-kit.md` |

**Skill shortcuts**: `/about`, `/briefing <scope>`, `/peruse <file>`, `/review-charters` — thin wrappers in `.claude/commands/` that invoke the corresponding procedure.

## Charter Status

All charters are complete as of initial project creation.

| Charter | Status |
|---------|--------|
| `models_accounts.md` | COMPLETE |
| `models_courses.md` | COMPLETE |
| `models_assignments.md` | COMPLETE |
| `views_courses.md` | COMPLETE |
| `views_assignments.md` | COMPLETE |
| `views_discussions.md` | COMPLETE |
| `views_api.md` | COMPLETE |
| `infrastructure.md` | COMPLETE |
| `cross_cutting.md` | COMPLETE |
