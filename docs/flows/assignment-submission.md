# Assignment Submission — How Students Submit Work

## Overview

This flow covers how students view assignments, submit their work, handle late submissions, and resubmit revised versions.

## Key Files

| File | Purpose |
|------|---------|
| `core/views_lib/assignments/submit.py` | Submission views |
| `core/models.py` (Assignment, Submission) | Assignment and submission records |
| `core/forms.py` (SubmissionForm) | Submission form |
| `core/utils/grading.py` | Late penalty calculation (used later at grading) |

---

## Step 1: View Assignments

Students visit the assignments tab on their course page (`/course/<id>/assignments/`). Each assignment shows:
- Title and description
- Due date (with "overdue" badge if past)
- Max score and late policy
- Student's submission status (not submitted / submitted / graded)

## Step 2: Open Assignment

Clicking an assignment opens the detail page (`/course/<id>/assignment/<id>/`). The student sees:
- Full assignment description
- Due date and late policy clearly displayed
- Their previous submissions (if any) with versions, dates, statuses
- A "Submit" button (or "Resubmit" if they have prior versions)

## Step 3: Submit Work

The student clicks Submit and fills in the submission form. On POST:

**Checks performed:**
1. Student must have active enrollment in the course
2. Previous submission count must be < MAX_SUBMISSION_VERSIONS (default: 5)
3. If assignment.late_policy == 'reject' and current time > due_date → submission is rejected with an error message

**If checks pass:**
- A new Submission record is created with version = previous_max + 1
- Status is set to 'submitted'
- Student is redirected to the assignment detail page

**Important**: Previous submission versions are NOT modified. All versions are preserved for audit trail.

## Step 4: Late Submissions

Late handling depends on the assignment's `late_policy`:

| Policy | At Submission Time | At Grading Time |
|--------|-------------------|-----------------|
| `none` | Accepted normally | Full credit |
| `penalize` | Accepted normally (with warning banner) | Penalty applied: score * (1 - days_late * 0.10) |
| `reject` | REJECTED — cannot submit | N/A |

**Key point**: For the `penalize` policy, the student's submission is accepted without modification. The penalty is only applied when the instructor grades it. This means a late submission looks identical to an on-time submission in the database — the only difference is `submitted_at > assignment.due_date`.

## Step 5: Resubmission

Students can resubmit up to MAX_SUBMISSION_VERSIONS times. Each resubmission:
- Creates a new Submission record (version incremented)
- Does NOT delete or modify previous versions
- The latest version (highest version number) is what the instructor grades

Previous versions remain accessible for reference on the assignment detail page.

---

