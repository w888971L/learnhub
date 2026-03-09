# Discussion Views — course discussion forums

Last verified: 2026-03-08
Files covered: core/views_lib/discussions/threads.py

---

## thread_list [L39]
GET: Lists discussion threads for a course. Pinned threads first, then by created_at descending.
Guards: user must be enrolled or be the instructor
Decorators: @login_required, @course_participant_required
Template: core/discussions/thread_list.html

## thread_create [L63]
GET/POST: Create a new discussion thread.
Sets author = request.user, course from URL.
Decorators: @login_required, @course_participant_required
Form: ThreadForm

## thread_detail [L93]
GET: Shows thread with all posts in threaded order. Posts include reaction counts.
Uses: `Post.objects.filter(thread=).select_related('author').prefetch_related('reactions')` with manual tree building for threaded display.
Decorators: @login_required, @course_participant_required
Template: core/discussions/thread_detail.html

## post_reply [L132]
POST only. Creates a reply post in a thread.
Guards: thread must not be locked. If locked, returns redirect with error message.
Side effects: calls `notify_new_discussion_post(post)` — sends notification to thread participants.
Decorators: @login_required, @course_participant_required
Form: PostForm

! Discussion notifications: `notify_new_discussion_post()` creates in-app Notification records synchronously. A background daemon thread handles secondary processing (e.g., email dispatch). The post is created regardless of notification outcome.
→ see infrastructure.md `notify_new_discussion_post` for the threading pattern
