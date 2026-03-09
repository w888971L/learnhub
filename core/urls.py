"""
LearnHub URL configuration.

All URL patterns for the ``core`` app, grouped by domain.
API views are imported directly from ``core.views_lib.api.views``;
everything else comes through the ``core.views`` import router.
"""

from django.urls import path

from core import views
from core.views_lib.api import views as api_views

app_name = "core"

urlpatterns = [
    # ── Course catalog ───────────────────────────────────────────────────
    path("", views.course_list, name="course_list"),
    path("course/<int:course_id>/", views.course_detail, name="course_detail"),

    # ── Course management ────────────────────────────────────────────────
    path("course/create/", views.course_create, name="course_create"),
    path("course/<int:course_id>/edit/", views.course_edit, name="course_edit"),

    # ── Enrollment ───────────────────────────────────────────────────────
    path("course/<int:course_id>/enroll/", views.enroll, name="enroll"),
    path("course/<int:course_id>/drop/", views.drop_enrollment, name="drop_enrollment"),
    path("course/<int:course_id>/students/", views.enrollment_list, name="enrollment_list"),
    path(
        "course/<int:course_id>/enrollment/<int:enrollment_id>/status/",
        views.update_enrollment_status,
        name="update_enrollment_status",
    ),

    # ── Modules & Lessons ────────────────────────────────────────────────
    path("course/<int:course_id>/modules/", views.module_list, name="module_list"),
    path("course/<int:course_id>/module/create/", views.module_create, name="module_create"),
    path(
        "course/<int:course_id>/module/<int:module_id>/lessons/",
        views.lesson_list,
        name="lesson_list",
    ),
    path(
        "course/<int:course_id>/module/<int:module_id>/lesson/create/",
        views.lesson_create,
        name="lesson_create",
    ),

    # ── Assignments ──────────────────────────────────────────────────────
    path("course/<int:course_id>/assignments/", views.assignment_list, name="assignment_list"),
    path(
        "course/<int:course_id>/assignment/create/",
        views.assignment_create,
        name="assignment_create",
    ),
    path(
        "course/<int:course_id>/assignment/<int:assignment_id>/",
        views.assignment_detail,
        name="assignment_detail",
    ),
    path(
        "course/<int:course_id>/assignment/<int:assignment_id>/submit/",
        views.submit_assignment,
        name="submit_assignment",
    ),
    path(
        "course/<int:course_id>/assignment/<int:assignment_id>/submissions/",
        views.submission_list,
        name="submission_list",
    ),
    path(
        "course/<int:course_id>/assignment/<int:assignment_id>/submission/<int:submission_id>/grade/",
        views.grade_submission,
        name="grade_submission",
    ),

    # ── Discussions ──────────────────────────────────────────────────────
    path("course/<int:course_id>/discussions/", views.thread_list, name="thread_list"),
    path("course/<int:course_id>/discussion/create/", views.thread_create, name="thread_create"),
    path(
        "course/<int:course_id>/discussion/<int:thread_id>/",
        views.thread_detail,
        name="thread_detail",
    ),
    path(
        "course/<int:course_id>/discussion/<int:thread_id>/reply/",
        views.post_reply,
        name="post_reply",
    ),

    # ── Dashboard & Analytics ────────────────────────────────────────────
    path("course/<int:course_id>/analytics/", views.course_analytics, name="course_analytics"),
    path("dashboard/", views.student_dashboard, name="student_dashboard"),

    # ── API endpoints ────────────────────────────────────────────────────
    path("api/notifications/", api_views.api_notifications, name="api_notifications"),
    path(
        "api/notifications/<int:notification_id>/read/",
        api_views.api_mark_read,
        name="api_mark_read",
    ),
    path(
        "api/course/<int:course_id>/analytics/",
        api_views.api_course_analytics,
        name="api_course_analytics",
    ),
    path(
        "api/course/<int:course_id>/grade-distribution/",
        api_views.api_grade_distribution,
        name="api_grade_distribution",
    ),

    # ── Auth ─────────────────────────────────────────────────────────────
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
