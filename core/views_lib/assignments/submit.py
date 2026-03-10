"""
Assignment browsing and submission views.

SUBMISSION VERSIONING LOGIC
===========================
When a student submits to an assignment they already have a previous
submission for, the new submission's ``version`` is incremented.
``MAX_SUBMISSION_VERSIONS`` caps how many versions are allowed.
The new submission is created with status='submitted'; previous versions
remain untouched.

LATE POLICY — REJECT
=====================
If the assignment's ``late_policy`` is 'reject' and the deadline has
passed, the submission attempt is refused outright. Late *penalty*
calculation is handled at grading time (see ``grade.py``), not here.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms import AssignmentForm, SubmissionForm
from core.models import (
    Assignment,
    Course,
    Enrollment,
    EnrollmentStatus,
    LatePolicy,
    Submission,
    SubmissionStatus,
)
from core.utils.permissions import (
    course_participant_required,
    instructor_required,
    student_required,
)

# Maximum number of submission versions allowed per student per assignment
MAX_SUBMISSION_VERSIONS = 5


@login_required
@course_participant_required
def assignment_list(request, course_id):
    """
    GET: Display all assignments for a course.

    Students see their own latest submission status per assignment.
    Instructors see total submission counts per assignment.
    """
    course = get_object_or_404(Course, pk=course_id)
    assignments = course.assignments.order_by("due_date")

    if request.user.is_student:
        # Annotate each assignment with the student's latest submission status
        latest_sub = (
            Submission.objects.filter(
                assignment=OuterRef("pk"),
                student=request.user,
            )
            .order_by("-version")
            .values("status")[:1]
        )
        assignments = assignments.annotate(
            my_submission_status=Subquery(latest_sub),
        )
    elif request.user.is_instructor or request.user.is_admin_role:
        assignments = assignments.annotate(
            submission_count=Count(
                "submissions",
                filter=Q(submissions__status=SubmissionStatus.SUBMITTED),
            ),
        )

    return render(request, "core/assignment_list.html", {
        "course": course,
        "assignments": assignments,
    })


@login_required
@instructor_required
def assignment_create(request, course_id):
    """
    GET:  Display assignment creation form.
    POST: Create a new assignment for the course.

    Only the course instructor or admin may create assignments.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "Only the course instructor can create assignments.")
        return redirect("core:assignment_list", course_id=course.pk)

    if request.method == "POST":
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.save()
            messages.success(request, f"Assignment '{assignment.title}' created.")
            return redirect("core:assignment_detail", course_id=course.pk, assignment_id=assignment.pk)
    else:
        form = AssignmentForm()

    return render(request, "core/assignment_form.html", {
        "course": course,
        "form": form,
    })


@login_required
@course_participant_required
def assignment_detail(request, course_id, assignment_id):
    """
    GET: Display a single assignment.

    Students see their latest submission and any associated grade.
    Instructors see all submissions for the assignment.
    """
    course = get_object_or_404(Course, pk=course_id)
    assignment = get_object_or_404(Assignment, pk=assignment_id, course=course)

    student_submission = None
    student_grade = None
    all_submissions = None

    if request.user.is_student:
        student_submission = (
            Submission.objects.filter(
                assignment=assignment,
                student=request.user,
            )
            .order_by("-version")
            .first()
        )
        if student_submission:
            student_grade = student_submission.grades.filter(is_final=True).first()

    if request.user.is_instructor or request.user.is_admin_role:
        all_submissions = (
            assignment.submissions
            .select_related("student")
            .order_by("student__username", "-version")
        )

    return render(request, "core/assignment_detail.html", {
        "course": course,
        "assignment": assignment,
        "student_submission": student_submission,
        "student_grade": student_grade,
        "all_submissions": all_submissions,
    })


@login_required
@student_required
def submit_assignment(request, course_id, assignment_id):
    """
    GET:  Display the submission form.
    POST: Create a new submission for the assignment.

    Version logic:
        - If the student has a previous submission, the new version is
          ``previous.version + 1``.
        - If the student has reached ``MAX_SUBMISSION_VERSIONS``, the
          submission is refused.
        - Previous versions' statuses are left unchanged.

    Late-policy 'reject':
        - If the assignment is past due and ``late_policy == 'reject'``,
          the submission is refused with an error message.
    """
    course = get_object_or_404(Course, pk=course_id)
    assignment = get_object_or_404(Assignment, pk=assignment_id, course=course)

    # Verify active enrollment
    if not Enrollment.objects.filter(
        student=request.user,
        course=course,
        status=EnrollmentStatus.ACTIVE,
    ).exists() and not request.user.is_admin_role:
        messages.error(request, "You must be actively enrolled to submit assignments.")
        return redirect("core:assignment_detail", course_id=course.pk, assignment_id=assignment.pk)

    # Check late policy — reject
    if assignment.is_past_due and assignment.late_policy == LatePolicy.REJECT:
        messages.error(
            request,
            "This assignment is past due and does not accept late submissions.",
        )
        return redirect("core:assignment_detail", course_id=course.pk, assignment_id=assignment.pk)

    # Determine current version
    latest_version = (
        Submission.objects.filter(
            assignment=assignment,
            student=request.user,
        )
        .aggregate(max_version=Max("version"))["max_version"]
    ) or 0

    if latest_version >= MAX_SUBMISSION_VERSIONS:
        messages.error(
            request,
            f"Maximum number of submissions ({MAX_SUBMISSION_VERSIONS}) reached.",
        )
        return redirect("core:assignment_detail", course_id=course.pk, assignment_id=assignment.pk)

    next_version = latest_version + 1

    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.version = next_version
            submission.status = SubmissionStatus.SUBMITTED
            submission.save()

            messages.success(
                request,
                f"Submission v{next_version} received for '{assignment.title}'.",
            )
            return redirect(
                "core:assignment_detail",
                course_id=course.pk,
                assignment_id=assignment.pk,
            )
    else:
        form = SubmissionForm()

    return render(request, "core/assignment_submit.html", {
        "course": course,
        "assignment": assignment,
        "form": form,
        "next_version": next_version,
        "is_late": assignment.is_past_due,
    })
