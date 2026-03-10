"""
Grading views — viewing submissions and grading them.

CRITICAL GRADING FLOW
=====================
Late penalty is applied at grade time, NOT at submission time.

1. Validate GradeForm.
2. Call ``apply_grade(submission, raw_score, grader=request.user)`` — this
   function applies any late penalty based on the assignment's late_policy.
3. Set submission.status = 'graded'.
4. If ``is_final``:
   a. Call ``recalculate_grade_cache(enrollment)`` to refresh the cached
      aggregate grade on the Enrollment record.
   b. Call ``notify_grade_posted(grade)`` to send notification.
5. Call ``invalidate_course_analytics(course)`` so stale analytics are
   recomputed on next access.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import GradeForm
from core.models import (
    Assignment,
    Course,
    Enrollment,
    EnrollmentStatus,
    Submission,
    SubmissionStatus,
)
from core.utils.permissions import instructor_required
from core.utils.grading import (
    apply_grade,
    recalculate_grade_cache,
)
from core.utils.notifications import notify_grade_posted
from core.utils.cache_manager import invalidate_course_analytics


@login_required
@instructor_required
def submission_list(request, course_id, assignment_id):
    """
    GET: Instructor views all submissions for a specific assignment.

    Filters:
        ``?status=`` — filter by submission status.

    Displays the latest version per student by default.
    """
    course = get_object_or_404(Course, pk=course_id)
    assignment = get_object_or_404(Assignment, pk=assignment_id, course=course)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "Only the course instructor can view submissions.")
        return redirect(
            "core:assignment_detail",
            course_id=course.pk,
            assignment_id=assignment.pk,
        )

    # Subquery: latest version per student
    latest_version_subquery = (
        Submission.objects.filter(
            assignment=assignment,
            student=OuterRef("student"),
        )
        .order_by("-version")
        .values("version")[:1]
    )

    submissions = (
        assignment.submissions
        .annotate(max_version=Subquery(latest_version_subquery))
        .filter(version=Subquery(latest_version_subquery))
        .select_related("student")
        .order_by("student__username")
    )

    status_filter = request.GET.get("status")
    if status_filter and status_filter in SubmissionStatus.values:
        submissions = submissions.filter(status=status_filter)

    return render(request, "core/submission_list.html", {
        "course": course,
        "assignment": assignment,
        "submissions": submissions,
        "status_choices": SubmissionStatus.choices,
        "current_filter": status_filter,
    })


@login_required
@instructor_required
def grade_submission(request, course_id, assignment_id, submission_id):
    """
    GET:  Display grading form for a submission.
    POST: Grade the submission.

    WARNING: Late penalty is applied HERE via ``apply_grade()``,
    not at submission time.

    POST flow:
        1. Validate GradeForm (score, feedback, is_final, rubric_scores).
        2. ``apply_grade()`` creates a Grade record with penalty applied.
        3. Set submission.status = 'graded'.
        4. If is_final: recalculate enrollment grade cache, notify student.
        5. Invalidate course analytics cache.
    """
    course = get_object_or_404(Course, pk=course_id)
    assignment = get_object_or_404(Assignment, pk=assignment_id, course=course)
    submission = get_object_or_404(
        Submission.objects.select_related("student"),
        pk=submission_id,
        assignment=assignment,
    )

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "Only the course instructor can grade submissions.")
        return redirect(
            "core:submission_list",
            course_id=course.pk,
            assignment_id=assignment.pk,
        )

    # Existing grades for context
    existing_grades = submission.grades.order_by("-graded_at")

    if request.method == "POST":
        form = GradeForm(request.POST, max_score=assignment.max_score)
        if form.is_valid():
            raw_score = form.cleaned_data["score"]
            is_final = form.cleaned_data.get("is_final", False)

            # Step 1-2: apply_grade creates the Grade record with late penalty
            # Pass is_final so apply_grade creates the grade with the correct
            # finality from the start (avoids demote-then-flip bug).
            grade = apply_grade(
                submission=submission,
                raw_score=raw_score,
                grader=request.user,
                is_final=is_final,
            )

            # Transfer additional form fields to the grade
            grade.feedback = form.cleaned_data.get("feedback", "")
            grade.save(update_fields=["feedback"])

            # Step 3: update submission status
            submission.status = SubmissionStatus.GRADED
            submission.save(update_fields=["status"])

            # Step 4: always recalculate cache — apply_grade may have demoted
            # a previous final grade, so the cache must be refreshed regardless
            # of whether the new grade is final.
            enrollment = Enrollment.objects.filter(
                student=submission.student,
                course=course,
                status__in=[
                    EnrollmentStatus.ACTIVE,
                    EnrollmentStatus.COMPLETED,
                ],
            ).first()

            if enrollment:
                recalculate_grade_cache(enrollment)

            if is_final:
                notify_grade_posted(grade)

            # Step 5: invalidate analytics
            invalidate_course_analytics(course)

            messages.success(
                request,
                f"Graded submission v{submission.version} for "
                f"{submission.student.username} — score: {grade.score}."
                + (" (final)" if is_final else ""),
            )
            return redirect(
                "core:submission_list",
                course_id=course.pk,
                assignment_id=assignment.pk,
            )
    else:
        form = GradeForm(max_score=assignment.max_score)

    return render(request, "core/grade_form.html", {
        "course": course,
        "assignment": assignment,
        "submission": submission,
        "form": form,
        "existing_grades": existing_grades,
    })
