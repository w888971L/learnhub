#!/usr/bin/env python3
"""
Extract normalized tool-use events from Gemini CLI session transcripts.

Reads Gemini session JSON files from ~/.gemini/tmp/<project>/chats/ and
writes compact per-session JSONL logs in the shared schema.

Usage:
    python scripts/extract_gemini_log.py <session.json>
    python scripts/extract_gemini_log.py --dir <chats-directory>
    python scripts/extract_gemini_log.py <session.json> --stdout
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
    AGENT_GEMINI,
    EVENT_SESSION_END,
    EVENT_SESSION_START,
    EVENT_TOOL_FAILURE,
    EVENT_TOOL_SUCCESS,
    ToolEvent,
)

# Tool name mappings: Gemini tool names → action categories
READ_TOOLS = {"read_file", "read_many_files"}
WRITE_TOOLS = {"write_file", "edit_file", "replace_in_file"}
SEARCH_TOOLS = {"grep_search", "list_dir", "find_files", "glob"}
SHELL_TOOLS = {"run_shell_command"}


def classify_tool(name: str) -> str:
    """Map a Gemini tool name to an action category."""
    if name in READ_TOOLS:
        return "read"
    if name in WRITE_TOOLS:
        return "write"
    if name in SEARCH_TOOLS:
        return "search"
    if name in SHELL_TOOLS:
        return "shell"
    return name


def extract_file_paths(name: str, args: dict) -> list[str]:
    """Extract file paths from tool call arguments."""
    paths = []

    # Direct file_path argument (read_file, write_file, edit_file)
    fp = args.get("file_path") or args.get("path")
    if fp and isinstance(fp, str):
        paths.append(fp)

    # Multiple files (read_many_files)
    file_list = args.get("files") or args.get("file_paths")
    if isinstance(file_list, list):
        for f in file_list:
            if isinstance(f, str):
                paths.append(f)
            elif isinstance(f, dict) and "file_path" in f:
                paths.append(f["file_path"])

    return paths


def build_summary(name: str, action: str, args: dict, file_paths: list[str]) -> str:
    """Build a human-readable summary of the tool call."""
    if file_paths:
        names = ", ".join(extract_filename(p) for p in file_paths[:3])
        return f"{action}({names})"

    if name == "run_shell_command":
        command = args.get("command", "")
        compact = " ".join(command.split())[:80]
        return f"shell({compact})" if compact else "shell"

    if name == "grep_search":
        pattern = args.get("pattern", "")
        return f"search({pattern[:60]})"

    return action


def extract_events(session_path: Path) -> tuple[str, list[ToolEvent]]:
    """Parse a Gemini session JSON file and extract ToolEvents."""
    with session_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    session_id = data.get("sessionId", session_path.stem)
    messages = data.get("messages", [])
    events: list[ToolEvent] = []

    # Session start
    start_time = data.get("startTime", "")
    if not start_time and messages:
        start_time = messages[0].get("timestamp", "")

    # Determine cwd from first shell command or project context
    session_cwd: Optional[str] = None

    events.append(ToolEvent(
        timestamp=start_time,
        session_id=session_id,
        agent=AGENT_GEMINI,
        event_type=EVENT_SESSION_START,
        cwd=session_cwd,
    ))

    last_timestamp = start_time

    for msg in messages:
        tool_calls = msg.get("toolCalls", [])
        for tc in tool_calls:
            name = tc.get("name", "unknown")
            args = tc.get("args", {})
            status = tc.get("status", "success")
            timestamp = tc.get("timestamp", msg.get("timestamp", ""))

            if timestamp:
                last_timestamp = timestamp

            action = classify_tool(name)
            file_paths = extract_file_paths(name, args)

            # Classify files
            file_classes = [classify_file(p) for p in file_paths] if file_paths else []

            summary = build_summary(name, action, args, file_paths)

            # Extract error from result if failed
            error = None
            if status != "success":
                results = tc.get("result", [])
                for r in results:
                    resp = r.get("functionResponse", {}).get("response", {})
                    output = resp.get("output", "")
                    if output:
                        error = str(output)[:500]
                        break

            # Detect cwd from shell commands or file paths
            if not session_cwd and file_paths:
                for fp in file_paths:
                    normalized = normalize_path(fp)
                    if "learnhub" in normalized.lower():
                        # Extract project root from absolute path
                        idx = normalized.lower().find("learnhub")
                        session_cwd = normalized[:idx + len("learnhub")]
                        break

            event = ToolEvent(
                timestamp=timestamp,
                session_id=session_id,
                agent=AGENT_GEMINI,
                event_type=EVENT_TOOL_SUCCESS if status == "success" else EVENT_TOOL_FAILURE,
                tool_name=name,
                summary=summary,
                status=status,
                file_paths=file_paths,
                cwd=session_cwd,
                error=error,
            )
            # file_classes are set by ToolEvent.__post_init__ via classify,
            # but the paths may be relative — override with our classification
            if file_classes:
                event.file_classes = file_classes

            events.append(event)

    # Backfill cwd on session_start if we found it later
    if session_cwd and events and events[0].event_type == EVENT_SESSION_START:
        events[0].cwd = session_cwd

    # Session end
    if last_timestamp:
        events.append(ToolEvent(
            timestamp=last_timestamp,
            session_id=session_id,
            agent=AGENT_GEMINI,
            event_type=EVENT_SESSION_END,
        ))

    return session_id, events


def write_events(events: list[ToolEvent], destination: Path) -> None:
    """Write events to a JSONL file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as f:
        for event in events:
            f.write(event.to_json())
            f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract shared-schema tool logs from Gemini CLI session transcripts."
    )
    parser.add_argument("session", nargs="?", help="Path to a single Gemini session .json file")
    parser.add_argument("--dir", help="Extract all .json session files in a directory")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / ".gemini" / "logs"),
        help="Directory for extracted per-session logs (default: .gemini/logs)",
    )
    parser.add_argument("--output", help="Explicit output path for a single session")
    parser.add_argument("--stdout", action="store_true", help="Print extracted JSONL instead of writing files")
    return parser.parse_args()


def collect_session_files(args: argparse.Namespace) -> list[Path]:
    if args.session and args.dir:
        raise SystemExit("Pass either a single session path or --dir, not both.")
    if not args.session and not args.dir:
        raise SystemExit("Pass a session path or --dir.")

    if args.dir:
        return sorted(Path(args.dir).glob("session-*.json"))
    return [Path(args.session)]


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    args = parse_args()
    session_files = collect_session_files(args)

    for session_path in session_files:
        session_id, events = extract_events(session_path)
        if args.stdout:
            for event in events:
                print(event.to_json())
            continue

        if args.output and len(session_files) > 1:
            raise SystemExit("--output may only be used with a single session.")

        destination = Path(args.output) if args.output else Path(args.output_dir) / f"tool-use-{session_id}.jsonl"
        write_events(events, destination)
        print(f"{session_path} -> {destination} ({len(events)} events)")


if __name__ == "__main__":
    main()
