# Courses Domain — courses, modules, lessons, enrollment

Last verified: 2026-03-08
Files covered: core/models.py (Course, Module, Lesson, Enrollment)

---

## Course [L236]
Central entity. Courses belong to an organization and are taught by one instructor.

Fields: title, slug, description, instructor FK(User), organization FK, status (draft/published/archived), max_enrollment (default 50), settings JSONField, created_at, updated_at
Properties: `is_published`, `enrollment_count`, `is_full`

Status lifecycle: draft → published → archived. Only published courses are visible to students. Instructors see their own courses in all statuses.
→ see views_courses.md `course_list` for visibility rules

## Module [L311]
Ordered container within a course. Holds lessons.

Fields: course FK, title, description, order PositiveInt, is_published bool, created_at
Meta: ordering=['course', 'order'], unique_together=[['course', 'order']]

The `order` field enforces sequence. When creating a new module, auto-assign `max(order) + 1` for the course.
→ see views_courses.md `module_create`

## Lesson [L347]
Content unit within a module.

Fields: module FK, title, content_type (text/video/document/interactive), content TextField, order PositiveInt, duration_minutes (nullable), is_published bool
Meta: ordering=['module', 'order']

`content_type` determines rendering in templates but has no model-level behavior difference.

## Enrollment [L393]
Links a student to a course. Contains the grade cache.

Fields: student FK(User), course FK, status (pending/active/completed/dropped), enrolled_at, completed_at (nullable), final_grade_cache DecimalField (nullable)
Meta: unique_together=[['student', 'course']]

! TRIPWIRE — Grade Cache Duality: `final_grade_cache` is a CACHED aggregate derived from Grade records. It is NOT the source of truth. The source of truth is the individual Grade records linked through Submission → Assignment → Course. Any code that reads `final_grade_cache` must understand it may be stale. Any code that modifies grades must call `recalculate_grade_cache(enrollment)`.
→ see cross_cutting.md "Grade Cache Duality"
→ see infrastructure.md `recalculate_grade_cache`

### Enrollment State Machine
```
pending → active      (enrollment approved)
pending → dropped     (enrollment rejected or student withdraws)
active  → completed   (all coursework done, final grade assigned)
active  → dropped     (student drops mid-course)
dropped → pending     (re-enrollment request)
completed = TERMINAL  (no transitions out)
```
! State transitions are enforced in views (`update_enrollment_status`), not in the model. Invalid transitions return 400.
→ see views_courses.md `update_enrollment_status`
