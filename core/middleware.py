"""
Custom middleware for LearnHub.

ActiveUserMiddleware — tracks user activity timestamps.
CourseContextMiddleware — injects the current course into the request object.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import Course


class ActiveUserMiddleware:
    """
    Update the authenticated user's ``last_login`` timestamp on each
    request, throttled to once every 5 minutes to avoid excessive writes.

    Uses the session key ``_learnhub_last_activity_update`` to track when
    the last update occurred.
    """

    THROTTLE_SECONDS = 300  # 5 minutes

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            last_update = request.session.get("_learnhub_last_activity_update")

            should_update = False
            if last_update is None:
                should_update = True
            else:
                elapsed = (now - timezone.datetime.fromisoformat(last_update)).total_seconds()
                if elapsed >= self.THROTTLE_SECONDS:
                    should_update = True

            if should_update:
                request.user.last_login = now
                request.user.save(update_fields=["last_login"])
                request.session["_learnhub_last_activity_update"] = now.isoformat()

        return self.get_response(request)


class CourseContextMiddleware:
    """
    If the URL resolver match contains a ``course_id`` or ``course_slug``
    keyword argument, load the corresponding :class:`Course` and attach
    it to ``request.course``.

    Downstream views and context processors can then access
    ``request.course`` without repeating the lookup.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.course = None

        if hasattr(request, "resolver_match") and request.resolver_match:
            kwargs = request.resolver_match.kwargs or {}

            course_id = kwargs.get("course_id")
            course_slug = kwargs.get("course_slug")

            if course_id:
                try:
                    request.course = Course.objects.get(pk=course_id)
                except Course.DoesNotExist:
                    pass
            elif course_slug:
                try:
                    request.course = Course.objects.get(slug=course_slug)
                except Course.DoesNotExist:
                    pass

        return self.get_response(request)
