#!/usr/bin/env python3
"""
Analyze Codex CLI JSONL session transcripts for Memex vs Memory behavior.

Codex session logs differ from Claude Code transcripts: most repository access
appears through `shell_command` invocations, edits appear through `apply_patch`,
and assistant output is split across commentary/final phases. This script
extracts those events, classifies file access heuristically, and computes a
Memex-style score similar to the Claude analyzer.

Usage:
    python scripts/analyze_codex_session.py <session.jsonl>
    python scripts/analyze_codex_session.py <session.jsonl> --json
    python scripts/analyze_codex_session.py <session.jsonl> --csv
    python scripts/analyze_codex_session.py --dir <directory>
    python scripts/analyze_codex_session.py --dir <directory> --csv
"""

import argparse
import csv
import io
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# Shared classification — single source of truth
from scripts.classify import (
    classify_file,
    count_constitutional_terms,
    detect_tripwire_coverage,
    extract_filename,
    normalize_path,
    KNOWN_CROSS_REFS,
    TRIPWIRE_PATTERNS,
)

PATCH_HEADER_PATTERNS = [
    re.compile(r"^\*\*\* Add File: (.+)$", re.MULTILINE),
    re.compile(r"^\*\*\* Update File: (.+)$", re.MULTILINE),
    re.compile(r"^\*\*\* Delete File: (.+)$", re.MULTILINE),
]

TEXT_FILE_SUFFIXES = {
    ".md",
    ".py",
    ".html",
    ".txt",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".scss",
    ".sql",
    ".csv",
}


def is_likely_path(token: str) -> bool:
    cleaned = token.strip("\"'")
    lower = normalize_path(cleaned.lower())
    if not cleaned:
        return False
    if any(marker in lower for marker in ("/", "\\", ".md", ".py", ".html", ".json", ".toml")):
        return True
    if cleaned in {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md", "manage.py"}:
        return True
    return Path(cleaned).suffix.lower() in TEXT_FILE_SUFFIXES


def extract_powershell_path(segment: str) -> Optional[str]:
    tail = re.sub(r"^\s*(Get-Content|gc|type|cat)\b", "", segment, flags=re.IGNORECASE).strip()
    option_pattern = re.compile(
        r"^\s*-(Raw|First|TotalCount|Tail|Encoding|ReadCount|Wait)\b(?:\s+(\"[^\"]*\"|'[^']*'|\S+))?",
        re.IGNORECASE,
    )
    while True:
        match = option_pattern.match(tail)
        if not match:
            break
        tail = tail[match.end():].strip()

    if not tail:
        return None
    if tail[0] in "'\"":
        quote = tail[0]
        end = tail.find(quote, 1)
        return tail[1:end] if end > 0 else None
    return tail.split()[0]


def extract_list_path(segment: str) -> Optional[str]:
    tail = re.sub(r"^\s*(Get-ChildItem|dir|ls)\b", "", segment, flags=re.IGNORECASE).strip()
    option_pattern = re.compile(
        r"^\s*-(Force|Recurse|File|Directory|Hidden|Name|Filter|Path)\b(?:\s+(\"[^\"]*\"|'[^']*'|\S+))?",
        re.IGNORECASE,
    )
    last_path = None
    while True:
        match = option_pattern.match(tail)
        if not match:
            break
        value = match.group(2)
        if value and is_likely_path(value):
            last_path = value.strip("\"'")
        tail = tail[match.end():].strip()
    if tail and is_likely_path(tail.split()[0]):
        return tail.split()[0].strip("\"'")
    return last_path


def extract_search_paths(command: str) -> list[str]:
    tokens = re.findall(r'"[^"]+"|\'[^\']+\'|\S+', command)
    paths = []
    seen = set()
    for token in tokens:
        cleaned = token.strip("\"'")
        if cleaned.startswith("-"):
            continue
        if cleaned.lower() in {"rg", "select-string", "findstr", "where-object"}:
            continue
        if is_likely_path(cleaned):
            normed = normalize_path(cleaned)
            if normed not in seen:
                seen.add(normed)
                paths.append(cleaned)
    return paths


def classify_shell_command(command: str) -> tuple[str, list[str]]:
    segment = command.split("|", 1)[0].strip()
    lower = segment.lower()

    if re.match(r"^(get-content|gc|type|cat)\b", lower):
        path = extract_powershell_path(segment)
        return "read", [path] if path else []
    if re.match(r"^(rg|select-string|findstr)\b", lower):
        return "search", extract_search_paths(command)
    if re.match(r"^(get-childitem|dir|ls)\b", lower):
        path = extract_list_path(segment)
        return "list", [path] if path else []
    return "other", []


def extract_patch_paths(patch_text: str) -> list[str]:
    paths = []
    for pattern in PATCH_HEADER_PATTERNS:
        for match in pattern.findall(patch_text):
            paths.append(match.strip())
    return paths


@dataclass
class ToolCall:
    index: int
    timestamp: str
    tool_name: str
    action_kind: Optional[str] = None
    command: Optional[str] = None
    file_paths: list[str] = field(default_factory=list)
    file_classes: list[str] = field(default_factory=list)
    phase: Optional[str] = None

    @property
    def primary_path(self) -> Optional[str]:
        return self.file_paths[0] if self.file_paths else None

    @property
    def is_governance_read(self) -> bool:
        return self.action_kind == "read" and "governance" in self.file_classes

    @property
    def is_read(self) -> bool:
        return self.action_kind == "read"

    @property
    def is_search(self) -> bool:
        return self.action_kind == "search"

    @property
    def is_list(self) -> bool:
        return self.action_kind == "list"

    @property
    def is_edit(self) -> bool:
        return self.tool_name == "apply_patch"


@dataclass
class TrailHop:
    source_file: str
    target_file: str
    source_index: int
    target_index: int
    hops_between: int


@dataclass
class SessionAnalysis:
    session_file: str
    session_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_tool_calls: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    total_shell_commands: int = 0
    total_reads: int = 0
    total_searches: int = 0
    total_lists: int = 0
    total_other_shell: int = 0
    total_edits: int = 0
    total_plan_updates: int = 0
    governance_reads: int = 0
    flow_reads: int = 0
    experiment_reads: int = 0
    code_reads: int = 0
    governance_files_accessed: list[str] = field(default_factory=list)
    edited_files: list[str] = field(default_factory=list)
    governance_edit_files: int = 0
    code_edit_files: int = 0
    governance_read_before_code_edit: bool = False
    first_governance_read_index: Optional[int] = None
    first_code_edit_index: Optional[int] = None
    trails_detected: list[TrailHop] = field(default_factory=list)
    constitutional_term_counts: dict[str, int] = field(default_factory=dict)
    total_constitutional_terms: int = 0
    tripwires_addressed: list[str] = field(default_factory=list)
    tool_sequence: list[str] = field(default_factory=list)


def extract_tool_calls(jsonl_path: str) -> tuple[list[ToolCall], str, str]:
    calls: list[ToolCall] = []
    assistant_text: list[str] = []
    session_id = Path(jsonl_path).stem
    idx = 0

    with open(jsonl_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            record_type = obj.get("type")
            timestamp = obj.get("timestamp", "")

            if record_type == "session_meta":
                payload = obj.get("payload", {})
                session_id = payload.get("id", session_id)
                continue

            if record_type != "response_item":
                continue

            payload = obj.get("payload", {})
            payload_type = payload.get("type")

            if payload_type == "function_call":
                name = payload.get("name")
                if name == "shell_command":
                    tc = parse_shell_command(payload, idx, timestamp)
                elif name == "update_plan":
                    tc = ToolCall(index=idx, timestamp=timestamp, tool_name="update_plan")
                else:
                    tc = ToolCall(index=idx, timestamp=timestamp, tool_name=name or "unknown")
                calls.append(tc)
                idx += 1
            elif payload_type == "custom_tool_call":
                tc = parse_custom_tool_call(payload, idx, timestamp)
                calls.append(tc)
                idx += 1
            elif payload_type == "message" and payload.get("role") == "assistant":
                for block in payload.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "output_text":
                        assistant_text.append(block.get("text", ""))

    return calls, "\n".join(assistant_text), session_id


def parse_shell_command(payload: dict, idx: int, timestamp: str) -> ToolCall:
    args = payload.get("arguments", "{}")
    try:
        parsed = json.loads(args)
    except json.JSONDecodeError:
        parsed = {}

    command = parsed.get("command", "")
    action_kind, paths = classify_shell_command(command)
    file_classes = [classify_file(path) for path in paths]

    return ToolCall(
        index=idx,
        timestamp=timestamp,
        tool_name="shell_command",
        action_kind=action_kind,
        command=command,
        file_paths=paths,
        file_classes=file_classes,
    )


def parse_custom_tool_call(payload: dict, idx: int, timestamp: str) -> ToolCall:
    name = payload.get("name", "custom_tool_call")
    patch_text = payload.get("input", "")
    paths = extract_patch_paths(patch_text) if name == "apply_patch" else []
    file_classes = [classify_file(path) for path in paths]
    return ToolCall(
        index=idx,
        timestamp=timestamp,
        tool_name=name,
        action_kind="edit" if name == "apply_patch" else None,
        command=patch_text[:120] if patch_text else None,
        file_paths=paths,
        file_classes=file_classes,
    )


def detect_trails(calls: list[ToolCall]) -> list[TrailHop]:
    trails = []
    read_history: list[tuple[int, str]] = []
    for tc in calls:
        if not tc.is_read or not tc.primary_path:
            continue
        current = extract_filename(tc.primary_path)
        for prev_idx, prev_name in read_history:
            refs = KNOWN_CROSS_REFS.get(prev_name, [])
            if current in refs:
                trails.append(
                    TrailHop(
                        source_file=prev_name,
                        target_file=current,
                        source_index=prev_idx,
                        target_index=tc.index,
                        hops_between=tc.index - prev_idx - 1,
                    )
                )
        read_history.append((tc.index, current))
    return trails


def analyze_session(jsonl_path: str) -> SessionAnalysis:
    calls, assistant_text, session_id = extract_tool_calls(jsonl_path)
    analysis = SessionAnalysis(
        session_file=jsonl_path,
        session_id=session_id,
        total_tool_calls=len(calls),
        tool_calls=calls,
    )

    if calls:
        analysis.start_time = calls[0].timestamp
        analysis.end_time = calls[-1].timestamp

    governance_files = set()
    edited_files = set()

    for tc in calls:
        if tc.tool_name == "shell_command":
            analysis.total_shell_commands += 1
            if tc.action_kind == "read":
                analysis.total_reads += 1
                if tc.primary_path:
                    file_class = classify_file(tc.primary_path)
                    if file_class == "governance":
                        analysis.governance_reads += 1
                        governance_files.add(extract_filename(tc.primary_path))
                        if analysis.first_governance_read_index is None:
                            analysis.first_governance_read_index = tc.index
                    elif file_class == "flow":
                        analysis.flow_reads += 1
                    elif file_class == "experiment":
                        analysis.experiment_reads += 1
                    else:
                        analysis.code_reads += 1
            elif tc.action_kind == "search":
                analysis.total_searches += 1
            elif tc.action_kind == "list":
                analysis.total_lists += 1
            else:
                analysis.total_other_shell += 1
        elif tc.tool_name == "apply_patch":
            analysis.total_edits += 1
            if tc.file_paths and analysis.first_code_edit_index is None:
                analysis.first_code_edit_index = tc.index
            for path, file_class in zip(tc.file_paths, tc.file_classes):
                edited_files.add(normalize_path(path))
                if file_class == "governance":
                    analysis.governance_edit_files += 1
                else:
                    analysis.code_edit_files += 1
        elif tc.tool_name == "update_plan":
            analysis.total_plan_updates += 1

        analysis.tool_sequence.append(compact_tool_entry(tc))

    analysis.governance_files_accessed = sorted(governance_files)
    analysis.edited_files = sorted(edited_files)
    if (
        analysis.first_governance_read_index is not None
        and analysis.first_code_edit_index is not None
    ):
        analysis.governance_read_before_code_edit = (
            analysis.first_governance_read_index < analysis.first_code_edit_index
        )

    analysis.trails_detected = detect_trails(calls)
    analysis.constitutional_term_counts = count_constitutional_terms(assistant_text)
    analysis.total_constitutional_terms = sum(analysis.constitutional_term_counts.values())
    analysis.tripwires_addressed = detect_tripwire_coverage(assistant_text)
    return analysis


def compact_tool_entry(tc: ToolCall) -> str:
    if tc.tool_name == "shell_command":
        if tc.primary_path:
            return f"shell:{tc.action_kind}({extract_filename(tc.primary_path)})"
        if tc.command:
            snippet = tc.command.replace("\n", " ")[:40]
            return f"shell:{tc.action_kind}({snippet})"
        return f"shell:{tc.action_kind}"
    if tc.tool_name == "apply_patch":
        if tc.file_paths:
            files = ", ".join(extract_filename(path) for path in tc.file_paths[:3])
            return f"apply_patch({files})"
        return "apply_patch"
    return tc.tool_name


def compute_memex_score(a: SessionAnalysis) -> tuple[float, dict[str, float]]:
    breakdown = {}
    score = 0.0

    gov_pts = min(a.governance_reads / 3, 1.0) * 2
    breakdown["Governance docs read (max 2)"] = gov_pts
    score += gov_pts

    preemptive_pts = 2.0 if a.governance_read_before_code_edit else 0.0
    breakdown["Preemptive governance read (max 2)"] = preemptive_pts
    score += preemptive_pts

    trail_pts = min(len(a.trails_detected) / 2, 1.0) * 2
    breakdown["Trail following detected (max 2)"] = trail_pts
    score += trail_pts

    tripwire_pts = (len(a.tripwires_addressed) / len(TRIPWIRE_PATTERNS)) * 2
    breakdown["Tripwire coverage (max 2)"] = tripwire_pts
    score += tripwire_pts

    term_pts = min(a.total_constitutional_terms / 10, 1.0) * 2
    breakdown["Constitutional terminology (max 2)"] = term_pts
    score += term_pts

    return min(score, 10.0), breakdown


def format_report(a: SessionAnalysis) -> str:
    score, breakdown = compute_memex_score(a)
    lines = []
    sep = "=" * 72
    lines.append(sep)
    lines.append(f"CODEX SESSION ANALYSIS: {a.session_id}")
    lines.append(sep)
    lines.append(f"File:       {a.session_file}")
    lines.append(f"Time range: {a.start_time or 'N/A'} -> {a.end_time or 'N/A'}")
    lines.append(f"Total tool calls: {a.total_tool_calls}")
    lines.append("")
    lines.append("TOOL CALL BREAKDOWN")
    lines.append("-" * 40)
    lines.append(f"  Shell commands: {a.total_shell_commands:4d}")
    lines.append(f"  Patch edits:    {a.total_edits:4d}")
    lines.append(f"  Plan updates:   {a.total_plan_updates:4d}")
    lines.append("")
    lines.append("SHELL COMMAND BREAKDOWN")
    lines.append("-" * 40)
    lines.append(
        f"  Reads:          {a.total_reads:4d}  "
        f"(governance: {a.governance_reads}, flow: {a.flow_reads}, experiment: {a.experiment_reads}, code: {a.code_reads})"
    )
    lines.append(f"  Searches:       {a.total_searches:4d}")
    lines.append(f"  Listings:       {a.total_lists:4d}")
    lines.append(f"  Other shell:    {a.total_other_shell:4d}")
    lines.append("")
    lines.append("MEMEX BEHAVIOR INDICATORS")
    lines.append("-" * 40)
    gov_ratio = a.governance_reads / max(a.total_reads, 1)
    lines.append(f"  Governance read ratio:          {gov_ratio:.1%} ({a.governance_reads}/{a.total_reads})")
    lines.append(
        f"  First governance read at:       "
        f"{'#' + str(a.first_governance_read_index) if a.first_governance_read_index is not None else 'NEVER'}"
    )
    lines.append(
        f"  First patch edit at:            "
        f"{'#' + str(a.first_code_edit_index) if a.first_code_edit_index is not None else 'NEVER'}"
    )
    lines.append(
        f"  Governance read before edit:    {'YES' if a.governance_read_before_code_edit else 'NO'}"
    )
    lines.append(f"  Governance files accessed:      {len(a.governance_files_accessed)}")
    for path in a.governance_files_accessed:
        lines.append(f"    - {path}")
    lines.append("")
    lines.append("ASSOCIATIVE TRAIL FOLLOWING")
    lines.append("-" * 40)
    lines.append(f"  Trails detected: {len(a.trails_detected)}")
    for trail in a.trails_detected:
        lines.append(
            f"    #{trail.source_index} {trail.source_file} -> "
            f"#{trail.target_index} {trail.target_file} ({trail.hops_between} calls between)"
        )
    lines.append("")
    lines.append("TRIPWIRE COVERAGE")
    lines.append("-" * 40)
    for tripwire in TRIPWIRE_PATTERNS:
        status = "ADDRESSED" if tripwire in a.tripwires_addressed else "not found"
        lines.append(f"  [{status:>11s}] {tripwire}")
    lines.append(f"  Coverage: {len(a.tripwires_addressed)}/{len(TRIPWIRE_PATTERNS)}")
    lines.append("")
    lines.append("CONSTITUTIONAL TERMINOLOGY IN RESPONSES")
    lines.append("-" * 40)
    lines.append(f"  Total constitutional terms used: {a.total_constitutional_terms}")
    for term, count in sorted(a.constitutional_term_counts.items(), key=lambda item: -item[1]):
        lines.append(f"    {term}: {count}")
    lines.append("")
    lines.append("PATCHED FILES")
    lines.append("-" * 40)
    lines.append(f"  Governance edit files: {a.governance_edit_files}")
    lines.append(f"  Code edit files:       {a.code_edit_files}")
    for path in a.edited_files:
        lines.append(f"    - {path}")
    lines.append("")
    lines.append("TOOL CALL SEQUENCE (compact)")
    lines.append("-" * 40)
    for i, entry in enumerate(a.tool_sequence):
        lines.append(f"  {i:3d}. {entry}")
    lines.append("")
    lines.append("MEMEX SCORE (heuristic)")
    lines.append("-" * 40)
    for component, value in breakdown.items():
        lines.append(f"  {component:40s} {value:+.1f}")
    lines.append(f"  {'TOTAL':40s} {score:.1f} / 10.0")
    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


def format_json(a: SessionAnalysis) -> str:
    score, breakdown = compute_memex_score(a)
    output = {
        "session_id": a.session_id,
        "session_file": a.session_file,
        "time_range": {"start": a.start_time, "end": a.end_time},
        "tool_call_summary": {
            "total": a.total_tool_calls,
            "shell_commands": a.total_shell_commands,
            "patch_edits": a.total_edits,
            "plan_updates": a.total_plan_updates,
            "reads": {
                "total": a.total_reads,
                "governance": a.governance_reads,
                "flow": a.flow_reads,
                "experiment": a.experiment_reads,
                "code": a.code_reads,
            },
            "searches": a.total_searches,
            "listings": a.total_lists,
            "other_shell": a.total_other_shell,
        },
        "memex_indicators": {
            "governance_read_ratio": a.governance_reads / max(a.total_reads, 1),
            "governance_read_before_code_edit": a.governance_read_before_code_edit,
            "first_governance_read_index": a.first_governance_read_index,
            "first_code_edit_index": a.first_code_edit_index,
            "governance_files_accessed": a.governance_files_accessed,
        },
        "trails": [asdict(trail) for trail in a.trails_detected],
        "tripwire_coverage": {
            "addressed": a.tripwires_addressed,
            "total_possible": len(TRIPWIRE_PATTERNS),
            "coverage_ratio": len(a.tripwires_addressed) / len(TRIPWIRE_PATTERNS),
        },
        "constitutional_terminology": {
            "total_uses": a.total_constitutional_terms,
            "by_term": a.constitutional_term_counts,
        },
        "edited_files": {
            "all": a.edited_files,
            "governance_file_count": a.governance_edit_files,
            "code_file_count": a.code_edit_files,
        },
        "memex_score": {
            "total": score,
            "breakdown": breakdown,
        },
        "tool_sequence": a.tool_sequence,
    }
    return json.dumps(output, indent=2)


def format_csv_row(a: SessionAnalysis) -> dict[str, object]:
    score, _ = compute_memex_score(a)
    return {
        "session_id": a.session_id,
        "start_time": a.start_time or "",
        "end_time": a.end_time or "",
        "total_tool_calls": a.total_tool_calls,
        "shell_commands": a.total_shell_commands,
        "patch_edits": a.total_edits,
        "plan_updates": a.total_plan_updates,
        "total_reads": a.total_reads,
        "governance_reads": a.governance_reads,
        "flow_reads": a.flow_reads,
        "experiment_reads": a.experiment_reads,
        "code_reads": a.code_reads,
        "total_searches": a.total_searches,
        "total_lists": a.total_lists,
        "total_other_shell": a.total_other_shell,
        "governance_files_accessed": len(a.governance_files_accessed),
        "governance_read_before_code_edit": a.governance_read_before_code_edit,
        "first_governance_read_index": a.first_governance_read_index if a.first_governance_read_index is not None else "",
        "first_code_edit_index": a.first_code_edit_index if a.first_code_edit_index is not None else "",
        "trails_detected": len(a.trails_detected),
        "tripwires_addressed": len(a.tripwires_addressed),
        "tripwire_list": "; ".join(a.tripwires_addressed),
        "constitutional_terms_total": a.total_constitutional_terms,
        "governance_edit_files": a.governance_edit_files,
        "code_edit_files": a.code_edit_files,
        "memex_score": f"{score:.1f}",
    }


CSV_FIELDS = [
    "session_id",
    "start_time",
    "end_time",
    "total_tool_calls",
    "shell_commands",
    "patch_edits",
    "plan_updates",
    "total_reads",
    "governance_reads",
    "flow_reads",
    "experiment_reads",
    "code_reads",
    "total_searches",
    "total_lists",
    "total_other_shell",
    "governance_files_accessed",
    "governance_read_before_code_edit",
    "first_governance_read_index",
    "first_code_edit_index",
    "trails_detected",
    "tripwires_addressed",
    "tripwire_list",
    "constitutional_terms_total",
    "governance_edit_files",
    "code_edit_files",
    "memex_score",
]


def main() -> None:
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Analyze Codex CLI session transcripts for Memex vs Memory behavior."
    )
    parser.add_argument("session", nargs="?", help="Path to a single Codex .jsonl session file")
    parser.add_argument("--dir", help="Analyze all .jsonl files in a directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    args = parser.parse_args()

    if not args.session and not args.dir:
        parser.print_help()
        sys.exit(1)

    if args.dir:
        files = sorted(Path(args.dir).glob("*.jsonl"))
        if not files:
            print(f"No .jsonl files found in {args.dir}", file=sys.stderr)
            sys.exit(1)
    else:
        files = [Path(args.session)]

    analyses = []
    for fp in files:
        try:
            analyses.append(analyze_session(str(fp)))
        except Exception as exc:
            print(f"Error analyzing {fp}: {exc}", file=sys.stderr)

    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for analysis in analyses:
            writer.writerow(format_csv_row(analysis))
        return

    if args.json:
        if len(analyses) == 1:
            print(format_json(analyses[0]))
        else:
            print(json.dumps([json.loads(format_json(analysis)) for analysis in analyses], indent=2))
        return

    for analysis in analyses:
        print(format_report(analysis))


if __name__ == "__main__":
    main()
