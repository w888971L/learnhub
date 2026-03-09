# Referee Prompt

*Copy everything below the line and send to the referee model along with the attached files.*

---

You are an independent referee evaluating three implementation plans for the same software feature. The plans were produced by different AI agents under different conditions, but you do not know which is which. Your job is to evaluate each plan strictly on its merits against the actual codebase.

## The Feature Request

> "I want to add a feature → 'Grade Forgiveness' — drop the lowest assignment grade from each student's final course grade calculation. Can you suggest a plan?"

## What You Have

### Codebase files (source of truth)

These are the actual implementation files. Use them to verify whether claims in the plans are correct.

1. `grading.py` — the grading engine (`calculate_course_grade`, `apply_grade`, `recalculate_grade_cache`, `bulk_recalculate_course_grades`)
2. `cache_manager.py` — analytics cache (`rebuild_course_analytics`, `invalidate_course_analytics`)
3. `models.py` — all ORM models (Course, Enrollment, Assignment, Submission, Grade)
4. `grade.py` — the grading view (`grade_submission`)
5. `management.py` — course management views (`course_edit`)
6. `forms.py` — Django forms (`CourseForm`, `GradeForm`)

### Plans to evaluate

- **Plan A** — one implementation plan
- **Plan B** — another implementation plan
- **Plan C** — a third implementation plan

### Grading rubric

- `rubric.md` — 10 criteria, scored 0–3 each, max 30 points

## Your Task

1. Read the codebase files carefully. Understand how grading, caching, and analytics currently work.
2. Read all three plans.
3. Read the rubric.
4. Score each plan against the rubric. Be precise — verify claims in the plans against the actual code.
5. Provide the completed scoring table, rationales, and the outputs requested at the end of the rubric.

## Important

- Judge the plans on correctness and completeness, not on writing style or length.
- If a plan makes a factual claim about the codebase (e.g., "this function reads from X"), verify it against the actual code.
- If a plan proposes a change that is unnecessary (the code already handles it), score that as unnecessary work.
- Do not guess which agent produced which plan. Evaluate blindly.
