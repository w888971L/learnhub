# Course Views — catalog, enrollment, course management

Last verified: 2026-03-09
Files covered: core/views_lib/courses/catalog.py, enrollment.py, management.py

---

## Catalog (catalog.py)

### course_list [L20]
GET: Lists courses. Students see published courses only. Instructors see their own courses (all statuses).
Supports: `?q=` title filter, `?org=` organization filter. Paginated by 12.
Decorators: @login_required
Template: core/course_list.html
→ see models_courses.md Course `status` for visibility rules

### course_detail [L66]
GET: Course detail with modules, lessons, assignments. Checks enrollment status for student context.
Decorators: @login_required, @course_participant_required
Template: core/course_detail.html
Context: course, modules (prefetch lessons), assignments, enrollment (if student), enrollment_count (if instructor/admin)

---

## Enrollment (enrollment.py)

### enroll [L41]
POST only. Creates Enrollment(status='active') for the requesting student.
Guards: course must be published, not full, student not already enrolled.
Side effects: calls `notify_enrollment_change(enrollment, "enrolled")`
Redirects to course_detail.
Decorators: @login_required, @student_required

### drop_enrollment [L82]
POST only. Sets enrollment status to 'dropped'.
Guards: enrollment must exist and be in 'active' or 'pending' status.
Side effects: calls `notify_enrollment_change(enrollment, "dropped")`
Decorators: @login_required, @student_required

### enrollment_list [L111]
GET: Instructor view of all enrollments for a course. Shows student name, status, enrolled date, final_grade_cache.
Supports: `?status=` filter (active/completed/dropped/pending)
Decorators: @login_required, @instructor_required
Template: core/enrollment_list.html

### update_enrollment_status [L141]
POST: Instructor updates enrollment status. Validates state machine transitions.
! TRIPWIRE — State Machine: Invalid transitions return 400. See models_courses.md for valid transitions.
Side effects: calls `notify_enrollment_change(enrollment, enrollment.get_status_display())`.
Decorators: @login_required, @instructor_required

---

## Management (management.py)

### course_create [L20]
GET/POST: Instructor creates a new course. Auto-sets instructor=request.user, organization=user.organization.
Decorators: @login_required, @instructor_required
Form: CourseForm
Template: core/course_form.html

### course_edit [L49]
GET/POST: Edit existing course. Only the course's instructor or admin.
Decorators: @login_required, @instructor_required

### module_list [L80]
GET: Shows modules for a course, ordered by `order` field. Includes lesson count annotation.
Decorators: @login_required, @course_participant_required

### module_create [L102]
GET/POST: Create module. Auto-assigns order = max(existing) + 1.
Decorators: @login_required, @instructor_required

### lesson_list [L143]
GET: Shows lessons for a specific module.
Decorators: @login_required, @course_participant_required

### lesson_create [L161]
GET/POST: Create lesson within a module. Auto-assigns order.
Decorators: @login_required, @instructor_required
