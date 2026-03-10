"""
Enrollment views — enrolling, dropping, and managing student enrollment status.

ENROLLMENT STATE MACHINE
========================
Valid transitions:
    pending   -> active, dropped
    active    -> completed, dropped
    completed -> (terminal — no transitions out)
    dropped   -> pending  (re-enrollment only)

``update_enrollment_status`` enforces this state machine and returns 400
for any invalid transition.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import Course, CourseStatus, Enrollment, EnrollmentStatus
from core.utils.permissions import instructor_required, student_required
from core.utils.notifications import notify_enrollment_change


# ---------------------------------------------------------------------------
# Allowed enrollment transitions — source of truth for the state machine
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
    EnrollmentStatus.PENDING: {EnrollmentStatus.ACTIVE, EnrollmentStatus.DROPPED},
    EnrollmentStatus.ACTIVE: {EnrollmentStatus.COMPLETED, EnrollmentStatus.DROPPED},
    EnrollmentStatus.COMPLETED: set(),  # terminal
    EnrollmentStatus.DROPPED: {EnrollmentStatus.PENDING},  # re-enrollment only
}


@login_required
@student_required
@require_POST
def enroll(request, course_id):
    """
    POST: Enroll the current student in a published course.

    Guards:
        - Course must be published.
        - Course must not be full (active enrollments < max_enrollment).
        - Student must not already have an enrollment record.

    On success: creates Enrollment(status='active'), fires notification,
    redirects to course_detail.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.status != CourseStatus.PUBLISHED:
        messages.error(request, "This course is not open for enrollment.")
        return redirect("core:course_list")

    if course.is_full:
        messages.error(request, "This course has reached its enrollment limit.")
        return redirect("core:course_detail", course_id=course.pk)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.warning(request, "You are already enrolled in this course.")
        return redirect("core:course_detail", course_id=course.pk)

    enrollment = Enrollment.objects.create(
        student=request.user,
        course=course,
        status=EnrollmentStatus.ACTIVE,
    )

    notify_enrollment_change(enrollment, "enrolled")

    messages.success(request, f"Successfully enrolled in {course.title}.")
    return redirect("core:course_detail", course_id=course.pk)


@login_required
@student_required
@require_POST
def drop_enrollment(request, course_id):
    """
    POST: Drop the current student's enrollment (sets status to 'dropped').

    Only the student themselves may drop. The enrollment must be in a
    state that allows transition to 'dropped' (pending or active).
    """
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course=course,
    )

    if EnrollmentStatus.DROPPED not in VALID_TRANSITIONS.get(enrollment.status, set()):
        messages.error(request, "Your enrollment cannot be dropped in its current state.")
        return redirect("core:course_detail", course_id=course.pk)

    enrollment.status = EnrollmentStatus.DROPPED
    enrollment.save(update_fields=["status"])

    notify_enrollment_change(enrollment, "dropped")

    messages.success(request, f"You have dropped {course.title}.")
    return redirect("core:course_list")


@login_required
@instructor_required
def enrollment_list(request, course_id):
    """
    GET: Instructor view of all students enrolled in a course.

    Supports ``?status=`` filter. Displays final_grade_cache per student.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "Only the course instructor can view enrollments.")
        return redirect("core:course_detail", course_id=course.pk)

    enrollments = Enrollment.objects.filter(course=course).select_related("student")

    status_filter = request.GET.get("status")
    if status_filter and status_filter in EnrollmentStatus.values:
        enrollments = enrollments.filter(status=status_filter)

    context = {
        "course": course,
        "enrollments": enrollments,
        "status_choices": EnrollmentStatus.choices,
        "current_filter": status_filter,
    }
    return render(request, "core/enrollment_list.html", context)


@login_required
@instructor_required
@require_POST
def update_enrollment_status(request, course_id, enrollment_id):
    """
    POST: Instructor updates an enrollment's status.

    Enforces the enrollment state machine. Returns 400 for invalid
    transitions with a descriptive error message.

    Expected POST data:
        ``new_status`` — one of the EnrollmentStatus values.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "Only the course instructor can update enrollment status.")
        return redirect("core:enrollment_list", course_id=course.pk)

    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, course=course)

    new_status = request.POST.get("new_status", "").strip()

    if new_status not in EnrollmentStatus.values:
        return HttpResponseBadRequest(
            f"Invalid status '{new_status}'. "
            f"Must be one of: {', '.join(EnrollmentStatus.values)}."
        )

    allowed = VALID_TRANSITIONS.get(enrollment.status, set())
    if new_status not in allowed:
        current_label = enrollment.get_status_display()
        allowed_labels = ", ".join(
            EnrollmentStatus(s).label for s in allowed
        ) or "none (terminal state)"
        return HttpResponseBadRequest(
            f"Invalid transition: {current_label} -> {new_status}. "
            f"Allowed transitions from '{current_label}': {allowed_labels}."
        )

    enrollment.status = new_status
    enrollment.save(update_fields=["status"])

    notify_enrollment_change(enrollment, enrollment.get_status_display())

    messages.success(
        request,
        f"Enrollment for {enrollment.student.username} updated to "
        f"{enrollment.get_status_display()}.",
    )
    return redirect("core:enrollment_list", course_id=course.pk)
