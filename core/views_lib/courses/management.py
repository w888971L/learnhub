"""
Course management views — creating/editing courses, modules, and lessons.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import CourseForm, ModuleForm, LessonForm
from core.models import Course, Module, Lesson
from core.utils.permissions import (
    course_participant_required,
    instructor_required,
)


@login_required
@instructor_required
def course_create(request):
    """
    GET:  Display the course creation form.
    POST: Validate and create a new course.

    Automatically sets the instructor to the requesting user and the
    organization to the user's organization.
    """
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            if request.user.organization:
                course.organization = request.user.organization
            course.save()
            messages.success(request, f"Course '{course.title}' created successfully.")
            return redirect("core:course_detail", course_id=course.pk)
    else:
        form = CourseForm()

    return render(request, "core/course_form.html", {
        "form": form,
        "editing": False,
    })


@login_required
@instructor_required
def course_edit(request, course_id):
    """
    GET:  Display the course editing form pre-filled with current data.
    POST: Validate and update the course.

    Only the course's instructor or an admin may edit.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "You do not have permission to edit this course.")
        return redirect("core:course_detail", course_id=course.pk)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f"Course '{course.title}' updated.")
            return redirect("core:course_detail", course_id=course.pk)
    else:
        form = CourseForm(instance=course)

    return render(request, "core/course_form.html", {
        "form": form,
        "course": course,
        "editing": True,
    })


@login_required
@course_participant_required
def module_list(request, course_id):
    """
    GET: Display all modules for a course, ordered by ``order``.

    Includes a count of lessons per module.
    """
    course = get_object_or_404(Course, pk=course_id)

    modules = (
        course.modules
        .annotate(lesson_count=Count("lessons"))
        .order_by("order")
    )

    return render(request, "core/module_list.html", {
        "course": course,
        "modules": modules,
    })


@login_required
@instructor_required
def module_create(request, course_id):
    """
    GET:  Display the module creation form.
    POST: Validate and create a new module.

    Auto-assigns the next ``order`` number (max existing + 1).
    Only the course instructor or admin may create modules.
    """
    course = get_object_or_404(Course, pk=course_id)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "You do not have permission to add modules to this course.")
        return redirect("core:module_list", course_id=course.pk)

    if request.method == "POST":
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course

            # Auto-assign next order number
            max_order = course.modules.aggregate(
                max_order=Count("order")
            )["max_order"] or 0
            last_order = course.modules.order_by("-order").values_list("order", flat=True).first()
            module.order = (last_order or 0) + 1

            module.save()
            messages.success(request, f"Module '{module.title}' created.")
            return redirect("core:module_list", course_id=course.pk)
    else:
        form = ModuleForm()

    return render(request, "core/module_form.html", {
        "form": form,
        "course": course,
    })


@login_required
@course_participant_required
def lesson_list(request, course_id, module_id):
    """
    GET: Display all lessons for a module, ordered by ``order``.
    """
    course = get_object_or_404(Course, pk=course_id)
    module = get_object_or_404(Module, pk=module_id, course=course)

    lessons = module.lessons.order_by("order")

    return render(request, "core/lesson_list.html", {
        "course": course,
        "module": module,
        "lessons": lessons,
    })


@login_required
@instructor_required
def lesson_create(request, course_id, module_id):
    """
    GET:  Display the lesson creation form.
    POST: Validate and create a new lesson within the given module.

    Auto-assigns the next ``order`` number. Only the course instructor
    or admin may create lessons.
    """
    course = get_object_or_404(Course, pk=course_id)
    module = get_object_or_404(Module, pk=module_id, course=course)

    if course.instructor_id != request.user.pk and not request.user.is_admin_role:
        messages.error(request, "You do not have permission to add lessons.")
        return redirect("core:lesson_list", course_id=course.pk, module_id=module.pk)

    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module

            # Auto-assign next order number
            last_order = module.lessons.order_by("-order").values_list("order", flat=True).first()
            lesson.order = (last_order or 0) + 1

            lesson.save()
            messages.success(request, f"Lesson '{lesson.title}' created.")
            return redirect("core:lesson_list", course_id=course.pk, module_id=module.pk)
    else:
        form = LessonForm()

    return render(request, "core/lesson_form.html", {
        "form": form,
        "course": course,
        "module": module,
    })
