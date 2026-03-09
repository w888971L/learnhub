# Plan: Assignment Extensions

This document outlines the implementation plan for allowing instructors to grant individual students deadline extensions on specific assignments.

## 1. Goal
Instructors should be able to grant a student a new `due_date` for an assignment. This "effective" due date must be respected by:
- The submission system (preventing/allowing submissions based on `late_policy`).
- The grading system (calculating late penalties based on the extended deadline).
- The UI (showing the student their personal deadline).

## 2. Architecture Changes

### A. Models (`core/models.py`)
- **Add `AssignmentExtension` Model**:
    - `assignment` (FK to Assignment)
    - `student` (FK to User)
    - `new_due_date` (DateTimeField)
    - `reason` (TextField, optional)
    - `granted_at` (DateTimeField, auto_now_add)
    - `granted_by` (FK to User - Instructor)
    - *Constraints*: `unique_together = [['assignment', 'student']]`
- **Update `Assignment` Model**:
    - Add `get_effective_due_date(student)` helper to return either the extension date or the base `due_date`.
    - Add `is_past_due_for(student)` helper.
- **Update `Submission` Model**:
    - Update `is_late` property to use `assignment.get_effective_due_date(student)` instead of the static `assignment.due_date`.

### B. Business Logic (`core/utils/grading.py`)
- **Update `calculate_late_penalty`**:
    - Modify the logic to use the student-specific effective due date when calculating `days_late`.

## 3. View & UI Changes

### A. Instructor Experience
- **New View: `grant_extension`**:
    - A view to create or update an `AssignmentExtension` for a student.
    - Accessible from the assignment's submission list.
- **Form: `AssignmentExtensionForm`**:
    - Fields for `student` (dropdown of enrolled students), `new_due_date`, and `reason`.

### B. Student Experience
- **Update `assignment_detail`**:
    - Show the extended deadline clearly if one exists.
- **Update `submit_assignment`**:
    - Modify the `REJECT` policy check to use `assignment.is_past_due_for(request.user)`.

## 4. Side Effects & Cross-Cutting Concerns

- **Notifications**:
    - Trigger a notification to the student when an extension is granted using `core/utils/notifications.py`.
- **Cache**:
    - Extensions do not directly affect `Enrollment.final_grade_cache` until a *new* grade is issued, but they may require a `bulk_recalculate_course_grades` if an extension is granted *after* a late penalty has already been applied to an existing grade.

## 5. Implementation Steps

1.  **Migration**: Create and run the migration for the `AssignmentExtension` model.
2.  **Model Logic**: Update `Assignment` and `Submission` properties.
3.  **Grading Logic**: Update `calculate_late_penalty`.
4.  **Views & Forms**: Implement the extension management UI for instructors.
5.  **Submission Updates**: Update the student submission view to respect extensions.
6.  **Notifications**: Add the notification trigger.
7.  **Documentation**: Update `models_assignments.md` and `views_assignments.md` charters.

## 6. Verification Strategy

- **Automated Tests**:
    - Test that `Submission.is_late` is `False` for a student with an extension even if they submit after the base `due_date`.
    - Test that `calculate_late_penalty` returns `0.0` if submitted before the extended deadline.
    - Test that `REJECT` policy allows submission for extended students but blocks others.
- **Manual Verification**:
    - Grant an extension as an instructor.
    - Log in as the student and verify the new deadline appears.
    - Submit and verify no late penalty is applied in the grading view.
