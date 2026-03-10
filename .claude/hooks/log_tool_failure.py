#!/usr/bin/env python3
"""
Claude Code PostToolUseFailure hook — logs failed tool calls.

Same structure as log_tool_use.py but records event_type as 'tool_failure'
and captures the error from tool_response.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.classify import classify_file, extract_filename, normalize_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_file_paths(tool_name: str, tool_input: dict) -> list[str]:
    paths = []
    if tool_name in ("Read", "Edit", "Write"):
        fp = tool_input.get("file_path", "")
        if fp:
            paths.append(fp)
    elif tool_name in ("Grep", "Glob"):
        p = tool_input.get("path", "")
        if p:
            paths.append(p)
    return paths


def _build_summary(tool_name: str, tool_input: dict, file_paths: list[str]) -> str:
    if tool_name in ("Read", "Edit", "Write") and file_paths:
        fname = extract_filename(file_paths[0])
        return f"{tool_name}({fname}) FAILED"
    elif tool_name == "Bash":
        desc = tool_input.get("description", "")
        cmd = tool_input.get("command", "")
        label = desc or (cmd[:50] + "..." if len(cmd) > 50 else cmd)
        return f"Bash({label}) FAILED"
    else:
        return f"{tool_name} FAILED"


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)

        session_id = data.get("session_id", "unknown")
        tool_name = data.get("tool_name", "unknown")
        tool_input = data.get("tool_input", {})
        tool_response = data.get("tool_response", {})
        agent_id = data.get("agent_id")
        cwd = data.get("cwd", "")

        # Extract error from response
        error_msg = ""
        if isinstance(tool_response, dict):
            error_msg = tool_response.get("stderr", "") or tool_response.get("error", "") or str(tool_response)[:200]
        elif isinstance(tool_response, str):
            error_msg = tool_response[:200]

        file_paths = _extract_file_paths(tool_name, tool_input)
        file_classes = [classify_file(p) for p in file_paths]
        summary = _build_summary(tool_name, tool_input, file_paths)

        event = {
            "timestamp": _now_iso(),
            "session_id": session_id,
            "agent": "claude",
            "event_type": "tool_failure",
            "tool_name": tool_name,
            "summary": summary,
            "status": "failure",
        }

        if error_msg:
            event["error"] = error_msg
        if file_paths:
            event["file_paths"] = file_paths
            event["file_classes"] = file_classes
        if cwd:
            event["cwd"] = normalize_path(cwd)
        if agent_id:
            event["agent_id"] = agent_id

        log_dir = PROJECT_ROOT / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"tool-use-{session_id}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    except Exception:
        pass


if __name__ == "__main__":
    main()
