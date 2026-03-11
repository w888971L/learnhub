# Plan: Memex Architecture Refactor

**Author:** Codex
**Date:** 2026-03-11
**Status:** draft

---

## Original Request

> What would be your best practice to maintain the integrity of the charter documents?
>
> Where do you see the human in this process?
>
> Do you have any ideas on a more optimal Memex? Right now there is a single cross-cutting charter. Should there be more? Is the referencing system inefficient?
>
> may I have a formal plan about this? Those are good ideas.

## Problem Statement

The current constitutional architecture is usable, but its Memex layer is starting to concentrate too much semantic load in a single `cross_cutting.md` file with lightly typed references. That creates retrieval noise, mixes durable invariants with transient findings, and makes propagation harder to reason about as the governance surface grows. The architecture needs a clearer invariant model, better routing between governance artifacts, and a lightweight enforcement path that scales without turning into documentation bureaucracy.

## Scope

| In scope | Out of scope |
|----------|-------------|
| Refactoring the governance-layer Memex structure | Application feature work in Django code |
| Splitting cross-cutting knowledge into a clearer index + focused invariant docs | Rewriting all existing charters for style only |
| Improving reference semantics and navigation patterns across charters | Building a full graph database or search UI |
| Defining a first-pass invariant registry and propagation model | Replacing the existing plans framework |
| Establishing an enforcement workflow for Memex integrity | Automated auto-fix of stale governance docs |

## Affected Domains

| Domain | Charter | Impact |
|--------|---------|--------|
| Cross-Cutting Concerns | `cross_cutting.md` | Becomes a routing/index layer instead of a warehouse for all cross-domain truth |
| Infrastructure | `infrastructure.md` | Documents the invariant registry, propagation model, and enforcement workflow if adopted |
| Assignment Views / Models | `views_assignments.md`, `models_assignments.md` | Gain more precise links into grading-specific invariants |
| Course Views / Models | `views_courses.md`, `models_courses.md` | Gain more precise links into enrollment/caching invariants |
| Public Record | `docs/flows/*.md` | May require revised propagation rules and stronger linkage to invariant docs |

## Cross-Cutting Concerns

- [x] Grade Cache Duality
- [x] Late Penalty Timing
- [x] Grade Cascade
- [x] Enrollment State Machine
- [x] Other: **Memex routing integrity** — the architecture must preserve fast, reliable navigation between stable invariants, procedural guidance, and human-facing flow docs.

All four existing tripwires are directly implicated because they are the initial candidates for extraction into focused invariant documents. The plan preserves them as first-class architectural truths while making them easier to locate, reference, and enforce. The additional concern is routing integrity itself: if references become fragmented or ambiguous, the Memex degrades even if the underlying content is still correct.

## Proposed Approach

### Step 1: Reframe `cross_cutting.md` as an index of invariants

Keep `docs/architecture/modules/cross_cutting.md`, but narrow its role.

Change it from a mixed document containing:
- invariant definitions
- rationale
- operational caveats
- pending issues

into a compact index that:
- lists each major invariant/tripwire
- gives a one-paragraph summary of why it matters
- routes the reader to the focused invariant document
- names the primary source modules and downstream flow docs

This preserves the current "read this first" behavior while reducing retrieval noise.

### Step 2: Split stable invariant families into focused cross-cutting documents

Add a small set of focused governance docs, each centered on a real invariant family rather than a technical layer. Initial candidates:

- `docs/architecture/modules/cross_cutting_grading.md`
- `docs/architecture/modules/cross_cutting_enrollment.md`
- `docs/architecture/modules/cross_cutting_caching.md`
- `docs/architecture/modules/cross_cutting_notifications.md`

Rules for what belongs there:
- stable behavioral truths
- cascades and side effects
- source-of-truth vs cache distinctions
- tripwires that span multiple modules

Rules for what does not belong there:
- stale bug inventories
- one-off audit findings
- temporary implementation notes

This turns one broad cross-cutting file into a thin index plus a small number of high-signal invariant docs.

### Step 3: Introduce typed references

Replace purely generic `→ see ...` links with a constrained vocabulary that explains why the link exists. Proposed reference types:

- `→ invariant:` stable truth implemented elsewhere
- `→ depends on:` upstream concept this behavior relies on
- `→ triggers:` side effect or downstream cascade
- `→ updates:` document or cache that must be propagated
- `→ flow:` human-facing public record for the same behavior

The goal is not syntax novelty for its own sake. The goal is to reduce inference work for future agents by making edge semantics explicit.

### Step 4: Add a lightweight invariant registry

Create a compact registry file, for example:

- `docs/architecture/invariant_registry.md`

Each entry should capture:
- invariant name
- brief description
- primary docs
- enforcing code paths
- side effects / cascades
- likely failure modes
- dependent flow docs

This becomes the fastest orientation surface for agents and humans working on cross-domain changes. It also gives enforcers a declared object model instead of forcing them to infer invariants from prose.

### Step 5: Separate durable architecture from transient findings

Move "Known Issues" and similar audit residue out of `cross_cutting.md` and into a more appropriate artifact, such as:

- plan review findings
- `docs/architecture/review_scratchpad.md`
- a dedicated drift/issues register if the team wants one later

The Memex should store durable knowledge, not accumulate every discovered flaw. Mixing the two makes the architecture feel authoritative while quietly aging.

### Step 6: Strengthen propagation metadata

Expand `docs/architecture/propagation_map.md` so it is not only charter-to-flow, but also invariant-aware. For each invariant family, declare:
- source charter(s)
- focused invariant doc
- dependent flow docs
- likely enforcement target

This gives the enforcer a cleaner orientation path:
changed charter -> affected invariant(s) -> downstream flow docs/public record.

### Step 7: Add a first-pass Memex integrity enforcer

Define the first practical enforcement loop as:

1. detect changed charter(s) or invariant doc(s)
2. resolve affected invariant family via the registry/propagation map
3. verify mapped flow docs still reflect the current invariant truth
4. report `STALE`, `MISSING`, or `OK`

The enforcer remains read-only and model-independent. This is the minimum viable enforcement path that checks whether the Memex still propagates architectural truth correctly.

### Step 8: Roll out incrementally

Do not rewrite all governance docs at once. Use a phased migration:

1. create the invariant registry
2. convert `cross_cutting.md` into an index
3. extract grading and enrollment first (highest-value invariants)
4. update affected charters to use typed references
5. update the propagation map
6. trial the enforcer on one changed invariant family
7. only then decide whether caching and notifications need their own focused docs

This avoids a documentation migration that outruns the repo's actual complexity.

## Data Model Changes

None. This is governance-layer architecture only.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Over-structuring the Memex before the repo needs it | medium | medium | Start with index + 2 focused invariant docs, not a full taxonomy |
| Fragmentation makes orientation worse instead of better | medium | high | Keep `cross_cutting.md` as the single entry point and require bidirectional links |
| Typed references become inconsistent across charters | medium | medium | Define a small fixed vocabulary and document it in the constitution or infrastructure charter |
| Invariant docs drift from source charters | medium | high | Treat invariant docs as first-class governance artifacts in `/review-charters` and enforcement |
| Transient findings continue leaking into durable docs | high | medium | Explicitly move issue tracking to review artifacts or a separate drift register |

## Testing Strategy

1. **Orientation test:** Give a fresh agent a cross-domain change request and compare whether it reaches the right invariant docs faster than with the current single-file cross-cutting structure.
2. **Propagation test:** Modify one charter linked to grading, then run the enforcer and confirm it correctly identifies which flow docs need verification.
3. **Reference clarity test:** Sample several typed references and verify that a second agent can explain the relationship without reading surrounding prose.
4. **Noise test:** Compare the length and relevance of retrieved governance context before and after the refactor for tasks in grading and enrollment.
5. **Drift test:** Run `/review-charters` after extracting the first two invariant docs and confirm the new structure does not create duplicate or contradictory claims.

## Open Questions

1. Should the invariant registry live under `docs/architecture/` as a shared routing file, or under `docs/architecture/modules/` as a charter-like artifact?
2. Should typed references be introduced as soft convention first, or enforced immediately across all updated charters?
3. Is notifications mature enough to deserve its own focused invariant doc now, or should the first rollout stop at grading/enrollment/caching?
4. Should a dedicated drift register be introduced now, or is it sufficient to keep transient issues in plans/reviews until volume increases?
