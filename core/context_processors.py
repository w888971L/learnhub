"""
Template context processors for LearnHub.

Provides global template variables related to the current user's role,
notification state, and active course context.
"""

from core.models import Notification


def learnhub_context(request):
    """
    Inject LearnHub-specific variables into every template context.

    Returns a dict with:
    - ``user_role``: the user's role string, or None for anonymous users.
    - ``is_instructor``: True if the user is an instructor.
    - ``is_student``: True if the user is a student.
    - ``unread_notification_count``: number of unread in-app notifications.
    - ``current_course``: the Course instance set by
      :class:`CourseContextMiddleware`, or None.
    """
    ctx = {
        "user_role": None,
        "is_instructor": False,
        "is_student": False,
        "unread_notification_count": 0,
        "current_course": getattr(request, "course", None),
    }

    if request.user.is_authenticated:
        ctx["user_role"] = request.user.role
        ctx["is_instructor"] = request.user.is_instructor
        ctx["is_student"] = request.user.is_student
        ctx["unread_notification_count"] = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

    return ctx
