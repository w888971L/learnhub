# Charter Review Scratchpad — 2026-03-08

| Charter | Status | Issues Found | Issues Fixed |
|---------|--------|-------------|-------------|
| `models_accounts.md` | FIXED | 4 issues (line anchors, missing field) | All fixed |
| `models_courses.md` | FIXED | 6 issues (line anchors, missing field, bad xref) | All fixed |
| `models_assignments.md` | FIXED | 3 issues (line anchors only) | All fixed |
| `views_courses.md` | FIXED | 15+ issues (templates, line anchors, params, behaviors) | All fixed |
| `views_assignments.md` | FIXED | 10+ issues (templates, line anchors, behaviors, missing view) | All fixed |
| `views_discussions.md` | FIXED | 8 issues (templates, line anchors, behaviors) | All fixed |
| `views_api.md` | FIXED | 6 issues (line anchors, response formats, guards) | All fixed |
| `infrastructure.md` | FIXED | 20+ issues (line anchors, signatures, behaviors, missing entries) | All fixed |
| `cross_cutting.md` | FIXED | 4 issues (threading description, cascade details) | All fixed |

---

## Systemic Issues (affect all charters)

### 1. Line Anchors — Universal Drift
Nearly every `[Lnnn]` anchor is stale. Model charters are off by 80-240 lines (consistent with models.py growing). View charters are off by 20-90 lines. Infrastructure charters off by 20-120 lines. **All line anchors need updating.**

### 2. Template Paths — Systematic Error
All view charters use flat paths (e.g., `core/course_list.html`) but code uses subdirectory structure (e.g., `core/courses/course_list.html`). Every template reference is wrong.

---

## Priority 1: Functional Errors (will mislead developers)

1. **cross_cutting.md + infrastructure.md**: Threading description says "notifications are created in background." WRONG — DB notification records are created synchronously; only email dispatch is backgrounded. Affects both charters.

2. **views_courses.md**: `update_enrollment_status` documented as calling `recalculate_grade_cache()` — it does NOT. Side effect doesn't exist.

3. **views_courses.md**: `notify_enrollment_change(enrollment, 'enrolled')` — function called with 1 arg, not 2. Charter documents wrong signature.

4. **views_courses.md**: Search param is `?q=` not `?search=`.

5. **views_courses.md**: `course_detail` missing `@course_participant_required` decorator in charter.

6. **views_assignments.md**: `assignment_detail` shows final grade only, not "grade history."

7. **views_discussions.md**: Locked thread returns redirect+message, not 403.

8. **views_api.md**: `api_mark_read` never returns 403 (uses get_object_or_404 → 404 only).

9. **views_api.md**: `api_grade_distribution` response field is `total_graded` not `total`.

10. **views_api.md**: Both analytics endpoints have inline course-ownership checks not documented.

11. **infrastructure.md**: `send_notification` param is `notification_type` not `type`.

12. **infrastructure.md**: `ActiveUserMiddleware` session key is `_learnhub_last_activity_update` not `_last_activity_update`.

13. **infrastructure.md**: `CourseContextMiddleware` also handles `course_slug`, not just `course_id`.

14. **infrastructure.md**: `apply_grade()` also marks previous final grades as non-final and updates submission status — charter omits these.

15. **infrastructure.md**: `seed_data` accepts `--flush` arg, charter says "Args: none."

16. **models_courses.md**: Cross-ref `→ see grading.md` points to non-existent charter. Should be `infrastructure.md`.

## Priority 2: Missing Entries

1. **views_assignments.md**: `assignment_create` view in submit.py is completely undocumented.
2. **infrastructure.md**: `enrollment_active_required` decorator in permissions.py is undocumented.
3. **infrastructure.md**: `core/admin.py` listed in header but no body section documents it.
4. **infrastructure.md**: `GradeForm` has `rubric_scores` field not documented.
5. **views_courses.md**: `course_detail` context includes `enrollment_count` not `is_instructor`.

## Priority 3: Stale Line Numbers

Every charter needs line number updates. See Systemic Issues above.

## Priority 4: Cosmetic / Minor

1. **infrastructure.md**: URL pattern count is 31 not 30. Grouping sum doesn't match.
2. **infrastructure.md**: `seed_data` is ~311 lines not ~200. `grade_report` is ~142 lines not ~80.
3. **views_assignments.md**: Version check uses `Max` aggregate not `.count()`.
4. **views_assignments.md**: `submission_list` dedup uses subquery, not "manual dedup."

---

## Potential Code Bugs Discovered

1. **LATENT BUG**: `notify_enrollment_change()` called without required `action` arg in all 3 call sites in enrollment.py → would raise `TypeError` at runtime.
2. **LATENT BUG**: `GradeForm` instantiated without `max_score` in `grade_submission()` → `clean_score` max_score validation bypassed.
3. **SUBTLE**: `apply_grade()` always sets `is_final=True`, then `grade_submission()` overwrites with form value. Works but fragile.
