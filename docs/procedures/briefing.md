# Procedure: Briefing

*Synthesize a domain or flow explanation that no single document contains. The "lunch & learn" for AI-assisted teams.*

**Invocation**: `/briefing <scope>` (e.g., `/briefing grading-flow`, `/briefing enrollment`)

---

## What This Produces

A technical brief — structured, readable, opinionated — covering not just *what* a system does but *why* it works this way, *what's non-obvious*, *what's risky*, and *where it connects to things you wouldn't expect*.

## Briefing Structure

1. **Executive Summary** (2-3 sentences) — what and why
2. **Architecture Overview** — components, interactions, file paths in service of narrative
3. **Key Design Decisions** — the "why" that gets lost when the original developer leaves
4. **Non-Obvious Behavior** — tripwires and surprises, explained in context
5. **Risk Profile** — fragility, missing coverage, coupling points
6. **Technical Debt & Opportunities** — what's suboptimal, what you'd change
7. **Connections** — cross-domain touches that aren't obvious from code structure

## Source Material

Load in order:
1. Relevant charter(s) from `docs/architecture/modules/`
2. `cross_cutting.md` — tripwires, coupling points
3. Public record doc from `docs/flows/` (if one exists)
4. Targeted source code reads from key files identified by charters

Use the Cross-References table in the constitution to identify which charters to load.

## Agent Configuration

Dispatch a subagent (Sonnet is adequate for synthesis):

```
You are producing a technical briefing on [SCOPE].

Read all source material, then produce a briefing following the 7-section structure.

Guidelines:
- Write for a technical audience that is smart but unfamiliar with this system
- Be specific — reference actual function names, file paths, line numbers
- Be opinionated about design quality
- Highlight connections to other domains that would surprise a newcomer
- If you find something the charter doesn't document, note it as a finding
- Include an Author line in the metadata header identifying which agent produced the briefing
- Target length: 800-1500 words
```

## Output

Write to `docs/briefings/[scope-name].md` with metadata header:
```
Author: [agent name] (e.g., Claude, Codex, Gemini)
Last produced: YYYY-MM-DD
Charter sources: [list]
```

## Quality Guidelines

- **Explain the "why" behind non-obvious patterns**, not just that they exist
- **Cover all entry points into a flow** — missing an entry point leaves an incomplete mental model
- **Separate product gaps from technical debt** — categorize honestly
- The test: does the briefing contain understanding you can't get from any single existing document?

## Governance Status

Briefings are **NOT living documents**. They are point-in-time snapshots. Do not reference them from charters or add them to any update chain. Re-run when fresh understanding is needed.

## Cost

~$0.02-0.05 per briefing (Sonnet). ~2-5 minutes.
