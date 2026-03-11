# Review: Memex Architecture Refactor

**Reviewer:** Gemini
**Date:** 2026-03-11
**Plan reviewed:** docs/plans/2026-03-11-memex-architecture-refactor/plan.md

---

## Verdict

**approve-with-concerns**

## Summary

The proposed refactor is a high-signal evolution that addresses the primary scaling bottleneck of the current architecture: "semantic overload" in the cross-cutting documentation. Transitioning from a monolithic warehouse to a structured, typed invariant network will significantly reduce agent retrieval noise and inference costs. My primary concern is the potential for "governance sprawl"—specifically the overlapping roles of the Invariant Registry, the Propagation Map, and the revised Cross-cutting Index.

## Section-by-Section

### Problem Statement
- [x] Agree with framing
- Comments: The diagnosis of "retrieval noise" is accurate. Agents currently consume unnecessary context when searching for domain-specific invariants.

### Scope
- [x] Scope is appropriate
- Comments: Focusing strictly on the governance layer prevents this from becoming an intrusive codebase refactor.

### Affected Domains
- [ ] All affected domains identified
- Missing domains: **Root Constitution Files (`GEMINI.md`, `CLAUDE.md`, etc.)**. The "Dispatch Table" in these files is the entry point for all agent work. If `cross_cutting.md` becomes an index, the dispatch tables must be updated to route agents to the new focused invariant docs.

### Cross-Cutting Concerns
- [x] All relevant tripwires identified
- [x] Mitigations are adequate
- Comments: Identifying "Memex routing integrity" as a new cross-cutting concern is a sophisticated touch.

### Proposed Approach
- [x] Steps are in the right order
- [ ] No missing steps
- Concerns: **Step 3 (Typed References)** is the most valuable part of the plan, but it lacks a defined grammar. To be "machine-readable," these tags should have a consistent format (e.g., `[→ invariant: name]`) that an Enforcer can regex-match without full-model inference.
- Concerns: **Step 4 (Invariant Registry)** feels redundant with an improved **Step 6 (Propagation Map)**. I recommend merging these into a single "Active Propagation Registry" to avoid maintaining two separate mapping files for the same relationships.

### Data Model Changes
- [x] No unnecessary schema changes
- Comments: Correct. This is a metadata-only refactor.

### Risk Assessment
- [x] Risks are realistic
- Comments: "Fragmentation making orientation worse" is the highest risk. The "Index" must be the absolute single source of truth for routing.

### Testing Strategy
- [x] Covers the critical paths
- Comments: The "Reference clarity test" is essential. If a sub-agent cannot explain a link based *only* on its type, the system has failed.

## Charter Verification

| Charter | Contradiction or Concern |
|---------|------------------------|
| `infrastructure.md` | Currently documents `rebuild_course_analytics` inaccurately (as discovered in experiment-1). This refactor is the perfect time to fix the "Dual Calculation Path" tripwire documentation as part of the new `cross_cutting_caching.md`. |

## Alternative Approach (if applicable)

**Consolidate Mapping Layers:** Instead of a separate Invariant Registry, add "Invariant Headers" to the existing Charters. An Enforcer can then crawl the Charters to build a virtual registry on the fly, reducing the number of files that require manual synchronization. This follows the "Source of Truth" principle used in the Django models.
