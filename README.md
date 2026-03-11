# LearnHub

> **[Development Log](docs/dev-log.md)** — daily summaries of what changed and why.

A Django learning management system — and a reference implementation for **constitutional architecture**, a governance pattern for AI-assisted software development.

The application is real and functional (courses, enrollments, assignments, grading, discussions). The architecture documentation is the showcase.

---

## From Memex to Constitutional Architecture

In 1945, Vannevar Bush published *"As We May Think"* in The Atlantic. He described the **Memex** — a hypothetical device where a researcher could store documents and, critically, create **associative trails** between them. Bush's insight wasn't about storage. Filing cabinets already stored things. His insight was that knowledge becomes powerful through *links* — when navigating one document naturally surfaces related documents, warnings, and context that the researcher would not have thought to look for.

> "The human mind operates by association. With one item in its grasp, it snaps instantly to the next that is suggested by the association of thoughts."
> — Vannevar Bush, *As We May Think* (1945)

The web partially realized this vision for humans. Hyperlinks let people follow associative trails through knowledge. But we now have a new class of knowledge worker — the AI coding agent — and it faces the same problem Bush identified 80 years ago.

When an AI agent encounters a task, it reads code. Code tells you *what* exists. It does not tell you:

- **What will break** if you change this function (non-obvious dependencies across modules)
- **What's deceptive** about this value (a score field that stores penalty-adjusted values, not raw scores)
- **What else must change** when you change this (a cache that must be invalidated, a downstream document that must be updated)
- **What to read first** before attempting a category of change

These are exactly the kinds of associative connections Bush wanted the Memex to provide. Without them, AI agents make changes that look correct in isolation but break things they didn't know were connected.

Constitutional architecture is, in a practical sense, **a Memex for AI-assisted development**.

### The Layers

| Layer | Bush's Memex Analog | Purpose |
|-------|-------------------|---------|
| **Constitution** (`AGENTS.md`, `CLAUDE.md`, or another agent-specific root file) | The desk — starting point with an index of all trails | Routes the agent to relevant knowledge based on the task at hand |
| **Charters** (`docs/architecture/modules/`) | Core reference documents with margin annotations | Per-domain API reference with tripwire warnings and cross-references |
| **Cross-cutting concerns** (`cross_cutting.md`) | Associative trails linking documents across topics | Documents invisible dependencies between domains |
| **Procedures** (`docs/procedures/`) | Repeatable research protocols | Executable practices with prompt templates |
| **Reference notes** (`docs/reference-notes/`) | Researcher's judgment notes | Cognitive aids consulted at decision points |
| **Public record** (`docs/flows/`) | Published summaries for colleagues | Human-readable walkthroughs of how features work |
| **Enforcers** | Peer review by a different researcher | Independent verification that knowledge stays consistent |

### Associative Trails in Practice

Bush's trails were links between documents that a researcher created as they worked. In constitutional architecture, these trails are formalized:

**Cross-references** (`→`) connect related concepts across charters:
```
### apply_grade(submission, raw_score, grader)
Creates Grade record with penalty-adjusted score.
! The instructor sees raw_score in the form, but Grade.score is penalty-adjusted.
→ see cross_cutting.md "Late Penalty Timing"
```

**Tripwire warnings** (`!`) are Bush's margin annotations — notes that say "this is not what you think it is." They interrupt the agent's assumptions before those assumptions become bugs.

**The dispatch table** in the constitution maps task patterns to document sets — "if you're working on grading, read these three charters together." This is the Memex's associative index: given what you're doing, here's the trail to follow.

**The propagation map** tracks how changes ripple through the knowledge layer — when a charter changes, which downstream documents need updating. Bush envisioned trails as static once created. The propagation map makes them *maintainable*.

### Why Now — The Super-Archivist

Bush could not build the Memex. The physics of 1945 were not the obstacle — the *labor* was. Creating associative trails between documents, maintaining them as knowledge evolved, verifying their consistency — this required a dedicated archivist who could read everything, understand the connections, and update them in real time. No human could do this at scale. The trails would go stale, the links would rot, and the Memex would decay into a filing cabinet with dead references.

For eighty years, that problem had no solution. Until now.

AI coding agents are the first workers capable of serving as both **knowledge consumers and knowledge curators** simultaneously. When an agent follows a charter's cross-reference to discover a tripwire, it is *using* the Memex. When that same agent updates the charter after changing the code it describes, it is *maintaining* the Memex. This dual role — reader and archivist in the same action — is what makes constitutional architecture viable where Bush's original vision was not.

The constitution encodes this as a rule: *make the change, then update the knowledge layer*. The agent doesn't maintain the Memex as a separate task — it maintains the Memex as a natural consequence of doing its work. The living docs update chain (code change → charter update → flow doc update) is not bureaucracy. It is the mechanism that keeps the associative trails alive.

This is the specific break from conventional agent memory. Most approaches to inter-session agent memory focus on *loading* — vector stores, RAG pipelines, embedding retrieval, session summaries injected into context. They solve the problem of "how do I get relevant information in front of the agent?" Constitutional architecture solves a different problem: **"how does the agent know what to look for before it looks?"** The constitution, charters, and cross-references act as *routing indexes* — cheat cards that narrow the search space before the agent reads a single line of code. An agent doesn't need the entire codebase retrieved into its context. It needs to know that touching the grading flow requires reading three specific documents first, that a cached value is not the source of truth, and that a cascade of side effects must be triggered in a specific order. The Memex provides this orientation layer, and because the agents maintain it as they work, it stays current without an external retrieval system.

### What This Is Not

- **Not prompt engineering.** Prompts tell an AI what to *do*. The constitution tells it what to *know*. Knowledge shapes judgment across every task, not just the one a prompt was written for.
- **Not documentation.** Documentation is written for humans to read linearly. Charters are written for AI agents to consult associatively — compact notation, line anchors, tripwire markers, cross-references. The format is optimized for a different kind of reader.
- **Not "just skills files."** Skills execute procedures. The constitutional architecture provides the knowledge that makes those procedures (and all other work) correct. A skill says "run this." A charter says "here's what you'll get wrong if you don't understand this first."

---

## Prompt Zero — Onboarding an AI Assistant

The first time you point an AI assistant at this project:

> Read the active repo-root constitution file first (`AGENTS.md` for Codex, `CLAUDE.md` for Claude Code). It will tell you where everything is, what the key terms mean, and which charters to read for each domain. Before making any code changes, check cross_cutting.md for tripwires — non-obvious patterns that will break if you assume the obvious.

**Reading order for the AI:**
1. The active repo-root constitution file (`AGENTS.md`, `CLAUDE.md`, etc.) — the constitution (master index, conventions, cross-references)
2. `docs/architecture/modules/cross_cutting.md` — tripwires and cache dualities (read before touching anything)
3. The relevant domain charter(s) for whatever you're working on
4. The relevant flow doc(s) in `docs/flows/` for business context

**To adopt this architecture for your own project**, say:
> Read the constitutional architecture in this repository (the repo-root constitution file, docs/architecture/modules/, docs/flows/) and build the same governance structure for my codebase. Start with a constitution, then write charters for each domain, then write flow docs for the key user journeys.

---

## The Control Study

This repository includes a control study comparing AI agent performance with and without constitutional architecture. The same feature — **grade forgiveness** (dropping a student's lowest assignment grade) — is planned by two agents:

1. **Control**: Claude Code with the raw codebase, no constitutional architecture
2. **Constitutional**: Claude Code with the full constitution, charters, and cross-cutting concerns

The feature was chosen because it crosses multiple domains (grading, enrollment, caching, analytics) and contains non-obvious tripwires (penalty-adjusted scores, cache invalidation chains, late penalty timing) that are documented in the constitution but invisible in the code alone.

Results are in `docs/experiments/experiment-1/`.

---

## The Tripwires

These are the non-obvious patterns that will break if you assume the obvious:

1. **Grade Cache Duality** — `Enrollment.final_grade_cache` is NOT the source of truth. Grade records are. The cache must be explicitly recalculated after any grade change.

2. **Late Penalty Timing** — Penalties are applied at GRADING time, not submission time. A late submission is accepted normally; the penalty appears only when the instructor grades it.

3. **Grade Cascade** — Finalizing a grade triggers: recalculate_grade_cache → invalidate_course_analytics. Skip a step and data goes stale.

4. **Enrollment State Machine** — Transitions are enforced in views, not models. Django admin bypasses the state machine entirely.

All four are documented in detail in `docs/architecture/modules/cross_cutting.md`.

---

## Project Structure

```
learnhub/
├── AGENTS.md                              # Codex constitution
├── CLAUDE.md                              # Claude Code constitution
├── GEMINI.md                              # Gemini constitution
├── config/                                # Django settings, URLs, WSGI
├── core/
│   ├── models.py                          # All 16 models (~950 lines)
│   ├── views.py                           # Import router
│   ├── urls.py                            # 30 URL patterns
│   ├── forms.py                           # 9 Django forms
│   ├── admin.py                           # Admin registration
│   ├── middleware.py                       # Activity tracking, course loading
│   ├── context_processors.py              # Template context
│   ├── templatetags/core_tags.py          # Custom template tags
│   ├── views_lib/
│   │   ├── courses/                       # Catalog, enrollment, management
│   │   ├── assignments/                   # Submission, grading
│   │   ├── discussions/                   # Threaded forums
│   │   ├── api/                           # JSON API endpoints
│   │   ├── auth/                          # Registration, login, logout
│   │   └── dashboard/                     # Student dashboard, analytics
│   ├── utils/
│   │   ├── permissions.py                 # Role-based access decorators
│   │   ├── grading.py                     # Grade engine (late penalty!)
│   │   ├── notifications.py              # Notification dispatch
│   │   └── cache_manager.py               # Analytics cache
│   └── management/commands/
│       ├── seed_data.py                   # Sample data generator
│       └── grade_report.py                # Grade reporting
├── templates/                             # Tailwind CSS templates
├── docs/
│   ├── architecture/modules/              # 9 charter documents
│   ├── flows/                             # 3 public record documents
│   ├── procedures/                        # Executable procedures
│   └── reference-notes/                   # Judgment aids
└── requirements.txt                       # Django 5.1
```

## Quick Start

```bash
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Demo Credentials

The `seed_data` command creates sample users with password **`testpass123`** for all accounts:

| Username | Role | Organization |
|----------|------|-------------|
| `prof_chen` | Instructor | Acme University |
| `prof_garcia` | Instructor | Acme University |
| `prof_jones` | Instructor | TechCorp Academy |
| `prof_smith` | Instructor | TechCorp Academy |
| `prof_wilson` | Instructor | Acme University |
| `student_01` | Student | TechCorp Academy |
| `student_02` | Student | Acme University |
| ... through `student_20` | Student | Mixed |

## Domain Overview

| Domain | Models | What it does |
|--------|--------|-------------|
| Accounts | User, Organization, InstructorProfile | Multi-role user system with organizations |
| Courses | Course, Module, Lesson, Enrollment | Course catalog, content structure, enrollment state machine |
| Assignments | Assignment, Submission, Grade | Assignment submission with versioning, grading with late penalties |
| Discussions | Thread, Post, Reaction | Threaded course discussion forums |
| Notifications | Notification, NotificationPreference | In-app notifications with preferences |
| Analytics | CourseAnalytics | Cached course-level aggregates |

## Further Reading

- Vannevar Bush, [*"As We May Think"*](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/), The Atlantic, July 1945
- Doug Engelbart, *"Augmenting Human Intellect: A Conceptual Framework"*, SRI, 1962 — extended Bush's vision to interactive computing
- Cumberland Laboratories, [*"Constitutional Architecture for AI-Assisted Development"*](https://cumberlandlaboratories.substack.com/p/constitutional-architecture-for-ai) — the source paper describing this governance pattern
- The constitution itself: start with the active repo-root constitution file and follow the trails

## License

MIT — use this architecture pattern freely.
