# Reference Note: Risk Awareness

*Consult after completing a plan, before presenting to the human operator.*

---

## Purpose

This note provides a framework for evaluating the risk of a planned change. It is not a checklist — it's a set of questions that surface risks the plan may not have considered.

## Risk Dimensions

### Blast Radius
- How many files does this change touch?
- How many domains (per the module index) are affected?
- Are any cross-cutting concerns involved? (Check `cross_cutting.md`)
- Could this change affect behavior in a domain not listed in the plan?

### Reversibility
- Can this change be reverted with a single `git revert`?
- Does it involve database migrations? (Migrations are hard to reverse cleanly)
- Does it modify shared state (session, cache, database) in ways that affect other features?

### Confidence
- Has the plan been validated against the relevant charters?
- Are there tripwire warnings (!) in the charters that apply?
- Does the plan assume behavior that should be verified by reading code?
- Is there test coverage for the affected code paths?

### Human Impact
- Does this change affect user-facing behavior?
- Could it affect data integrity (grades, scores, financial records)?
- Does it touch authentication, authorization, or security boundaries?

## How to Use

After drafting a plan, read through each dimension. If any question surfaces a concern, note it in the plan and flag it for the human operator. The goal is not to prevent all risk — it's to ensure risk is **visible and acknowledged** before execution.
