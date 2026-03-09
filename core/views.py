"""
LearnHub view import router.

Re-exports every view function from ``core.views_lib`` submodules so that
``core.urls`` (and anything else) can do a single
``from core import views; views.course_list`` style import.
"""

# -- Courses ------------------------------------------------------------------
from core.views_lib.courses.catalog import course_list, course_detail
from core.views_lib.courses.enrollment import (
    enroll,
    drop_enrollment,
    enrollment_list,
    update_enrollment_status,
)
from core.views_lib.courses.management import (
    course_create,
    course_edit,
    module_list,
    module_create,
    lesson_list,
    lesson_create,
)

# -- Assignments --------------------------------------------------------------
from core.views_lib.assignments.submit import (
    assignment_list,
    assignment_create,
    assignment_detail,
    submit_assignment,
)
from core.views_lib.assignments.grade import submission_list, grade_submission

# -- Discussions --------------------------------------------------------------
from core.views_lib.discussions.threads import (
    thread_list,
    thread_create,
    thread_detail,
    post_reply,
)

# -- API ----------------------------------------------------------------------
from core.views_lib.api.views import (
    api_notifications,
    api_mark_read,
    api_course_analytics,
    api_grade_distribution,
)

# -- Auth ---------------------------------------------------------------------
from core.views_lib.auth.auth import register, login_view, logout_view

# -- Dashboard / Analytics ---------------------------------------------------
from core.views_lib.dashboard.analytics import student_dashboard, course_analytics
