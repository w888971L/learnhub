#!/usr/bin/env python3
"""
Extract normalized tool-use events from Codex CLI session transcripts.

Reads Codex session JSONL files and writes a compact per-session JSONL log
in the shared schema used by Claude, Codex, and Gemini logging work.

Usage:
    python scripts/extract_codex_log.py <session.jsonl>
    python scripts/extract_codex_log.py --dir <session-directory>
    python scripts/extract_codex_log.py <session.jsonl> --stdout
"""

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_codex_session import (
    classify_shell_command,
    extract_filename,
    extract_patch_paths,
)
from scripts.session_log_schema import (
    AGENT_CODEX,
    EVENT_SESSION_END,
    EVENT_SESSION_START,
    EVENT_TOOL_FAILURE,
    EVENT_TOOL_SUCCESS,
    ToolEvent,
)


EXIT_CODE_PATTERN = re.compile(r"Exit code:\s*(-?\d+)")
OUTPUT_SECTION_PATTERN = re.compile(r"\nOutput:\n", re.MULTILINE)


@dataclass
class PendingCall:
    call_id: str
    timestamp: str
    tool_name: str
    summary: str
    cwd: Optional[str]
    file_paths: list[str]
    raw_backend: dict


def normalize_cwd(cwd: Optional[str]) -> Optional[str]:
    if not cwd:
        return None
    return str(PureWindowsPath(cwd))


def resolve_path(raw_path: str, cwd: Optional[str]) -> str:
    path = PureWindowsPath(raw_path)
    if path.is_absolute() or not cwd:
        return str(path)
    return str(PureWindowsPath(cwd) / path)


def resolve_paths(paths: list[str], cwd: Optional[str]) -> list[str]:
    return [resolve_path(path, cwd) for path in paths]


def path_exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except OSError:
        return False


def summarize_shell_command(command: str, file_paths: list[str]) -> str:
    action_kind, _ = classify_shell_command(command)
    if file_paths:
        names = ", ".join(extract_filename(path) for path in file_paths[:3])
        return f"shell_command:{action_kind}({names})"
    compact = " ".join(command.split())[:80]
    return f"shell_command:{action_kind}({compact})" if compact else "shell_command"


def summarize_apply_patch(file_paths: list[str]) -> str:
    if file_paths:
        names = ", ".join(extract_filename(path) for path in file_paths[:3])
        return f"apply_patch({names})"
    return "apply_patch"


def summarize_update_plan(arguments: dict) -> str:
    plan = arguments.get("plan")
    if isinstance(plan, list):
        return f"update_plan({len(plan)} steps)"
    return "update_plan"


def build_pending_call(payload: dict, default_cwd: Optional[str]) -> Optional[PendingCall]:
    payload_type = payload.get("type")
    call_id = payload.get("call_id")
    timestamp = payload.get("timestamp_override") or ""
    if not call_id:
        return None

    if payload_type == "function_call":
        tool_name = payload.get("name", "unknown")
        try:
            arguments = json.loads(payload.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}

        cwd = normalize_cwd(arguments.get("workdir")) or default_cwd
        if tool_name == "shell_command":
            command = arguments.get("command", "")
            action_kind, raw_paths = classify_shell_command(command)
            file_paths = resolve_paths(raw_paths, cwd)
            if action_kind == "search":
                file_paths = [path for path in file_paths if path_exists(path)]
            summary = summarize_shell_command(command, file_paths)
        elif tool_name == "update_plan":
            file_paths = []
            summary = summarize_update_plan(arguments)
        else:
            file_paths = []
            summary = tool_name

        return PendingCall(
            call_id=call_id,
            timestamp=timestamp,
            tool_name=tool_name,
            summary=summary,
            cwd=cwd,
            file_paths=file_paths,
            raw_backend={
                "call_id": call_id,
                "payload_type": payload_type,
                "arguments": arguments,
            },
        )

    if payload_type == "custom_tool_call":
        tool_name = payload.get("name", "custom_tool_call")
        cwd = default_cwd
        raw_input = payload.get("input", "")
        file_paths = resolve_paths(extract_patch_paths(raw_input), cwd) if tool_name == "apply_patch" else []
        summary = summarize_apply_patch(file_paths) if tool_name == "apply_patch" else tool_name
        return PendingCall(
            call_id=call_id,
            timestamp=timestamp,
            tool_name=tool_name,
            summary=summary,
            cwd=cwd,
            file_paths=file_paths,
            raw_backend={
                "call_id": call_id,
                "payload_type": payload_type,
                "status": payload.get("status"),
            },
        )

    return None


def parse_function_output(output_text: str) -> tuple[bool, Optional[str], dict]:
    match = EXIT_CODE_PATTERN.search(output_text)
    exit_code = int(match.group(1)) if match else 0
    output_body = OUTPUT_SECTION_PATTERN.split(output_text, maxsplit=1)[1] if OUTPUT_SECTION_PATTERN.search(output_text) else ""
    metadata = {"exit_code": exit_code}
    if output_body:
        metadata["output_excerpt"] = output_body[:500]
    success = exit_code == 0
    stripped = output_body.strip()
    error = None if success else (stripped[-500:] if stripped else f"Exit code: {exit_code}")
    return success, error, metadata


def parse_custom_output(output_text: str) -> tuple[bool, Optional[str], dict]:
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        return True, None, {"raw_output": output_text[:500]}

    metadata = parsed.get("metadata", {}) if isinstance(parsed, dict) else {}
    exit_code = metadata.get("exit_code", 0)
    success = exit_code == 0
    output_body = str(parsed.get("output", "")) if isinstance(parsed, dict) else ""
    error = None if success else (output_body.strip()[-500:] if output_body.strip() else f"Exit code: {exit_code}")
    backend = {"metadata": metadata}
    if output_body:
        backend["output_excerpt"] = output_body[:500]
    return success, error, backend


def build_tool_event(
    pending: PendingCall,
    timestamp: str,
    success: bool,
    error: Optional[str],
    output_backend: dict,
) -> ToolEvent:
    raw_backend = dict(pending.raw_backend)
    raw_backend.update(output_backend)
    return ToolEvent(
        timestamp=timestamp,
        session_id="",
        agent=AGENT_CODEX,
        event_type=EVENT_TOOL_SUCCESS if success else EVENT_TOOL_FAILURE,
        tool_name=pending.tool_name,
        summary=pending.summary,
        status="success" if success else "failure",
        file_paths=pending.file_paths,
        cwd=pending.cwd,
        error=error,
        raw_backend=raw_backend,
    )


def extract_events(session_path: Path) -> tuple[str, list[ToolEvent]]:
    session_id = session_path.stem
    session_start_ts = ""
    session_cwd: Optional[str] = None
    last_timestamp = ""
    pending_calls: dict[str, PendingCall] = {}
    events: list[ToolEvent] = []

    with session_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = record.get("timestamp", "")
            if timestamp:
                last_timestamp = timestamp

            record_type = record.get("type")
            payload = record.get("payload", {})

            if record_type == "session_meta":
                session_id = payload.get("id", session_id)
                session_start_ts = payload.get("timestamp") or timestamp or session_start_ts
                session_cwd = normalize_cwd(payload.get("cwd"))
                continue

            if record_type != "response_item":
                continue

            payload_type = payload.get("type")
            if payload_type in {"function_call", "custom_tool_call"}:
                enriched_payload = dict(payload)
                enriched_payload["timestamp_override"] = timestamp
                pending = build_pending_call(enriched_payload, session_cwd)
                if pending:
                    pending_calls[pending.call_id] = pending
                continue

            if payload_type == "function_call_output":
                pending = pending_calls.pop(payload.get("call_id", ""), None)
                if not pending:
                    continue
                success, error, output_backend = parse_function_output(payload.get("output", ""))
                events.append(build_tool_event(pending, timestamp or pending.timestamp, success, error, output_backend))
                continue

            if payload_type == "custom_tool_call_output":
                pending = pending_calls.pop(payload.get("call_id", ""), None)
                if not pending:
                    continue
                success, error, output_backend = parse_custom_output(payload.get("output", ""))
                events.append(build_tool_event(pending, timestamp or pending.timestamp, success, error, output_backend))

    start_timestamp = session_start_ts or (events[0].timestamp if events else last_timestamp)
    if start_timestamp:
        events.insert(
            0,
            ToolEvent(
                timestamp=start_timestamp,
                session_id=session_id,
                agent=AGENT_CODEX,
                event_type=EVENT_SESSION_START,
                cwd=session_cwd,
            ),
        )

    for event in events:
        event.session_id = session_id

    if last_timestamp:
        events.append(
            ToolEvent(
                timestamp=last_timestamp,
                session_id=session_id,
                agent=AGENT_CODEX,
                event_type=EVENT_SESSION_END,
            )
        )

    return session_id, events


def write_events(events: list[ToolEvent], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(event.to_json())
            handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract shared-schema tool logs from Codex CLI session transcripts."
    )
    parser.add_argument("session", nargs="?", help="Path to a single Codex session .jsonl file")
    parser.add_argument("--dir", help="Extract all .jsonl sessions in a directory tree")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / ".codex" / "logs"),
        help="Directory for extracted per-session logs (default: .codex/logs)",
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
        return sorted(Path(args.dir).rglob("*.jsonl"))
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
