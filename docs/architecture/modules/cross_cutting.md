# Cross-Cutting Concerns — code health issues spanning multiple modules

Last verified: 2026-03-08
Files covered: (cross-cutting — spans all modules)

---

## Grade Cache Duality (TRIPWIRE)

The system maintains TWO representations of a student's course grade:

1. **Source of truth**: Individual `Grade` records linked via Submission → Assignment → Course
2. **Cached aggregate**: `Enrollment.final_grade_cache` — a single DecimalField

These MUST stay synchronized. The cache exists for performance (avoids recalculating across all grades every time a student dashboard loads), but creates a consistency risk.

**What breaks**: Any code path that creates, modifies, or deletes a Grade record WITHOUT calling `recalculate_grade_cache(enrollment)` will cause the cache to drift from reality. Students will see stale grades. Analytics will report incorrect data.

**Safe paths** (these call recalculate automatically):
- `grade_submission()` view → always calls `recalculate_grade_cache()` (even for non-final grades, since `apply_grade()` may have demoted a previous final grade)
- `bulk_recalculate_course_grades(course)` → rebuilds all enrollments for a course

**Unsafe paths** (manual cache update required):
- Direct ORM operations: `Grade.objects.create(...)` or `grade.delete()` without view layer
- Management commands that modify grades
- Any future bulk import/export of grade data

→ see models_courses.md Enrollment `final_grade_cache`
→ see infrastructure.md `recalculate_grade_cache`

---

## Late Penalty Timing (TRIPWIRE)

Late penalties are applied at **GRADING time**, not at submission time.

**Why this is confusing**: Intuitively, you'd expect the penalty to be calculated when the student submits (since that's when "lateness" is determined). Instead, the raw submission is accepted, and the penalty is applied when `apply_grade()` is called during grading.

**Why it's designed this way**: Instructors should see the student's actual work quality before the penalty is applied. The Grade record stores the penalty-adjusted score, but the grading UI shows both raw and adjusted scores so the instructor understands the impact.

**What breaks**: If you add a code path that creates Grade records directly (bypassing `apply_grade()`), late penalties will not be applied. Students who submit late will receive full credit.

**The penalty chain**:
```
Instructor submits GradeForm
  → grade_submission() validates form
    → apply_grade(submission, raw_score, grader)
      → calculate_late_penalty(submission)
        → reads assignment.late_policy and LEARNHUB_SETTINGS
        → returns multiplier (0.0 to 1.0)
      → final_score = raw_score * (1 - penalty)
      → Grade.objects.create(score=final_score)
```

→ see models_assignments.md Assignment "Late Policy Behavior"
→ see views_assignments.md `grade_submission` (5-step flow)
→ see infrastructure.md `apply_grade`

---

## Grade Cascade

When a grade is finalized, a chain of updates must fire in strict order:

```
Grade.is_final = True
  → recalculate_grade_cache(enrollment)     # updates Enrollment.final_grade_cache
    → invalidate_course_analytics(course)    # marks CourseAnalytics as stale
```

This cascade is triggered in `grade_submission()` (step 4 for recalculate, step 5 for invalidate). Note: `invalidate_course_analytics()` is called unconditionally in `grade_submission()` — even for non-final grades — ensuring analytics stay fresh for any grading activity.

**What breaks**: If `invalidate_course_analytics()` is not called, the analytics dashboard will show stale data until the cache TTL expires naturally (GRADE_CACHE_TTL = 3600 seconds = 1 hour).

**Rubric change amplification**: If a rubric is modified after grades exist, ALL grades using that rubric are potentially incorrect. `bulk_recalculate_course_grades(course)` must be called. This recalculates every enrollment in the course — potentially expensive for large courses.

→ see views_assignments.md `grade_submission` for the triggering code
→ see infrastructure.md `recalculate_grade_cache`, `invalidate_course_analytics`

---

## Enrollment State Machine

State transitions are enforced in views, not models. The model stores a plain CharField with no transition validation.

**Why views, not models**: Django model `save()` doesn't have clean access to "previous state" without additional querying or field tracking. The view layer already has the enrollment loaded and can validate transitions cheaply. This is a deliberate trade-off of model purity for simplicity.

**Risk**: Any code that directly sets `enrollment.status = 'completed'` and calls `save()` bypasses the state machine. This is especially dangerous for:
- Management commands that bulk-update enrollments
- Admin panel edits (Django admin has no transition validation)
- Future API endpoints

**Mitigation**: Consider extracting a `transition_enrollment(enrollment, new_status)` function that validates transitions and fires side effects. Currently, this logic lives inline in `update_enrollment_status()`.

→ see models_courses.md "Enrollment State Machine" for the transition table
→ see views_courses.md `update_enrollment_status`

---

## Background Notification Threading

Discussion post notifications create in-app Notification DB records **synchronously** via `send_bulk_notifications()`. A secondary `threading.Thread(daemon=True)` handles background processing (e.g., email dispatch via `_send_notifications_background()`). The HTTP response returns after notification records are created but before background email processing completes.

**Why**: The background thread handles secondary delivery channels (email) that would otherwise add latency. The in-app notification records are always created before the response returns.

**What breaks**: If the main process exits (e.g., worker recycling in production), daemon threads are killed immediately. Background email processing in-flight is lost. However, the in-app notification records are already persisted.

**Acceptable risk**: Lost background processing only affects secondary channels (email). In-app notifications are safe. The alternative (Celery task queue) adds infrastructure complexity disproportionate to the risk.

→ see infrastructure.md `notify_new_discussion_post`

---

## Cached Aggregates Pattern

Three fields in the system are cached aggregates (derived values stored for performance):

| Field | Source of Truth | Recalculated By |
|-------|----------------|-----------------|
| `Enrollment.final_grade_cache` | Grade records | `recalculate_grade_cache()` |
| `CourseAnalytics.average_grade` | Grade records (direct query, NOT `final_grade_cache`) | `rebuild_course_analytics()` |
| `CourseAnalytics.completion_rate` | Enrollment records | `rebuild_course_analytics()` |
| `CourseAnalytics.active_students` | Enrollment records | `rebuild_course_analytics()` |
| `CourseAnalytics.total_submissions` | Submission records | `rebuild_course_analytics()` |
| `InstructorProfile.rating` | (future) Student ratings | Not yet implemented |

**General rule**: Any code that modifies the source-of-truth data MUST invalidate or recalculate the corresponding cache. The invalidation functions are in `core/utils/cache_manager.py` (for analytics) and `core/utils/grading.py` (for grade cache).

! TRIPWIRE — Dual Calculation Paths: `Enrollment.final_grade_cache` and `CourseAnalytics.average_grade` are both derived from Grade records, but they use **separate calculation paths**: `calculate_course_grade()` for the enrollment cache and a direct Grade query loop in `rebuild_course_analytics()` for analytics. Any feature that changes which grades are included (e.g., dropping lowest grade, grade forgiveness) must update BOTH paths, or the per-student grade and the course-wide analytics average will diverge.
→ see infrastructure.md `rebuild_course_analytics` and `calculate_course_grade`

---

## Django Admin Bypass Risk

The Django admin panel allows direct editing of all models without business logic enforcement:
- Enrollment status can be set to any value (bypasses state machine)
- Grades can be created without late penalty (bypasses `apply_grade()`)
- Enrollments can be modified without triggering grade cache updates

**Current mitigation**: None. The admin is trusted-user-only.
**Future mitigation**: Custom admin actions that call the proper business logic functions, or read-only admin for sensitive fields.

---

## Known Issues (pending fix)

Identified by Codex audit (2026-03-10). The two HIGH issues (non-final regrade orphaning grades, resubmission double-counting) were fixed in commit `ee4160b`. Three MEDIUM issues remain:

1. **Rubric scoring path is dead.** `GradeForm` has no `rubric_scores` field, so `grade.rubric_scores` is always saved as `None` despite the model supporting it. The view at `grade.py:147` calls `form.cleaned_data.get("rubric_scores")` which always returns `None`. Fix: add a JSONField to GradeForm if rubric support is needed, or remove the dead code path.

2. **seed_data creates grades without cache recalculation.** `seed_data.py` calls `Grade.objects.create()` directly with `is_final=True` but never calls `recalculate_grade_cache()`. Seeded environments start with stale `Enrollment.final_grade_cache` values. Fix: call `bulk_recalculate_course_grades()` at the end of the seed command, or use `apply_grade()` instead of direct creation.

3. **Max-score validation was inactive** (now fixed). `GradeForm` was instantiated without `max_score`, silently skipping the upper-bound check. Fixed in `ee4160b` — `grade_submission()` now passes `assignment.max_score` to the form on both GET and POST paths.
