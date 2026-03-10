"""
Discussion views — thread listing, creation, detail, and replies.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forms import ThreadForm, PostForm
from core.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Post,
    Reaction,
    Thread,
)
from core.utils.permissions import course_participant_required
from core.utils.notifications import notify_new_discussion_post


def _is_course_participant(user, course):
    """Return True if the user is the course instructor, admin, or actively enrolled."""
    if user.is_admin_role:
        return True
    if course.instructor_id == user.pk:
        return True
    return Enrollment.objects.filter(
        student=user,
        course=course,
        status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
    ).exists()


@login_required
@course_participant_required
def thread_list(request, course_id):
    """
    GET: Display discussion threads for a course.

    Ordering: pinned threads first, then by creation date (newest first).
    Enrolled students and the instructor only (enforced by decorator).
    """
    course = get_object_or_404(Course, pk=course_id)

    threads = (
        course.threads
        .select_related("author")
        .annotate(reply_count_annotated=Count("posts"))
        .order_by("-is_pinned", "-created_at")
    )

    return render(request, "core/thread_list.html", {
        "course": course,
        "threads": threads,
    })


@login_required
@course_participant_required
def thread_create(request, course_id):
    """
    GET:  Display thread creation form.
    POST: Create a new discussion thread.

    Must be an enrolled student or the course instructor.
    """
    course = get_object_or_404(Course, pk=course_id)

    if request.method == "POST":
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.course = course
            thread.author = request.user
            thread.save()

            messages.success(request, f"Thread '{thread.title}' created.")
            return redirect("core:thread_detail", course_id=course.pk, thread_id=thread.pk)
    else:
        form = ThreadForm()

    return render(request, "core/thread_form.html", {
        "course": course,
        "form": form,
    })


@login_required
@course_participant_required
def thread_detail(request, course_id, thread_id):
    """
    GET: Display a thread with all posts (threaded view).

    Posts are ordered chronologically with reactions prefetched for
    efficient display.
    """
    course = get_object_or_404(Course, pk=course_id)
    thread = get_object_or_404(
        Thread.objects.select_related("author"),
        pk=thread_id,
        course=course,
    )

    posts = (
        thread.posts
        .select_related("author", "parent")
        .prefetch_related(
            Prefetch(
                "reactions",
                queryset=Reaction.objects.select_related("user"),
            ),
        )
        .order_by("created_at")
    )

    reply_form = PostForm()

    return render(request, "core/thread_detail.html", {
        "course": course,
        "thread": thread,
        "posts": posts,
        "reply_form": reply_form,
    })


@login_required
@course_participant_required
@require_POST
def post_reply(request, course_id, thread_id):
    """
    POST: Add a reply to a discussion thread.

    Checks that the thread is not locked before accepting the post.
    Sends a notification to thread participants via
    ``notify_new_discussion_post()``.
    """
    course = get_object_or_404(Course, pk=course_id)
    thread = get_object_or_404(Thread, pk=thread_id, course=course)

    if thread.is_locked:
        messages.error(request, "This thread is locked and no longer accepts replies.")
        return redirect("core:thread_detail", course_id=course.pk, thread_id=thread.pk)

    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.thread = thread
        post.author = request.user

        # Optional parent post for nested replies
        parent_id = request.POST.get("parent_id")
        if parent_id:
            parent = Post.objects.filter(pk=parent_id, thread=thread).first()
            if parent:
                post.parent = parent

        post.save()

        notify_new_discussion_post(post)

        messages.success(request, "Reply posted.")
    else:
        messages.error(request, "Could not post reply. Please check your input.")

    return redirect("core:thread_detail", course_id=course.pk, thread_id=thread.pk)
