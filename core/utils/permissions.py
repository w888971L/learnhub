"""
Role-based access control decorators for LearnHub views.

Provides reusable decorators that enforce role checks, course participation,
and active enrollment before allowing access to a view.
"""

from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from core.models import Course, Enrollment, EnrollmentStatus


# ---------------------------------------------------------------------------
# Generic role decorator
# ---------------------------------------------------------------------------


def role_required(*roles):
    """
    Decorator that restricts access to users whose ``role`` attribute
    matches one of the given *roles*.

    Usage::

        @role_required('admin', 'instructor')
        def my_view(request):
            ...

    Returns 403 Forbidden if the user's role is not in the allowed set.
    Requires ``django.contrib.auth.middleware.AuthenticationMiddleware``.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required.")
            if request.user.role not in roles:
                return HttpResponseForbidden(
                    f"Access denied. Required role(s): {', '.join(roles)}."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


# ---------------------------------------------------------------------------
# Convenience shortcuts
# ---------------------------------------------------------------------------

instructor_required = role_required("instructor", "admin")
student_required = role_required("student", "admin")


# ---------------------------------------------------------------------------
# Course-scoped decorators
# ---------------------------------------------------------------------------


def course_participant_required(view_func):
    """
    Ensures the user is either the instructor of, or actively enrolled in,
    the course identified by the ``course_id`` URL keyword argument.

    Admins are always allowed through.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if request.user.role == "admin":
            return view_func(request, *args, **kwargs)

        course_id = kwargs.get("course_id")
        course = get_object_or_404(Course, pk=course_id)

        is_instructor = course.instructor_id == request.user.pk
        is_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
        ).exists()

        if not (is_instructor or is_enrolled):
            return HttpResponseForbidden(
                "You must be the course instructor or an enrolled student."
            )

        return view_func(request, *args, **kwargs)

    return _wrapped


def enrollment_active_required(view_func):
    """
    Ensures the user has an **active** enrollment in the course identified
    by the ``course_id`` URL keyword argument.

    Admins bypass this check.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if request.user.role == "admin":
            return view_func(request, *args, **kwargs)

        course_id = kwargs.get("course_id")
        course = get_object_or_404(Course, pk=course_id)

        has_active = Enrollment.objects.filter(
            student=request.user,
            course=course,
            status=EnrollmentStatus.ACTIVE,
        ).exists()

        if not has_active:
            return HttpResponseForbidden(
                "An active enrollment in this course is required."
            )

        return view_func(request, *args, **kwargs)

    return _wrapped
