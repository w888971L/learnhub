# Reference Note: Starter Kit

*How to bootstrap constitutional architecture on a new codebase.*

---

## Minimum Viable Constitution

A constitutional architecture needs three things to start:

1. **Constitution** (an agent-specific file such as `AGENTS.md` or `CLAUDE.md` at repo root) — conventions, key terms, module index
2. **One cross-cutting charter** (`cross_cutting.md`) — the dangerous patterns that span modules
3. **One domain charter** — pick the highest-traffic or most complex domain first

Everything else (public record, procedures, reference notes, enforcers) can be added incrementally. Enforcers in particular should only be added once there are both charters and public record docs to verify propagation between.

## Bootstrap Order

1. Write the constitution — conventions, file structure, key terms
2. Write `cross_cutting.md` — what's dangerous, what's coupled, what breaks if you don't know about it
3. Write 2-3 domain charters for the most important modules
4. Write 1 public record flow doc for the most common user journey
5. Add the dispatch table and cross-references to the constitution
6. Add procedures as the team needs them (briefing, perusal, full review)

## Document Hierarchy

```
Constitution (always loaded)
├── Charters (frequently referenced, per-domain)
├── Procedures (executable practices, invoked on demand)
├── Enforcers (consistency checks, run by independent agent)
├── Reference Notes (cognitive aids, consulted situationally)
└── Public Record (human-readable flows)
```

**Enforcer independence**: Enforcers must be run by a different agent/model than the one that made the changes. Self-review is not enforcement. Add enforcers once you have both charters and public record docs to verify propagation between.

## Principles

- **Code is truth** — if docs and code disagree, code wins
- **Domain concept first, file path second** — organize by what the code does, not where it lives
- **Living docs** — update chain is Code → Charter → Public Record in the same session
- **Incremental** — start small, add as needed. A partial constitution is better than none.
