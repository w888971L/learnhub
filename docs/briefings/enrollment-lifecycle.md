# Technical Briefing: Enrollment Lifecycle

**Author**: Gemini  
**Last produced**: 2026-03-10  
**Charter sources**: `views_courses.md`, `models_courses.md`, `cross_cutting.md`, `infrastructure.md`

---

## 1. Executive Summary
The enrollment lifecycle in LearnHub manages the relationship between students and courses through a strict state machine enforced at the view layer. It serves as the gateway to course content and the anchor for the "Grade Cache Duality," a performance-oriented architecture that mirrors student performance in a cached aggregate field.

## 2. Architecture Overview
The system centers around the `Enrollment` model (`core/models.py [L393]`), which links a `User` (student) to a `Course`.

### Key Components:
- **Model**: `Enrollment` tracks `status`, `enrolled_at`, `completed_at`, and `final_grade_cache`.
- **Views**: 
    - `enroll` (`enrollment.py [L41]`): The entry point for students.
    - `drop_enrollment` (`enrollment.py [L82]`): Allows students to withdraw.
    - `update_enrollment_status` (`enrollment.py [L141]`): The instructor-facing control point for the state machine.
- **State Machine**: Defined in `enrollment.py` via `VALID_TRANSITIONS`.
- **Notifications**: Triggered via `notify_enrollment_change` (`core/utils/notifications.py [L145]`).

## 3. Key Design Decisions

### View-Layer State Enforcement
Unlike many systems that enforce state transitions in the model's `save()` method, LearnHub enforces the enrollment state machine in the view layer (`update_enrollment_status`). This was a deliberate trade-off to avoid the complexity of tracking "previous state" within the Django ORM, as the view already has the necessary context to validate transitions cheaply.

### Decoupled Grade Cache
The `final_grade_cache` on the `Enrollment` model is a performance optimization. The system avoids recalculating a student's entire grade history on every dashboard load by storing a cached aggregate. This requires a "Grade Cascade" where any grade finalization triggers a cache refresh.

## 4. Non-Obvious Behavior

### The Re-enrollment "Lockout"
Students cannot re-enroll themselves once they have an enrollment record, even if its status is `dropped`. The `enroll` view (`enrollment.py [L68]`) blocks any student who already has an enrollment record. Re-enrollment MUST be instructor-initiated by transitioning the status from `dropped` back to `pending`.

### Terminal Completion
The `completed` state is strictly terminal. Once an enrollment is marked `completed`, no transitions out are allowed by the state machine. This prevents accidental modification of historical records but requires instructors to be certain before finalizing.

### Side-Effect Consistency
Status changes trigger notifications synchronously. If `notify_enrollment_change` fails, the status change (which is saved just before) will persist, but the user won't be notified.

## 5. Risk Profile

### Admin Panel Bypass (TRIPWIRE)
Because the state machine is enforced in the view layer, the Django Admin panel bypasses all transition logic. An admin can move an enrollment from `completed` back to `active` or set it to an invalid string entirely, potentially breaking application logic that expects valid states.

### Stale Grade Cache
The `final_grade_cache` is highly susceptible to drift. Any direct ORM operations on `Grade` records (e.g., via management commands or the admin panel) that bypass the `grade_submission` view will result in a stale cache.

### Analytics Coupling
Enrollment status changes do not automatically invalidate course analytics. Only the grading flow triggers `invalidate_course_analytics`. This means course-wide "completion rates" or "active student" counts in analytics may be stale for up to 1 hour (the cache TTL).

## 6. Technical Debt & Opportunities

### State Machine Encapsulation
The logic for `VALID_TRANSITIONS` and the status update side effects are currently split between a global dictionary and inline view code. Moving this into a dedicated `EnrollmentService` or a `transition_to(new_status)` method on the model would improve testability and prevent bypasses.

### Completion Automation
Currently, the transition to `completed` is manual. There is an opportunity to automate this when a student completes all lessons and assignments, though the requirement for a "final grade" makes this a complex cross-domain touchpoint.

## 7. Connections

### The Grading Flow
Enrollment is the primary consumer of the grading system. The "Grade Cascade" (`Grade` -> `Enrollment.final_grade_cache` -> `CourseAnalytics`) is the most significant architectural connection, linking student performance directly to course-level reporting.

### Notification Batching
Enrollment changes use the `send_notification` utility, which is synchronous. For very large courses, if an instructor were to bulk-update statuses (a feature not yet implemented but logically possible), this could lead to request timeouts.

### Course Visibility
The `Course.enrollment_count` property (`core/models.py [L306]`) dynamically filters for `active` enrollments. This count determines if a course is "full" (`is_full`), which in turn controls the visibility of the "Enroll" button in the catalog.
