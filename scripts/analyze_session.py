#!/usr/bin/env python3
"""
Analyze Claude Code JSONL session transcripts for Memex vs Memory behavior.
Detects governance doc usage, associative trail-following, tripwire coverage,
and constitutional terminology to score sessions on a Memex (0-10) scale.

Extracts tool call sequences, classifies file accesses as governance vs code,
detects associative trail-following, and produces a structured report.

Usage:
    python scripts/analyze_session.py <session.jsonl>
    python scripts/analyze_session.py <session.jsonl> --json
    python scripts/analyze_session.py <session.jsonl> --csv
    python scripts/analyze_session.py --dir <directory>        # analyze all .jsonl files
    python scripts/analyze_session.py --dir <directory> --csv  # CSV summary across sessions
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from io import StringIO
from pathlib import Path, PurePosixPath, PureWindowsPath
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


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    """A single tool invocation."""
    index: int
    timestamp: str
    tool_name: str
    file_path: Optional[str] = None
    file_class: Optional[str] = None  # governance | flow | experiment | code
    description: Optional[str] = None
    grep_pattern: Optional[str] = None
    glob_pattern: Optional[str] = None
    agent_description: Optional[str] = None
    agent_type: Optional[str] = None
    caller_type: str = "direct"  # direct | subagent

    @property
    def is_file_access(self) -> bool:
        return self.tool_name in ("Read", "Edit", "Write", "Grep", "Glob")

    @property
    def is_governance_access(self) -> bool:
        return self.file_class == "governance"

    @property
    def is_read(self) -> bool:
        return self.tool_name == "Read"

    @property
    def is_search(self) -> bool:
        return self.tool_name in ("Grep", "Glob")


@dataclass
class TrailHop:
    """A detected associative trail: file A was read, then file B was read,
    where A is known to reference B."""
    source_file: str
    target_file: str
    source_index: int
    target_index: int
    hops_between: int  # number of tool calls between source and target reads


@dataclass
class SessionAnalysis:
    """Complete analysis of a single session."""
    session_file: str
    session_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_tool_calls: int = 0
    tool_calls: list = field(default_factory=list)

    # Counts by category
    governance_reads: int = 0
    code_reads: int = 0
    flow_reads: int = 0
    governance_edits: int = 0
    code_edits: int = 0
    total_reads: int = 0
    total_edits: int = 0
    total_searches: int = 0
    total_bash: int = 0
    total_agents: int = 0

    # Governance-specific
    governance_files_accessed: list = field(default_factory=list)
    governance_read_before_code_edit: bool = False
    first_governance_read_index: Optional[int] = None
    first_code_edit_index: Optional[int] = None

    # Trail detection
    trails_detected: list = field(default_factory=list)

    # Constitutional terminology in assistant messages
    constitutional_term_counts: dict = field(default_factory=dict)
    total_constitutional_terms: int = 0

    # Tool sequence (compact)
    tool_sequence: list = field(default_factory=list)

    # Tripwire coverage
    tripwires_addressed: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_tool_calls(jsonl_path: str) -> tuple[list[ToolCall], str]:
    """Parse a JSONL session file and extract all tool calls in order."""
    calls = []
    assistant_text = []
    idx = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            record_type = obj.get("type")

            # Extract tool calls from assistant messages
            if record_type == "assistant" and "message" in obj:
                ts = obj.get("timestamp", "")
                msg = obj["message"]
                for block in msg.get("content", []):
                    if isinstance(block, dict):
                        if block.get("type") == "tool_use":
                            tc = _parse_tool_block(block, idx, ts)
                            calls.append(tc)
                            idx += 1
                        elif block.get("type") == "text":
                            assistant_text.append(block.get("text", ""))
                    elif isinstance(block, str):
                        assistant_text.append(block)

    return calls, "\n".join(assistant_text)


def _parse_tool_block(block: dict, idx: int, timestamp: str) -> ToolCall:
    """Parse a single tool_use block into a ToolCall."""
    name = block.get("name", "unknown")
    inp = block.get("input", {})
    caller = block.get("caller", {})
    caller_type = caller.get("type", "direct")

    tc = ToolCall(
        index=idx,
        timestamp=timestamp,
        tool_name=name,
        caller_type=caller_type,
    )

    # Extract file path based on tool type
    if name in ("Read", "Edit", "Write"):
        fp = inp.get("file_path", "")
        tc.file_path = fp
        tc.file_class = classify_file(fp) if fp else None
    elif name == "Grep":
        tc.grep_pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        glob = inp.get("glob", "")
        tc.file_path = path if path else None
        tc.glob_pattern = glob
        if path:
            tc.file_class = classify_file(path)
    elif name == "Glob":
        tc.glob_pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        tc.file_path = path if path else None
        if path:
            tc.file_class = classify_file(path)
    elif name == "Bash":
        tc.description = inp.get("description", "")
        cmd = inp.get("command", "")
        tc.description = tc.description or cmd[:80]
    elif name == "Agent":
        tc.agent_description = inp.get("description", "")
        tc.agent_type = inp.get("subagent_type", "general-purpose")

    return tc


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def detect_trails(calls: list[ToolCall]) -> list[TrailHop]:
    """Detect associative trail-following: read file A, then read file B,
    where A is known to cross-reference B."""
    trails = []
    read_history = []  # (index, filename)

    for tc in calls:
        if tc.is_read and tc.file_path:
            fname = extract_filename(tc.file_path)
            # Check if any previously-read file cross-references this one
            for prev_idx, prev_fname in read_history:
                refs = KNOWN_CROSS_REFS.get(prev_fname, [])
                if fname in refs:
                    trails.append(TrailHop(
                        source_file=prev_fname,
                        target_file=fname,
                        source_index=prev_idx,
                        target_index=tc.index,
                        hops_between=tc.index - prev_idx - 1,
                    ))
            read_history.append((tc.index, fname))

    return trails


def analyze_session(jsonl_path: str) -> SessionAnalysis:
    """Perform full analysis of a session transcript."""
    calls, assistant_text = extract_tool_calls(jsonl_path)

    session_id = Path(jsonl_path).stem
    analysis = SessionAnalysis(
        session_file=jsonl_path,
        session_id=session_id,
        total_tool_calls=len(calls),
        tool_calls=calls,
    )

    if calls:
        analysis.start_time = calls[0].timestamp
        analysis.end_time = calls[-1].timestamp

    gov_files_seen = set()

    for tc in calls:
        # Build compact sequence
        seq_entry = tc.tool_name
        if tc.file_path:
            seq_entry += f"({extract_filename(tc.file_path)})"
        elif tc.agent_description:
            seq_entry += f"({tc.agent_description})"
        elif tc.description:
            seq_entry += f"({tc.description[:40]})"
        analysis.tool_sequence.append(seq_entry)

        # Count by type
        if tc.tool_name == "Read":
            analysis.total_reads += 1
            if tc.file_class == "governance":
                analysis.governance_reads += 1
                if analysis.first_governance_read_index is None:
                    analysis.first_governance_read_index = tc.index
                gov_files_seen.add(extract_filename(tc.file_path))
            elif tc.file_class == "flow":
                analysis.flow_reads += 1
            else:
                analysis.code_reads += 1
        elif tc.tool_name == "Edit":
            analysis.total_edits += 1
            if tc.file_class == "governance":
                analysis.governance_edits += 1
            else:
                analysis.code_edits += 1
                if analysis.first_code_edit_index is None:
                    analysis.first_code_edit_index = tc.index
        elif tc.tool_name in ("Grep", "Glob"):
            analysis.total_searches += 1
        elif tc.tool_name == "Bash":
            analysis.total_bash += 1
        elif tc.tool_name == "Agent":
            analysis.total_agents += 1

    analysis.governance_files_accessed = sorted(gov_files_seen)

    # Did governance reads happen before first code edit?
    if (analysis.first_governance_read_index is not None
            and analysis.first_code_edit_index is not None):
        analysis.governance_read_before_code_edit = (
            analysis.first_governance_read_index < analysis.first_code_edit_index
        )

    # Trail detection
    analysis.trails_detected = detect_trails(calls)

    # Constitutional terminology
    term_counts = count_constitutional_terms(assistant_text)
    analysis.constitutional_term_counts = term_counts
    analysis.total_constitutional_terms = sum(term_counts.values())

    # Tripwire coverage
    analysis.tripwires_addressed = detect_tripwire_coverage(assistant_text)

    return analysis


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_report(a: SessionAnalysis) -> str:
    """Format a human-readable report."""
    lines = []
    sep = "=" * 72

    lines.append(sep)
    lines.append(f"SESSION ANALYSIS: {a.session_id}")
    lines.append(sep)
    lines.append(f"File:       {a.session_file}")
    lines.append(f"Time range: {a.start_time or 'N/A'} → {a.end_time or 'N/A'}")
    lines.append(f"Total tool calls: {a.total_tool_calls}")
    lines.append("")

    # --- Tool call breakdown ---
    lines.append("TOOL CALL BREAKDOWN")
    lines.append("-" * 40)
    lines.append(f"  Reads:       {a.total_reads:4d}  (governance: {a.governance_reads}, flow: {a.flow_reads}, code: {a.code_reads})")
    lines.append(f"  Edits:       {a.total_edits:4d}  (governance: {a.governance_edits}, code: {a.code_edits})")
    lines.append(f"  Searches:    {a.total_searches:4d}")
    lines.append(f"  Bash:        {a.total_bash:4d}")
    lines.append(f"  Agents:      {a.total_agents:4d}")
    lines.append("")

    # --- Memex indicators ---
    lines.append("MEMEX BEHAVIOR INDICATORS")
    lines.append("-" * 40)

    gov_ratio = a.governance_reads / max(a.total_reads, 1)
    lines.append(f"  Governance read ratio:          {gov_ratio:.1%} ({a.governance_reads}/{a.total_reads})")

    if a.first_governance_read_index is not None:
        lines.append(f"  First governance read at:       tool call #{a.first_governance_read_index}")
    else:
        lines.append(f"  First governance read at:       NEVER")

    if a.first_code_edit_index is not None:
        lines.append(f"  First code edit at:             tool call #{a.first_code_edit_index}")
    else:
        lines.append(f"  First code edit at:             NEVER")

    preemptive = "YES" if a.governance_read_before_code_edit else "NO"
    lines.append(f"  Governance read before edit:     {preemptive}")
    lines.append(f"  Governance files accessed:       {len(a.governance_files_accessed)}")
    for gf in a.governance_files_accessed:
        lines.append(f"    - {gf}")
    lines.append("")

    # --- Trail following ---
    lines.append("ASSOCIATIVE TRAIL FOLLOWING")
    lines.append("-" * 40)
    lines.append(f"  Trails detected: {len(a.trails_detected)}")
    for trail in a.trails_detected:
        lines.append(f"    #{trail.source_index} {trail.source_file} → #{trail.target_index} {trail.target_file} ({trail.hops_between} calls between)")
    lines.append("")

    # --- Tripwire coverage ---
    lines.append("TRIPWIRE COVERAGE")
    lines.append("-" * 40)
    all_tripwires = list(TRIPWIRE_PATTERNS.keys())
    for tw in all_tripwires:
        status = "ADDRESSED" if tw in a.tripwires_addressed else "not found"
        lines.append(f"  [{status:>11s}] {tw}")
    lines.append(f"  Coverage: {len(a.tripwires_addressed)}/{len(all_tripwires)}")
    lines.append("")

    # --- Constitutional terminology ---
    lines.append("CONSTITUTIONAL TERMINOLOGY IN RESPONSES")
    lines.append("-" * 40)
    lines.append(f"  Total constitutional terms used: {a.total_constitutional_terms}")
    if a.constitutional_term_counts:
        for term, count in sorted(a.constitutional_term_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {term}: {count}")
    lines.append("")

    # --- Compact tool sequence ---
    lines.append("TOOL CALL SEQUENCE (compact)")
    lines.append("-" * 40)
    for i, entry in enumerate(a.tool_sequence):
        lines.append(f"  {i:3d}. {entry}")
    lines.append("")

    # --- Memex score ---
    lines.append("MEMEX SCORE (heuristic)")
    lines.append("-" * 40)
    score, breakdown = compute_memex_score(a)
    for component, value in breakdown.items():
        lines.append(f"  {component:40s} {value:+.1f}")
    lines.append(f"  {'TOTAL':40s} {score:.1f} / 10.0")
    lines.append("")

    lines.append(sep)
    return "\n".join(lines)


def compute_memex_score(a: SessionAnalysis) -> tuple[float, dict]:
    """Compute a 0-10 heuristic score for Memex behavior.
    Higher = more Memex-like, lower = more Memory-like."""
    breakdown = {}
    score = 0.0

    # 1. Governance reads exist (0-2 points)
    gov_pts = min(a.governance_reads / 3, 1.0) * 2
    breakdown["Governance docs read (max 2)"] = gov_pts
    score += gov_pts

    # 2. Governance read before code edit (0 or 2 points)
    preemptive_pts = 2.0 if a.governance_read_before_code_edit else 0.0
    breakdown["Preemptive governance read (max 2)"] = preemptive_pts
    score += preemptive_pts

    # 3. Trail following detected (0-2 points)
    trail_pts = min(len(a.trails_detected) / 2, 1.0) * 2
    breakdown["Trail following detected (max 2)"] = trail_pts
    score += trail_pts

    # 4. Tripwire coverage (0-2 points)
    tw_pts = (len(a.tripwires_addressed) / len(TRIPWIRE_PATTERNS)) * 2
    breakdown["Tripwire coverage (max 2)"] = tw_pts
    score += tw_pts

    # 5. Constitutional terminology (0-2 points)
    term_pts = min(a.total_constitutional_terms / 10, 1.0) * 2
    breakdown["Constitutional terminology (max 2)"] = term_pts
    score += term_pts

    return min(score, 10.0), breakdown


def format_json(a: SessionAnalysis) -> str:
    """Format as JSON for programmatic consumption."""
    score, breakdown = compute_memex_score(a)
    output = {
        "session_id": a.session_id,
        "session_file": a.session_file,
        "time_range": {"start": a.start_time, "end": a.end_time},
        "tool_call_summary": {
            "total": a.total_tool_calls,
            "reads": {"total": a.total_reads, "governance": a.governance_reads, "flow": a.flow_reads, "code": a.code_reads},
            "edits": {"total": a.total_edits, "governance": a.governance_edits, "code": a.code_edits},
            "searches": a.total_searches,
            "bash": a.total_bash,
            "agents": a.total_agents,
        },
        "memex_indicators": {
            "governance_read_ratio": a.governance_reads / max(a.total_reads, 1),
            "governance_read_before_code_edit": a.governance_read_before_code_edit,
            "first_governance_read_index": a.first_governance_read_index,
            "first_code_edit_index": a.first_code_edit_index,
            "governance_files_accessed": a.governance_files_accessed,
        },
        "trails": [
            {
                "source": t.source_file,
                "target": t.target_file,
                "source_index": t.source_index,
                "target_index": t.target_index,
                "hops_between": t.hops_between,
            }
            for t in a.trails_detected
        ],
        "tripwire_coverage": {
            "addressed": a.tripwires_addressed,
            "total_possible": len(TRIPWIRE_PATTERNS),
            "coverage_ratio": len(a.tripwires_addressed) / len(TRIPWIRE_PATTERNS),
        },
        "constitutional_terminology": {
            "total_uses": a.total_constitutional_terms,
            "by_term": a.constitutional_term_counts,
        },
        "memex_score": {
            "total": score,
            "breakdown": breakdown,
        },
        "tool_sequence": a.tool_sequence,
    }
    return json.dumps(output, indent=2)


def format_csv_row(a: SessionAnalysis) -> dict:
    """Return a flat dict suitable for CSV output."""
    score, _ = compute_memex_score(a)
    return {
        "session_id": a.session_id,
        "start_time": a.start_time or "",
        "end_time": a.end_time or "",
        "total_tool_calls": a.total_tool_calls,
        "total_reads": a.total_reads,
        "governance_reads": a.governance_reads,
        "flow_reads": a.flow_reads,
        "code_reads": a.code_reads,
        "total_edits": a.total_edits,
        "governance_edits": a.governance_edits,
        "code_edits": a.code_edits,
        "total_searches": a.total_searches,
        "total_bash": a.total_bash,
        "total_agents": a.total_agents,
        "governance_files_accessed": len(a.governance_files_accessed),
        "governance_read_before_code_edit": a.governance_read_before_code_edit,
        "first_governance_read_index": a.first_governance_read_index if a.first_governance_read_index is not None else "",
        "first_code_edit_index": a.first_code_edit_index if a.first_code_edit_index is not None else "",
        "trails_detected": len(a.trails_detected),
        "tripwires_addressed": len(a.tripwires_addressed),
        "tripwire_list": "; ".join(a.tripwires_addressed),
        "constitutional_terms_total": a.total_constitutional_terms,
        "memex_score": f"{score:.1f}",
    }


CSV_FIELDS = [
    "session_id", "start_time", "end_time",
    "total_tool_calls", "total_reads", "governance_reads", "flow_reads", "code_reads",
    "total_edits", "governance_edits", "code_edits",
    "total_searches", "total_bash", "total_agents",
    "governance_files_accessed", "governance_read_before_code_edit",
    "first_governance_read_index", "first_code_edit_index",
    "trails_detected", "tripwires_addressed", "tripwire_list",
    "constitutional_terms_total", "memex_score",
]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    # Force UTF-8 output on Windows
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Analyze Claude Code session transcripts for Memex vs Memory behavior."
    )
    parser.add_argument("session", nargs="?", help="Path to a single .jsonl session file")
    parser.add_argument("--dir", help="Analyze all .jsonl files in a directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", help="Output as CSV (best with --dir)")
    args = parser.parse_args()

    if not args.session and not args.dir:
        parser.print_help()
        sys.exit(1)

    # Collect files to analyze
    files = []
    if args.dir:
        dirpath = Path(args.dir)
        files = sorted(dirpath.glob("*.jsonl"))
        if not files:
            print(f"No .jsonl files found in {args.dir}", file=sys.stderr)
            sys.exit(1)
    else:
        files = [Path(args.session)]

    analyses = []
    for fp in files:
        try:
            a = analyze_session(str(fp))
            analyses.append(a)
        except Exception as e:
            print(f"Error analyzing {fp}: {e}", file=sys.stderr)

    # Output
    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for a in analyses:
            writer.writerow(format_csv_row(a))
    elif args.json:
        if len(analyses) == 1:
            print(format_json(analyses[0]))
        else:
            outputs = []
            for a in analyses:
                score, breakdown = compute_memex_score(a)
                outputs.append(json.loads(format_json(a)))
            print(json.dumps(outputs, indent=2))
    else:
        for a in analyses:
            print(format_report(a))


if __name__ == "__main__":
    main()
