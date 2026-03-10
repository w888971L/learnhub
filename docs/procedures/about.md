# Procedure: About

*Generate a 3-paragraph executive summary of the entire codebase. A cold-start orientation for someone who just opened the project.*

**Invocation**: `/about`

---

## What This Produces

Three concise paragraphs:

1. **What it does** — the product, its users, the core workflow
2. **How it's built** — tech stack, file organization, governance structure
3. **What to know before changing anything** — the most dangerous patterns, the one thing that will bite you

## Source Material

Read (in order):
1. The active repo-root constitution file (`AGENTS.md`, `CLAUDE.md`, or another agent-specific equivalent) — Key Terms, Module Index tables, Conventions
2. `cross_cutting.md` — the tripwires and cascading patterns
3. Skim 2-3 charter headers (not full charters) for domain coverage

Do NOT read source code. This is a governance-layer summary, not a code walkthrough.

## Guidelines

- **3 paragraphs maximum.** If you can't say it in 3 paragraphs, you're going too deep.
- **No bullet lists.** Prose only. This reads like the opening of a technical brief, not a README.
- **Name the dangerous things.** Paragraph 3 should make someone appropriately cautious.
- **Present directly to the user.** No file output — just display the summary in the conversation.

## Cost

Negligible — reads only governance docs, no subagent needed.
