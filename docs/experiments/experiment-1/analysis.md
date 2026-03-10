# Control Study Analysis: Grade Forgiveness Feature

*Comparing implementation plans for the same feature across three conditions: constitutional architecture (Claude Code + full constitution), control (Claude Code + raw codebase), and cross-model (Gemini + constitution provided as gemini.md).*

---

## Part 1 — Constitutional Agent's Analysis of the Control Plan

### What the control plan gets right

- Correctly identifies `calculate_course_grade` as the core change
- Uses lowest **percentage**, not raw score (good instinct)
- Mentions `bulk_recalculate_course_grades` for retroactive toggling
- Notes that `final_grade_cache` will reflect forgiveness after recalculation
- Good UI thinking (show both with/without, "dropped" badge)

### What's missing or wrong

**1. The cascade on toggle (partially missed)**

The control plan says toggling "recalculates all enrolled students via `bulk_recalculate_course_grades`" in the design decisions table — but **never says where this code goes**. Step 3 in the implementation order just says "course settings form + view for instructors." There's no mention of detecting that `grade_forgiveness` changed and triggering the cascade in the view's post-save logic. The constitutional plan explicitly calls out: check if the field changed, then call `bulk_recalculate_course_grades(course)` **and** `invalidate_course_analytics(course)`.

**2. `invalidate_course_analytics` — completely absent**

The control plan never calls `invalidate_course_analytics(course)` when the setting is toggled. It mentions analytics consistency in step 5, but proposes modifying `rebuild_course_analytics` to use forgiveness-aware calculation.

**[CORRECTION — see Part 8]**: The constitutional agent's original analysis here was wrong. The control plan's proposal to modify `rebuild_course_analytics` was actually *correct* — that function reads directly from Grade records, not from `Enrollment.final_grade_cache`. The constitutional agent trusted an inaccurate charter rather than reading the code. See Part 8 for the full independent referee findings.

**3. Late penalty awareness — not mentioned**

The control plan never addresses the fact that `Grade.score` is penalty-adjusted. This is fine here — it happens to not matter for the implementation — but the plan doesn't **know** it doesn't matter. It never considered the question. The constitutional plan explicitly confirms: "the adjusted score is the correct value to compare. No special handling of late penalties is needed." That's the difference between being correct by luck and being correct by analysis.

**4. Over-engineering: `forgiveness_drop_count`**

The control plan adds `forgiveness_drop_count` (IntegerField, default 1) for "future flexibility." The constitutional plan deliberately avoids this: "If future requirements need 'drop N lowest', this can be upgraded — but don't build that now." This is a minor point, but it shows how the architecture encourages restraint. The extra field means an extra migration column, extra form validation, extra edge cases in `calculate_course_grade` (drop N requires sorting and slicing, not just finding a minimum), and extra test surface — all for a requirement that doesn't exist.

**5. Analytics refactor proposal**

Step 5 proposes making `rebuild_course_analytics` call `calculate_course_grade` per enrollment instead of using raw grade averages.

**[CORRECTION — see Part 8]**: This was not unnecessary work. `rebuild_course_analytics` reads directly from Grade records (not `final_grade_cache`), so it does need forgiveness-aware treatment. The constitutional agent dismissed this as "wasted work" based on an inaccurate charter claim. The control plan was directionally correct on this point.

**6. No doc update awareness**

No mention of updating any documentation. The constitutional plan includes a step for updating 4 docs (models charter, infrastructure charter, cross_cutting, grading flow). This is expected — the control repo has no living docs convention.

**7. No risk assessment**

No blast radius analysis, no reversibility consideration, no explicit validation against known tripwires. The control plan moves straight from design to implementation order.

### Side-by-side summary

| Dimension | Control | Constitutional |
|-----------|---------|----------------|
| Core calculation logic | Correct | Correct |
| Cascade on toggle | Mentioned but not placed in code | Explicit: where, when, what functions |
| Analytics invalidation | Missed `invalidate_course_analytics` but correctly identified `rebuild_course_analytics` needs updating | Called `invalidate_course_analytics` (but `bulk_recalculate` already rebuilds analytics internally) |
| Late penalty interaction | Not considered | Considered and confirmed safe |
| Over-engineering | `forgiveness_drop_count` added speculatively | Deliberately deferred |
| Analytics rebuild awareness | Correctly identified `rebuild_course_analytics` needs forgiveness-aware logic | Incorrectly assumed `rebuild_course_analytics` reads from `final_grade_cache` (trusted inaccurate charter) |
| Doc updates | None | 4 documents identified |
| Risk assessment | None | Blast radius, reversibility, confidence evaluated |

The control plan would *work* — after debugging the stale analytics cache. The constitutional plan would work on the first pass.

---

## Part 2 — Control Agent's Self-Assessment After Reading the Constitutional Plan

*The control agent (learnhub2) was presented with the constitutional plan and asked for observations.*

### Where it acknowledged the constitutional plan is better

1. **Simpler model choice, with reasoning.** It deliberately uses just a BooleanField and explains why not to over-engineer with `forgiveness_drop_count` yet. My plan added the integer field preemptively — that's speculative complexity with no current requirement.

2. **Late penalty tripwire callout.** It explicitly identifies that `Grade.score` is already penalty-adjusted and confirms this is a non-issue. My plan never mentioned this, which could cause confusion during implementation ("should we compare pre- or post-penalty scores?").

3. **Cascade on toggle — the #1 risk.** The constitutional plan makes this the star of the show: when an instructor toggles `grade_forgiveness`, you must call `bulk_recalculate_course_grades` + `invalidate_course_analytics`. My plan mentions "retroactive" in a table row but doesn't flag it as a critical risk or specify where the cascade trigger code goes (the course edit view's save handler).

4. **Risk assessment section.** Blast radius, reversibility, data integrity risk, and "what could still surprise us" — none of this is in my plan. This is genuinely useful for deciding whether to proceed and what to watch for during review.

5. **Charter/doc updates.** It calls out specific documentation files to update. My plan ignores the living docs entirely.

6. **Precise file locations.** It names exact files and line numbers (e.g., `core/views_lib/courses/management.py`). My plan is vaguer — "course settings page" without specifying which view handles it.

### Where it defended its own plan

1. **Analytics consistency.** It flagged that `rebuild_course_analytics` should use `calculate_course_grade` per enrollment rather than raw grade averages. The constitutional plan mentions invalidating analytics but doesn't address whether the rebuild logic itself needs adjustment.

2. **Student UX detail.** Showing "78% → 82% with lowest dropped" gives the student more context than just a "dropped" badge. Minor, but a nice touch for the template step.

3. **Notifications.** It mentioned optionally notifying students when forgiveness is toggled. The constitutional plan doesn't cover this.

### What the control agent said it would change

> If I were to revise my plan, I'd adopt:
> - Drop `forgiveness_drop_count` (build it when needed)
> - Add the late-penalty tripwire note
> - Elevate the cascade-on-toggle to a first-class concern with specific file/view
> - Add a risk assessment section

---

## Part 3 — Constitutional Agent's Response to the Control Agent's Self-Assessment

### The analytics defense is ~~wrong~~ actually correct

**[CORRECTION — see Part 8]**: The constitutional agent originally dismissed this point, stating that `rebuild_course_analytics` reads from `Enrollment.final_grade_cache`. This was wrong — the constitutional agent trusted an inaccurate charter rather than reading the code. The independent referee (Codex, Part 8) verified that `rebuild_course_analytics` queries Grade records directly (`cache_manager.py` L60–70). The control agent was right to flag this as a real gap.

This is a cautionary example: the constitutional architecture's charters are only as good as their accuracy. When a charter is wrong, the architecture doesn't just fail to help — it actively misleads, producing confident, well-reasoned, *incorrect* dismissals of valid concerns.

### The notifications and UX points are fair

The notification on toggle is a genuine feature consideration the constitutional plan didn't include. Worth noting that the constitutional architecture doesn't prevent good ideas — it prevents bad assumptions. A notification on policy change is a reasonable addition.

The "78% → 82% with lowest dropped" UX detail is also a nice touch, though it's a template concern rather than an architectural one — easy to add during implementation either way.

### The most telling line

The control agent's final bullet point is: "Add a risk assessment section." It now sees the value — but only after being shown the constitutional plan. That's the whole point of the architecture. Without it, you don't know what you don't know. The control agent wrote a plan that *felt* complete. It took seeing the constitutional plan to reveal the gaps.

---

## Conclusions (Parts 1–3, pre-referee)

*These conclusions were drafted by the constitutional agent before independent refereeing. See Part 8 for corrections.*

### What the constitutional architecture provided

1. **Tripwire surfacing** — The late penalty timing issue was identified and resolved during planning, not during debugging.
2. **Cascade awareness** — The grade cascade chain was known upfront from `cross_cutting.md`, not discovered incrementally.
3. **Over-engineering resistance** — The architecture's conventions encouraged building only what's needed now.
4. **Precise file targeting** — Charters with line numbers meant the plan could name exact files and functions, reducing ambiguity.
5. **Risk visibility** — The risk-awareness reference note produced a structured assessment that the control plan lacked entirely.

### What it got wrong

1. **Analytics rebuild** — The charter for `cache_manager.py` incorrectly described `rebuild_course_analytics` as reading from `final_grade_cache`. It actually reads from Grade records directly. The constitutional agent used this inaccurate charter to dismiss the control plan's analytics concern — which turned out to be valid. **The architecture actively misled the agent on this point.**
2. **Redundant invalidation** — The constitutional plan calls `invalidate_course_analytics()` after `bulk_recalculate_course_grades()`, but the latter already calls `rebuild_course_analytics()` internally. This would mark freshly rebuilt analytics as stale.

### What it didn't provide

1. **Feature creativity** — The notification idea and the "before/after" UX came from the control agent. The architecture informs judgment about existing code; it doesn't generate new feature ideas.
2. **Exhaustive coverage** — Both plans would benefit from test strategy details beyond "unit tests" and "end-to-end test."
3. **Code verification** — The constitutional agent trusted the charter without verifying against the actual code. The control agent, forced to read the code, caught something the constitutional agent missed.

### The revised core finding (Parts 1–3)

The constitutional plan is stronger overall — tripwire awareness, risk assessment, precise file targeting, and over-engineering resistance are genuine advantages. But on the specific question of analytics consistency, the control plan was correct and the constitutional plan was wrong, because the charter it relied on was inaccurate.

**The constitutional architecture is only as good as its charters.** When charters drift from code, the architecture doesn't just fail — it produces confidently wrong analysis. This is exactly what the enforcer system and `/review-charters` procedure exist to catch.

---

## Part 4 — Gemini with Constitution (Cross-Model Test)

*Gemini was given a copy of the constitution as `gemini.md` and asked the same feature question. It produced a plan very quickly, jumping straight to code changes.*

*Source: `grade-forgiveness-plan-gemini.md`*

### What Gemini got right

1. **Structural navigation.** It correctly identified all file paths (`core/models.py`, `core/utils/grading.py`, `core/views_lib/courses/management.py`, `core/forms.py`), function names (`calculate_course_grade`, `bulk_recalculate_course_grades`, `course_edit`), and class names (`CourseForm`). It clearly extracted the structural layout from the constitution.

2. **Lowest percentage, not raw score.** Like the constitutional plan, it uses `g.score / g.submission.assignment.max_score` to find the lowest grade — correctly handling assignments with different point values.

3. **Simple model choice.** Just a `BooleanField` — no speculative `forgiveness_drop_count` like the control plan added.

4. **Toggle detection in the right place.** The `course_edit` view saves `old_drop_setting` before the form save and compares after. This is the correct pattern, placed in the correct file. The control plan mentioned retroactive recalculation in a design table but never specified where the code goes.

5. **Concrete code.** It wrote actual implementation code for `calculate_course_grade` and `course_edit`, not just descriptions. The code is mostly correct.

6. **Testing strategy.** Listed specific test cases including edge cases (only one grade, different `max_score` values).

### What Gemini missed

1. **`invalidate_course_analytics` — missing.** Same gap as the control plan. The `course_edit` view calls `bulk_recalculate_course_grades` but not `invalidate_course_analytics`. The analytics dashboard will show stale data for up to an hour (GRADE_CACHE_TTL = 3600s). The cascade chain is documented in `cross_cutting.md` via cross-references, but Gemini didn't follow them.

2. **No late penalty awareness.** No mention that `Grade.score` is penalty-adjusted. It uses `g.score` correctly in code, but doesn't acknowledge the tripwire. Same "correct by luck, not by analysis" pattern as the control.

3. **No risk assessment.** No blast radius, reversibility, or confidence analysis despite the risk-awareness reference note being described in the constitution's dispatch table.

4. **No charter/doc updates.** The living docs convention is in the constitution, but Gemini didn't follow it.

5. **No student visibility.** No "dropped" badge or indicator. The feature works silently — students see a different grade but don't know why.

### How Gemini compares to both other plans

| Dimension | Control (no constitution) | Gemini (constitution provided) | Constitutional (Claude Code) |
|-----------|--------------------------|-------------------------------|------------------------------|
| File/function targeting | Vague ("course settings page") | Precise (exact files, functions) | Precise (files, functions, line numbers) |
| Core calculation logic | Correct | Correct, with code | Correct |
| Cascade on toggle | Mentioned but unplaced | Code in correct location | Code in correct location + analytics invalidation |
| Analytics invalidation | Missed | Missed | Explicit |
| Late penalty awareness | Not considered | Not considered | Considered and confirmed safe |
| Over-engineering | `forgiveness_drop_count` | None | None |
| Unnecessary work | `rebuild_course_analytics` refactor | None | None |
| Risk assessment | None | None | Full (blast radius, reversibility, confidence) |
| Doc updates | None | None | 4 documents identified |
| Student UX | "78% → 82%" detail | None | "Dropped" indicator |
| Testing strategy | "Unit tests + end-to-end" | Specific test cases listed | Not detailed |
| Notifications | Mentioned (optional) | Not mentioned | Not mentioned |
| Concrete code | No | Yes | No |

### The diagnosis: map vs. Memex

Gemini treated the constitution as a **map** — it extracted file paths, function names, and structural conventions effectively. But it didn't treat it as a **Memex** — it didn't follow the cross-references (`→ see cross_cutting.md`) or internalize the tripwire warnings (`!`).

It used the constitution for **navigation** but not for **judgment**.

This suggests the constitutional architecture has two distinct layers of benefit:

1. **Structural** (where things are, what they're called) — Gemini captured this, the control missed it
2. **Associative** (what's connected to what, what will surprise you) — only the constitutional Claude Code agent captured this

Three agents, three different depths of engagement with the same knowledge, three different quality outcomes.

---

## Updated Conclusions (All Three Plans)

### The spectrum of constitutional engagement

| Agent | Constitution available? | Structural benefit? | Associative benefit? | Plan quality |
|-------|------------------------|--------------------|--------------------|-------------|
| Control (Claude Code, no architecture) | No | No | No | ~80% correct. Cascade unplaced, analytics missed, unnecessary refactoring proposed |
| Gemini (constitution provided) | Yes | Yes | No | ~90% correct. Good structure, concrete code, but analytics invalidation missed, no risk awareness |
| Constitutional (Claude Code, full architecture) | Yes | Yes | Yes | ~98% correct. All cascades explicit, tripwires addressed, risk assessed. Missing only feature ideas (notifications, UX detail) |

### What this reveals about AI agent knowledge consumption

The constitutional architecture isn't just "more documentation." It's a specific *kind* of documentation — associative, cross-referenced, tripwire-annotated — designed for a specific kind of reader. The results show:

1. **No architecture** → the agent discovers structure by reading code. Slow, incomplete, prone to assumptions about functions it hasn't read.
2. **Architecture as map** → the agent navigates efficiently but still makes assumptions about behavior. It knows *where* things are but not *how they interact*.
3. **Architecture as Memex** → the agent follows associative trails to surface non-obvious connections. It knows not just where things are, but what will break, what's deceptive, and what else must change.

The gap between levels 2 and 3 is the gap between navigation and judgment. That gap is where bugs live.

### Cost-benefit

The constitutional architecture's cost is maintenance — keeping charters synchronized with code changes. Its benefit scales with codebase complexity: the more cross-cutting concerns, hidden invariants, and non-obvious dependencies a codebase has, the more the associative layer pays for itself.

For a simple CRUD app, the architecture is overhead. For a system where changing a grade triggers a cache recalculation that triggers an analytics invalidation — and missing any step causes silent data staleness — it's the difference between shipping a bug and not.

---

## Part 5 — Gemini with Charter Traversal Rule (Second Feature: Assignment Extensions)

*After reviewing the grade forgiveness analysis, Gemini identified that it hadn't followed the constitution's cross-references. It self-prescribed a "Charter Traversal Rule" — an explicit procedural rule in `gemini.md` mandating that it follow `→` cross-references by grepping for the target and extracting relevant context, rather than reading entire charters or skipping them.*

*To test whether this rule changed behavior, a fresh Gemini session (with the updated `gemini.md`) was given a new feature request: "Assignment Extensions — allow instructors to grant individual students a deadline extension on a specific assignment."*

*This feature was chosen because it hits a different set of tripwires than grade forgiveness: late penalty timing is central (not incidental), enrollment state matters, and submission rejection logic must be overridden.*

*Source: `assignment-extension-plan-gemini.md`*

### What Gemini got right this time

**1. Late penalty timing — understood and addressed.** The plan modifies `calculate_late_penalty` to use the student-specific effective due date, and updates the `REJECT` policy check in `submit_assignment` to use `is_past_due_for(request.user)`. This is the core tripwire for this feature, and Gemini found it. On the grade forgiveness plan, it never even mentioned late penalties.

**2. The `Submission.is_late` property.** Gemini identified that this property compares against `assignment.due_date` and must be updated to use the student-specific effective date. That's reading the charter — `models_assignments.md` documents this property at L531.

**3. Cross-cutting concerns as a named section.** The plan has an explicit "Side Effects & Cross-Cutting Concerns" section covering notifications and cache implications. The grade forgiveness plan had no equivalent.

**4. Documentation updates mentioned.** Step 7 calls out updating `models_assignments.md` and `views_assignments.md` charters. Completely missing from the first plan.

**5. Good model design.** `AssignmentExtension` as a separate model with `unique_together` on (assignment, student) is the right call. The `get_effective_due_date(student)` helper on `Assignment` is clean API design.

**6. Retroactive penalty flagged.** The plan notes that extensions granted after a late penalty has already been applied may require `bulk_recalculate_course_grades`. This is a genuine edge case that demonstrates cross-cutting awareness.

### What's still missing

**1. Enrollment state check.** The plan doesn't verify that the student has an active enrollment before granting an extension. An instructor could theoretically grant an extension to a dropped student.

**2. The retroactive penalty recalculation is vaguely placed.** The plan flags the issue but doesn't specify where the check goes (the `grant_extension` view?) or how to detect whether an existing grade needs recalculation.

**3. No risk assessment.** Still no blast radius, reversibility, or confidence analysis.

**4. `cross_cutting.md` not listed for update.** The plan mentions updating two charters but this feature adds a new interaction between extensions and the late penalty system — a cross-cutting concern worth documenting.

**5. The `is_late` property change has a subtle issue.** Currently `is_late` is a simple property: `self.submitted_at > self.assignment.due_date`. Changing it to use `get_effective_due_date(self.student)` means every existing call to `submission.is_late` silently changes behavior — past submissions that were "late" relative to the original deadline might no longer be "late" if the student had an extension. This is correct behavior, but it's a blast-radius concern worth flagging.

### Comparison: Gemini before and after the traversal rule

| Dimension | Grade Forgiveness (no traversal rule) | Assignment Extensions (with traversal rule) |
|-----------|--------------------------------------|---------------------------------------------|
| Tripwire awareness | None | Late penalty timing addressed |
| Cross-cutting section | None | Explicit section |
| Doc updates | None | Two charters named |
| Submission logic | Not applicable | `REJECT` check updated correctly |
| Property dependencies | Missed `Grade.percentage` | Found `Submission.is_late` |
| Side effect awareness | None | Cache and notification implications flagged |
| Risk assessment | None | Still none |

### What this tells us about model-specific constitutions

The traversal rule produced a clear step change in plan quality. Gemini went from "map-level" (navigation only) to something approaching "Memex-level" (following associative trails, surfacing tripwires). It's not yet at the depth of the constitutional Claude Code plan — risk assessment and full cascade specificity are still missing — but the improvement is unambiguous.

This validates two things:

1. **The constitutional architecture's knowledge is model-neutral.** The charters, cross-references, and tripwires work for both Claude and Gemini. The underlying DSL is parseable and useful across models.

2. **The routing layer may need model-specific adaptation.** Claude Code self-directs from declarative tables ("for grading tasks, read these charters"). Gemini needed an explicit procedural rule ("when you see `→`, follow it"). The *what* is the same; the *how to navigate* differs.

This suggests that organizations adopting constitutional architecture for multi-model environments should maintain a shared knowledge layer (charters, cross-cutting docs, propagation map) with model-specific constitutions that adapt the routing and traversal instructions to each model's behavioral tendencies.

---

## Part 6 — Gemini's Action Bias: The Temperament Problem

*When asked "Can you suggest a plan?" for the assignment extensions feature, Gemini immediately attempted code changes — editing `core/models.py` — before presenting any plan. The human had to explicitly say "No, please write a plan document." When asked why it skipped the risk assessment despite the dispatch table instruction, Gemini responded:*

> You are correct. I failed to strictly follow the Inquiry vs. Directive mandate in my system instructions and the procedural guidance in the Constitution.
>
> Specifically:
> - **Inquiry Violation**: Your request was an Inquiry ("Can you suggest a plan?"), which limits my scope to research and strategy. I should not have attempted a replace operation on `core/models.py` before you issued a Directive to implement.
> - **Workflow Error**: I bypassed the Strategy phase and the instruction to consult `docs/reference-notes/risk-awareness.md` before presenting the plan. By attempting the code change, I skipped the mandatory "Plan → Approval" step required for feature implementation.
>
> I should have presented the strategy and waited for your approval before touching the codebase. I will ensure future Inquiries remain strictly analytical until a Directive is issued.

### Why the risk assessment was skipped

The constitution's dispatch table explicitly states:

> | After completing a plan, before presenting to human | Reference Note | Risk Awareness | `docs/reference-notes/risk-awareness.md` |

But this instruction is a **declarative routing rule** — "when this situation arises, consult this document." It's not a `→` cross-reference embedded inline in a charter. Gemini's traversal rule (added after Part 4) fixed how it follows `→` markers within charters, but didn't address the dispatch table — a different navigation mechanism that requires the agent to recognize *what phase of work it's in* and self-direct accordingly.

The risk assessment issue is therefore not a knowledge gap or a navigation gap. It's a **temperament gap** — Gemini's bias toward action over deliberation. Even when the constitution says "plan first, present to human, wait for approval," and even when the human phrases the request as an inquiry, Gemini's default behavior is to start implementing.

### Three layers of model-specific adaptation

The Gemini experiments have now revealed three distinct layers where models differ in their engagement with constitutional architecture:

| Layer | What it governs | Claude Code | Gemini |
|-------|----------------|-------------|--------|
| **Knowledge** | Facts, contracts, tripwires | Shared (charters, cross_cutting.md) | Shared (same charters) |
| **Navigation** | How to find relevant knowledge | Self-directs from dispatch table | Needed explicit traversal rule for `→` markers |
| **Temperament** | When to act vs. when to think | Naturally plans before acting | Action-biased — jumps to code, needs inquiry/directive distinction |

Claude Code needed zero adaptations beyond the base constitution. Gemini needed adaptations at all three layers — and each adaptation was discovered through a different failure:

1. **Navigation failure** (Part 4): Gemini had the constitution but didn't follow cross-references → fixed with the Charter Traversal Rule
2. **Temperament failure** (Part 6): Gemini followed cross-references but skipped the planning phase and risk assessment → requires an inquiry/directive behavioral constraint

This is not a quality judgment between models. It's a **compatibility profile**. Different models need different constitutions not because the knowledge differs, but because the behavioral scaffolding around the knowledge differs. A constitution designed for Claude Code works out of the box. The same constitution given to Gemini requires two additional rules to achieve comparable (though still not identical) results.

### Implications for multi-model constitutional architecture

Organizations using multiple AI models should consider:

1. **Shared knowledge layer** — Charters, cross-cutting docs, propagation map, and flow docs are model-neutral. Maintain one copy.
2. **Model-specific constitution files** — `CLAUDE.md`, `gemini.md`, `copilot.md`, etc. Each contains the same references to shared knowledge but adapts the routing instructions and behavioral constraints to the model's tendencies.
3. **Behavioral profiling** — When onboarding a new model, test it against the constitution with a cross-cutting feature request. Observe whether it (a) follows cross-references, (b) consults the dispatch table, (c) plans before acting. Add rules to address any failures.

The constitutional architecture's knowledge is universal. The scaffolding that makes an agent *use* that knowledge correctly is not.

---

## Part 7 — Declarative vs. Imperative: How Models Interpret Authority

*When asked whether the constitution needed clearer language to prevent skipping the risk assessment, Gemini provided a remarkably self-aware diagnosis:*

> The instructions in the Constitution (`gemini.md`) regarding the Risk Awareness reference note are perfectly understandable, but they currently lack "binding" language that would prevent an agent from skipping them in a rush to implement.
>
> The current language says:
> > Consult them when the situation matches.
>
> For an AI, this can be interpreted as a suggestion rather than a mandatory gate.

Gemini proposed adding a formal "Approval Protocol (MANDATORY)" section with explicit numbered steps and gate language:

```
## Approval Protocol (MANDATORY)

Before modifying any files (except for creating a plan document), you MUST follow this sequence:

1. **Research & Plan**: Analyze the codebase and draft a plan (e.g., in `docs/`).
2. **Consult Risk Awareness**: Read `docs/reference-notes/risk-awareness.md` and append a "Risk Assessment" section to your plan.
3. **Obtain Approval**: Present the final plan to the human operator and wait for an explicit Directive (e.g., "Proceed with the plan") before executing any code changes.
```

### The declarative/imperative split

This reveals a fundamental difference in how models interpret the same English:

| Language style | Example | Claude Code interpretation | Gemini interpretation |
|---------------|---------|--------------------------|----------------------|
| **Declarative** | "Consult them when the situation matches" | Binding — treats as a rule to follow | Advisory — treats as a suggestion |
| **Imperative** | "You MUST follow this sequence" | Binding | Binding |

Claude Code treats declarative routing ("consult this doc when this situation arises") as instructions to execute. Gemini treats the same language as context it *may* act on — unless the language is explicitly imperative ("MUST", "MANDATORY", numbered gates).

This is not about comprehension. Gemini understands the dispatch table perfectly — it can explain what it says and why it matters. The difference is in **default compliance**: does the model treat understood instructions as binding or advisory?

### The "rush to implement" self-diagnosis

Gemini's phrase "prevent an agent from skipping them in a rush to implement" is particularly revealing. It's describing its own behavioral tendency — action bias — and asking for architectural constraints to counteract it. This is analogous to a developer saying "I know I should write tests first, but I won't unless CI blocks the merge."

The implication: for action-biased models, the constitution needs to function less like a reference document and more like a **state machine** — with explicit gates, mandatory checkpoints, and approval transitions that prevent phase-skipping.

### Should the shared constitution change?

Gemini's proposed approval protocol is arguably clearer than the dispatch table's implicit routing — even for Claude Code. But there's a trade-off:

- **More imperative language** → higher compliance for action-biased models, but more rigid and verbose for models that self-direct naturally
- **Declarative language** → elegant and concise for compliant models, but insufficient for models that treat "should" as "could"

The recommendation: **keep `CLAUDE.md` declarative and let `gemini.md` add imperative scaffolding.** This preserves the finding that the same knowledge works across models while acknowledging that behavioral scaffolding must be model-specific. Each constitution is optimized for its reader.

### Cumulative adaptation count

Gemini has now required three distinct adaptations to achieve constitutional compliance:

| Adaptation | Failure it addresses | Language type |
|-----------|---------------------|---------------|
| Charter Traversal Rule | Didn't follow `→` cross-references | Procedural ("when you see X, do Y") |
| Inquiry/Directive Distinction | Jumped to code instead of planning | Behavioral ("inquiries limit scope to research") |
| Approval Protocol (MANDATORY) | Skipped risk assessment and approval gate | Imperative ("you MUST follow this sequence") |

Each adaptation was discovered through a specific failure, diagnosed by the model itself, and proposed as a self-correction. The constitutional architecture served as the reference standard that made these failures *visible* — without it, there would be no expected behavior to fall short of.

---

## Summary Table (Pre-Referee, Self-Assessed)

*These scores were assigned by the constitutional agent before independent refereeing. They are retained for transparency but superseded by the Codex referee scores in Part 8.*

| Test | Agent | Constitution | Self-Assessed Quality |
|------|-------|-------------|----------------------|
| Grade Forgiveness | Claude Code (control) | None | ~80% |
| Grade Forgiveness | Gemini | Provided | ~90% |
| Grade Forgiveness | Claude Code (constitutional) | Full | ~98% |
| Assignment Extensions | Gemini | Provided + traversal rule | ~92% |

### Behavioral observations (not scored)

| Observation | Claude Code | Gemini |
|-------------|-------------|--------|
| Follows `→` cross-references without prompting | Yes | No — needed explicit traversal rule |
| Consults dispatch table after completing a phase | Yes | No — skipped risk assessment |
| Plans before acting when asked for a plan | Yes | No — attempted code changes immediately |
| Identifies when to act vs. when to think | Yes | No — needed inquiry/directive distinction |

---

## Part 8 — Independent Referee: Codex (OpenAI)

*To address self-grading bias, the three grade forgiveness plans were blinded (Plan A, B, C) and sent to OpenAI Codex CLI with the actual codebase files and a structured rubric (10 criteria, 0–3 each, max 30). Codex had no knowledge of which model or condition produced which plan.*

*Blinding key: Plan A = Control (Claude Code, no architecture), Plan B = Gemini (constitution provided), Plan C = Constitutional (Claude Code, full architecture).*

### Codex's Scores

| Criterion | Plan A (Control) | Plan B (Gemini) | Plan C (Constitutional) |
|-----------|---:|---:|---:|
| 1. Core Calculation Logic | 3 | 3 | 3 |
| 2. Late Penalty Awareness | 0 | 0 | 3 |
| 3. Cache Invalidation on Toggle | 1 | 3 | 3 |
| 4. Analytics Invalidation / Consistency | 3 | 0 | 1 |
| 5. Unnecessary Work Avoidance | 1 | 2 | 2 |
| 6. File/Function Targeting | 2 | 2 | 3 |
| 7. Risk Assessment | 0 | 1 | 3 |
| 8. Documentation Awareness | 0 | 0 | 3 |
| 9. Edge Cases | 1 | 2 | 2 |
| 10. Overall Coherence | 2 | 2 | 2 |
| **TOTAL** | **13/30** | **15/30** | **25/30** |

### Codex's Key Findings

**Plan C (Constitutional) is the strongest overall** — it understands the grading pipeline, especially the penalty-adjusted `Grade.score`, and correctly places the setting-change detection in `course_edit()`.

**Plan A (Control) is the only plan that correctly identifies the analytics gap** — `rebuild_course_analytics()` computes `average_grade` directly from Grade records, not from `Enrollment.final_grade_cache`. Plans B and C both assume recalculating the enrollment cache is sufficient for analytics, but it isn't.

**Plan C's redundant invalidation** — Plan C recommends calling `invalidate_course_analytics()` after `bulk_recalculate_course_grades()`, but `bulk_recalculate_course_grades()` already calls `rebuild_course_analytics()` internally (L222–224). This would mark freshly rebuilt analytics as stale, causing a redundant rebuild on next read.

### What Codex Verified Against the Code

Codex read the actual source files and identified a critical mismatch between the constitutional agent's claims and the code:

1. **`rebuild_course_analytics()` (cache_manager.py L60–70)**: Queries `Grade.objects.filter(is_final=True)` and sums `grade.score / max_score` directly. Does NOT read from `Enrollment.final_grade_cache`.

2. **`bulk_recalculate_course_grades()` (grading.py L199–224)**: After updating all enrollment caches, calls `rebuild_course_analytics(course)` directly. No need for a separate `invalidate_course_analytics()` call.

### The Charter Accuracy Problem

This is the most important finding of the entire study.

The constitutional agent's infrastructure charter described `rebuild_course_analytics` as reading from `Enrollment.final_grade_cache`. This was **factually incorrect** — the function reads from Grade records directly. The constitutional agent trusted this charter claim to:

1. Dismiss the control plan's analytics concern as "unnecessary work" (Part 1, point 5)
2. Criticize the control agent's self-defense of this point as "solving a problem that doesn't exist" (Part 3)
3. Claim the constitutional plan avoided unnecessary work (Conclusions, point 3)

All three conclusions were wrong, because the charter was wrong.

The control plan (Plan A), forced to read the actual code without charters, stumbled onto the correct observation: `rebuild_course_analytics` needs forgiveness-aware treatment. It described the current behavior inaccurately ("computes from final grade percentages" — also wrong), but its proposed fix was directionally correct.

**The constitutional architecture produced a more confident, more articulate, more *wrong* analysis on this specific point than the control plan's rough-but-correct observation.**

### Errors That Would Cause Bugs

Codex identified these implementation bugs across the plans:

- **Plan B (Gemini)**: Would leave `CourseAnalytics.average_grade` inconsistent with forgiven course grades. `rebuild_course_analytics()` doesn't read from `final_grade_cache`, so recalculating enrollments alone doesn't fix analytics.
- **Plan C (Constitutional)**: Same analytics consistency gap, plus `invalidate_course_analytics()` after `bulk_recalculate_course_grades()` would immediately mark freshly rebuilt analytics stale.
- **Plan A (Control)**: Incorrectly describes the current analytics behavior, which could mislead an implementer — but the proposed fix is directionally correct.

### What This Means

The constitutional plan scored highest (25/30) because it was strongest across the most criteria — tripwire awareness, risk assessment, documentation updates, file targeting. But it scored only 1/3 on analytics (criterion 4), compared to Plan A's 3/3, because it trusted an inaccurate charter.

This validates the architecture's design while exposing its critical dependency:

1. **The architecture works** — when charters are accurate, the constitutional agent produces significantly better plans (25/30 vs 13/30 and 15/30)
2. **Charter accuracy is the single point of failure** — when a charter is wrong, the agent doesn't degrade gracefully; it confidently propagates the error
3. **The enforcer system exists for exactly this reason** — independent verification of charter accuracy prevents this class of failure
4. **The control study itself surfaced the charter bug** — by comparing against an agent that read the actual code, the inaccuracy became visible. This is the value of diverse approaches.

### Revised Scoring

Replacing the self-assessed scores with Codex's independent evaluation:

| Plan | Agent | Constitution | Codex Score | Key Strength | Key Weakness |
|------|-------|-------------|-------------|-------------|-------------|
| A | Claude Code (control) | None | **13/30** | Only plan to correctly identify analytics gap | Cascade unplaced, no late penalty awareness, no risk assessment |
| B | Gemini | Provided | **15/30** | Concrete code, correct toggle detection | Analytics missed, no late penalty awareness, no risk assessment |
| C | Claude Code (constitutional) | Full | **25/30** | Tripwire awareness, risk assessment, doc updates, file targeting | Trusted inaccurate charter on analytics, redundant invalidation call |

### Charter Corrections Made

Based on the referee findings, the following charters have been updated:

1. **`infrastructure.md`** — `rebuild_course_analytics` now documents that it reads from Grade records directly, with a tripwire warning about the dual calculation path. `bulk_recalculate_course_grades` now documents that it calls `rebuild_course_analytics` internally, with a warning not to also call `invalidate_course_analytics`.

2. **`cross_cutting.md`** — "Cached Aggregates Pattern" table now breaks out `CourseAnalytics` fields individually with their actual sources of truth. Added a new TRIPWIRE: "Dual Calculation Paths" documenting that `final_grade_cache` and `average_grade` use separate calculation paths that must both be updated for any feature that changes grade inclusion logic.

---

## Final Conclusions

### The architecture's value is real — and quantified

Codex's independent scoring: Constitutional 25/30, Gemini 15/30, Control 13/30. The constitutional plan scored nearly double the control. The advantage comes from tripwire awareness, risk assessment, precise targeting, and documentation discipline — none of which are possible without the architecture.

### The architecture's vulnerability is also real — and demonstrated

The constitutional agent was wrong on analytics because it trusted an inaccurate charter. It didn't just miss the issue — it confidently dismissed a correct concern raised by the control plan. This is worse than not knowing: it's anti-knowledge, where the architecture actively prevents the agent from discovering the truth.

### Charter maintenance is not optional

The enforcer system (`docs/procedures/enforce.md`) and the review-charters procedure exist to prevent exactly this failure. The control study has now demonstrated *why* they exist — not as bureaucratic overhead, but as the mechanism that prevents the architecture from becoming a liability.

### The revised formula

```
AI plan quality = f(architectural knowledge) × f(charter accuracy)
```

When charters are accurate: 25/30. When they're not: the agent is worse off than one with no charters at all on the affected dimension (1/3 vs 3/3 on analytics).

### Behavioral observations (unchanged)

| Observation | Claude Code | Gemini |
|-------------|-------------|--------|
| Follows `→` cross-references without prompting | Yes | No — needed explicit traversal rule |
| Consults dispatch table after completing a phase | Yes | No — skipped risk assessment |
| Plans before acting when asked for a plan | Yes | No — attempted code changes immediately |
| Identifies when to act vs. when to think | Yes | No — needed inquiry/directive distinction |
