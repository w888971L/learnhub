"""
Management command to generate a grade report for a course.

Lists all enrolled students with their per-assignment grades and computed
final course grade. Supports text (tabular) and CSV output formats.

Usage::

    python manage.py grade_report --course-id 1
    python manage.py grade_report --course-id 1 --output csv
    python manage.py grade_report --course-id 1 --output csv > report.csv
"""

import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO

from django.core.management.base import BaseCommand, CommandError

from core.models import (
    Assignment,
    Course,
    Enrollment,
    EnrollmentStatus,
    Grade,
)
from core.utils.grading import calculate_course_grade


class Command(BaseCommand):
    help = "Generate a grade report for a course."

    def add_arguments(self, parser):
        parser.add_argument(
            "--course-id",
            type=int,
            required=True,
            help="Primary key of the course to report on.",
        )
        parser.add_argument(
            "--output",
            choices=["text", "csv"],
            default="text",
            help="Output format: 'text' (tabular) or 'csv'. Default: text.",
        )

    def handle(self, *args, **options):
        course_id = options["course_id"]
        output_format = options["output"]

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise CommandError(f"Course with id={course_id} does not exist.")

        assignments = list(
            Assignment.objects.filter(course=course).order_by("due_date")
        )

        if not assignments:
            self.stdout.write(
                self.style.WARNING(f"No assignments found for '{course.title}'.")
            )
            return

        enrollments = Enrollment.objects.filter(
            course=course,
            status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED],
        ).select_related("student").order_by("student__username")

        if not enrollments.exists():
            self.stdout.write(
                self.style.WARNING(f"No enrolled students for '{course.title}'.")
            )
            return

        # Build report data
        header = ["Student"] + [a.title for a in assignments] + ["Course Grade"]
        rows = []

        for enrollment in enrollments:
            row = [enrollment.student.username]

            for assignment in assignments:
                final_grade = Grade.objects.filter(
                    submission__student=enrollment.student,
                    submission__assignment=assignment,
                    is_final=True,
                ).first()

                if final_grade:
                    pct = (
                        (final_grade.score / assignment.max_score) * 100
                    ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                    row.append(f"{final_grade.score}/{assignment.max_score} ({pct}%)")
                else:
                    row.append("--")

            course_grade = calculate_course_grade(enrollment)
            row.append(f"{course_grade}%" if course_grade is not None else "--")
            rows.append(row)

        if output_format == "csv":
            self._output_csv(header, rows)
        else:
            self._output_text(course, header, rows)

    def _output_text(self, course, header, rows):
        """Render the report as a formatted text table."""
        self.stdout.write(f"\nGrade Report: {course.title}")
        self.stdout.write("=" * (15 + len(course.title)))
        self.stdout.write("")

        # Calculate column widths
        col_widths = [len(h) for h in header]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        def format_row(cells):
            parts = []
            for i, cell in enumerate(cells):
                parts.append(str(cell).ljust(col_widths[i]))
            return "  ".join(parts)

        self.stdout.write(format_row(header))
        self.stdout.write("  ".join("-" * w for w in col_widths))

        for row in rows:
            self.stdout.write(format_row(row))

        self.stdout.write("")
        self.stdout.write(f"Total students: {len(rows)}")
        self.stdout.write(f"Total assignments: {len(header) - 2}")

    def _output_csv(self, header, rows):
        """Render the report as CSV to stdout."""
        writer = csv.writer(self.stdout)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
