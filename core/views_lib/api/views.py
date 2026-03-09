"""
JSON API endpoints for LearnHub.

All views in this module return ``JsonResponse`` objects.
"""

from collections import Counter

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from core.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Grade,
    Notification,
)
from core.utils.permissions import instructor_required
from core.utils.cache_manager import get_or_rebuild_analytics


@login_required
@require_GET
def api_notifications(request):
    """
    GET: Return the current user's most recent notifications (up to 50).

    Response format::

        {
            "notifications": [
                {
                    "id": 1,
                    "type": "grade",
                    "title": "Grade posted",
                    "message": "You received 85/100...",
                    "is_read": false,
                    "created_at": "2026-03-05T12:00:00Z"
                },
                ...
            ]
        }
    """
    notifications = (
        Notification.objects.filter(user=request.user)
        .order_by("-created_at")[:50]
    )

    data = [
        {
            "id": n.pk,
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]

    return JsonResponse({"notifications": data})


@login_required
@require_POST
def api_mark_read(request, notification_id):
    """
    POST: Mark a single notification as read.

    Returns ``{"success": true}`` on success.
    Returns 404 if the notification does not exist or belongs to another user.
    """
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        user=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return JsonResponse({"success": True})


@login_required
@instructor_required
@require_GET
def api_course_analytics(request, course_id):
    """
    GET: Return cached course analytics as JSON.

    Calls ``get_or_rebuild_analytics()`` which transparently refreshes
    stale data. Instructor or admin only.

    Response format::

        {
            "course_id": 1,
            "average_grade": 82.5,
            "completion_rate": 65.0,
            "active_students": 30,
            "total_submissions": 450,
            "last_calculated": "2026-03-05T10:00:00Z"
        }
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        return JsonResponse(
            {"error": "Only the course instructor or admin can view analytics."},
            status=403,
        )

    analytics = get_or_rebuild_analytics(course)

    return JsonResponse({
        "course_id": course.pk,
        "average_grade": float(analytics.average_grade) if analytics.average_grade else None,
        "completion_rate": float(analytics.completion_rate) if analytics.completion_rate else None,
        "active_students": analytics.active_students,
        "total_submissions": analytics.total_submissions,
        "last_calculated": (
            analytics.last_calculated.isoformat() if analytics.last_calculated else None
        ),
    })


@login_required
@instructor_required
@require_GET
def api_grade_distribution(request, course_id):
    """
    GET: Return grade distribution histogram data for a course.

    Groups final grades into letter-grade buckets:
        A: 90-100, B: 80-89, C: 70-79, D: 60-69, F: 0-59

    Response format::

        {
            "course_id": 1,
            "distribution": {
                "A": 12,
                "B": 18,
                "C": 8,
                "D": 3,
                "F": 1
            },
            "total_graded": 42
        }
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        return JsonResponse(
            {"error": "Only the course instructor or admin can view grade distribution."},
            status=403,
        )

    # Collect final_grade_cache values from completed/active enrollments
    enrollments = Enrollment.objects.filter(
        course=course,
        status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
        final_grade_cache__isnull=False,
    ).values_list("final_grade_cache", flat=True)

    buckets = Counter({"A": 0, "B": 0, "C": 0, "D": 0, "F": 0})

    for grade_pct in enrollments:
        pct = float(grade_pct)
        if pct >= 90:
            buckets["A"] += 1
        elif pct >= 80:
            buckets["B"] += 1
        elif pct >= 70:
            buckets["C"] += 1
        elif pct >= 60:
            buckets["D"] += 1
        else:
            buckets["F"] += 1

    return JsonResponse({
        "course_id": course.pk,
        "distribution": dict(buckets),
        "total_graded": sum(buckets.values()),
    })
