# LearnHub — Flow Documentation Index

These documents describe how features work end-to-end, written for humans (staff, new developers, onboarding).

Each flow doc traces a user journey across multiple files. They are the "public record" — the human-readable complement to the technical charters in `docs/architecture/modules/`.

## Flows

| Flow | Description | Key Roles |
|------|-------------|-----------|
| [Enrollment Flow](enrollment-flow.md) | How students discover, enroll in, and drop courses | Student, Instructor |
| [Assignment Submission](assignment-submission.md) | How students submit work, including resubmission and late handling | Student |
| [Grading Flow](grading-flow.md) | How instructors grade submissions, including late penalties and grade cascades | Instructor |

## Relationship to Charters

Flow docs reference charters for technical details. Each flow doc has a footer listing its charter sources.

**Update chain**: When code changes, update the relevant charter first, then update any affected flow docs.
