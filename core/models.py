"""
LearnHub Core Models
====================

All ORM models for the LearnHub course management platform.
Single-file convention — every domain's models live here.

Domain layout (in definition order):
    1. Accounts   — User, Organization, InstructorProfile
    2. Courses    — Course, Module, Lesson, Enrollment
    3. Assignments — Assignment, Submission, Grade
    4. Discussions — Thread, Post, Reaction
    5. Notifications — Notification, NotificationPreference
    6. Analytics  — CourseAnalytics
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Choices — gathered at module level for reuse in forms / serializers
# ---------------------------------------------------------------------------

class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    INSTRUCTOR = "instructor", "Instructor"
    STUDENT = "student", "Student"


class CourseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class ContentType(models.TextChoices):
    TEXT = "text", "Text"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"
    INTERACTIVE = "interactive", "Interactive"


class EnrollmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    DROPPED = "dropped", "Dropped"


class AssignmentType(models.TextChoices):
    ESSAY = "essay", "Essay"
    CODE = "code", "Code"
    QUIZ = "quiz", "Quiz"
    FILE_UPLOAD = "file_upload", "File Upload"


class LatePolicy(models.TextChoices):
    NONE = "none", "None"
    PENALIZE = "penalize", "Penalize"
    REJECT = "reject", "Reject"


class SubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    GRADING = "grading", "Grading"
    GRADED = "graded", "Graded"
    RETURNED = "returned", "Returned"


class NotificationType(models.TextChoices):
    ENROLLMENT = "enrollment", "Enrollment"
    GRADE = "grade", "Grade"
    DISCUSSION = "discussion", "Discussion"
    ASSIGNMENT = "assignment", "Assignment"
    SYSTEM = "system", "System"


class NotificationChannel(models.TextChoices):
    IN_APP = "in_app", "In-App"
    EMAIL = "email", "Email"
    BOTH = "both", "Both"


class ReactionType(models.TextChoices):
    LIKE = "like", "Like"
    HELPFUL = "helpful", "Helpful"
    INSIGHTFUL = "insightful", "Insightful"


# ===========================================================================
#  ACCOUNTS DOMAIN
# ===========================================================================


class User(AbstractUser):
    """
    Custom user model for LearnHub. Extends Django's AbstractUser with
    role-based access, optional organization membership, and a short bio.

    AUTH_USER_MODEL = 'core.User'
    """

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True,
        help_text="Primary role that governs default permissions.",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text="Organization this user belongs to, if any.",
    )
    bio = models.TextField(
        blank=True,
        default="",
        help_text="Short biography displayed on the user's profile page.",
    )
    # AbstractUser already provides date_joined with auto_now_add semantics,
    # so we do not redefine it here.

    class Meta:
        ordering = ["username"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_instructor(self):
        return self.role == UserRole.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_admin_role(self):
        """True when user holds the LearnHub admin role (distinct from is_staff)."""
        return self.role == UserRole.ADMIN


class Organization(models.Model):
    """
    A school, company, or other entity that groups users and courses.
    The *settings* JSONField stores org-level configuration such as
    branding overrides and feature flags.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="URL-safe identifier. Must be globally unique.",
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Org-level configuration (branding, feature flags, etc.).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft-delete flag. Inactive orgs are hidden from listings.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "organization"
        verbose_name_plural = "organizations"

    def __str__(self):
        return self.name


class InstructorProfile(models.Model):
    """
    Extended profile for users with the *instructor* role.
    Stores department affiliation, office-hours description,
    and a cached aggregate rating.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )
    department = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Academic department or team within the organization.",
    )
    office_hours = models.TextField(
        blank=True,
        default="",
        help_text="Free-text description of availability for students.",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cached aggregate rating (1.00–5.00). Recomputed by analytics job.",
    )

    class Meta:
        verbose_name = "instructor profile"
        verbose_name_plural = "instructor profiles"

    def __str__(self):
        return f"InstructorProfile: {self.user.username}"


# ===========================================================================
#  COURSES DOMAIN
# ===========================================================================


class Course(models.Model):
    """
    Top-level teaching unit. A course belongs to one instructor and
    optionally to one organization. Contains modules, which contain lessons.
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        help_text="URL-safe identifier for the course.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Markdown-formatted course description shown on the catalogue page.",
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_taught",
        help_text="Primary instructor responsible for this course.",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="courses",
        help_text="Organization that owns this course.",
    )
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT,
        db_index=True,
    )
    max_enrollment = models.PositiveIntegerField(
        default=50,
        help_text="Maximum number of active enrollments allowed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Course-level configuration. Keys may include: "
            "'allow_late_submissions', 'grading_scheme', 'discussion_enabled'."
        ),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "course"
        verbose_name_plural = "courses"

    def __str__(self):
        return self.title

    # ------------------------------------------------------------------
    # Derived data helpers
    # ------------------------------------------------------------------

    @property
    def is_published(self):
        return self.status == CourseStatus.PUBLISHED

    @property
    def enrollment_count(self):
        """Current number of active enrollments."""
        return self.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()

    @property
    def is_full(self):
        return self.enrollment_count >= self.max_enrollment


class Module(models.Model):
    """
    A grouping of lessons within a course.  Modules define the
    top-level curriculum structure visible to students.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        default="",
    )
    order = models.PositiveIntegerField(
        help_text="Display position within the course. Lower = earlier.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Unpublished modules are invisible to students.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "order"]
        unique_together = [["course", "order"]]
        verbose_name = "module"
        verbose_name_plural = "modules"

    def __str__(self):
        return f"{self.course.title} — Module {self.order}: {self.title}"


class Lesson(models.Model):
    """
    An individual piece of content inside a module. The *content_type*
    field determines how the front-end renders the *content* blob
    (plain text, embedded video URL, document link, or interactive widget config).
    """

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.TEXT,
        help_text="Determines the rendering strategy for the content field.",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Lesson body. Interpretation depends on content_type.",
    )
    order = models.PositiveIntegerField(
        help_text="Display position within the module.",
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated time to complete, in minutes.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        ordering = ["module", "order"]
        verbose_name = "lesson"
        verbose_name_plural = "lessons"

    def __str__(self):
        return f"{self.module.title} — Lesson {self.order}: {self.title}"


class Enrollment(models.Model):
    """
    Tracks a student's membership in a course.

    ``final_grade_cache`` is a **CACHED aggregate**. The source of truth
    is the collection of :class:`Grade` records attached to the student's
    submissions for this course. The cache must be explicitly recalculated
    after any grade change via ``recalculate_grade_cache()``.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        help_text="The enrolled student.",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        help_text="The course the student is enrolled in.",
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING,
        db_index=True,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the student completed or was marked complete.",
    )
    final_grade_cache = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Cached final grade percentage. NOT the source of truth — "
            "recomputed from Grade records by the grade-cache refresh job."
        ),
    )

    class Meta:
        unique_together = [["student", "course"]]
        ordering = ["-enrolled_at"]
        verbose_name = "enrollment"
        verbose_name_plural = "enrollments"

    def __str__(self):
        return (
            f"{self.student.username} enrolled in {self.course.title} "
            f"({self.get_status_display()})"
        )


# ===========================================================================
#  ASSIGNMENTS DOMAIN
# ===========================================================================


class Assignment(models.Model):
    """
    A graded task within a course, optionally scoped to a specific module.
    Supports multiple assignment types and configurable late-submission policies.
    The *rubric* JSONField stores structured grading criteria when applicable.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
        help_text="Optional: restrict this assignment to a specific module.",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(
        blank=True,
        default="",
        help_text="Instructions shown to students. Supports Markdown.",
    )
    assignment_type = models.CharField(
        max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.ESSAY,
    )
    due_date = models.DateTimeField(
        help_text="Deadline for on-time submission.",
    )
    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text="Maximum achievable score for this assignment.",
    )
    late_policy = models.CharField(
        max_length=20,
        choices=LatePolicy.choices,
        default=LatePolicy.NONE,
        help_text="How late submissions are handled.",
    )
    rubric = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Structured rubric for grading. Format: "
            "[{'criterion': str, 'max_points': int, 'description': str}, ...]"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Unpublished assignments are invisible to students.",
    )

    class Meta:
        ordering = ["course", "due_date"]
        verbose_name = "assignment"
        verbose_name_plural = "assignments"

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    @property
    def is_past_due(self):
        """True when the current time is past the due date."""
        return timezone.now() > self.due_date


class Submission(models.Model):
    """
    A student's work product for an assignment. Versioned — each resubmission
    creates a new Submission row with an incremented *version* number.
    """

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Submission version; incremented on each resubmission.",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Inline submission content (text, code, etc.).",
    )
    file_path = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="Path to uploaded file in object storage, if applicable.",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        unique_together = [["assignment", "student", "version"]]
        ordering = ["-version"]
        verbose_name = "submission"
        verbose_name_plural = "submissions"

    def __str__(self):
        return (
            f"{self.student.username} — {self.assignment.title} "
            f"(v{self.version}, {self.get_status_display()})"
        )

    @property
    def is_late(self):
        """True when this submission was made after the assignment's due date."""
        return self.submitted_at > self.assignment.due_date


class Grade(models.Model):
    """
    A grader's evaluation of a single submission. Multiple grades may exist
    per submission (e.g. peer review + instructor review). Only the grade
    marked ``is_final=True`` is used for aggregate calculations.

    The *rubric_scores* JSONField mirrors the assignment rubric structure
    with actual scores filled in, enabling per-criterion feedback.
    """

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    grader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="grades_given",
        help_text="The user (instructor or peer) who assigned this grade.",
    )
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text="Points awarded for this submission.",
    )
    feedback = models.TextField(
        blank=True,
        default="",
        help_text="Written feedback to the student.",
    )
    rubric_scores = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Per-criterion scores matching the assignment rubric. "
            "Format: [{'criterion': str, 'score': int, 'comment': str}, ...]"
        ),
    )
    graded_at = models.DateTimeField(auto_now_add=True)
    is_final = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If True, this grade is used for official records and cache refresh.",
    )

    class Meta:
        ordering = ["-graded_at"]
        verbose_name = "grade"
        verbose_name_plural = "grades"

    def __str__(self):
        return (
            f"Grade for {self.submission.student.username} — "
            f"{self.submission.assignment.title}: {self.score}"
        )

    @property
    def percentage(self):
        """Return the score as a percentage of the assignment's max_score."""
        max_score = self.submission.assignment.max_score
        if not max_score:
            return None
        return float(self.score) / float(max_score) * 100


# ===========================================================================
#  DISCUSSIONS DOMAIN
# ===========================================================================


class Thread(models.Model):
    """
    A discussion thread within a course. Threads can be pinned (always
    shown at the top) and locked (no new posts allowed).
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="threads",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="threads",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(
        help_text="Opening post content. Supports Markdown.",
    )
    is_pinned = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Pinned threads appear at the top of the thread list.",
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked threads reject new posts.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        verbose_name = "thread"
        verbose_name_plural = "threads"

    def __str__(self):
        return f"{self.title} (by {self.author.username})"

    @property
    def reply_count(self):
        """Total number of posts in this thread (excluding the opening post)."""
        return self.posts.count()


class Post(models.Model):
    """
    A single post within a discussion thread. Supports nested replies
    via the self-referential *parent* FK. Top-level posts have parent=None.
    """

    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    content = models.TextField(
        help_text="Post body. Supports Markdown.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent post for nested replies. Null for top-level posts.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "post"
        verbose_name_plural = "posts"

    def __str__(self):
        label = "Reply" if self.is_reply else "Post"
        return f"{label} by {self.author.username} in {self.thread.title}"

    @property
    def is_reply(self):
        """True when this post is a reply to another post (not top-level)."""
        return self.parent is not None


class Reaction(models.Model):
    """
    A lightweight reaction on a post. Each user may apply at most one
    reaction of each type per post (enforced by unique_together).
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["post", "user", "reaction_type"]]
        verbose_name = "reaction"
        verbose_name_plural = "reactions"

    def __str__(self):
        return (
            f"{self.user.username} reacted {self.get_reaction_type_display()} "
            f"on post #{self.post.pk}"
        )


# ===========================================================================
#  NOTIFICATIONS DOMAIN
# ===========================================================================


class Notification(models.Model):
    """
    In-app (and optionally emailed) notification for a user.
    The *related_object_id* + *related_content_type* pair provides a
    lightweight generic relation without pulling in Django's full
    ContentType framework.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(
        help_text="Full notification body.",
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="PK of the related object (assignment, thread, etc.).",
    )
    related_content_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="App-label.model string identifying the related object type.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"[{status}] {self.title} — {self.user.username}"


class NotificationPreference(models.Model):
    """
    Per-user, per-notification-type delivery preferences.
    Controls which channel(s) notifications are sent through
    and whether they are enabled at all.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
        help_text="Delivery channel for this notification type.",
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Master switch. When False, this type is fully suppressed.",
    )

    class Meta:
        unique_together = [["user", "notification_type"]]
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def __str__(self):
        state = "enabled" if self.is_enabled else "disabled"
        return (
            f"{self.user.username}: "
            f"{self.get_notification_type_display()} via "
            f"{self.get_channel_display()} ({state})"
        )


# ===========================================================================
#  ANALYTICS DOMAIN
# ===========================================================================


class CourseAnalytics(models.Model):
    """
    Cached aggregate analytics for a course. Recomputed periodically
    by the ``refresh_analytics`` management command. All fields except
    *course* are nullable to support the initial (un-computed) state.

    Use :meth:`is_stale` to decide whether a refresh is warranted
    before serving cached data.
    """

    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="analytics",
    )
    average_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Mean final grade percentage across all completed enrollments.",
    )
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage of enrollments that reached 'completed' status.",
    )
    active_students = models.PositiveIntegerField(
        default=0,
        help_text="Count of currently active enrollments.",
    )
    total_submissions = models.PositiveIntegerField(
        default=0,
        help_text="Lifetime count of submissions across all assignments.",
    )
    last_calculated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the analytics were last refreshed.",
    )

    class Meta:
        verbose_name = "course analytics"
        verbose_name_plural = "course analytics"

    def __str__(self):
        return f"Analytics for {self.course.title}"

    def is_stale(self, ttl_seconds=3600):
        """
        Return True if analytics data is older than *ttl_seconds*
        (default: 1 hour) or has never been computed.

        Args:
            ttl_seconds: Maximum acceptable age of the cached data,
                         in seconds. Defaults to 3600 (one hour).

        Returns:
            bool: True if a refresh is needed, False otherwise.
        """
        if self.last_calculated is None:
            return True
        age = timezone.now() - self.last_calculated
        return age > timedelta(seconds=ttl_seconds)
