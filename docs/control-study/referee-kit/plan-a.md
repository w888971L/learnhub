# Plan A

## Concept

Allow instructors to enable a per-course setting that automatically drops each student's lowest assignment grade when calculating the course grade. The dropped grade is excluded from the aggregate but still visible (marked as "dropped").

## Changes by Layer

### 1. Model — `core/models.py`

- **Add to `Course` model**: a `grade_forgiveness` BooleanField (default `False`) and optionally `forgiveness_drop_count` (IntegerField, default 1) for future flexibility.

### 2. Settings Form — `core/forms.py`

- Add the new field(s) to the course settings form so instructors can toggle forgiveness on/off.

### 3. Grade Calculation Engine — `core/utils/grading.py`

This is the core change. Modify **`calculate_course_grade(enrollment)`**:

- Query all final grades for the student in the course (as it does now).
- If `course.grade_forgiveness` is enabled and the student has more than `forgiveness_drop_count` graded assignments:
  - Identify the grade(s) with the lowest **percentage** (score / max_score).
  - Exclude those from the weighted sum.
- Return the recalculated percentage.
- **Important**: `recalculate_grade_cache` and `bulk_recalculate_course_grades` already call this function, so the cache pipeline stays intact.

### 4. Analytics — `core/utils/cache_manager.py`

- `rebuild_course_analytics` computes `average_grade` from final grade percentages. It should use the forgiveness-aware calculation (call `calculate_course_grade` per enrollment rather than raw grade averages) to stay consistent.

### 5. API — `core/views_lib/api/views.py`

- `api_grade_distribution`: currently reads `final_grade_cache`, which will already reflect forgiveness after recalculation. **No change needed** if caches are up to date.
- Consider adding a `dropped_assignments` field to the student-facing API response so the frontend can show which grade was dropped.

### 6. Templates / Frontend

- **`grade_dashboard.html`**: Show a "dropped" badge next to the lowest grade when forgiveness is active.
- **Student dashboard**: Display the student's grade both with and without forgiveness so they understand the benefit (e.g., "78% → 82% with lowest dropped").
- **Course settings page**: Toggle for instructors to enable/disable forgiveness.

### 7. Notifications — `core/utils/notifications.py`

- Optional: notify students when forgiveness is enabled/toggled on their course so they're aware of the policy change.

## Key Design Decisions

| Question | Recommendation |
|---|---|
| Per-course or per-assignment-type? | **Per-course** (simpler, covers the common case) |
| Drop count | Default 1, store as integer for future "drop N" support |
| What if student has only 1 assignment? | Don't drop — require > `drop_count` graded assignments |
| Retroactive? | Yes — toggling recalculates all enrolled students via `bulk_recalculate_course_grades` |
| Show dropped grade to student? | Yes, visibly marked as "dropped" but not hidden |

## Implementation Order

1. **Model field** + migration
2. **`calculate_course_grade`** logic change (+ unit tests)
3. **Course settings form** + view for instructors
4. **Template updates** (dropped badge, student dashboard info)
5. **Analytics consistency** fix in cache_manager
6. **End-to-end test**
