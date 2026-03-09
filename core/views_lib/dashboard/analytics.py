"""
Dashboard and analytics views.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import (
    Assignment,
    Course,
    Enrollment,
    EnrollmentStatus,
    Notification,
    Submission,
)
from core.utils.permissions import instructor_required
from core.utils.cache_manager import get_or_rebuild_analytics


@login_required
def student_dashboard(request):
    """
    GET: Student's personal dashboard.

    Displays:
        - Enrolled courses with current grades (final_grade_cache).
        - Upcoming assignments (due in the future, from active enrollments).
        - Recent notifications (last 10).
    """
    enrollments = (
        Enrollment.objects.filter(
            student=request.user,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
        )
        .select_related("course", "course__instructor")
        .order_by("-enrolled_at")
    )

    # Upcoming assignments from actively enrolled courses
    active_course_ids = enrollments.filter(
        status=EnrollmentStatus.ACTIVE,
    ).values_list("course_id", flat=True)

    upcoming_assignments = (
        Assignment.objects.filter(
            course_id__in=active_course_ids,
            due_date__gt=timezone.now(),
            is_published=True,
        )
        .select_related("course")
        .order_by("due_date")[:10]
    )

    # Recent notifications
    recent_notifications = (
        Notification.objects.filter(user=request.user)
        .order_by("-created_at")[:10]
    )

    return render(request, "core/dashboard/student_dashboard.html", {
        "enrollments": enrollments,
        "upcoming_assignments": upcoming_assignments,
        "recent_notifications": recent_notifications,
    })


@login_required
@instructor_required
def course_analytics(request, course_id):
    """
    GET: Instructor analytics dashboard for a specific course.

    Displays:
        - Grade distribution chart data (A/B/C/D/F buckets).
        - Completion rates.
        - Submission trends (submissions per assignment).
        - Active student count.

    Uses ``get_or_rebuild_analytics()`` for cached aggregate data.
    """
    course = get_object_or_404(
        Course.objects.select_related("instructor"),
        pk=course_id,
    )

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only the course instructor can view analytics.")

    analytics = get_or_rebuild_analytics(course)

    # Grade distribution from enrollment caches
    enrollments = Enrollment.objects.filter(
        course=course,
        status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
    )

    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0, "ungraded": 0}
    for enrollment in enrollments:
        if enrollment.final_grade_cache is None:
            grade_distribution["ungraded"] += 1
        else:
            pct = float(enrollment.final_grade_cache)
            if pct >= 90:
                grade_distribution["A"] += 1
            elif pct >= 80:
                grade_distribution["B"] += 1
            elif pct >= 70:
                grade_distribution["C"] += 1
            elif pct >= 60:
                grade_distribution["D"] += 1
            else:
                grade_distribution["F"] += 1

    # Submission counts per assignment
    assignments = course.assignments.order_by("due_date")
    submission_trends = []
    for assignment in assignments:
        count = Submission.objects.filter(assignment=assignment).count()
        submission_trends.append({
            "assignment_title": assignment.title,
            "due_date": assignment.due_date,
            "submission_count": count,
        })

    return render(request, "core/dashboard/course_analytics.html", {
        "course": course,
        "analytics": analytics,
        "grade_distribution": grade_distribution,
        "submission_trends": submission_trends,
        "enrollment_count": enrollments.count(),
    })
