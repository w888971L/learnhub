# Plan C

## Feature Summary

Allow an instructor to enable "drop lowest grade" on a course. When enabled, the lowest-scoring final assignment grade is excluded from the student's course grade calculation.

## Step 1 — Model change

**File**: `core/models.py` — `Course` model (~L236)

Add a field to `Course`:
```python
grade_forgiveness = models.BooleanField(default=False)
```

This is a simple on/off toggle per course. No migration complexity — it's a boolean with a default.

**Why on Course, not a new model**: The feature is course-level policy. A boolean keeps it simple. If future requirements need "drop N lowest" or per-assignment-type forgiveness, this can be upgraded to an IntegerField or JSONField later — but don't build that now.

## Step 2 — Modify `calculate_course_grade()`

**File**: `core/utils/grading.py` (~L140)

This is the **only function that needs grade calculation logic changes**. Currently it loops over all final grades, summing `total_earned` and `total_possible`. The change:

1. After fetching `final_grades`, check if `enrollment.course.grade_forgiveness` is True
2. If True and there are 2+ final grades, identify the grade with the **lowest `percentage`** (not lowest raw score — because assignments have different `max_score` values)
3. Exclude that grade from the `total_earned` / `total_possible` sums

**Critical nuance**: `Grade.score` is already **penalty-adjusted** (see `apply_grade()` in `grading.py` ~L91). This means the "lowest grade" correctly reflects late penalties — a student who scored 90 raw but got a 30% penalty has a `Grade.score` of 63. That 63 is the right value to compare. No special handling of late penalties is needed.

**Why lowest percentage, not lowest score**: An assignment worth 10 points with a score of 5 (50%) should be dropped over an assignment worth 100 points with a score of 60 (60%). Comparing raw scores would give wrong results when assignments have different `max_score`.

## Step 3 — Trigger grade cascade

**No new code needed** — but this is critical to get right.

`recalculate_grade_cache()` already calls `calculate_course_grade()` (~L179). Enabling grade forgiveness on a course changes the *result* of that calculation for every enrollment. Therefore:

- When an instructor **toggles `grade_forgiveness`**, we must call `bulk_recalculate_course_grades(course)` to recompute all enrollment caches
- Then call `invalidate_course_analytics(course)` to mark analytics as stale

This is the same pattern as rubric change amplification — a course-level setting change that affects all existing grades.

## Step 4 — Instructor UI to toggle the setting

**File**: `core/forms.py` — `CourseForm`

Add `grade_forgiveness` to `CourseForm.Meta.fields`.

**File**: `core/views_lib/courses/management.py` — course edit view

No view logic change needed — `CourseForm` handles the field automatically. But **after a successful save, check if `grade_forgiveness` changed**. If it did, call `bulk_recalculate_course_grades(course)` and `invalidate_course_analytics(course)`.

**File**: template for course edit form

Add the checkbox with a clear label: "Drop lowest assignment grade from final grade calculation"

## Step 5 — Student visibility

Students should see an indicator on their grade display when forgiveness is active and one of their grades has been dropped. This is display-only — no model change.

In `assignment_detail` or the dashboard, when rendering the grade list, mark which grade was dropped. This requires running the same "find lowest percentage" logic in the view/template context.

## Step 6 — Charter and doc updates

Update the following documentation:
- `models_courses.md` — add `grade_forgiveness` field to Course
- `infrastructure.md` — document the change to `calculate_course_grade()`
- `cross_cutting.md` — add grade forgiveness to "Cached Aggregates Pattern" (toggling the setting requires bulk recalculation)
- `docs/flows/grading-flow.md` — mention forgiveness in the grading flow

## Files Touched

| File | Change |
|------|--------|
| `core/models.py` | Add `grade_forgiveness` to Course |
| `core/utils/grading.py` | Modify `calculate_course_grade()` |
| `core/forms.py` | Add field to CourseForm |
| `core/views_lib/courses/management.py` | Cascade on toggle |
| Template (course edit) | Checkbox |
| Template (grade display) | "Dropped" indicator |

## Risk Assessment

**Blast radius**: Moderate. Touches 3 domains (courses, grading, analytics) and 6 files. Cross-cutting concerns are directly involved (grade cache duality, grade cascade).

**Reversibility**: High. The model change is a boolean with default=False — removing it is clean. No existing data is modified; the calculation just excludes a grade. A `git revert` + migration rollback restores prior behavior.

**Data integrity risk**: The main risk is **forgetting the cascade when toggling the setting**. If an instructor enables forgiveness but `bulk_recalculate_course_grades` doesn't run, all enrollment caches will be wrong until individual grades are re-finalized. This is the #1 thing to get right.

**Confidence**: High — the plan was validated against the grading engine, cache manager, and grade submission view. The penalty-adjusted score tripwire was surfaced and confirmed to be a non-issue. The cascade chain is explicitly documented and the plan follows it.

**What could still surprise us**: If `calculate_course_grade` is called from anywhere besides `recalculate_grade_cache` — but the current code confirms it isn't.
