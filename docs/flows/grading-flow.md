# Grading Flow — How Instructors Grade Submissions

## Overview

This flow covers how instructors grade student submissions, including the late penalty mechanism, the grade cascade, and the analytics update chain.

## Key Files

| File | Purpose |
|------|---------|
| `core/views_lib/assignments/grade.py` | Grading views |
| `core/utils/grading.py` | Late penalty calculation, grade cache updates |
| `core/utils/cache_manager.py` | Analytics cache invalidation |
| `core/utils/notifications.py` | Grade notification to student |
| `core/models.py` (Grade, Enrollment) | Grade record and cached grade |

---

## Step 1: View Submissions

The instructor navigates to an assignment's submission list (`/course/<id>/assignment/<id>/submissions/`). They see a table of submissions showing:
- Student name
- Version number
- Submission date
- Late indicator (if submitted after due date)
- Current status (submitted / grading / graded / returned)
- Existing grade (if any)

The list shows the latest version per student.

## Step 2: Open Grading Form

Clicking "Grade" on a submission opens the grading form (`/course/<id>/assignment/<id>/submission/<id>/grade/`). The form shows:
- Student's submission content
- Assignment rubric (if defined)
- Score input (0 to max_score)
- Feedback textarea
- "Final grade" checkbox

If the submission is late, a warning banner shows the expected penalty.

## Step 3: Submit Grade

The instructor enters a score and submits. The following happens in strict order:

### Step 3a: Late Penalty Calculation
`calculate_late_penalty(submission)` runs. If the assignment uses the `penalize` policy and the submission is late:
- penalty = days_late * 0.10 (LATE_PENALTY_PER_DAY)
- Capped at: MAX_LATE_DAYS (7) * 0.10 = 0.70 maximum penalty
- Example: 3 days late → 30% penalty. Instructor enters 85 → student receives 59.5

If late_policy is `none`, penalty = 0 (full credit regardless).

### Step 3b: Grade Record Created
`apply_grade()` creates a Grade record with the penalty-adjusted score. The instructor entered 85 but the Grade.score stores 59.5. Both values are shown in the UI so the instructor understands the impact.

### Step 3c: Submission Status Updated
`submission.status` is set to 'graded'.

### Step 3d: Grade Cascade (if final)
If the "Final grade" checkbox was checked:
1. `recalculate_grade_cache(enrollment)` — recalculates the student's overall course grade from all final Grade records, stores in `Enrollment.final_grade_cache`
2. `notify_grade_posted(grade)` — sends notification to the student
3. `invalidate_course_analytics(course)` — marks analytics cache as stale

### Step 3e: Analytics Invalidation
`invalidate_course_analytics(course)` is called regardless of whether the grade is final. This ensures the analytics dashboard reflects the latest grading activity.

## Step 4: Student Sees Grade

The student receives a notification (in-app). On their dashboard or assignment detail page, they see:
- Raw score (what the instructor entered)
- Penalty applied (if any)
- Final score (after penalty)
- Feedback text

## Special Case: Rubric Changes

If an instructor modifies an assignment's rubric after grades exist, all existing grades may be based on outdated criteria. The system does NOT automatically recalculate — the instructor must manually call `bulk_recalculate_course_grades(course)` (via admin or management command) to recompute all enrollment grade caches.

---

