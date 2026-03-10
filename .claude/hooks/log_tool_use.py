#!/usr/bin/env python3
"""
Claude Code PostToolUse hook — logs tool calls to a per-session JSONL file.

Runs async after every tool call. Zero token cost — output is silent.
Reads hook event JSON from stdin, classifies file paths, and appends
a structured event to .claude/logs/tool-use-{session_id}.jsonl.

Requires: Python 3.10+, no external dependencies.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so we can import shared modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.classify import classify_file, extract_filename, normalize_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_file_paths(tool_name: str, tool_input: dict) -> list[str]:
    """Extract file paths from tool input based on tool type."""
    paths = []
    if tool_name in ("Read", "Edit", "Write"):
        fp = tool_input.get("file_path", "")
        if fp:
            paths.append(fp)
    elif tool_name == "Grep":
        p = tool_input.get("path", "")
        if p:
            paths.append(p)
    elif tool_name == "Glob":
        p = tool_input.get("path", "")
        if p:
            paths.append(p)
    return paths


def _build_summary(tool_name: str, tool_input: dict, file_paths: list[str]) -> str:
    """Build a human-readable one-line summary of the tool call."""
    if tool_name in ("Read", "Edit", "Write") and file_paths:
        fname = extract_filename(file_paths[0])
        return f"{tool_name}({fname})"
    elif tool_name == "Bash":
        desc = tool_input.get("description", "")
        cmd = tool_input.get("command", "")
        label = desc or (cmd[:50] + "..." if len(cmd) > 50 else cmd)
        return f"Bash({label})"
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        truncated = pattern[:40] + "..." if len(pattern) > 40 else pattern
        return f"Grep({truncated})"
    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"Glob({pattern})"
    elif tool_name == "Agent":
        desc = tool_input.get("description", "")
        return f"Agent({desc})"
    elif tool_name == "Skill":
        skill = tool_input.get("skill", "")
        return f"Skill({skill})"
    else:
        return tool_name


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)

        session_id = data.get("session_id", "unknown")
        tool_name = data.get("tool_name", "unknown")
        tool_input = data.get("tool_input", {})
        agent_id = data.get("agent_id")
        cwd = data.get("cwd", "")

        file_paths = _extract_file_paths(tool_name, tool_input)
        file_classes = [classify_file(p) for p in file_paths]
        summary = _build_summary(tool_name, tool_input, file_paths)

        event = {
            "timestamp": _now_iso(),
            "session_id": session_id,
            "agent": "claude",
            "event_type": "tool_success",
            "tool_name": tool_name,
            "summary": summary,
            "status": "success",
        }

        # Only include non-empty optional fields
        if file_paths:
            event["file_paths"] = file_paths
            event["file_classes"] = file_classes
        if cwd:
            event["cwd"] = normalize_path(cwd)
        if agent_id:
            event["agent_id"] = agent_id

        # Write to per-session log file
        log_dir = PROJECT_ROOT / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"tool-use-{session_id}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    except Exception:
        # Silent failure — never interrupt the agent
        pass


if __name__ == "__main__":
    main()
