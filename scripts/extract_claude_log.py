#!/usr/bin/env python3
"""
Extract normalized tool-use events from Claude Code native session transcripts.

Reads Claude Code session JSONL files from ~/.claude/projects/<project>/ and
writes compact per-session JSONL logs in the shared schema.

Claude Code transcript format:
  - Each line is a JSON object with a "type" field
  - "assistant" type messages contain content arrays with "tool_use" blocks
  - Tool calls have "name" and "input" fields
  - Tool results appear in subsequent "tool_result" messages

Usage:
    python scripts/extract_claude_log.py <session.jsonl>
    python scripts/extract_claude_log.py --project learnhub2
    python scripts/extract_claude_log.py <session.jsonl> --stdout
"""

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.classify import classify_file, extract_filename, normalize_path
from scripts.session_log_schema import (
    AGENT_CLAUDE,
    EVENT_DELEGATION_END,
    EVENT_DELEGATION_START,
    EVENT_SESSION_END,
    EVENT_SESSION_START,
    EVENT_TOOL_FAILURE,
    EVENT_TOOL_SUCCESS,
    ToolEvent,
)

# Claude Code native transcript directory
CLAUDE_PROJECTS_BASE = Path.home() / ".claude" / "projects"

# Tool name mappings: Claude Code tools → action categories
READ_TOOLS = {"Read"}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
SEARCH_TOOLS = {"Glob", "Grep", "ToolSearch"}
SHELL_TOOLS = {"Bash"}
DELEGATION_TOOLS = {"Agent"}
SKILL_TOOLS = {"Skill"}
META_TOOLS = {"TaskCreate", "TaskUpdate", "TaskGet", "TaskList", "TaskOutput",
              "TaskStop", "CronCreate", "CronDelete", "CronList",
              "EnterPlanMode", "ExitPlanMode", "EnterWorktree", "ExitWorktree",
              "AskUserQuestion"}
WEB_TOOLS = {"WebFetch", "WebSearch"}


def classify_tool(name: str) -> str:
    """Map a Claude Code tool name to an action category."""
    if name in READ_TOOLS:
        return "read"
    if name in WRITE_TOOLS:
        return "write"
    if name in SEARCH_TOOLS:
        return "search"
    if name in SHELL_TOOLS:
        return "shell"
    if name in DELEGATION_TOOLS:
        return "delegation"
    if name in SKILL_TOOLS:
        return "skill"
    if name in WEB_TOOLS:
        return "web"
    if name in META_TOOLS:
        return "meta"
    return name.lower()


def extract_file_paths(name: str, input_data: dict) -> list[str]:
    """Extract file paths from tool call input."""
    paths = []

    # Read tool
    if name == "Read":
        fp = input_data.get("file_path")
        if fp:
            paths.append(fp)

    # Write/Edit tools
    elif name in ("Write", "Edit"):
        fp = input_data.get("file_path")
        if fp:
            paths.append(fp)

    # Glob
    elif name == "Glob":
        path = input_data.get("path")
        if path:
            paths.append(path)

    # Grep
    elif name == "Grep":
        path = input_data.get("path")
        if path:
            paths.append(path)

    # Bash — try to extract paths from command
    elif name == "Bash":
        # Don't try to parse bash commands for paths — too unreliable
        pass

    return paths


def build_summary(name: str, action: str, input_data: dict, file_paths: list[str]) -> str:
    """Build a human-readable summary of the tool call."""
    if file_paths:
        names = ", ".join(extract_filename(p) for p in file_paths[:3])
        return f"{action}({names})"

    if name == "Bash":
        command = input_data.get("command", "")
        compact = " ".join(command.split())[:80]
        return f"shell({compact})" if compact else "shell"

    if name == "Grep":
        pattern = input_data.get("pattern", "")
        return f"search({pattern[:60]})"

    if name == "Glob":
        pattern = input_data.get("pattern", "")
        return f"search(glob:{pattern[:60]})"

    if name == "Agent":
        desc = input_data.get("description", "")
        return f"delegation({desc[:60]})"

    if name == "Skill":
        skill = input_data.get("skill", "")
        return f"skill({skill})"

    return action


def find_project_dir(project_name: str) -> Optional[Path]:
    """Find the Claude projects directory for a given project name."""
    if not CLAUDE_PROJECTS_BASE.exists():
        return None

    # Claude uses path-encoded directory names like C--Users-curator-code2-learnhub
    for d in CLAUDE_PROJECTS_BASE.iterdir():
        if d.is_dir() and project_name.lower() in d.name.lower():
            return d
    return None


def find_latest_session(project_name: str) -> Optional[Path]:
    """Find the most recent Claude session transcript for a project."""
    project_dir = find_project_dir(project_name)
    if not project_dir:
        return None

    sessions = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return sessions[-1] if sessions else None


def extract_events(session_path: Path) -> tuple[str, list[ToolEvent]]:
    """Parse a Claude Code session JSONL file and extract ToolEvents."""
    events: list[ToolEvent] = []
    session_id = None
    session_cwd = None
    first_timestamp = None
    last_timestamp = None

    with session_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            rec_type = record.get("type")
            timestamp = record.get("timestamp", "")

            # Extract session info from user messages
            if rec_type == "user":
                if not session_id:
                    session_id = record.get("sessionId", "")
                if not session_cwd:
                    session_cwd = record.get("cwd")
                if not first_timestamp and timestamp:
                    first_timestamp = timestamp

            if timestamp:
                last_timestamp = timestamp

            # Helper to process tool_use content blocks
            def _process_content(content, ts, agent_id=None):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue

                    tool_name = block.get("name", "unknown")
                    input_data = block.get("input", {})

                    action = classify_tool(tool_name)
                    file_paths = extract_file_paths(tool_name, input_data)
                    summary = build_summary(tool_name, action, input_data, file_paths)

                    # Handle delegation tools specially
                    if tool_name == "Agent":
                        events.append(ToolEvent(
                            timestamp=ts,
                            session_id=session_id or session_path.stem,
                            agent=AGENT_CLAUDE,
                            event_type=EVENT_DELEGATION_START,
                            tool_name=tool_name,
                            summary=summary,
                            delegated_to=input_data.get("description", ""),
                            agent_id=input_data.get("resume") or agent_id,
                            cwd=session_cwd,
                        ))
                        continue

                    event = ToolEvent(
                        timestamp=ts,
                        session_id=session_id or session_path.stem,
                        agent=AGENT_CLAUDE,
                        event_type=EVENT_TOOL_SUCCESS,
                        tool_name=tool_name,
                        summary=summary,
                        status="success",
                        file_paths=file_paths,
                        cwd=session_cwd,
                        agent_id=agent_id,
                    )
                    events.append(event)

            # Extract tool calls from assistant messages (main agent)
            if rec_type == "assistant":
                message = record.get("message", {})
                content = message.get("content", [])
                ts = timestamp or last_timestamp or ""
                _process_content(content, ts)

            # Extract tool calls from progress messages (subagent calls)
            if rec_type == "progress":
                data = record.get("data", {})
                msg = data.get("message", {})
                if msg.get("type") == "assistant":
                    inner_msg = msg.get("message", {})
                    content = inner_msg.get("content", [])
                    agent_id = data.get("agentId")
                    ts = timestamp or last_timestamp or ""
                    _process_content(content, ts, agent_id=agent_id)

            # Track tool results for failure detection
            if rec_type == "tool_result":
                # Claude Code logs tool results separately
                is_error = record.get("is_error", False)
                if is_error and events:
                    # Mark the last event as failure
                    last = events[-1]
                    if last.event_type == EVENT_TOOL_SUCCESS:
                        last.event_type = EVENT_TOOL_FAILURE
                        last.status = "failure"
                        content_data = record.get("content", "")
                        if isinstance(content_data, str):
                            last.error = content_data[:500]
                        elif isinstance(content_data, list):
                            for item in content_data:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    last.error = item.get("text", "")[:500]
                                    break

    if not session_id:
        session_id = session_path.stem

    # Prepend session_start
    all_events = [ToolEvent(
        timestamp=first_timestamp or "",
        session_id=session_id,
        agent=AGENT_CLAUDE,
        event_type=EVENT_SESSION_START,
        cwd=session_cwd,
    )]
    all_events.extend(events)

    # Append session_end
    all_events.append(ToolEvent(
        timestamp=last_timestamp or "",
        session_id=session_id,
        agent=AGENT_CLAUDE,
        event_type=EVENT_SESSION_END,
    ))

    return session_id, all_events


def write_events(events: list[ToolEvent], destination: Path) -> None:
    """Write events to a JSONL file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as f:
        for event in events:
            f.write(event.to_json())
            f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract shared-schema tool logs from Claude Code session transcripts."
    )
    parser.add_argument("session", nargs="?", help="Path to a single Claude session .jsonl file")
    parser.add_argument("--project", help="Project name to find latest session (e.g., 'learnhub2')")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / ".claude" / "logs"),
        help="Directory for extracted per-session logs (default: .claude/logs)",
    )
    parser.add_argument("--output", help="Explicit output path for a single session")
    parser.add_argument("--stdout", action="store_true", help="Print extracted JSONL instead of writing files")
    return parser.parse_args()


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    args = parse_args()

    if args.session and args.project:
        raise SystemExit("Pass either a session path or --project, not both.")

    session_path = None
    if args.session:
        session_path = Path(args.session)
    elif args.project:
        session_path = find_latest_session(args.project)
        if not session_path:
            raise SystemExit(f"No Claude sessions found for project matching '{args.project}'")
        print(f"Found session: {session_path}", file=sys.stderr)
    else:
        raise SystemExit("Pass a session path or --project.")

    if not session_path.exists():
        raise SystemExit(f"Session file not found: {session_path}")

    session_id, events = extract_events(session_path)

    if args.stdout:
        for event in events:
            print(event.to_json())
        return

    destination = Path(args.output) if args.output else Path(args.output_dir) / f"tool-use-{session_id}.jsonl"
    write_events(events, destination)
    print(f"{session_path} -> {destination} ({len(events)} events)")


if __name__ == "__main__":
    main()
