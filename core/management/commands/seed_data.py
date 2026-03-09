"""
Management command to populate the database with sample data for
development and testing.

Creates organizations, users (instructors and students), courses with
modules and lessons, assignments, submissions, and grades.

Usage::

    python manage.py seed_data
    python manage.py seed_data --flush   # clear existing data first
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Assignment,
    AssignmentType,
    ContentType,
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Grade,
    InstructorProfile,
    LatePolicy,
    Lesson,
    Module,
    Organization,
    Submission,
    SubmissionStatus,
    Thread,
    Post,
    User,
    UserRole,
)


class Command(BaseCommand):
    help = "Seed the database with sample LearnHub data for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            self._flush()

        self.stdout.write("Seeding organizations...")
        orgs = self._create_organizations()

        self.stdout.write("Seeding instructors...")
        instructors = self._create_instructors(orgs)

        self.stdout.write("Seeding students...")
        students = self._create_students(orgs)

        self.stdout.write("Seeding courses...")
        courses = self._create_courses(instructors, orgs)

        self.stdout.write("Seeding modules and lessons...")
        self._create_modules_and_lessons(courses)

        self.stdout.write("Seeding enrollments...")
        enrollments = self._create_enrollments(students, courses)

        self.stdout.write("Seeding assignments...")
        assignments = self._create_assignments(courses)

        self.stdout.write("Seeding submissions and grades...")
        self._create_submissions_and_grades(
            students, assignments, instructors
        )

        self.stdout.write("Seeding discussion threads...")
        self._create_discussions(courses, students, instructors)

        self.stdout.write(
            self.style.SUCCESS("Successfully seeded the database.")
        )

    def _flush(self):
        """Remove all non-superuser data."""
        Grade.objects.all().delete()
        Submission.objects.all().delete()
        Assignment.objects.all().delete()
        Post.objects.all().delete()
        Thread.objects.all().delete()
        Enrollment.objects.all().delete()
        Lesson.objects.all().delete()
        Module.objects.all().delete()
        Course.objects.all().delete()
        InstructorProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Organization.objects.all().delete()

    def _create_organizations(self):
        orgs = []
        org_data = [
            ("Acme University", "acme-university"),
            ("TechCorp Academy", "techcorp-academy"),
        ]
        for name, slug in org_data:
            org, _ = Organization.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            orgs.append(org)
        return orgs

    def _create_instructors(self, orgs):
        instructors = []
        instructor_data = [
            ("prof_chen", "chen@example.com", "Computer Science", orgs[0]),
            ("prof_garcia", "garcia@example.com", "Mathematics", orgs[0]),
            ("prof_smith", "smith@example.com", "Data Science", orgs[1]),
            ("prof_jones", "jones@example.com", "Engineering", orgs[1]),
            ("prof_wilson", "wilson@example.com", "Design", orgs[0]),
        ]
        for username, email, dept, org in instructor_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": UserRole.INSTRUCTOR,
                    "organization": org,
                },
            )
            if created:
                user.set_password("testpass123")
                user.save()
            InstructorProfile.objects.get_or_create(
                user=user,
                defaults={"department": dept, "office_hours": "Mon/Wed 2-4 PM"},
            )
            instructors.append(user)
        return instructors

    def _create_students(self, orgs):
        students = []
        for i in range(1, 21):
            org = orgs[i % 2]
            username = f"student_{i:02d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"student{i}@example.com",
                    "role": UserRole.STUDENT,
                    "organization": org,
                },
            )
            if created:
                user.set_password("testpass123")
                user.save()
            students.append(user)
        return students

    def _create_courses(self, instructors, orgs):
        now = timezone.now()
        course_data = [
            ("Introduction to Python", "intro-python", instructors[0], orgs[0]),
            ("Data Structures & Algorithms", "data-structures", instructors[0], orgs[0]),
            ("Calculus I", "calculus-1", instructors[1], orgs[0]),
            ("Linear Algebra", "linear-algebra", instructors[1], orgs[0]),
            ("Machine Learning Fundamentals", "ml-fundamentals", instructors[2], orgs[1]),
            ("Database Systems", "database-systems", instructors[3], orgs[1]),
            ("Web Development", "web-dev", instructors[4], orgs[0]),
            ("UX Design Principles", "ux-design", instructors[4], orgs[0]),
        ]
        courses = []
        for title, slug, instructor, org in course_data:
            course, _ = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "instructor": instructor,
                    "organization": org,
                    "status": CourseStatus.PUBLISHED,
                    "description": f"A comprehensive course on {title.lower()}.",
                    "max_enrollment": 30,
                },
            )
            courses.append(course)
        return courses

    def _create_modules_and_lessons(self, courses):
        for course in courses:
            if course.modules.exists():
                continue
            for m_idx in range(1, 4):
                module = Module.objects.create(
                    course=course,
                    title=f"Module {m_idx}: {'Foundations' if m_idx == 1 else 'Intermediate' if m_idx == 2 else 'Advanced'}",
                    order=m_idx,
                    is_published=True,
                )
                lessons = []
                for l_idx in range(1, 4):
                    lessons.append(
                        Lesson(
                            module=module,
                            title=f"Lesson {l_idx}",
                            content_type=ContentType.TEXT,
                            content=f"Content for {course.title}, Module {m_idx}, Lesson {l_idx}.",
                            order=l_idx,
                            duration_minutes=30 + (l_idx * 10),
                            is_published=True,
                        )
                    )
                Lesson.objects.bulk_create(lessons)

    def _create_enrollments(self, students, courses):
        enrollments = []
        for i, student in enumerate(students):
            # Each student enrolls in 3-4 courses
            assigned_courses = courses[i % len(courses) : i % len(courses) + 3]
            if not assigned_courses:
                assigned_courses = courses[:3]
            for course in assigned_courses:
                enrollment, _ = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults={"status": EnrollmentStatus.ACTIVE},
                )
                enrollments.append(enrollment)
        return enrollments

    def _create_assignments(self, courses):
        now = timezone.now()
        assignments = []
        types = list(AssignmentType.values)
        policies = list(LatePolicy.values)

        for c_idx, course in enumerate(courses):
            if course.assignments.exists():
                continue
            for a_idx in range(1, 3):
                assignment = Assignment.objects.create(
                    course=course,
                    title=f"Assignment {a_idx}: {course.title}",
                    description=f"Complete the following tasks for {course.title}.",
                    assignment_type=types[(c_idx + a_idx) % len(types)],
                    due_date=now + timedelta(days=14 + a_idx * 7),
                    max_score=Decimal("100.00"),
                    late_policy=policies[c_idx % len(policies)],
                    is_published=True,
                )
                assignments.append(assignment)
        return assignments

    def _create_submissions_and_grades(self, students, assignments, instructors):
        now = timezone.now()
        for assignment in assignments[:8]:
            enrolled_students = User.objects.filter(
                enrollments__course=assignment.course,
                enrollments__status=EnrollmentStatus.ACTIVE,
            ).distinct()[:5]

            for student in enrolled_students:
                if Submission.objects.filter(
                    assignment=assignment, student=student
                ).exists():
                    continue

                submission = Submission.objects.create(
                    assignment=assignment,
                    student=student,
                    version=1,
                    content=f"Submission by {student.username} for {assignment.title}.",
                    status=SubmissionStatus.GRADED,
                )

                # Create a grade for roughly half
                if student.pk % 2 == 0:
                    score = Decimal(str(60 + (student.pk * 7) % 40))
                    Grade.objects.create(
                        submission=submission,
                        grader=assignment.course.instructor,
                        score=score,
                        feedback="Good work. See inline comments.",
                        is_final=True,
                    )

    def _create_discussions(self, courses, students, instructors):
        for course in courses[:3]:
            if course.threads.exists():
                continue
            thread = Thread.objects.create(
                course=course,
                author=students[0],
                title=f"General discussion for {course.title}",
                content="Welcome! Use this thread for general questions.",
            )
            Post.objects.create(
                thread=thread,
                author=instructors[0],
                content="Great to see everyone here. Don't hesitate to ask questions!",
            )
            Post.objects.create(
                thread=thread,
                author=students[1],
                content="Thanks! Looking forward to the course.",
            )
