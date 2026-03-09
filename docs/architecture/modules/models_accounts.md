# Accounts Domain — users, organizations, roles

Last verified: 2026-03-08
Files covered: core/models.py (User, Organization, InstructorProfile)

---

## User [L101]
Custom user extending AbstractUser. Single-table role system (no separate role table).

Fields: role (admin/instructor/student), organization FK (nullable), bio TextField
Properties: `is_instructor`, `is_student`, `is_admin_role` — convenience booleans derived from role field.

! Role is stored as a plain CharField, not enforced at DB level beyond the choices constraint. Permission checks happen in view decorators (`core/utils/permissions.py`), not in the model.
→ see infrastructure.md `role_required`, `instructor_required`

## Organization [L158]
Multi-tenant container. Courses, users, and analytics are scoped to organizations.

Fields: name, slug (unique), settings JSONField (default=dict), is_active bool, created_at
The `settings` JSONField is extensible — used for org-level overrides (e.g., custom late penalty policies). Currently unused but designed for future expansion.

## InstructorProfile [L192]
One-to-one extension for instructor-specific data.

Fields: user OneToOne, department CharField, office_hours TextField, rating DecimalField
`rating` is a CACHED aggregate of student course ratings. Not currently computed — placeholder for future feature.
→ see cross_cutting.md "Cached Aggregates" for the general cache pattern
