"""
Django admin configuration for all LearnHub core models.

Provides customized ModelAdmin subclasses for frequently managed models
and simple registrations for the rest.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import (
    Assignment,
    Course,
    CourseAnalytics,
    Enrollment,
    Grade,
    InstructorProfile,
    Lesson,
    Module,
    Notification,
    NotificationPreference,
    Organization,
    Post,
    Reaction,
    Submission,
    Thread,
    User,
)


# ---------------------------------------------------------------------------
# Accounts domain
# ---------------------------------------------------------------------------


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "role",
        "organization",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff", "organization"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["username"]

    # Add 'role', 'organization', and 'bio' to the default fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "LearnHub Profile",
            {"fields": ("role", "organization", "bio")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "LearnHub Profile",
            {"fields": ("role", "organization")},
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "department", "rating"]
    search_fields = ["user__username", "department"]


# ---------------------------------------------------------------------------
# Courses domain
# ---------------------------------------------------------------------------


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "instructor",
        "organization",
        "status",
        "max_enrollment",
        "created_at",
    ]
    list_filter = ["status", "organization"]
    search_fields = ["title", "slug", "instructor__username"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["instructor", "organization"]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order", "is_published"]
    list_filter = ["is_published", "course"]
    ordering = ["course", "order"]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["title", "module", "content_type", "order", "is_published"]
    list_filter = ["content_type", "is_published"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "course",
        "status",
        "enrolled_at",
        "final_grade_cache",
    ]
    list_filter = ["status", "course"]
    search_fields = ["student__username", "course__title"]
    raw_id_fields = ["student", "course"]


# ---------------------------------------------------------------------------
# Assignments domain
# ---------------------------------------------------------------------------


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "course",
        "assignment_type",
        "due_date",
        "max_score",
        "late_policy",
        "is_published",
    ]
    list_filter = ["assignment_type", "late_policy", "is_published"]
    search_fields = ["title", "course__title"]
    raw_id_fields = ["course", "module"]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "assignment",
        "version",
        "status",
        "submitted_at",
    ]
    list_filter = ["status"]
    search_fields = ["student__username", "assignment__title"]
    raw_id_fields = ["student", "assignment"]


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = [
        "submission",
        "grader",
        "score",
        "is_final",
        "graded_at",
    ]
    list_filter = ["is_final"]
    raw_id_fields = ["submission", "grader"]


# ---------------------------------------------------------------------------
# Discussions domain
# ---------------------------------------------------------------------------


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "author", "is_pinned", "is_locked", "created_at"]
    list_filter = ["is_pinned", "is_locked", "course"]
    search_fields = ["title", "author__username"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["thread", "author", "is_reply", "created_at"]
    search_fields = ["author__username", "thread__title"]
    raw_id_fields = ["thread", "author", "parent"]

    @admin.display(boolean=True, description="Reply?")
    def is_reply(self, obj):
        return obj.parent is not None


# ---------------------------------------------------------------------------
# Simple registrations (no custom admin needed)
# ---------------------------------------------------------------------------

admin.site.register(Reaction)
admin.site.register(Notification)
admin.site.register(NotificationPreference)
admin.site.register(CourseAnalytics)
