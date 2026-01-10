#!/usr/bin/env python3
"""
This tool is a proposal generator, not an auto-refactor.
"""

import argparse
import difflib
import os
import re
import sys
from typing import List, Dict, Tuple


def read_input(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _count_regex(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def summarize_code(text: str, lang: str) -> str:
    lines = text.splitlines()
    nonempty = sum(1 for line in lines if line.strip())
    summary_parts = [f"{len(lines)} lines ({nonempty} non-empty)"]

    if lang == "python":
        defs = _count_regex(r"^\s*def\s+\w+\s*\(", text)
        classes = _count_regex(r"^\s*class\s+\w+\s*\(", text)
        classes += _count_regex(r"^\s*class\s+\w+\s*:", text)
        summary_parts.append(f"functions: {defs}")
        summary_parts.append(f"classes: {classes}")
    elif lang == "javascript":
        funcs = _count_regex(r"^\s*function\s+\w+\s*\(", text)
        classes = _count_regex(r"^\s*class\s+\w+\s*", text)
        arrows = _count_regex(r"=>", text)
        summary_parts.append(f"functions: {funcs}")
        summary_parts.append(f"classes: {classes}")
        summary_parts.append(f"arrow functions (approx): {arrows}")
    else:
        summary_parts.append("language: unknown")

    return "Summary: " + ", ".join(summary_parts) + "."


def _detect_language(path: str) -> str:
    _, ext = os.path.splitext(path.lower())
    if ext in {".py"}:
        return "python"
    if ext in {".js", ".mjs", ".cjs", ".ts", ".mts", ".cts"}:
        return "javascript"
    return "unknown"


def _join_lines(lines: List[str], ends_with_newline: bool) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + ("\n" if ends_with_newline else "")


def _triple_quote_states(lines: List[str]) -> List[bool]:
    states = []
    in_triple = False
    delim = None

    for line in lines:
        states.append(in_triple)
        if not in_triple:
            idx1 = line.find("'''")
            idx2 = line.find('"""')
            if idx1 == -1 and idx2 == -1:
                continue
            if idx1 == -1 or (idx2 != -1 and idx2 < idx1):
                delim = '"""'
            else:
                delim = "'''"
            if line.count(delim) % 2 == 1:
                in_triple = True
        else:
            if delim and line.count(delim) % 2 == 1:
                in_triple = False

    return states


def _trim_leading_blank_lines(lines: List[str], states: List[bool]) -> List[str]:
    i = 0
    while i < len(lines) and not lines[i].strip() and not states[i]:
        i += 1
    return lines[i:]


def _trim_trailing_blank_lines(lines: List[str], states: List[bool]) -> List[str]:
    j = len(lines) - 1
    while j >= 0 and not lines[j].strip() and not states[j]:
        j -= 1
    if j < 0:
        return []
    return lines[: j + 1]


def _collapse_consecutive_blank_lines(lines: List[str], states: List[bool]) -> List[str]:
    out = []
    blank_run = 0
    for line, in_triple in zip(lines, states):
        if not line.strip() and not in_triple:
            blank_run += 1
            if blank_run == 1:
                out.append(line)
        else:
            blank_run = 0
            out.append(line)
    return out


def _strip_trailing_whitespace(lines: List[str], states: List[bool]) -> List[str]:
    out = []
    for line, in_triple in zip(lines, states):
        if in_triple:
            out.append(line)
        else:
            out.append(re.sub(r"[ \t]+$", "", line))
    return out


def _inline_return_python(lines: List[str], states: List[bool]) -> Tuple[List[str], int]:
    out = []
    i = 0
    changes = 0
    assign_re = re.compile(r"^(\s*)([A-Za-z_]\w*)\s*=\s*(.+)$")
    return_re = re.compile(r"^(\s*)return\s+([A-Za-z_]\w*)\s*$")

    while i < len(lines):
        if i + 1 < len(lines) and not states[i] and not states[i + 1]:
            m1 = assign_re.match(lines[i])
            m2 = return_re.match(lines[i + 1])
            if m1 and m2 and m1.group(2) == m2.group(2):
                if "#" not in lines[i] and ";" not in lines[i]:
                    out.append(f"{m2.group(1)}return {m1.group(3)}")
                    changes += 1
                    i += 2
                    continue
        out.append(lines[i])
        i += 1
    return out, changes


def _inline_return_js(lines: List[str], states: List[bool]) -> Tuple[List[str], int]:
    out = []
    i = 0
    changes = 0
    assign_re = re.compile(r"^(\s*)const\s+([A-Za-z_$][\w$]*)\s*=\s*(.+);\s*$")
    return_re = re.compile(r"^(\s*)return\s+([A-Za-z_$][\w$]*)\s*;\s*$")

    while i < len(lines):
        if i + 1 < len(lines) and not states[i] and not states[i + 1]:
            m1 = assign_re.match(lines[i])
            m2 = return_re.match(lines[i + 1])
            if m1 and m2 and m1.group(2) == m2.group(2):
                if "//" not in lines[i]:
                    out.append(f"{m2.group(1)}return {m1.group(3)};")
                    changes += 1
                    i += 2
                    continue
        out.append(lines[i])
        i += 1
    return out, changes


def _proposal(
    title: str,
    lines: List[str],
    original: str,
    ends_with_newline: bool,
    changes: str,
    rationale: str,
    confidence: int,
) -> Dict[str, str] | None:
    code = _join_lines(lines, ends_with_newline)
    if code == original:
        return None
    lines_saved = max(0, len(original.splitlines()) - len(code.splitlines()))
    return {
        "title": title,
        "code": code,
        "changes": changes,
        "rationale": rationale,
        "confidence": confidence,
        "lines_saved": lines_saved,
    }


def _confidence_flag(score: int) -> str:
    if score >= 90:
        return "HIGH"
    if score >= 80:
        return "MED"
    if score >= 60:
        return "LOW"
    return "SKIP"


def propose_compressions(text: str, lang: str, mode: str) -> List[Dict[str, str]]:
    proposals = []
    ends_with_newline = text.endswith("\n")
    lines = text.splitlines()
    states = _triple_quote_states(lines) if lang == "python" else [False] * len(lines)

    p = _proposal(
        "Trim trailing blank lines",
        _trim_trailing_blank_lines(lines, states),
        text,
        ends_with_newline,
        "Removed empty lines at the end of the file.",
        "Trailing blank lines do not affect execution semantics.",
        100,
    )
    if p:
        proposals.append(p)

    p = _proposal(
        "Trim leading blank lines",
        _trim_leading_blank_lines(lines, states),
        text,
        ends_with_newline,
        "Removed empty lines at the start of the file.",
        "Leading blank lines do not affect execution semantics.",
        100,
    )
    if p:
        proposals.append(p)

    p = _proposal(
        "Collapse consecutive blank lines",
        _collapse_consecutive_blank_lines(lines, states),
        text,
        ends_with_newline,
        "Collapsed multiple blank lines down to a single blank line.",
        "Whitespace-only lines outside strings are layout-only.",
        100,
    )
    if p:
        proposals.append(p)

    p = _proposal(
        "Strip trailing whitespace",
        _strip_trailing_whitespace(lines, states),
        text,
        ends_with_newline,
        "Removed trailing spaces/tabs on line endings.",
        "Trailing whitespace is not semantically meaningful.",
        100,
    )
    if p:
        proposals.append(p)

    if lang == "python":
        inlined, changes = _inline_return_python(lines, states)
        if changes:
            p = _proposal(
                "Inline immediate return variable",
                inlined,
                text,
                ends_with_newline,
                "Replaced a temporary assignment followed by return with a direct return.",
                "The variable is not reused; direct return is equivalent.",
                85,
            )
            if p:
                proposals.append(p)
    elif lang == "javascript":
        inlined, changes = _inline_return_js(lines, states)
        if changes:
            p = _proposal(
                "Inline immediate return variable",
                inlined,
                text,
                ends_with_newline,
                "Replaced const assignment followed by return with a direct return.",
                "The variable is not reused; direct return is equivalent.",
                85,
            )
            if p:
                proposals.append(p)

    if mode == "aggressive":
        for proposal in proposals:
            proposal["rationale"] += " Aggressive mode keeps whitespace-only or direct-return changes for safety."

    return proposals


def analyze_redundancies(text: str, lang: str) -> List[str]:
    lines = text.splitlines()
    states = _triple_quote_states(lines) if lang == "python" else [False] * len(lines)

    leading = 0
    for line, in_triple in zip(lines, states):
        if not line.strip() and not in_triple:
            leading += 1
        else:
            break

    trailing = 0
    for line, in_triple in zip(reversed(lines), reversed(states)):
        if not line.strip() and not in_triple:
            trailing += 1
        else:
            break

    blank_runs = 0
    run = 0
    for line, in_triple in zip(lines, states):
        if not line.strip() and not in_triple:
            run += 1
            if run == 2:
                blank_runs += 1
        else:
            run = 0

    trailing_ws = sum(1 for line, in_triple in zip(lines, states) if not in_triple and re.search(r"[ \t]+$", line))

    redundancies = [
        f"Leading blank lines: {leading}",
        f"Trailing blank lines: {trailing}",
        f"Consecutive blank line runs: {blank_runs}",
        f"Lines with trailing whitespace: {trailing_ws}",
    ]

    return redundancies


def explain_changes(original: str, proposed: str, proposal: Dict[str, str], explain: bool) -> str:
    if not explain:
        return ""
    if original == proposed:
        return "No change required by this proposal; the file already matches this compression."
    return f"{proposal['changes']} {proposal['rationale']} Confidence: {proposal['confidence']}%."


def _rank_proposals(proposals: List[Dict[str, str]], sort_by: str) -> List[Dict[str, str]]:
    if sort_by == "confidence":
        return sorted(
            proposals,
            key=lambda p: (p["confidence"], p["lines_saved"], p["title"]),
            reverse=True,
        )
    return sorted(
        proposals,
        key=lambda p: (p["lines_saved"], p["confidence"], p["title"]),
        reverse=True,
    )


def render_output(
    original: str,
    summary: str,
    redundancies: List[str],
    proposals: List[Dict[str, str]],
    explain: bool,
    show_diff: bool,
) -> str:
    parts = [summary, ""]
    parts.append("Codex explores compression candidates. Humans evaluate and decide. Output is proposals only.")
    parts.append("CLI is the execution layer; this tool never auto-writes files.")
    parts.append("")
    parts.append("Redundancies:")
    parts.extend(f"- {item}" for item in redundancies)
    parts.append("")

    total_lines_saved = sum(p["lines_saved"] for p in proposals)
    avg_conf = int(round(sum(p["confidence"] for p in proposals) / len(proposals))) if proposals else 0
    parts.append(f"{len(proposals)} proposals, {total_lines_saved} lines saved, avg confidence {avg_conf}%")

    parts.append("Proposals:")
    for idx, proposal in enumerate(proposals, start=1):
        flag = _confidence_flag(proposal["confidence"])
        parts.append("")
        parts.append(
            f"[{flag}][{proposal['confidence']}%] {proposal['title']} - saves {proposal['lines_saved']} lines"
        )
        if explain:
            parts.append(explain_changes(original, proposal["code"], proposal, explain=True))
        parts.append("--- Proposed code ---")
        parts.append(proposal["code"])
        if show_diff:
            diff = difflib.unified_diff(
                original.splitlines(),
                proposal["code"].splitlines(),
                fromfile="original",
                tofile=f"proposal-{idx}",
                lineterm="",
            )
            parts.append("--- Diff (unified) ---")
            parts.append("\n".join(diff))

    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(prog="compress-code")
    parser.add_argument("input_file")
    parser.add_argument("--mode", choices=["safe", "aggressive"], default="safe")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--min-confidence", type=int, default=60)
    parser.add_argument("--max-proposals", type=int, default=0)
    parser.add_argument("--sort", choices=["impact", "confidence"], default="impact")
    args = parser.parse_args()

    original = read_input(args.input_file)
    lang = _detect_language(args.input_file)

    summary = summarize_code(original, lang)
    redundancies = analyze_redundancies(original, lang)
    proposals = propose_compressions(original, lang, args.mode)

    proposals = [p for p in proposals if p["confidence"] >= args.min_confidence]
    proposals = _rank_proposals(proposals, args.sort)
    if args.max_proposals > 0:
        proposals = proposals[: args.max_proposals]

    output = render_output(
        original=original,
        summary=summary,
        redundancies=redundancies,
        proposals=proposals,
        explain=args.explain,
        show_diff=args.diff,
    )

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
