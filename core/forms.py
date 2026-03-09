"""
Django forms for LearnHub.

Provides ModelForms for the core domain models and standalone forms for
registration and grading.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import (
    Assignment,
    Course,
    Grade,
    Lesson,
    Module,
    Organization,
    Post,
    Submission,
    Thread,
    User,
    UserRole,
)


# ---------------------------------------------------------------------------
# Course domain forms
# ---------------------------------------------------------------------------


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "max_enrollment", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "description", "order", "is_published"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "content_type",
            "content",
            "order",
            "duration_minutes",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
        }


# ---------------------------------------------------------------------------
# Assignment domain forms
# ---------------------------------------------------------------------------


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "title",
            "description",
            "assignment_type",
            "due_date",
            "max_score",
            "late_policy",
            "is_published",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def clean_due_date(self):
        """Ensure the due date is in the future for new assignments."""
        due_date = self.cleaned_data.get("due_date")
        if due_date and not self.instance.pk and due_date <= timezone.now():
            raise ValidationError(
                "Due date must be in the future for new assignments."
            )
        return due_date


class SubmissionForm(forms.ModelForm):
    """
    Form for student submissions. Only exposes the ``content`` field;
    ``file_path`` is handled separately via file upload views.
    """

    class Meta:
        model = Submission
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 10}),
        }


class GradeForm(forms.Form):
    """
    Standalone form for grading a submission.

    Not a ModelForm because the grader and submission are set in the view,
    and the score needs custom validation against the assignment's max_score.
    """

    score = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        min_value=0,
        help_text="Points to award for this submission.",
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        help_text="Written feedback for the student.",
    )
    is_final = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Mark this grade as the final/official grade.",
    )

    def __init__(self, *args, max_score=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_score = max_score

    def clean_score(self):
        score = self.cleaned_data.get("score")
        if score is not None and self.max_score is not None:
            if score > self.max_score:
                raise ValidationError(
                    f"Score cannot exceed the maximum of {self.max_score}."
                )
            if score < 0:
                raise ValidationError("Score cannot be negative.")
        return score


# ---------------------------------------------------------------------------
# Discussion forms
# ---------------------------------------------------------------------------


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ["title", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

REGISTRATION_ROLE_CHOICES = [
    (UserRole.INSTRUCTOR, "Instructor"),
    (UserRole.STUDENT, "Student"),
]


class RegistrationForm(forms.Form):
    """
    User registration form. Limits role choices to instructor and student
    (admin accounts are created via the Django admin or management commands).
    """

    username = forms.CharField(
        max_length=150,
        help_text="Required. 150 characters or fewer.",
    )
    email = forms.EmailField(
        help_text="A valid email address.",
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        min_length=8,
    )
    role = forms.ChoiceField(
        choices=REGISTRATION_ROLE_CHOICES,
        initial=UserRole.STUDENT,
        help_text="Select your primary role on the platform.",
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True),
        required=False,
        empty_label="(No organization)",
        help_text="Optionally associate with an organization.",
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                "An account with this email address already exists."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(
                {"password2": "The two password fields must match."}
            )

        return cleaned_data
