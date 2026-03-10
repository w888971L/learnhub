"""
Shared JSONL event schema for per-session tool-use logging.

Defines the canonical event shape that all agents (Claude, Codex, Gemini)
produce. Capture backends write events using this schema; analysis tools
consume them.

Created as Phase 1 of the per-session tool-use logging plan.
See: docs/plans/2026-03-10-session-tool-logging/decision.md
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from scripts.classify import classify_files


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

EVENT_SESSION_START = "session_start"
EVENT_SESSION_END = "session_end"
EVENT_TOOL_SUCCESS = "tool_success"
EVENT_TOOL_FAILURE = "tool_failure"
EVENT_DELEGATION_START = "delegation_start"
EVENT_DELEGATION_END = "delegation_end"

VALID_EVENT_TYPES = {
    EVENT_SESSION_START,
    EVENT_SESSION_END,
    EVENT_TOOL_SUCCESS,
    EVENT_TOOL_FAILURE,
    EVENT_DELEGATION_START,
    EVENT_DELEGATION_END,
}

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

AGENT_CLAUDE = "claude"
AGENT_CODEX = "codex"
AGENT_GEMINI = "gemini"


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------

@dataclass
class ToolEvent:
    """A single tool-use event in the shared log format.

    Required fields:
        timestamp:  ISO 8601 UTC timestamp.
        session_id: Unique session identifier (agent-provided).
        agent:      Which agent produced this event (claude|codex|gemini).
        event_type: One of the VALID_EVENT_TYPES.

    Tool fields (required for tool_success/tool_failure):
        tool_name:  Name of the tool invoked.
        summary:    Human-readable one-line summary.
        status:     'success' or 'failure'.

    File fields (optional, populated when tool touches files):
        file_paths:   List of file paths involved.
        file_classes: List of classifications, same order as file_paths.

    Context fields (optional):
        cwd:         Working directory at time of event.
        agent_id:    Subagent ID if this was a delegated call.
        error:       Error message for tool_failure events.
        delegated_to: Description of delegation target.
        raw_backend:  Backend-specific data preserved for fidelity.
    """
    timestamp: str
    session_id: str
    agent: str
    event_type: str

    # Tool fields
    tool_name: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None

    # File fields
    file_paths: list[str] = field(default_factory=list)
    file_classes: list[str] = field(default_factory=list)

    # Context fields
    cwd: Optional[str] = None
    agent_id: Optional[str] = None
    error: Optional[str] = None
    delegated_to: Optional[str] = None
    raw_backend: Optional[dict] = None

    def __post_init__(self):
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {self.event_type!r}")

        # Auto-classify file paths if file_classes not provided
        if self.file_paths and not self.file_classes:
            self.file_classes = classify_files(self.file_paths)

    def to_json(self) -> str:
        """Serialize to a compact JSON string (one line, no nulls)."""
        d = asdict(self)
        # Strip None values and empty lists for compact output
        d = {k: v for k, v in d.items() if v is not None and v != [] and v != {}}
        return json.dumps(d, separators=(",", ":"))

    @classmethod
    def from_json(cls, line: str) -> "ToolEvent":
        """Deserialize from a JSON string."""
        d = json.loads(line)
        return cls(**d)


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tool_success(
    session_id: str,
    agent: str,
    tool_name: str,
    summary: str,
    file_paths: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    agent_id: Optional[str] = None,
    raw_backend: Optional[dict] = None,
) -> ToolEvent:
    """Create a tool_success event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_TOOL_SUCCESS,
        tool_name=tool_name,
        summary=summary,
        status="success",
        file_paths=file_paths or [],
        cwd=cwd,
        agent_id=agent_id,
        raw_backend=raw_backend,
    )


def tool_failure(
    session_id: str,
    agent: str,
    tool_name: str,
    summary: str,
    error: str,
    file_paths: Optional[list[str]] = None,
    cwd: Optional[str] = None,
    agent_id: Optional[str] = None,
    raw_backend: Optional[dict] = None,
) -> ToolEvent:
    """Create a tool_failure event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_TOOL_FAILURE,
        tool_name=tool_name,
        summary=summary,
        status="failure",
        error=error,
        file_paths=file_paths or [],
        cwd=cwd,
        agent_id=agent_id,
        raw_backend=raw_backend,
    )


def session_start(
    session_id: str,
    agent: str,
    cwd: Optional[str] = None,
) -> ToolEvent:
    """Create a session_start event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_SESSION_START,
        cwd=cwd,
    )


def session_end(
    session_id: str,
    agent: str,
) -> ToolEvent:
    """Create a session_end event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_SESSION_END,
    )


def delegation_start(
    session_id: str,
    agent: str,
    delegated_to: str,
    agent_id: Optional[str] = None,
) -> ToolEvent:
    """Create a delegation_start event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_DELEGATION_START,
        delegated_to=delegated_to,
        agent_id=agent_id,
    )


def delegation_end(
    session_id: str,
    agent: str,
    agent_id: Optional[str] = None,
) -> ToolEvent:
    """Create a delegation_end event."""
    return ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=agent,
        event_type=EVENT_DELEGATION_END,
        agent_id=agent_id,
    )
