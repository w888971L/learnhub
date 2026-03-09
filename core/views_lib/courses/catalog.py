"""
Course catalog views — browsing and viewing course details.
"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from core.models import (
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
)
from core.utils.permissions import course_participant_required


@login_required
def course_list(request):
    """
    GET: Display published courses.

    - Instructors also see their own courses in any status (draft, archived, etc.).
    - Supports ``?q=`` search by title and ``?org=`` filter by organization id.
    - Paginated by 12.
    """
    q = request.GET.get("q", "").strip()
    org_filter = request.GET.get("org")

    if request.user.is_instructor:
        # Instructors see published courses + all their own courses
        courses = Course.objects.filter(
            Q(status=CourseStatus.PUBLISHED) | Q(instructor=request.user)
        ).distinct()
    else:
        courses = Course.objects.filter(status=CourseStatus.PUBLISHED)

    if q:
        courses = courses.filter(title__icontains=q)

    if org_filter:
        courses = courses.filter(organization_id=org_filter)

    courses = courses.annotate(
        active_enrollment_count=Count(
            "enrollments",
            filter=Q(enrollments__status=EnrollmentStatus.ACTIVE),
        )
    ).select_related("instructor", "organization")

    paginator = Paginator(courses, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": q,
        "org_filter": org_filter,
    }
    return render(request, "core/courses/course_list.html", context)


@login_required
@course_participant_required
def course_detail(request, course_id):
    """
    GET: Display a single course with its modules, lessons, and assignments.

    Students see their enrollment status. Instructors see the active enrollment
    count. Admins have full visibility.
    """
    course = get_object_or_404(
        Course.objects.select_related("instructor", "organization"),
        pk=course_id,
    )

    modules = (
        course.modules.prefetch_related("lessons")
        .annotate(lesson_count=Count("lessons"))
        .order_by("order")
    )

    assignments = course.assignments.order_by("due_date")

    # Enrollment state for the current student
    enrollment = None
    if request.user.is_student:
        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).first()

    # Enrollment count for the instructor
    enrollment_count = None
    if request.user.is_instructor or request.user.is_admin_role:
        enrollment_count = course.enrollment_count

    context = {
        "course": course,
        "modules": modules,
        "assignments": assignments,
        "enrollment": enrollment,
        "enrollment_count": enrollment_count,
    }
    return render(request, "core/courses/course_detail.html", context)
