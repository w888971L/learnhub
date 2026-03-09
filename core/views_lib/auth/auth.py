"""
Authentication views — registration, login, and logout.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.forms import RegistrationForm
from core.models import Organization


def register(request):
    """
    GET:  Display the registration form.
    POST: Create a new user account.

    If the form includes an ``organization`` field, the user is linked to
    that organization upon creation. After successful registration the
    user is redirected to the login page.
    """
    if request.user.is_authenticated:
        return redirect("core:course_list")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])

            # Optional organization linking
            org_id = form.cleaned_data.get("organization")
            if org_id:
                try:
                    user.organization = Organization.objects.get(pk=org_id)
                except Organization.DoesNotExist:
                    pass

            user.save()

            messages.success(
                request,
                "Account created successfully. Please log in.",
            )
            return redirect("core:login")
    else:
        form = RegistrationForm()

    return render(request, "core/auth/register.html", {"form": form})


def login_view(request):
    """
    GET:  Display the login form.
    POST: Authenticate and log in the user.

    After successful login:
        - Students are redirected to ``student_dashboard``.
        - Instructors and admins are redirected to ``course_list``.
    """
    if request.user.is_authenticated:
        return redirect("core:course_list")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Role-based redirect
            if user.is_student:
                return redirect("core:student_dashboard")
            return redirect("core:course_list")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "core/auth/login.html")


@login_required
@require_POST
def logout_view(request):
    """
    POST: Log out the current user and redirect to the login page.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("core:login")
