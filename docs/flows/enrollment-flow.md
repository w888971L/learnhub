# Enrollment Flow — How Students Join and Leave Courses

## Overview

This flow covers how students discover courses, enroll, and drop. It also covers how instructors manage enrollment status.

## Key Files

| File | Purpose |
|------|---------|
| `core/views_lib/courses/catalog.py` | Course listing and detail views |
| `core/views_lib/courses/enrollment.py` | Enrollment and drop actions |
| `core/models.py` (Enrollment) | Enrollment record with state machine |
| `core/utils/notifications.py` | Enrollment change notifications |

---

## Step 1: Browse Courses

The student visits the course catalog (`/`). The `course_list` view shows all published courses, paginated 12 per page. Students can search by title and filter by organization.

Each course card shows: title, instructor name, enrollment count vs. max, and an "Enroll" button (or "Enrolled" badge if already enrolled).

## Step 2: View Course Detail

Clicking a course opens the detail page (`/course/<id>/`). The student sees:
- Course description and instructor info
- Module/lesson outline
- Assignment list with due dates
- Their enrollment status (if any)

## Step 3: Enroll

The student clicks "Enroll." This POSTs to `/course/<id>/enroll/`.

**Guards checked (in order):**
1. Course must be published (status = 'published')
2. Course must not be full (enrollment_count < max_enrollment)
3. Student must not already be enrolled

If all guards pass, an Enrollment record is created with status = 'active'. The system sends notifications to both the student ("You've enrolled in...") and the instructor ("New student enrolled in...").

The student is redirected back to the course detail page, now with full access to course materials.

## Step 4: Drop (Optional)

An enrolled student can drop a course by clicking "Drop" on the course detail page. This POSTs to `/course/<id>/drop/`.

The enrollment status changes to 'dropped'. Notifications are sent. The student loses access to course materials but their submission history is preserved.

## Step 5: Instructor Manages Status

Instructors can view all enrollments at `/course/<id>/students/` and update statuses.

**Allowed transitions:**
- pending → active (approve enrollment)
- pending → dropped (reject)
- active → completed (student finished the course)
- active → dropped (instructor removes student)
- dropped → pending (re-enrollment, instructor-initiated only)

**Note on re-enrollment**: Students cannot re-enroll themselves after being dropped. The `enroll` view blocks any student who already has an enrollment record (regardless of status). Re-enrollment requires an instructor to manually transition the enrollment from 'dropped' back to 'pending' via the enrollment management page.

**Note on completing**: Marking an enrollment as 'completed' does NOT automatically recalculate the student's grade cache. The grade cache is updated through the grading flow (when individual grades are finalized). Instructors should ensure all grades are finalized before completing an enrollment.

---

*Charter sources: views_courses.md, models_courses.md, infrastructure.md*
