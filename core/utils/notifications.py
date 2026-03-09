"""
Notification dispatch system for LearnHub.

Handles creation, preference checking, bulk dispatch, and convenience
wrappers for common notification events (grade posted, enrollment change,
new discussion post).
"""

import logging
import threading

from django.conf import settings

from core.models import (
    Notification,
    NotificationPreference,
    NotificationType,
)

logger = logging.getLogger(__name__)


def _get_setting(key):
    return settings.LEARNHUB_SETTINGS.get(key)


# ---------------------------------------------------------------------------
# Core dispatch
# ---------------------------------------------------------------------------


def send_notification(user, notification_type, title, message, related_object=None):
    """
    Create an in-app :class:`Notification` for *user*, respecting their
    :class:`NotificationPreference` settings.

    If the user has disabled this notification type, returns ``None``
    without creating a record.

    Args:
        user: The recipient :class:`User`.
        notification_type: A :class:`NotificationType` value.
        title: Short notification headline.
        message: Full notification body.
        related_object: Optional Django model instance to link via
            ``related_object_id`` / ``related_content_type``.

    Returns:
        Notification or None: The created notification, or None if
        suppressed by user preference.
    """
    # Check user preferences
    pref = NotificationPreference.objects.filter(
        user=user, notification_type=notification_type
    ).first()

    if pref and not pref.is_enabled:
        return None

    kwargs = {
        "user": user,
        "notification_type": notification_type,
        "title": title,
        "message": message,
    }

    if related_object is not None:
        kwargs["related_object_id"] = related_object.pk
        kwargs["related_content_type"] = (
            f"{related_object._meta.app_label}.{related_object._meta.model_name}"
        )

    return Notification.objects.create(**kwargs)


def send_bulk_notifications(users, notification_type, title, message):
    """
    Send the same notification to multiple users, processed in batches
    of ``NOTIFICATION_BATCH_SIZE``.

    Preferences are checked per-user; users who have disabled this type
    are silently skipped.

    Args:
        users: Iterable of :class:`User` instances.
        notification_type: A :class:`NotificationType` value.
        title: Short notification headline.
        message: Full notification body.

    Returns:
        list[Notification]: All successfully created notifications.
    """
    batch_size = _get_setting("NOTIFICATION_BATCH_SIZE")
    user_list = list(users)
    created = []

    # Pre-fetch suppressed user IDs for this notification type
    suppressed_ids = set(
        NotificationPreference.objects.filter(
            user__in=user_list,
            notification_type=notification_type,
            is_enabled=False,
        ).values_list("user_id", flat=True)
    )

    notifications_to_create = []
    for user in user_list:
        if user.pk in suppressed_ids:
            continue
        notifications_to_create.append(
            Notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
            )
        )

    # Create in batches
    for i in range(0, len(notifications_to_create), batch_size):
        batch = notifications_to_create[i : i + batch_size]
        created.extend(Notification.objects.bulk_create(batch))

    return created


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def notify_grade_posted(grade):
    """
    Notify the student that a grade has been posted for their submission.

    Args:
        grade: A :class:`Grade` instance (must have ``is_final=True``).
    """
    submission = grade.submission
    student = submission.student
    assignment = submission.assignment

    return send_notification(
        user=student,
        notification_type=NotificationType.GRADE,
        title=f"Grade posted: {assignment.title}",
        message=(
            f"Your submission for '{assignment.title}' has been graded. "
            f"Score: {grade.score}/{assignment.max_score}."
        ),
        related_object=grade,
    )


def notify_enrollment_change(enrollment, action):
    """
    Notify the student of an enrollment status change, and notify the
    course instructor when a new student enrolls.

    Args:
        enrollment: An :class:`Enrollment` instance.
        action: A string describing the change (e.g. 'enrolled', 'dropped',
            'completed').
    """
    student = enrollment.student
    course = enrollment.course

    # Notify the student
    send_notification(
        user=student,
        notification_type=NotificationType.ENROLLMENT,
        title=f"Enrollment update: {course.title}",
        message=f"Your enrollment in '{course.title}' has been {action}.",
        related_object=enrollment,
    )

    # Notify the instructor of new enrollments
    if action == "enrolled":
        send_notification(
            user=course.instructor,
            notification_type=NotificationType.ENROLLMENT,
            title=f"New enrollment: {course.title}",
            message=(
                f"{student.username} has enrolled in '{course.title}'."
            ),
            related_object=enrollment,
        )


def notify_new_discussion_post(post):
    """
    Notify participants of a discussion thread when a new post is added.

    Runs the notification dispatch in a background daemon thread to avoid
    blocking the HTTP request cycle.

    Args:
        post: A :class:`Post` instance (the newly created post).
    """
    thread = post.thread

    # Gather unique participant IDs (thread author + all post authors),
    # excluding the post's own author.
    participant_ids = set(
        thread.posts.values_list("author_id", flat=True)
    )
    participant_ids.add(thread.author_id)
    participant_ids.discard(post.author_id)

    if not participant_ids:
        return

    from core.models import User

    participants = User.objects.filter(pk__in=participant_ids)
    notifications = send_bulk_notifications(
        users=participants,
        notification_type=NotificationType.DISCUSSION,
        title=f"New reply in: {thread.title}",
        message=(
            f"{post.author.username} posted a reply in '{thread.title}'."
        ),
    )

    if notifications:
        notification_ids = [n.pk for n in notifications]
        t = threading.Thread(
            target=_send_notifications_background,
            args=(notification_ids,),
            daemon=True,
        )
        t.start()


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


def _send_notifications_background(notification_ids):
    """
    Background worker that processes notifications for email dispatch.

    Currently a placeholder — marks notifications as processed. In a
    production system, this would integrate with an email service
    (SendGrid, SES, etc.) based on the user's channel preference.

    Args:
        notification_ids: List of :class:`Notification` PKs to process.
    """
    try:
        # Placeholder: in production, this would send emails for
        # notifications whose user has channel='email' or channel='both'.
        count = Notification.objects.filter(
            pk__in=notification_ids
        ).count()
        logger.info(
            "Background notification worker processed %d notifications.",
            count,
        )
    except Exception:
        logger.exception("Error in background notification worker.")
