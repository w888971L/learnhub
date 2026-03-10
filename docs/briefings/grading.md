Last produced: 2026-03-10
Charter sources: views_assignments.md, models_assignments.md, models_courses.md, infrastructure.md, cross_cutting.md, docs/flows/grading-flow.md

# Grading Briefing

## Executive Summary

LearnHub's grading system is built around a deliberate split between raw instructor input and stored student outcome. Instructors enter a raw score in the grading view, but the persisted `Grade.score` may be lower because late penalties are applied at grading time, not submission time.

The rest of the design is about propagation. A final grade does not just create a `Grade` row; it can update `Enrollment.final_grade_cache`, notify the student, and mark course analytics stale. Most of the system's fragility comes from maintaining those derived values correctly when code paths bypass the main grading flow.

## Architecture Overview

The grading flow starts in [grade.py](C:/Users/curator/code2/learnhub/core/views_lib/assignments/grade.py), specifically `grade_submission()`. That view is the main orchestration point for instructor grading. It validates `GradeForm`, calls `apply_grade()` in [grading.py](C:/Users/curator/code2/learnhub/core/utils/grading.py), updates the submission status, optionally recalculates the enrollment grade cache, notifies the student, and invalidates course analytics.

The underlying data model lives in [models.py](C:/Users/curator/code2/learnhub/core/models.py). Three models matter most:
- `Assignment`: defines `max_score`, `due_date`, `late_policy`, and optional rubric structure.
- `Submission`: stores each student attempt, including version number and a status field.
- `Grade`: stores the instructor's assessment, including penalty-adjusted `score`, `feedback`, `rubric_scores`, and `is_final`.

`Enrollment` in [models.py](C:/Users/curator/code2/learnhub/core/models.py) is where grading leaves the assignment domain and becomes course state. Its `final_grade_cache` field is a cached aggregate for the student's course grade. That cache is computed by `calculate_course_grade()` and persisted by `recalculate_grade_cache()` in [grading.py](C:/Users/curator/code2/learnhub/core/utils/grading.py).

Analytics are a separate downstream consumer. [cache_manager.py](C:/Users/curator/code2/learnhub/core/utils/cache_manager.py) maintains `CourseAnalytics`, including `average_grade`, but it computes that directly from `Grade` records instead of reading `Enrollment.final_grade_cache`. That gives the system two grade-derived representations: per-enrollment cached grade and course-wide analytics aggregate.

Notifications are another downstream effect. [notifications.py](C:/Users/curator/code2/learnhub/core/utils/notifications.py) exposes `notify_grade_posted(grade)`, which is called from `grade_submission()` when the grade is marked final.

## Key Design Decisions

The most important design choice is applying late penalties at grading time via `calculate_late_penalty()` and `apply_grade()`, not when the student submits. That means submission acceptance and grade calculation are intentionally decoupled. A late submission with `late_policy='penalize'` is still accepted; the deduction is deferred until the instructor evaluates it. The likely reason is pedagogical: instructors can judge the work on its merits first, then the system applies policy.

The second major choice is storing course-grade state as a cache rather than deriving it on every page load. `Enrollment.final_grade_cache` exists for performance, but the source of truth remains the set of final `Grade` records for that student's submissions in the course. This is a pragmatic trade-off: better read performance in exchange for propagation complexity.

The third design choice is to keep analytics on their own calculation path. `rebuild_course_analytics()` recomputes `average_grade` directly from `Grade` rows. That avoids coupling analytics reads to enrollment caches, but it means any future grading-rule change has to be implemented twice: once in `calculate_course_grade()` and once in `rebuild_course_analytics()`.

There is also a notable split between utility-layer defaults and view-layer policy. `apply_grade()` creates the new grade with `is_final=True`, then `grade_submission()` overwrites `grade.is_final` with the form value. That is not elegant, but it does make the view the final authority over whether a grade participates in grade-cache propagation.

## Non-Obvious Behavior

The biggest tripwire is that `Grade.score` is not the same thing as the score the instructor typed. `apply_grade()` multiplies the raw score by `(1 - penalty)`, rounds the result, and stores that adjusted value. Anyone reading `Grade.score` later is reading the policy-adjusted result, not the rubric-only evaluation.

Another non-obvious behavior is that "final" is what drives aggregation, not "graded." A submission can have grades attached and still not affect the course total unless `is_final=True`. `calculate_course_grade()` filters only final grades, and `grade_submission()` only recalculates `Enrollment.final_grade_cache` when the form marks the grade final.

There is also a subtle duplication in the grading path. `apply_grade()` already marks the submission status as `graded`, and then `grade_submission()` sets `submission.status = SubmissionStatus.GRADED` again. That duplication is harmless, but it signals that responsibilities are split awkwardly across layers.

The analytics behavior is easy to misread. The user-facing docs describe an update chain, but the concrete implementation is "invalidate now, rebuild on next analytics read." `recalculate_grade_cache()` imports and calls `invalidate_course_analytics()`, and `grade_submission()` also invalidates analytics explicitly at the end of the request. So the system prefers deferred freshness over synchronous recomputation.

Finally, rubric changes are amplified by caching. Changing an assignment rubric does not automatically recalculate existing grades or caches. The intended repair path is `bulk_recalculate_course_grades(course)`, which recomputes enrollment caches for active and completed students and then rebuilds analytics once for the course.

## Risk Profile

The highest risk is bypassing the main grading path. Any code that creates or mutates `Grade` rows without using `apply_grade()` and `recalculate_grade_cache()` can break at least one of three things: late penalties, `Enrollment.final_grade_cache`, or analytics freshness.

The second major risk is dual calculation drift. `calculate_course_grade()` and `rebuild_course_analytics()` both derive percentages from final grades, but they are separate implementations. If you add features like grade drops, weighting, forgiveness, or selective inclusion rules, the per-student grade and course analytics can silently diverge.

The admin surface is another risk because it bypasses business logic. Direct admin edits can create grades without penalties, skip cache recalculation, or set inconsistent final-state data. The constitution explicitly calls this out as a trusted-user-only compromise, not a safe workflow.

There is also some conceptual fragility around `is_final`. Because `apply_grade()` starts by creating a final grade and the view may then flip it to non-final, future contributors could easily assume the utility enforces finality when it does not. That makes the flow more error-prone than it needs to be.

## Technical Debt & Opportunities

The cleanest improvement would be to make one layer own finalization. Either `apply_grade()` should accept `is_final` explicitly and persist the intended state once, or the utility should create a non-final grade by default and let the view finalize it. The current two-step overwrite works, but it obscures the contract.

The second improvement would be to extract a single shared grade-aggregation primitive used by both `calculate_course_grade()` and `rebuild_course_analytics()`. Right now the code documents the dual-path tripwire because the implementation has not eliminated it.

The third opportunity is clearer separation between "mark stale" and "rebuild now" semantics. The current code mostly invalidates analytics and rebuilds lazily, while some comments and mental models use language that sounds synchronous. Tightening that vocabulary would reduce confusion for future contributors.

Testing opportunity: the grading code would benefit from explicit coverage for late penalties on partial days, max late-day caps, non-final versus final grade behavior, rubric-change recomputation, and analytics divergence scenarios. Those are the places where the architecture is most likely to surprise someone.

## Connections

Grading is not just an assignments feature. It crosses into the courses domain through `Enrollment.final_grade_cache`, into analytics through `CourseAnalytics.average_grade`, and into notifications through `notify_grade_posted()`.

It also connects to submission versioning in a non-obvious way. Students can create multiple `Submission` versions, but the grading UI is built to show and grade the latest version per student. That means grade correctness depends partly on submission-selection logic in `submission_list()`, not just on grade math.

The grading system also depends on app settings more than a newcomer might expect. `calculate_late_penalty()` reads `LEARNHUB_SETTINGS` values like `LATE_PENALTY_PER_DAY`, `MAX_LATE_DAYS`, and analytics freshness depends on `GRADE_CACHE_TTL`.

The key mental model is this: grading in LearnHub is a cascade system, not a single write. A finalized grade can change persisted grade records, submission state, student-visible cached course grade, notification state, and the freshness of analytics. If you only modify the `Grade` model or the grading view in isolation, you will miss part of the system.
