# Features — Try These

Clone this repo. Open a session with any supported AI agent (Claude Code, Codex, Gemini). Try the prompts below and watch what happens.

No setup required beyond the agent itself. The constitutional architecture is already in the repo.

**A note on what you're testing:** The features below are not plugins or custom tooling. They're capabilities that emerge from the knowledge layer — the constitution, charters, cross-cutting concerns, and procedures in the `docs/` directory. The agent reads these documents, reasons against them, and produces output that would be impossible from code inspection alone. Remove the knowledge layer and the same prompts produce generic results.

---

## Instant Orientation

> "Tell me about this codebase."

The agent produces a grounded executive summary of the entire codebase — in seconds, on a fresh session. It doesn't explore the file tree or read random files. It reads the constitution and synthesizes.

**What to notice:** The summary references specific modules, conventions, and architectural decisions. This isn't generic — it's *this* codebase.

---

## Technical Briefing

> "Give me a briefing on the enrollment lifecycle."

Ask for a briefing on any domain or flow. The agent produces a multi-section technical synthesis — architecture, risks, cross-cutting concerns — grounded in charters, not guesswork.

**What to notice:** The agent cites specific functions, line numbers, and tripwire warnings. It knows where the dangers are before reading the code.

Try: "Briefing on the grade cascade", "Briefing on discussion permissions", "Briefing on analytics caching"

---

## Drift Detection

> "Peruse core/utils/grading.py — compare it against its charter."

Point the agent at any file. It compares the actual code, line by line, against the charter that describes it. Discrepancies are flagged — renamed functions, moved line numbers, undocumented behavior.

**What to notice:** The agent isn't just reading the file. It's reading the file *against a contract* and reporting violations. This is architectural drift detection, not code review.

Try: "Peruse core/models.py", "Peruse core/views_lib/courses/enrollment.py"

---

## Charter Audit

> "Review all charters against the codebase for accuracy."

The agent audits every charter in the system against the actual codebase. This is a full accuracy review — it finds real discrepancies, stale line anchors, missing functions, and undocumented behavior.

**What to notice:** The output is structured findings with verdicts, not vague suggestions. The agent is acting as an independent auditor using the governance framework as its standard.

---

## Formal Planning

> "Write a formal plan for adding a peer review system where students can review each other's submissions."

The agent will:
1. Read the plan template from `docs/plans/_TEMPLATES/plan.md`
2. Check cross-cutting concerns for cascade risks
3. Identify affected domains and charters
4. Produce a structured proposal with risk assessment

**What to notice:** The agent doesn't just design the feature. It designs the feature *within the governance framework* — checking what existing systems it will affect, what invariants it must respect, what documentation it will need to update.

---

## Multi-Agent Review

After one agent writes a plan, ask a different agent to review it:

> "Review the peer review plan in docs/plans/."

The second agent reads the plan, evaluates it against the charters and cross-cutting concerns, and produces a structured review with a verdict: approve, approve with concerns, or reject.

**What to notice:** Two different models, possibly from different providers, reasoning about the same codebase using the same governance framework. They coordinate through documents, not direct communication.

---

## What You're Seeing

Every feature above is powered by markdown files in the `docs/` directory that agents read, reason against, and maintain.

The constitutional architecture gives agents:
- **Orientation** in seconds instead of minutes (constitution + dispatch table)
- **Grounded reasoning** against documented contracts instead of inference from code alone
- **Coordination** across agents and sessions through shared governance documents
- **Self-maintenance** — the same agents that consume the knowledge layer update it as they work

For the full explanation, see the [README](README.md).
