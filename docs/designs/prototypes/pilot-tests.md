# Prototype: Pilot Tests

## The Problem

In AI-assisted development, the bottleneck is no longer coding speed. Agents can produce code fast. The problem is **catastrophic failure modes** when plowing ahead with changes that interact with non-obvious system invariants. A plan can look perfect on paper and still break things that weren't visible at planning time.

Traditional software development mitigates this with code review and testing *after* implementation. But when agents can implement a 15-step plan in minutes, the blast radius of a wrong assumption is enormous before any review happens.

## The Idea

Introduce **pilot tests** — small, surgical tests executed *after* a plan is approved but *before* significant coding begins. The goal is to tease out actual system behavior and validate assumptions before committing to implementation.

This is the software equivalent of a clinical trial's Phase I: don't test the full treatment on everyone. Test a small, controlled intervention first and see what happens.

## Levels

**Level 1 — Observation only (no code changes)**
- Read specific code paths the plan will modify
- Trace a function call through its full cascade
- Verify that documented invariants match actual code behavior
- Run existing tests to establish a baseline
- Example: "Before implementing the peer review system, trace what happens when `apply_grade()` is called — does the cascade actually fire in the order the charter says?"

**Level 2 — Surgical intervention (minimal, reversible code changes)**
- Add a temporary logging statement to observe runtime behavior
- Create a throwaway test that exercises the specific interaction the plan depends on
- Make a single, isolated change and observe side effects
- Example: "Add a test that creates two final grades for the same assignment and verify that `calculate_course_grade()` handles it correctly — the plan assumes it does."

**Level 3 — Prototype spike (small implementation fragment)**
- Implement the riskiest piece of the plan in isolation
- Build one model and test its interaction with existing models
- Wire one view and verify the template/URL/permission chain works
- Example: "Create the `MasteryLevel` model, run migrations, and verify that the foreign key relationships to Enrollment and Module work as expected before building the recommendation engine."

## Open Questions

- How formal should pilot test results be? A note in the plan directory? A structured report?
- Should pilot tests be required for all plans, or only plans that touch cross-cutting concerns?
- Can pilot tests be automated as part of the plan approval workflow?
- What's the right relationship between pilot tests and the enforcer framework?
