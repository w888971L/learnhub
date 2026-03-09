# Feature Plan: Grade Forgiveness (Drop Lowest Grade)

## Objective
Implement a "Grade Forgiveness" feature that allows instructors to configure a course to automatically exclude each student's lowest assignment grade from their final course aggregate calculation.

## Proposed Changes

### 1. Model Updates (`core/models.py`)
Add a new boolean field to the `Course` model to enable/disable this feature.

```python
class Course(models.Model):
    # ... existing fields ...
    drop_lowest_grade = models.BooleanField(
        default=False,
        help_text="When enabled, the lowest percentage grade for any final assignment is dropped from the course aggregate."
    )
```

### 2. Form Updates (`core/forms.py`)
Update `CourseForm` to allow instructors to toggle this setting.

```python
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "max_enrollment", "status", "drop_lowest_grade"]
```

### 3. Grading Logic (`core/utils/grading.py`)
Modify `calculate_course_grade` to implement the dropping logic.

**Logic Details:**
- Only drop the lowest grade if there is more than one `is_final` grade.
- "Lowest" is defined by the percentage (score / max_score) to ensure fairness across assignments with different point values.
- If multiple grades have the same lowest percentage, only one is dropped.

```python
def calculate_course_grade(enrollment):
    # ... fetch final_grades ...
    
    if not final_grades.exists():
        return None

    grades_list = list(final_grades)
    
    # Check if we should drop the lowest
    if enrollment.course.drop_lowest_grade and len(grades_list) > 1:
        # Calculate percentages to find the lowest
        lowest_grade = min(
            grades_list, 
            key=lambda g: g.score / g.submission.assignment.max_score
        )
        grades_list.remove(lowest_grade)

    total_earned = sum(g.score for g in grades_list)
    total_possible = sum(g.submission.assignment.max_score for g in grades_list)
    
    # ... return percentage calculation ...
```

### 4. View Logic (`core/views_lib/courses/management.py`)
Update the `course_edit` view to detect if `drop_lowest_grade` has changed. If it has, trigger a bulk recalculation of all enrollment grade caches for that course.

```python
def course_edit(request, course_id):
    # ...
    if request.method == "POST":
        old_drop_setting = course.drop_lowest_grade
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            if course.drop_lowest_grade != old_drop_setting:
                from core.utils.grading import bulk_recalculate_course_grades
                bulk_recalculate_course_grades(course)
            # ...
```

## Impact on Existing Data
- **Migrations**: A new migration will be required to add the `drop_lowest_grade` field.
- **Cache**: Changing this setting invalidates all `final_grade_cache` values for the course. The proposed bulk recalculation ensures consistency.

## Testing Strategy
1. **Unit Test for `calculate_course_grade`**:
   - Verify calculation with `drop_lowest_grade=False`.
   - Verify calculation with `drop_lowest_grade=True` and multiple assignments.
   - Verify it handles different `max_score` values correctly (dropping the lowest percentage, not just lowest raw score).
   - Verify it doesn't drop anything if only one grade exists.
2. **Integration Test for `course_edit`**:
   - Verify that toggling the setting triggers `bulk_recalculate_course_grades`.
