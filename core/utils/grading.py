"""
Grade calculation engine.

IMPORTANT: Late penalties are applied at GRADING time, not submission time.
See cross_cutting.md 'Late Penalty Timing'.

This module is a cross-cutting concern: grade calculations affect enrollment
caches, course analytics, and notification dispatch. Any change to penalty
logic or aggregation formulas must be validated against all downstream
consumers.
"""

import math
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from core.models import (
    Enrollment,
    EnrollmentStatus,
    Grade,
    LatePolicy,
    Submission,
    SubmissionStatus,
)


def _get_setting(key):
    """Retrieve a value from LEARNHUB_SETTINGS with a sane fallback."""
    return settings.LEARNHUB_SETTINGS.get(key)


# ---------------------------------------------------------------------------
# Late penalty calculation
# ---------------------------------------------------------------------------


def calculate_late_penalty(submission):
    """
    Return a penalty multiplier between 0.0 (no penalty) and 1.0 (100%
    penalty — score becomes zero).

    The multiplier is subtracted from 1.0 when computing the final score::

        adjusted = raw_score * (1 - penalty)

    Behaviour depends on the assignment's ``late_policy``:

    * ``none``     -- always returns 0.0 (no deduction).
    * ``reject``   -- returns 1.0 if the submission is late (full deduction).
    * ``penalize`` -- returns ``days_late * LATE_PENALTY_PER_DAY``, capped at
                      ``MAX_LATE_DAYS * LATE_PENALTY_PER_DAY``.

    Args:
        submission: A :class:`Submission` instance.

    Returns:
        float: Penalty multiplier in [0.0, 1.0].
    """
    assignment = submission.assignment
    late_policy = assignment.late_policy

    if late_policy == LatePolicy.NONE:
        return 0.0

    if not submission.is_late:
        return 0.0

    if late_policy == LatePolicy.REJECT:
        return 1.0

    # LatePolicy.PENALIZE
    rate = _get_setting("LATE_PENALTY_PER_DAY")
    max_late_days = _get_setting("MAX_LATE_DAYS")

    delta = submission.submitted_at - assignment.due_date
    days_late = math.ceil(delta.total_seconds() / 86400)  # partial day = full day

    penalty = days_late * rate
    cap = max_late_days * rate
    return min(penalty, cap, 1.0)


# ---------------------------------------------------------------------------
# Grade application
# ---------------------------------------------------------------------------


def apply_grade(submission, raw_score, grader, is_final=True):
    """
    Create a :class:`Grade` record for the given submission.

    Applies the late penalty (computed at grading time, NOT submission time)
    to the raw score. Marks the submission as graded and returns the new
    grade. Also demotes any previous final grades for this submission AND
    any final grades on other versions of the same assignment by the same
    student, preventing double-counting in course grade aggregation.

    TRIPWIRE: The penalty is baked into the stored score. If the late-policy
    rules change retroactively, existing grades are **not** automatically
    recalculated — a bulk recalculation must be triggered explicitly.

    Args:
        submission: The :class:`Submission` to grade.
        raw_score: Numeric score before penalty (Decimal or float).
        grader: The :class:`User` who is issuing the grade.
        is_final: Whether this grade should be marked as final.

    Returns:
        Grade: The newly created Grade instance.
    """
    penalty = calculate_late_penalty(submission)
    adjusted_score = Decimal(str(raw_score)) * Decimal(str(1 - penalty))
    adjusted_score = adjusted_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Ensure the adjusted score doesn't go below zero
    adjusted_score = max(adjusted_score, Decimal("0.00"))

    # Demote any previous final grades for this submission
    Grade.objects.filter(submission=submission, is_final=True).update(is_final=False)

    # Also demote final grades on OTHER versions of the same assignment
    # by the same student — prevents double-counting in course grade
    # aggregation when resubmissions exist.
    Grade.objects.filter(
        submission__student=submission.student,
        submission__assignment=submission.assignment,
        is_final=True,
    ).update(is_final=False)

    grade = Grade.objects.create(
        submission=submission,
        grader=grader,
        score=adjusted_score,
        is_final=is_final,
    )

    # Update submission status
    submission.status = SubmissionStatus.GRADED
    submission.save(update_fields=["status"])

    return grade


# ---------------------------------------------------------------------------
# Course grade aggregation
# ---------------------------------------------------------------------------


def calculate_course_grade(enrollment):
    """
    Calculate the weighted average of all final grades for a student in a
    course, expressed as a percentage (0-100).

    Only considers grades where ``is_final=True``. Each assignment
    contributes proportionally to its ``max_score``.

    Args:
        enrollment: An :class:`Enrollment` instance.

    Returns:
        Decimal or None: The aggregate percentage, or None if there are no
        final grades.
    """
    final_grades = Grade.objects.filter(
        submission__student=enrollment.student,
        submission__assignment__course=enrollment.course,
        is_final=True,
    ).select_related("submission__assignment")

    if not final_grades.exists():
        return None

    total_earned = Decimal("0.00")
    total_possible = Decimal("0.00")

    for grade in final_grades:
        max_score = grade.submission.assignment.max_score
        total_earned += grade.score
        total_possible += max_score

    if total_possible == 0:
        return None

    percentage = (total_earned / total_possible) * Decimal("100")
    return percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recalculate_grade_cache(enrollment):
    """
    Recompute the cached final grade for an enrollment and persist it.

    Also triggers an analytics cache rebuild for the course so that
    aggregate statistics stay consistent.

    Args:
        enrollment: An :class:`Enrollment` instance.
    """
    grade = calculate_course_grade(enrollment)
    enrollment.final_grade_cache = grade
    enrollment.save(update_fields=["final_grade_cache"])

    # Trigger analytics rebuild (import here to avoid circular dependency)
    from core.utils.cache_manager import invalidate_course_analytics

    invalidate_course_analytics(enrollment.course)


def bulk_recalculate_course_grades(course):
    """
    Recalculate all enrollment grade caches for a course.

    TRIPWIRE: This function MUST be called after any rubric modification
    that affects grading. Failure to do so leaves cached grades inconsistent
    with the current rubric.

    Args:
        course: A :class:`Course` instance.
    """
    enrollments = Enrollment.objects.filter(
        course=course,
        status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
    )

    for enrollment in enrollments:
        grade = calculate_course_grade(enrollment)
        enrollment.final_grade_cache = grade

    Enrollment.objects.bulk_update(enrollments, ["final_grade_cache"])

    # Rebuild analytics once after all grades are updated
    from core.utils.cache_manager import rebuild_course_analytics

    rebuild_course_analytics(course)
