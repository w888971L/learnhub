# API Endpoints — JSON API for frontend interactivity

Last verified: 2026-03-08
Files covered: core/views_lib/api/views.py

---

All endpoints return JsonResponse. No REST framework — lightweight JSON views.

## api_notifications [L27]
GET: Returns last 50 notifications for the authenticated user.
Response: `{"notifications": [{"id", "type", "title", "message", "is_read", "created_at"}, ...]}`
Decorators: @login_required, @require_GET

## api_mark_read [L69]
POST: Marks a single notification as read.
Guards: notification must belong to request.user (enforced via `get_object_or_404` filtering by user)
Response: `{"success": true}` or 404 if not found/not owned
Decorators: @login_required

## api_course_analytics [L90]
GET: Returns course analytics data. Calls `get_or_rebuild_analytics()` — may trigger a rebuild if cache is stale.
Guards: instructor or admin only. Inline check verifies requesting user is the course's instructor or an admin — other instructors are blocked.
Response: `{"course_id", "average_grade", "completion_rate", "active_students", "total_submissions", "last_calculated"}`
Decorators: @login_required, @instructor_required
→ see cross_cutting.md "Cached Aggregates"

## api_grade_distribution [L133]
GET: Returns grade distribution as histogram buckets.
Guards: instructor or admin only. Inline course-ownership check (same as api_course_analytics).
Buckets: A (90-100), B (80-89), C (70-79), D (60-69), F (<60)
Response: `{"course_id", "distribution": {"A": n, "B": n, "C": n, "D": n, "F": n}, "total_graded": n}`
Decorators: @login_required, @instructor_required
