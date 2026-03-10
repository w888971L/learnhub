# LearnHub

A Django learning management system supporting courses, enrollments, assignments, grading, and discussions.

---

## Project Structure

```
learnhub/
├── config/                                # Django settings, URLs, WSGI
├── core/
│   ├── models.py                          # All 16 models (~950 lines)
│   ├── views.py                           # Import router
│   ├── urls.py                            # 30 URL patterns
│   ├── forms.py                           # 9 Django forms
│   ├── admin.py                           # Admin registration
│   ├── middleware.py                       # Activity tracking, course loading
│   ├── context_processors.py              # Template context
│   ├── templatetags/core_tags.py          # Custom template tags
│   ├── views_lib/
│   │   ├── courses/                       # Catalog, enrollment, management
│   │   ├── assignments/                   # Submission, grading
│   │   ├── discussions/                   # Threaded forums
│   │   ├── api/                           # JSON API endpoints
│   │   ├── auth/                          # Registration, login, logout
│   │   └── dashboard/                     # Student dashboard, analytics
│   ├── utils/
│   │   ├── permissions.py                 # Role-based access decorators
│   │   ├── grading.py                     # Grade engine (late penalty!)
│   │   ├── notifications.py              # Notification dispatch
│   │   └── cache_manager.py               # Analytics cache
│   └── management/commands/
│       ├── seed_data.py                   # Sample data generator
│       └── grade_report.py                # Grade reporting
├── templates/                             # Tailwind CSS templates
└── requirements.txt                       # Django 5.1
```

## Quick Start

```bash
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Demo Credentials

The `seed_data` command creates sample users with password **`testpass123`** for all accounts:

| Username | Role | Organization |
|----------|------|-------------|
| `prof_chen` | Instructor | Acme University |
| `prof_garcia` | Instructor | Acme University |
| `prof_jones` | Instructor | TechCorp Academy |
| `prof_smith` | Instructor | TechCorp Academy |
| `prof_wilson` | Instructor | Acme University |
| `student_01` | Student | TechCorp Academy |
| `student_02` | Student | Acme University |
| ... through `student_20` | Student | Mixed |

## Domain Overview

| Domain | Models | What it does |
|--------|--------|-------------|
| Accounts | User, Organization, InstructorProfile | Multi-role user system with organizations |
| Courses | Course, Module, Lesson, Enrollment | Course catalog, content structure, enrollment state machine |
| Assignments | Assignment, Submission, Grade | Assignment submission with versioning, grading with late penalties |
| Discussions | Thread, Post, Reaction | Threaded course discussion forums |
| Notifications | Notification, NotificationPreference | In-app notifications with preferences |
| Analytics | CourseAnalytics | Cached course-level aggregates |

## License

MIT
