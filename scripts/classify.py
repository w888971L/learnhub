"""
Shared file classification and constitutional terminology detection.

This is the single source of truth for determining whether a file path
belongs to governance, flow, experiment, or code categories. All logging
hooks, extraction scripts, and analysis tools import from here.

Created as Phase 1 of the per-session tool-use logging plan.
See: docs/plans/2026-03-10-session-tool-logging/decision.md
"""

import re
from pathlib import PurePosixPath


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------

# Patterns that identify governance/constitutional files (case-insensitive)
GOVERNANCE_PATH_PATTERNS = [
    r"docs/architecture/",
    r"docs/procedures/",
    r"docs/reference-notes/",
    r"docs/plans/",
    r"\.claude/commands/",
    r"CLAUDE\.md$",
    r"GEMINI\.md$",
    r"AGENTS\.md$",
    r"cross_cutting\.md",
]

# Patterns for flow docs (governance-adjacent but human-facing)
FLOW_PATH_PATTERNS = [
    r"docs/flows/",
]

# Patterns for experiment/study docs
EXPERIMENT_PATH_PATTERNS = [
    r"docs/experiments/",
    r"docs/control-study/",
]


def normalize_path(raw_path: str) -> str:
    """Normalize a file path to forward-slash POSIX style for consistent matching."""
    return raw_path.replace("\\", "/")


def classify_file(path: str) -> str:
    """Classify a file path as 'governance', 'flow', 'experiment', or 'code'.

    Args:
        path: Absolute or relative file path (any OS format).

    Returns:
        One of: 'governance', 'flow', 'experiment', 'code'.
    """
    normed = normalize_path(path)
    for pat in GOVERNANCE_PATH_PATTERNS:
        if re.search(pat, normed, re.IGNORECASE):
            return "governance"
    for pat in FLOW_PATH_PATTERNS:
        if re.search(pat, normed, re.IGNORECASE):
            return "flow"
    for pat in EXPERIMENT_PATH_PATTERNS:
        if re.search(pat, normed, re.IGNORECASE):
            return "experiment"
    return "code"


def classify_files(paths: list[str]) -> list[str]:
    """Classify a list of file paths. Returns a list of categories in the same order."""
    return [classify_file(p) for p in paths]


def extract_filename(path: str) -> str:
    """Extract just the filename from a full path."""
    normed = normalize_path(path)
    return normed.rsplit("/", 1)[-1] if "/" in normed else normed


# ---------------------------------------------------------------------------
# Constitutional terminology detection
# ---------------------------------------------------------------------------

CONSTITUTIONAL_TERMS = [
    r"\btripwire\b",
    r"\bcharter\b",
    r"\bconstitution(?:al)?\b",
    r"\bcross[_-]cutting\b",
    r"\benforcer\b",
    r"\bgrade\s+cascade\b",
    r"\bgrade\s+cache\s+duality\b",
    r"\blate\s+penalty\s+timing\b",
    r"\bpropagation\s+map\b",
    r"\bliving\s+docs\b",
    r"\bdispatch\s+table\b",
    r"\bmemex\b",
]

CONSTITUTIONAL_TERM_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CONSTITUTIONAL_TERMS]


def count_constitutional_terms(text: str) -> dict[str, int]:
    """Count occurrences of constitutional terminology in text.

    Returns:
        Dict mapping cleaned term pattern to count.
    """
    counts = {}
    for pat in CONSTITUTIONAL_TERM_PATTERNS:
        matches = pat.findall(text)
        if matches:
            term = pat.pattern.replace(r"\b", "").replace(r"\s+", " ")
            counts[term] = len(matches)
    return counts


# ---------------------------------------------------------------------------
# Tripwire detection
# ---------------------------------------------------------------------------

TRIPWIRE_PATTERNS = {
    "Grade Cache Duality": [
        r"grade\s*cache\s*duality",
        r"final_grade_cache",
        r"recalculate_grade_cache",
        r"cached\s+aggregate",
        r"source\s+of\s+truth.*grade\s+records",
    ],
    "Late Penalty Timing": [
        r"late\s*penalty\s*timing",
        r"penalty.*grading\s+time",
        r"penalty.*not\s+submission\s+time",
        r"applied\s+at\s+grad(?:e|ing)\s+time",
    ],
    "Grade Cascade": [
        r"grade\s*cascade",
        r"recalculate_grade_cache.*invalidate_course_analytics",
        r"invalidate.*analytics.*after.*grade",
    ],
    "Enrollment State Machine": [
        r"enrollment\s+state\s+machine",
        r"transitions.*enforced\s+in\s+views",
        r"admin\s+bypasses.*state\s+machine",
        r"pending.*active.*completed.*dropped",
    ],
}


def detect_tripwire_coverage(text: str) -> list[str]:
    """Check which of the four main tripwires are addressed in text.

    Returns:
        List of tripwire names that were found.
    """
    addressed = []
    for tripwire_name, patterns in TRIPWIRE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                addressed.append(tripwire_name)
                break
    return addressed


# ---------------------------------------------------------------------------
# Known cross-references between governance docs
# ---------------------------------------------------------------------------

KNOWN_CROSS_REFS = {
    "CLAUDE.md": [
        "cross_cutting.md",
        "models_accounts.md", "models_courses.md", "models_assignments.md",
        "views_courses.md", "views_assignments.md", "views_discussions.md",
        "views_api.md", "infrastructure.md",
        "about.md", "briefing.md", "perusal.md", "full-review.md",
        "risk-awareness.md", "starter-kit.md",
    ],
    "GEMINI.md": [
        "cross_cutting.md",
        "models_accounts.md", "models_courses.md", "models_assignments.md",
        "views_courses.md", "views_assignments.md", "views_discussions.md",
        "views_api.md", "infrastructure.md",
    ],
    "AGENTS.md": [
        "cross_cutting.md",
        "models_accounts.md", "models_courses.md", "models_assignments.md",
        "views_courses.md", "views_assignments.md", "views_discussions.md",
        "views_api.md", "infrastructure.md",
    ],
    "cross_cutting.md": [
        "models_courses.md", "models_assignments.md",
        "views_courses.md", "views_assignments.md",
        "infrastructure.md",
    ],
    "views_assignments.md": ["models_assignments.md", "infrastructure.md", "cross_cutting.md"],
    "views_courses.md": ["models_courses.md", "infrastructure.md", "cross_cutting.md"],
    "models_assignments.md": ["cross_cutting.md"],
    "models_courses.md": ["cross_cutting.md"],
    "infrastructure.md": ["cross_cutting.md"],
}
