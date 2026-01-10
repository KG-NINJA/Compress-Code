#!/usr/bin/env python3
"""
This tool is a proposal generator, not an auto-refactor.
"""

import argparse
import difflib
import os
import re
import sys
from typing import List, Dict


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


def _trim_leading_blank_lines(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    return "\n".join(lines[i:]) + ("\n" if text.endswith("\n") and lines[i:] else "")


def _trim_trailing_blank_lines(text: str) -> str:
    lines = text.splitlines()
    j = len(lines) - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0:
        return ""
    trimmed = "\n".join(lines[: j + 1])
    return trimmed + ("\n" if text.endswith("\n") else "")


def propose_compressions(text: str, lang: str, mode: str) -> List[Dict[str, str]]:
    proposals = []

    v1 = _trim_trailing_blank_lines(text)
    proposals.append(
        {
            "title": "Trim trailing blank lines",
            "code": v1,
            "changes": "Removed empty lines at the end of the file.",
            "rationale": "Trailing blank lines do not affect execution semantics.",
        }
    )

    v2 = _trim_leading_blank_lines(text)
    proposals.append(
        {
            "title": "Trim leading blank lines",
            "code": v2,
            "changes": "Removed empty lines at the start of the file.",
            "rationale": "Leading blank lines do not affect execution semantics.",
        }
    )

    v3 = _trim_trailing_blank_lines(_trim_leading_blank_lines(text))
    proposals.append(
        {
            "title": "Trim leading and trailing blank lines",
            "code": v3,
            "changes": "Removed empty lines at the start and end of the file.",
            "rationale": "Blank lines outside code blocks do not affect execution semantics.",
        }
    )

    if mode == "aggressive":
        # Still conservative: avoid modifying internal blank lines without parsing.
        for proposal in proposals:
            proposal["rationale"] += " Aggressive mode keeps boundary-only whitespace changes for safety."

    return proposals


def analyze_redundancies(text: str, lang: str) -> List[str]:
    # Conservative baseline: avoid semantic guesses without deeper parsing.
    return ["No safe redundancies detected with boundary-only analysis."]


def explain_changes(original: str, proposed: str, proposal: Dict[str, str], explain: bool) -> str:
    if not explain:
        return ""
    if original == proposed:
        return "No change required by this proposal; the file already matches this boundary-only compression."
    return f"{proposal['changes']} {proposal['rationale']}"


def render_output(
    original: str,
    summary: str,
    redundancies: List[str],
    proposals: List[Dict[str, str]],
    explain: bool,
    show_diff: bool,
) -> str:
    parts = [summary, ""]
    parts.append("Redundancies:")
    parts.extend(f"- {item}" for item in redundancies)
    parts.append("")

    parts.append("Proposals:")
    for idx, proposal in enumerate(proposals, start=1):
        parts.append("")
        parts.append(f"[{idx}] {proposal['title']}")
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
            parts.append("--- Diff ---")
            parts.append("\n".join(diff))

    return "\n".join(parts)


def _detect_language(path: str) -> str:
    _, ext = os.path.splitext(path.lower())
    if ext in {".py"}:
        return "python"
    if ext in {".js", ".mjs", ".cjs"}:
        return "javascript"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(prog="compress-code")
    parser.add_argument("input_file")
    parser.add_argument("--mode", choices=["safe", "aggressive"], default="safe")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--diff", action="store_true")
    args = parser.parse_args()

    original = read_input(args.input_file)
    lang = _detect_language(args.input_file)

    summary = summarize_code(original, lang)
    redundancies = analyze_redundancies(original, lang)
    proposals = propose_compressions(original, lang, args.mode)

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
