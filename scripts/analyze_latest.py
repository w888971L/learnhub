#!/usr/bin/env python3
"""
Analyze the most recent session for any agent.

Finds the latest session transcript/log, extracts if needed (Codex/Gemini),
runs the analyzer, and optionally saves output to a configurable location.

Usage:
    python scripts/analyze_latest.py --agent claude
    python scripts/analyze_latest.py --agent codex
    python scripts/analyze_latest.py --agent gemini
    python scripts/analyze_latest.py --agent all
    python scripts/analyze_latest.py --agent claude --output-folder C:\\tmp --suffix test-a-b
    python scripts/analyze_latest.py --agent all --json --output-folder C:\\tmp --suffix round-1
"""

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Agent-specific discovery
# ---------------------------------------------------------------------------

CLAUDE_LOG_DIR = PROJECT_ROOT / ".claude" / "logs"

CODEX_SESSION_BASE = Path.home() / ".codex" / "sessions"
CODEX_LOG_DIR = PROJECT_ROOT / ".codex" / "logs"

GEMINI_CHATS_BASE = Path.home() / ".gemini" / "tmp"
GEMINI_LOG_DIR = PROJECT_ROOT / ".gemini" / "logs"


def find_latest_claude_log() -> Path | None:
    """Find the most recent Claude tool-use log."""
    if not CLAUDE_LOG_DIR.exists():
        return None
    logs = sorted(CLAUDE_LOG_DIR.glob("tool-use-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def find_latest_codex_session() -> Path | None:
    """Find the most recent Codex session transcript."""
    if not CODEX_SESSION_BASE.exists():
        return None
    sessions = sorted(CODEX_SESSION_BASE.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return sessions[-1] if sessions else None


def find_latest_gemini_session(project: str | None = None) -> Path | None:
    """Find the most recent Gemini session transcript for a project."""
    project_names = [project] if project else ["learnhub", "learnhub2"]
    latest = None
    for project_name in project_names:
        chats_dir = GEMINI_CHATS_BASE / project_name / "chats"
        if chats_dir.exists():
            sessions = sorted(chats_dir.glob("session-*.json"), key=lambda p: p.stat().st_mtime)
            if sessions and (latest is None or sessions[-1].stat().st_mtime > latest.stat().st_mtime):
                latest = sessions[-1]
    return latest


def extract_codex(session_path: Path) -> Path | None:
    """Extract a Codex session and return the output log path."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_codex_log.py"), str(session_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"Codex extraction failed: {result.stderr}", file=sys.stderr)
        return None
    print(result.stdout.strip(), file=sys.stderr)

    # Find the extracted log
    session_id = session_path.stem
    # Codex session files have format: rollout-DATE-SESSION_ID
    # The extractor uses the session_id from inside the file
    logs = sorted(CODEX_LOG_DIR.glob("tool-use-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def extract_gemini(session_path: Path) -> Path | None:
    """Extract a Gemini session and return the output log path."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_gemini_log.py"), str(session_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"Gemini extraction failed: {result.stderr}", file=sys.stderr)
        return None
    print(result.stdout.strip(), file=sys.stderr)

    logs = sorted(GEMINI_LOG_DIR.glob("tool-use-*.jsonl"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def run_analysis(log_path: Path, output_json: bool = False) -> dict | str | None:
    """Run analyze_session.py --tool-log on a log file."""
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "analyze_session.py"),
           "--tool-log", str(log_path)]
    if output_json:
        cmd.append("--json")

    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"Analysis failed: {result.stderr}", file=sys.stderr)
        return None

    if output_json:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout
    return result.stdout


def process_agent(agent: str, output_json: bool = False,
                   project: str | None = None) -> tuple[str, str | dict | None]:
    """Process a single agent: find, extract if needed, analyze. Returns (agent, result)."""
    log_path = None

    if agent == "claude":
        log_path = find_latest_claude_log()
        if not log_path:
            return agent, "No Claude logs found in .claude/logs/"

    elif agent == "codex":
        session = find_latest_codex_session()
        if not session:
            return agent, "No Codex sessions found in ~/.codex/sessions/"
        print(f"Extracting Codex session: {session.name}", file=sys.stderr)
        log_path = extract_codex(session)
        if not log_path:
            return agent, "Codex extraction failed"

    elif agent == "gemini":
        session = find_latest_gemini_session(project=project)
        if not session:
            target = project or "any project"
            return agent, f"No Gemini sessions found for {target} in ~/.gemini/tmp/*/chats/"
        print(f"Extracting Gemini session: {session.name}", file=sys.stderr)
        log_path = extract_gemini(session)
        if not log_path:
            return agent, "Gemini extraction failed"

    print(f"Analyzing: {log_path.name}", file=sys.stderr)
    result = run_analysis(log_path, output_json=output_json)
    return agent, result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_output(agent: str, content: str | dict, output_folder: Path, suffix: str,
                output_json: bool) -> Path:
    """Save analysis output to a file."""
    output_folder.mkdir(parents=True, exist_ok=True)

    ext = "json" if output_json else "txt"
    parts = [agent]
    if suffix:
        parts.append(suffix)
    filename = f"analysis-{'-'.join(parts)}.{ext}"
    output_path = output_folder / filename

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        if isinstance(content, dict):
            json.dump(content, f, indent=2)
        else:
            f.write(content)

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Analyze the most recent session for any agent."
    )
    parser.add_argument("--agent", required=True,
                        choices=["claude", "codex", "gemini", "all"],
                        help="Which agent's latest session to analyze")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of text")
    parser.add_argument("--output-folder",
                        help="Save output to this folder instead of printing")
    parser.add_argument("--suffix",
                        help="Suffix for output filename (e.g., 'test-a-b', 'round-1')")
    parser.add_argument("--project",
                        help="Project name for Gemini session lookup (e.g., 'learnhub2')")
    args = parser.parse_args()

    agents = ["claude", "codex", "gemini"] if args.agent == "all" else [args.agent]

    results = {}
    for agent in agents:
        agent_name, result = process_agent(agent, output_json=args.json,
                                           project=args.project)
        results[agent_name] = result

    # Output
    for agent, result in results.items():
        if result is None:
            print(f"\n[{agent}] Analysis returned no results.", file=sys.stderr)
            continue

        if args.output_folder:
            output_path = save_output(
                agent, result,
                Path(args.output_folder),
                args.suffix or "",
                args.json,
            )
            print(f"[{agent}] Saved to: {output_path}", file=sys.stderr)
        else:
            if isinstance(result, dict):
                print(json.dumps(result, indent=2))
            else:
                print(result)


if __name__ == "__main__":
    main()
