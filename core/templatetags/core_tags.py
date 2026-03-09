"""
Custom template tags and filters for LearnHub.

Provides grade-based color coding, human-readable time deltas,
notification badges, and role badges.
"""

from django import template
from django.utils import timezone
from django.utils.html import format_html

from core.models import Notification

register = template.Library()


@register.filter
def grade_color(grade):
    """
    Return a CSS class name based on a numeric grade percentage.

    Usage in templates::

        <span class="{{ student.grade|grade_color }}">{{ student.grade }}%</span>

    Mapping:
        A (90+) = green, B (80+) = blue, C (70+) = yellow,
        D (60+) = orange, F (<60) = red.
    """
    if grade is None:
        return "text-gray-500"

    try:
        value = float(grade)
    except (TypeError, ValueError):
        return "text-gray-500"

    if value >= 90:
        return "text-green-600"
    elif value >= 80:
        return "text-blue-600"
    elif value >= 70:
        return "text-yellow-600"
    elif value >= 60:
        return "text-orange-600"
    else:
        return "text-red-600"


@register.filter
def time_ago(dt):
    """
    Return a human-readable string describing how long ago *dt* occurred.

    Usage::

        {{ post.created_at|time_ago }}
        → "3 hours ago", "2 days ago", "just now"
    """
    if dt is None:
        return ""

    now = timezone.now()
    diff = now - dt

    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = seconds // 604800
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''} ago"


@register.inclusion_tag("core/partials/notification_badge.html")
def notification_badge(user):
    """
    Render a notification count badge for the given user.

    Template: ``core/partials/notification_badge.html``
    """
    count = 0
    if user.is_authenticated:
        count = Notification.objects.filter(user=user, is_read=False).count()
    return {"notification_count": count}


@register.simple_tag
def role_badge(user):
    """
    Return an HTML ``<span>`` element styled as a colored badge for the
    user's role.

    Usage::

        {% role_badge user %}
    """
    if not user or not user.is_authenticated:
        return ""

    role = user.role
    colors = {
        "admin": "bg-purple-100 text-purple-800",
        "instructor": "bg-blue-100 text-blue-800",
        "student": "bg-green-100 text-green-800",
    }
    css = colors.get(role, "bg-gray-100 text-gray-800")
    label = user.get_role_display()

    return format_html(
        '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs '
        'font-medium {}">{}</span>',
        css,
        label,
    )
