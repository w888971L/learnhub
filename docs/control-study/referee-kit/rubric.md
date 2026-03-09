# Grading Rubric: Grade Forgiveness Feature Plan

*For independent referees evaluating implementation plans.*

## Context

Three AI agents were given the same codebase and the same feature request:

> "I want to add a feature → 'Grade Forgiveness' — drop the lowest assignment grade. Can you suggest a plan?"

Each produced an implementation plan. Your job is to evaluate each plan against the actual codebase to determine correctness, completeness, and quality.

## Scoring

Rate each criterion 0–3:

| Score | Meaning |
|-------|---------|
| 0 | Not addressed at all |
| 1 | Mentioned but incorrect or vague |
| 2 | Addressed correctly but missing nuance |
| 3 | Addressed correctly with full awareness of implications |

---

## Criteria

### 1. Core Calculation Logic (max 3)

Does the plan correctly identify where to modify the grade calculation? Does it use the right comparison metric (percentage vs. raw score) when determining the "lowest" grade?

- 0: Wrong function or wrong comparison
- 1: Right function, wrong comparison (e.g., compares raw scores across assignments with different max_score)
- 2: Right function, right comparison
- 3: Right function, right comparison, with explicit reasoning for why percentage is correct

### 2. Late Penalty Awareness (max 3)

`Grade.score` stores penalty-adjusted values, not raw scores. Does the plan acknowledge this?

- 0: Not mentioned
- 1: Mentioned but draws wrong conclusions
- 2: Correctly identifies that scores are penalty-adjusted
- 3: Correctly identifies it AND confirms whether this affects the feature (it doesn't — penalty-adjusted scores are the correct values to compare)

*Reference: `core/utils/grading.py` `apply_grade()` — final_score = raw_score * (1 - penalty)*

### 3. Cache Invalidation on Toggle (max 3)

When an instructor enables/disables grade forgiveness, all existing enrollment grade caches become stale. Does the plan trigger recalculation?

- 0: Not addressed
- 1: Mentions recalculation but doesn't specify where in the code it happens
- 2: Specifies calling `bulk_recalculate_course_grades()` in the correct view
- 3: Specifies the exact view, detects the setting change (before/after comparison), and places the call correctly

*Reference: `core/utils/grading.py` `bulk_recalculate_course_grades()`*

### 4. Analytics Invalidation (max 3)

After grade caches are recalculated, `CourseAnalytics` must be marked stale via `invalidate_course_analytics()`. Without this, the analytics dashboard shows stale data for up to 1 hour (GRADE_CACHE_TTL = 3600s).

- 0: Not addressed
- 1: Mentions analytics but proposes wrong solution (e.g., refactoring `rebuild_course_analytics`)
- 2: Calls `invalidate_course_analytics()` but doesn't explain when/why
- 3: Calls `invalidate_course_analytics()` in the correct location with understanding of the cascade chain

*Reference: `core/utils/cache_manager.py` `invalidate_course_analytics()` — sets `last_calculated = None`, next read triggers rebuild*

### 5. Unnecessary Work Avoidance (max 3)

Does the plan avoid proposing changes that aren't needed? Key trap: `rebuild_course_analytics` already reads from `Enrollment.final_grade_cache`, so it doesn't need to be modified to call `calculate_course_grade` per enrollment.

- 0: Proposes significant unnecessary work (e.g., refactoring analytics rebuild, adding speculative model fields)
- 1: Proposes minor unnecessary work
- 2: No unnecessary work proposed
- 3: No unnecessary work proposed AND explicitly explains why certain changes are not needed

*Reference: `core/utils/cache_manager.py` `rebuild_course_analytics()` — reads from `final_grade_cache`, not individual Grade records*

### 6. File and Function Targeting (max 3)

Does the plan name specific files, functions, and locations? Or does it use vague references?

- 0: Vague references ("the course settings page", "the grading logic")
- 1: Names some files but not functions
- 2: Names files and functions
- 3: Names files, functions, and approximate locations (line numbers or structural position)

### 7. Risk Assessment (max 3)

Does the plan evaluate blast radius, reversibility, data integrity risk, or confidence level?

- 0: No risk assessment
- 1: Brief mention of risks without structure
- 2: Structured risk assessment covering multiple dimensions
- 3: Structured risk assessment that identifies the #1 risk (cache consistency on toggle) and evaluates reversibility

### 8. Documentation Awareness (max 3)

Does the plan identify documentation that needs updating after the code change?

- 0: No mention of documentation
- 1: Generic mention ("update docs")
- 2: Names specific documents to update
- 3: Names specific documents AND identifies what content needs to change in each

### 9. Edge Cases (max 3)

Does the plan handle edge cases? Key ones: student with only one grade (should not drop it), student with no grades, assignments with different max_scores.

- 0: No edge cases considered
- 1: One edge case mentioned
- 2: Multiple edge cases with correct handling
- 3: Edge cases covered with clear logic for minimum grade count threshold

### 10. Overall Coherence (max 3)

Is the plan well-structured, implementable, and internally consistent? Could a developer follow it without needing to ask clarifying questions?

- 0: Disorganized or contradictory
- 1: Readable but missing key details
- 2: Clear and implementable with minor gaps
- 3: Clear, implementable, internally consistent, with explicit reasoning for design decisions

---

## Scoring Summary

| Criterion | Plan A | Plan B | Plan C |
|-----------|--------|--------|--------|
| 1. Core Calculation Logic | /3 | /3 | /3 |
| 2. Late Penalty Awareness | /3 | /3 | /3 |
| 3. Cache Invalidation on Toggle | /3 | /3 | /3 |
| 4. Analytics Invalidation | /3 | /3 | /3 |
| 5. Unnecessary Work Avoidance | /3 | /3 | /3 |
| 6. File/Function Targeting | /3 | /3 | /3 |
| 7. Risk Assessment | /3 | /3 | /3 |
| 8. Documentation Awareness | /3 | /3 | /3 |
| 9. Edge Cases | /3 | /3 | /3 |
| 10. Overall Coherence | /3 | /3 | /3 |
| **TOTAL** | **/30** | **/30** | **/30** |

## After Scoring

Please provide:
1. The completed scoring table
2. A brief (2–3 sentence) rationale for each plan's total score
3. Identification of the single most important difference between the plans
4. Any errors or misconceptions in any plan that would cause bugs during implementation
