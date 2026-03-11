# Prototype: Zoom

## The Problem

The constitutional architecture is a knowledge graph — documents linked by cross-references, invariants connecting domains, propagation chains flowing through layers. But today it's navigated linearly: read a charter, follow a cross-reference, read another charter. The human operator builds the graph in their head.

At scale, this mental model breaks down. A codebase with dozens of domains, hundreds of invariants, and thousands of functions cannot be held in working memory. The operator needs a way to *see* the knowledge graph and navigate it spatially.

## The Idea

A **zoom interface** for the knowledge graph. The operator starts at the highest level — domains, their connections, major invariants — and zooms in progressively:

**Level 1 — Domain map**
The full knowledge graph. Domains as nodes, cross-cutting concerns as edges. Color-coded by health (recently verified, stale, unknown). The operator sees the shape of the system at a glance.

**Level 2 — Domain detail**
Zoom into a domain. Charters, models, views, and their relationships appear. Cross-references to other domains are visible as outgoing edges. Invariants that touch this domain are highlighted. The operator sees what a domain owns and what it depends on.

**Level 3 — Function map**
Zoom into a specific area. Major functions appear with their signatures, access patterns (R/W/RW), and cascade connections. Tripwire-marked functions are visually distinct. The operator sees the moving parts.

**Level 4 — Code**
Zoom into a function. The actual source code, with charter annotations overlaid — tripwire warnings, cross-references, line anchors. The operator is now reading code, but with the full governance context visible.

The key property: **at every zoom level, the view is relational to the starting point.** Zooming into the grading domain shows grading functions and their connections to enrollment and caching — not an alphabetical list of all functions in the codebase.

## What Would Power This

- The invariant registry (proposed in the Memex refactor plan) provides the node/edge data
- Typed references (`→ invariant:`, `→ triggers:`, `→ depends on:`) provide edge semantics
- Charter line anchors provide the bridge from knowledge graph to code
- The propagation map provides the cascade visualization

Most of the underlying data structure already exists or is proposed. The zoom interface is a visualization layer on top of it.

## Open Questions

- Web app? VS Code extension? CLI with ASCII rendering?
- Real-time or generated on demand?
- Could an agent generate a static zoom snapshot as part of a briefing?
- How does the zoom handle stale data? (Charter says function is at line 45, it's actually at line 67)
- Should the zoom interface itself be part of the constitutional architecture, or an external tool?
