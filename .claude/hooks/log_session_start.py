#!/usr/bin/env python3
"""
Claude Code SessionStart hook — writes a session_start marker to the log.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.classify import normalize_path


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)
        session_id = data.get("session_id", "unknown")
        cwd = data.get("cwd", "")

        event = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_id": session_id,
            "agent": "claude",
            "event_type": "session_start",
        }
        if cwd:
            event["cwd"] = normalize_path(cwd)

        log_dir = PROJECT_ROOT / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"tool-use-{session_id}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    except Exception:
        pass


if __name__ == "__main__":
    main()
