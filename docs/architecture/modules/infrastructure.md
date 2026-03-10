# Infrastructure — routing, middleware, utilities, management commands

Last verified: 2026-03-10
Files covered: core/urls.py, core/views.py, core/forms.py, core/admin.py, core/middleware.py, core/context_processors.py, core/templatetags/core_tags.py, core/utils/, core/management/commands/, scripts/classify.py, scripts/session_log_schema.py, scripts/extract_codex_log.py

---

## Routing

### core/urls.py (~117 lines)
31 URL patterns grouped by domain: courses/catalog (2), course management (2), enrollment (4), modules/lessons (4), assignments (6), discussions (4), dashboard (2), API (4), auth (3).
Most views imported via `core.views` (the import router). API views also imported directly from `core.views_lib.api.views`.

### core/views.py (~55 lines)
Import router only — imports all view functions from `views_lib/` submodules and re-exports. No logic.

---

## Middleware

### ActiveUserMiddleware [L14]
Updates `last_login` on each request, throttled to once per 5 minutes via session key `_learnhub_last_activity_update`. Prevents DB write on every request.

### CourseContextMiddleware [L49]
If URL resolves with `course_id` or `course_slug` kwarg, loads the Course object into `request.course`. Downstream views and context processors can use this without re-querying.

Both middleware classes and the `learnhub_context` context processor are registered in `config/settings.py` (MIDDLEWARE and TEMPLATES context_processors lists respectively).

---

## Context Processors

### learnhub_context [L11]
Injects: `user_role`, `is_instructor`, `is_student`, `unread_notification_count`, `current_course` (from middleware).
Available in all templates. Registered in `config/settings.py` TEMPLATES context_processors.

---

## Permissions (core/utils/permissions.py)

### role_required(*roles) [L21]
Decorator factory. Checks `request.user.role in roles`. Returns 403 HttpResponseForbidden if not.

### instructor_required [L56]
Shortcut: `role_required('instructor', 'admin')`

### student_required [L57]
Shortcut: `role_required('student', 'admin')`

### course_participant_required [L65]
Decorator. Checks user is either the course instructor OR has an active enrollment. Expects `course_id` in URL kwargs.

### enrollment_active_required [L101]
Decorator. Checks user has an active enrollment in the course. Stricter than `course_participant_required` — does not pass instructors.

---

## Grading Engine (core/utils/grading.py)

! CRITICAL FILE — Contains the late penalty calculation. Read cross_cutting.md before modifying.

### calculate_late_penalty(submission) [L40]
Returns penalty multiplier (0.0 to 1.0). Logic:
- late_policy == 'none' → 0.0 (no penalty)
- late_policy == 'reject' and submission.is_late → 1.0 (100% penalty, should have been caught at submission time)
- late_policy == 'penalize' → days_late * LATE_PENALTY_PER_DAY, capped at MAX_LATE_DAYS * rate
Uses `LEARNHUB_SETTINGS` from Django settings.

### apply_grade(submission, raw_score, grader, is_final=True) [L91]
Creates Grade record with penalty-adjusted score. Sequence:
1. penalty = calculate_late_penalty(submission)
2. final_score = raw_score * (1 - penalty), rounded with ROUND_HALF_UP, floored at 0.00
3. Demotes any previous final grades for this submission as non-final
4. Demotes any final grades on OTHER versions of the same assignment by the same student (prevents resubmission double-counting)
5. Grade.objects.create(submission=, grader=, score=final_score, is_final=is_final)
6. Updates submission.status to 'graded'
Returns the Grade.
! The instructor sees the raw_score in the form, but the stored Grade.score is penalty-adjusted. The caller (grade_submission view) always recalculates the enrollment cache after this call, since step 3-4 may have demoted a previous final grade.
→ see cross_cutting.md "Late Penalty Timing"

### calculate_course_grade(enrollment) [L140]
Calculates weighted average of all final grades for an enrollment. Returns Decimal or None.
Only considers `Grade.objects.filter(submission__assignment__course=, submission__student=, is_final=True)`.

### recalculate_grade_cache(enrollment) [L179]
Calls calculate_course_grade → updates enrollment.final_grade_cache → triggers analytics invalidation.
! This is the grade cascade trigger. Always call this after setting is_final=True on a Grade.
→ see cross_cutting.md "Grade Cascade"

### bulk_recalculate_course_grades(course) [L199]
Recalculates all enrollment caches for a course. Used after rubric changes.
! This function calls `rebuild_course_analytics(course)` internally after updating all enrollment caches. Do NOT also call `invalidate_course_analytics()` after calling this function — doing so would mark freshly rebuilt analytics as stale, causing a redundant rebuild on next read.

---

## Notification Dispatch (core/utils/notifications.py)

### send_notification(user, notification_type, title, message, related_object=None) [L32]
Creates Notification record if user has it enabled (checks NotificationPreference).

### send_bulk_notifications(users, notification_type, title, message) [L76]
Batch sends using NOTIFICATION_BATCH_SIZE.

### notify_grade_posted(grade) [L132]
Convenience wrapper — notifies the student that a grade was posted.

### notify_enrollment_change(enrollment, action) [L155]
Notifies student of status change. Notifies instructor of new enrollments. The `action` parameter describes the enrollment action (e.g., "enrolled", "dropped", or the status display value).

### notify_new_discussion_post(post) [L190]
Creates in-app Notification records synchronously via `send_bulk_notifications()`. A background `threading.Thread(daemon=True)` handles secondary processing (e.g., email dispatch via `_send_notifications_background()`). Notification DB records are fully created before the HTTP response returns — only the email processing is fire-and-forget.

---

## Cache Manager (core/utils/cache_manager.py)

### rebuild_course_analytics(course) [L36]
Full recalculation from scratch: average_grade, completion_rate, active_students, total_submissions. Creates CourseAnalytics if not exists.
! `average_grade` is computed directly from Grade records (`Grade.objects.filter(is_final=True)`) — it does NOT read from `Enrollment.final_grade_cache`. This means any feature that changes which grades are included in aggregate calculations (e.g., grade forgiveness, grade drops) must also be reflected in this function's query or logic, not just in `calculate_course_grade()`.
→ see cross_cutting.md "Cached Aggregates Pattern"

### invalidate_course_analytics(course) [L118]
Sets `last_calculated = None` on CourseAnalytics. Next read triggers rebuild.

### get_or_rebuild_analytics(course) [L140]
Returns CourseAnalytics. If `is_stale(GRADE_CACHE_TTL)`, triggers rebuild first.

### rebuild_all_analytics() [L167]
Iterates all published courses. Used by management command.

---

## Management Commands

### seed_data (~311 lines)
Creates sample data: 2 orgs, 5 instructors, 20 students, 8 courses, modules, lessons, assignments, submissions, grades. Uses bulk_create.
Args: `--flush` (optional, deletes existing data before seeding)

### grade_report (~142 lines)
Generates grade report for a course.
Args: --course-id, --output (csv/text)

---

## Admin (core/admin.py)

Custom admin configuration for all models. Uses custom UserAdmin and multiple ModelAdmin classes. No business logic enforcement — admin edits bypass state machines, grade cascade, and late penalty logic.
→ see cross_cutting.md "Django Admin Bypass Risk"

---

## Forms (core/forms.py)

9 forms: CourseForm, ModuleForm, LessonForm, AssignmentForm, SubmissionForm, GradeForm, ThreadForm, PostForm, RegistrationForm.
Notable: GradeForm has custom `clean_score` that validates `0 <= score <= max_score` (requires `max_score` kwarg in `__init__`). GradeForm also includes `rubric_scores` field. AssignmentForm has `clean_due_date` that ensures future dates.

---

## Template Tags (core/templatetags/core_tags.py)

- `grade_color` filter — returns CSS class by grade letter (A=green, B=blue, C=yellow, D=orange, F=red)
- `time_ago` filter — human-readable relative time
- `notification_badge` inclusion tag — renders badge with unread count
- `role_badge` simple tag — returns colored HTML badge for user role
---

## Session Logging Scripts (scripts/)

### classify.py
Shared path classification for governance, flow, experiment, and code files.
Imported by analyzers and logging/extraction scripts to keep "charter hit" logic consistent across agents.

### session_log_schema.py
Defines the shared `ToolEvent` JSONL schema and canonical event types used by Claude, Codex, and Gemini logging work.
Supports multi-file events via `file_paths` and auto-classifies `file_classes`.

### extract_codex_log.py
Reads Codex CLI session transcripts and emits normalized per-session logs to `.codex/logs/tool-use-{session_id}.jsonl`.
Captures `session_start`, `tool_success`, `tool_failure`, and `session_end` from `session_meta`, `function_call` / `function_call_output`, and `custom_tool_call` / `custom_tool_call_output` records.
! Failures are inferred from actual transcript outputs (non-zero exit codes or custom-tool metadata). Unmatched calls are not logged as successes.

### extract_gemini_log.py
Reads Gemini CLI session transcripts from `~/.gemini/tmp/<project>/chats/session-*.json` and emits normalized per-session logs to `.gemini/logs/tool-use-{session_id}.jsonl`.
Extracts `toolCalls` from each message, maps Gemini tool names (`read_file`, `write_file`, `grep_search`, `run_shell_command`) to action categories, and classifies file paths.
Usage: `python scripts/extract_gemini_log.py <session.json>` or `--dir <chats-directory>`.
! This is the preferred logging path for Gemini — it captures all tool calls from transcripts, unlike the self-logging script which depends on the agent remembering to call it.

### log_gemini_tool.py
CLI-invocable logger for Gemini sessions. Intended for real-time self-logging during a session.
Session ID managed via `.gemini/current_session` file; logs written to `.gemini/logs/tool-use-{session_id}.jsonl`.
! In practice, Gemini logs only a fraction of its tool calls when self-logging. Prefer `extract_gemini_log.py` for forensic analysis.

### analyze_session.py `--tool-log` flag
When `--tool-log` is passed, the analyzer reads standardized JSONL tool logs (from any agent) instead of full Claude transcripts.
Uses `extract_from_tool_log()` → `analyze_tool_log()` path. Maps tool names to read/edit/search/bash categories via keyword matching.
! Assistant text analysis (terminology usage, tripwire coverage) is unavailable from tool-only logs — those fields will be zero/empty.
