#!/usr/bin/env python3
"""
Gemini CLI tool-use logger.

Writes tool events to a per-session JSONL file in .gemini/logs/.
Consistent with the shared event schema (Phase 1).

Usage:
    python scripts/log_gemini_tool.py --event tool_success --tool-name read_file --summary "read(GEMINI.md)" --file-paths GEMINI.md
"""

import argparse
import sys
import uuid
from pathlib import Path

# Add project root to path for shared modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.session_log_schema import (
    ToolEvent,
    EVENT_TOOL_SUCCESS,
    EVENT_TOOL_FAILURE,
    EVENT_SESSION_START,
    EVENT_SESSION_END,
    EVENT_DELEGATION_START,
    EVENT_DELEGATION_END,
    AGENT_GEMINI,
    _now_iso
)
from scripts.classify import classify_files


def get_or_create_session_id() -> str:
    """Get the current session ID from .gemini/current_session or create a new one."""
    gemini_dir = PROJECT_ROOT / ".gemini"
    gemini_dir.mkdir(parents=True, exist_ok=True)
    session_file = gemini_dir / "current_session"

    if session_file.exists():
        return session_file.read_text().strip()

    # Create new session ID
    session_id = str(uuid.uuid4())[:8]  # Short ID for brevity
    session_file.write_text(session_id)

    return session_id


def log_event(
    event_type: str,
    session_id: str = None,
    tool_name: str = None,
    summary: str = None,
    status: str = None,
    file_paths: list[str] = None,
    error: str = None,
    delegated_to: str = None,
    agent_id: str = None,
    cwd: str = None,
):
    """Create and append a ToolEvent to the log file."""
    if not session_id:
        session_id = get_or_create_session_id()

    # Build event object
    event = ToolEvent(
        timestamp=_now_iso(),
        session_id=session_id,
        agent=AGENT_GEMINI,
        event_type=event_type,
        tool_name=tool_name,
        summary=summary,
        status=status,
        file_paths=file_paths or [],
        cwd=cwd or str(PROJECT_ROOT),
        error=error,
        delegated_to=delegated_to,
        agent_id=agent_id
    )

    # Ensure log directory exists
    log_dir = PROJECT_ROOT / ".gemini" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"tool-use-{session_id}.jsonl"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(event.to_json() + "\n")


def main():
    parser = argparse.ArgumentParser(description="Log a Gemini tool-use event.")
    parser.add_argument("--event", required=True, choices=[
        EVENT_SESSION_START, EVENT_SESSION_END, EVENT_TOOL_SUCCESS,
        EVENT_TOOL_FAILURE, EVENT_DELEGATION_START, EVENT_DELEGATION_END
    ])
    parser.add_argument("--session-id", help="Session ID (defaults to current_session)")
    parser.add_argument("--tool-name", help="Name of the tool")
    parser.add_argument("--summary", help="One-line summary of the tool call")
    parser.add_argument("--status", choices=["success", "failure"], help="Tool execution status")
    parser.add_argument("--file-paths", nargs="*", help="Files touched by the tool")
    parser.add_argument("--error", help="Error message for failures")
    parser.add_argument("--delegated-to", help="Target of delegation")
    parser.add_argument("--agent-id", help="Subagent ID")
    parser.add_argument("--cwd", help="Current working directory")

    args = parser.parse_args()

    log_event(
        event_type=args.event,
        session_id=args.session_id,
        tool_name=args.tool_name,
        summary=args.summary,
        status=args.status,
        file_paths=args.file_paths,
        error=args.error,
        delegated_to=args.delegated_to,
        agent_id=args.agent_id,
        cwd=args.cwd
    )


if __name__ == "__main__":
    main()
