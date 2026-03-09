# Assignments Domain — assignments, submissions, grades

Last verified: 2026-03-08
Files covered: core/models.py (Assignment, Submission, Grade)

---

## Assignment [L457]
Work unit within a course, optionally tied to a module.

Fields: course FK, module FK (nullable), title, description, assignment_type (essay/code/quiz/file_upload), due_date DateTimeField, max_score DecimalField, late_policy (none/penalize/reject), rubric JSONField (nullable), created_at, is_published bool
Property: `is_past_due` — compares timezone.now() to due_date

### Late Policy Behavior
- `none` — no penalty regardless of submission time
- `penalize` — late submissions graded with penalty applied (see grading utils)
- `reject` — late submissions are rejected at submission time (view-level enforcement)

! TRIPWIRE — Late Penalty Timing: The penalty is applied at GRADING time by `apply_grade()`, NOT at submission time. A late submission with `penalize` policy is accepted normally — the penalty only appears when the instructor grades it. This is intentional: it allows instructors to see the raw work before the penalty is applied.
→ see cross_cutting.md "Late Penalty Timing"
→ see views_assignments.md `grade_submission`

## Submission [L531]
A student's attempt at an assignment. Supports versioning (resubmission).

Fields: assignment FK, student FK(User), version PositiveInt (default 1), content TextField, file_path CharField (nullable), submitted_at auto, status (draft/submitted/grading/graded/returned)
Meta: unique_together=[['assignment', 'student', 'version']], ordering=['-version']
Property: `is_late` — compares submitted_at to assignment.due_date

### Submission Status Flow
```
draft     → submitted   (student submits)
submitted → grading     (instructor begins review)
grading   → graded      (grade assigned)
graded    → returned    (grade released to student)
```

### Version Tracking
Students can resubmit up to MAX_SUBMISSION_VERSIONS times. Each resubmission creates a new Submission record with incremented version. Only the latest version is considered for grading. Previous versions are preserved for audit trail.
→ see views_assignments.md `submit_assignment`

## Grade [L588]
Instructor's assessment of a submission.

Fields: submission FK, grader FK(User), score DecimalField, feedback TextField, rubric_scores JSONField (nullable), graded_at auto, is_final bool (default False)
Property: `percentage` — returns (score / submission.assignment.max_score * 100)

! When `is_final` is set to True, the grading view triggers `recalculate_grade_cache()` on the enrollment. This is the chain: Grade.is_final → recalculate_grade_cache → Enrollment.final_grade_cache → invalidate_course_analytics.
→ see cross_cutting.md "Grade Cascade"
