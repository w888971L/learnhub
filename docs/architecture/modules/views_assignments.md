# Assignment Views — submission, grading, review

Last verified: 2026-03-09
Files covered: core/views_lib/assignments/submit.py, grade.py

---

## Submission (submit.py)

### assignment_list [L47]
GET: Lists assignments for a course. Students see their submission status per assignment. Instructors see submission counts.
Decorators: @login_required, @course_participant_required
Template: core/assignment_list.html

### assignment_create [L86]
GET/POST: Instructor creates a new assignment for a course.
Decorators: @login_required, @instructor_required
Form: AssignmentForm

### assignment_detail [L118]
GET: Assignment detail. Students see their latest submission and final grade (if graded). Instructors see all submissions.
Decorators: @login_required, @course_participant_required
Template: core/assignment_detail.html

### submit_assignment [L162]
GET/POST: Student submits work for an assignment.
Decorators: @login_required, @student_required

**Versioning logic (IMPORTANT):**
1. Query existing submissions for this student+assignment
2. If count >= MAX_SUBMISSION_VERSIONS → return error
3. If late AND late_policy == 'reject' → return error with message
4. New Submission with version = previous_max + 1, status = 'submitted'
5. Previous submissions' statuses are NOT modified

! The version check uses `Max('version')` aggregate to determine the next version number. A race condition is possible under concurrent requests, but the unique_together constraint on (assignment, student, version) will catch duplicates at the DB level.
→ see models_assignments.md Submission "Version Tracking"

---

## Grading (grade.py)

### submission_list [L45]
GET: Instructor views all submissions for an assignment. Shows latest version per student.
Uses: Subquery to filter to each student's latest-version submission (SQLite-compatible alternative to `distinct('student')`).
Supports: `?status=` filter
Decorators: @login_required, @instructor_required
Template: core/submission_list.html

### grade_submission [L98]
GET/POST: Instructor grades a single submission.
Decorators: @login_required, @instructor_required
Form: GradeForm (score, feedback, rubric_scores, is_final)

! TRIPWIRE — This is the critical grading path. The sequence matters:

**Grading flow (5 steps, strict order):**
1. Validate GradeForm (score, feedback, rubric_scores, is_final)
2. Call `apply_grade(submission, raw_score, grader)` → this applies late penalty via `calculate_late_penalty()`. The score stored in Grade may be LOWER than what the instructor entered.
3. Update submission.status = 'graded', save
4. If grade.is_final: call `recalculate_grade_cache(enrollment)` → updates Enrollment.final_grade_cache. Call `notify_grade_posted(grade)` → notifies student.
5. Call `invalidate_course_analytics(course)` → marks CourseAnalytics as stale

**Why this order matters:**
- Step 2 must happen before step 3 (grade must exist before status changes)
- Step 4 must happen after step 2 (cache uses the new grade)
- Step 5 must happen after step 4 (analytics should reflect the new cache)
- Notification in step 4 must happen after grade is saved (student sees correct score)

→ see cross_cutting.md "Late Penalty Timing" and "Grade Cascade"
→ see models_assignments.md Assignment "Late Policy Behavior"
