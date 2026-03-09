"""
Analytics cache management for LearnHub.

Provides functions to rebuild, invalidate, and lazily refresh the
:class:`CourseAnalytics` aggregate cache. The cache is a performance
optimization — the source of truth is always the underlying Grade,
Enrollment, and Submission records.
"""

import logging

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

from core.models import (
    Course,
    CourseAnalytics,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Grade,
    Submission,
)

logger = logging.getLogger(__name__)


def _get_cache_ttl():
    """Return the grade cache TTL in seconds from settings."""
    return settings.LEARNHUB_SETTINGS.get("GRADE_CACHE_TTL", 3600)


def rebuild_course_analytics(course):
    """
    Recalculate :class:`CourseAnalytics` for a course from scratch.

    Computes:
    - **average_grade**: mean of all final Grade scores as a percentage
      of their respective assignment max_score values.
    - **completion_rate**: percentage of enrollments with status 'completed'
      out of all non-dropped enrollments.
    - **active_students**: count of enrollments with status 'active'.
    - **total_submissions**: lifetime count of submissions across all
      assignments in the course.

    Creates the :class:`CourseAnalytics` record if it does not exist.

    Args:
        course: A :class:`Course` instance.

    Returns:
        CourseAnalytics: The updated analytics record.
    """
    analytics, _ = CourseAnalytics.objects.get_or_create(course=course)

    # --- Average grade ---
    final_grades = Grade.objects.filter(
        submission__assignment__course=course,
        is_final=True,
    ).select_related("submission__assignment")

    if final_grades.exists():
        total_earned = Decimal("0.00")
        total_possible = Decimal("0.00")
        for grade in final_grades:
            total_earned += grade.score
            total_possible += grade.submission.assignment.max_score

        if total_possible > 0:
            avg = (total_earned / total_possible) * Decimal("100")
            analytics.average_grade = avg.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            analytics.average_grade = None
    else:
        analytics.average_grade = None

    # --- Completion rate ---
    relevant_enrollments = Enrollment.objects.filter(course=course).exclude(
        status=EnrollmentStatus.DROPPED
    )
    total_relevant = relevant_enrollments.count()

    if total_relevant > 0:
        completed = relevant_enrollments.filter(
            status=EnrollmentStatus.COMPLETED
        ).count()
        rate = (Decimal(completed) / Decimal(total_relevant)) * Decimal("100")
        analytics.completion_rate = rate.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        analytics.completion_rate = None

    # --- Active students ---
    analytics.active_students = Enrollment.objects.filter(
        course=course, status=EnrollmentStatus.ACTIVE
    ).count()

    # --- Total submissions ---
    analytics.total_submissions = Submission.objects.filter(
        assignment__course=course
    ).count()

    # --- Timestamp ---
    analytics.last_calculated = timezone.now()

    analytics.save()
    logger.info("Rebuilt analytics for course '%s' (pk=%d).", course.title, course.pk)

    return analytics


def invalidate_course_analytics(course):
    """
    Mark a course's analytics cache as stale by setting
    ``last_calculated`` to ``None``.

    The next call to :func:`get_or_rebuild_analytics` will trigger a
    full rebuild.

    Args:
        course: A :class:`Course` instance.
    """
    updated = CourseAnalytics.objects.filter(course=course).update(
        last_calculated=None
    )
    if updated:
        logger.info(
            "Invalidated analytics cache for course '%s' (pk=%d).",
            course.title,
            course.pk,
        )


def get_or_rebuild_analytics(course):
    """
    Return the :class:`CourseAnalytics` for a course, rebuilding the
    cache first if it is stale.

    Staleness is determined by comparing ``last_calculated`` against the
    ``GRADE_CACHE_TTL`` setting.

    Args:
        course: A :class:`Course` instance.

    Returns:
        CourseAnalytics: The (possibly freshly rebuilt) analytics record.
    """
    ttl = _get_cache_ttl()

    try:
        analytics = CourseAnalytics.objects.get(course=course)
    except CourseAnalytics.DoesNotExist:
        return rebuild_course_analytics(course)

    if analytics.is_stale(ttl_seconds=ttl):
        return rebuild_course_analytics(course)

    return analytics


def rebuild_all_analytics():
    """
    Rebuild analytics for all published courses.

    Intended for use by management commands (e.g. ``refresh_analytics``)
    as a periodic maintenance task.

    Returns:
        int: Number of courses whose analytics were rebuilt.
    """
    courses = Course.objects.filter(status=CourseStatus.PUBLISHED)
    count = 0

    for course in courses:
        rebuild_course_analytics(course)
        count += 1

    logger.info("Rebuilt analytics for %d published course(s).", count)
    return count
