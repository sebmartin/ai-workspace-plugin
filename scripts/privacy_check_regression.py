#!/usr/bin/env python3
"""Regression runner for the privacy-checker agent.

Measures how well the shipped `agents/privacy-checker.md` separates texts that
disclose private context ("leak") from texts that do not ("clean"), using the
fictional labelled cases in `tests/fixtures/privacy-check-cases.json`. Each case
is one `claude` CLI call to the real agent; the fixture is split
deterministically into a tune half (use it while editing the prompt) and a
held-out half (use it to measure, never to tune).

This calls a model and costs money, so it runs on demand only and is not part
of the unit tests. Invocation:

    uv run python3 scripts/privacy_check_regression.py --half tune
    uv run python3 scripts/privacy_check_regression.py --half holdout --runs 3

The bar, per run: every leak flagged, at most one false positive, no errors, and
no tool calls by the checker. The exit code is 0 only if every run meets it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "privacy-check-cases.json"
ALLOW_LIST_PATH = REPO_ROOT / "skills" / "privacy-check" / "allow-list.md"

# Flags are the ones established by the Task 1 spike: --setting-sources project and
# --strict-mcp-config keep the user's own instructions, hooks, plugins and MCP
# servers out of the checker's context.
RUNNER_COMMAND = [
    "claude",
    "-p",
    "--plugin-dir",
    "<repo>",
    "--agent",
    "ai-workspace:privacy-checker",
    "--output-format",
    "stream-json",
    "--verbose",
    "--no-session-persistence",
    "--permission-mode",
    "dontAsk",
    "--setting-sources",
    "project",
    "--strict-mcp-config",
]
INIT_EVENT_TOOLS_KEY = "tools"
MODEL_OVERRIDE = "--model"

Verdict = Literal["flagged", "cleared", "error"]

REQUIRED_KEYS = ("id", "kind", "category", "label", "text")
VERDICT_LINES: dict[str, Verdict] = {
    "verdict: flagged": "flagged",
    "verdict: nothing flagged": "cleared",
}


def load_cases(path: Path) -> list[dict]:
    """Load and validate the fixture. Raises ValueError naming the bad case."""
    data = json.loads(path.read_text())
    cases = data["cases"] if isinstance(data, dict) else data
    seen: set[str] = set()
    for index, case in enumerate(cases):
        name = case.get("id", f"#{index}") if isinstance(case, dict) else f"#{index}"
        if not isinstance(case, dict):
            raise ValueError(f"case {name}: not an object")
        missing = [k for k in REQUIRED_KEYS if not isinstance(case.get(k), str) or not case[k]]
        if missing:
            raise ValueError(f"case {name}: missing or empty {', '.join(missing)}")
        if case["label"] not in ("leak", "clean"):
            raise ValueError(f"case {name}: label must be 'leak' or 'clean'")
        if case["id"] in seen:
            raise ValueError(f"case {name}: duplicate id")
        seen.add(case["id"])
    return cases


def split_cases(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (tune, holdout), alternating within each label by (kind, id)."""
    tune: list[dict] = []
    holdout: list[dict] = []
    for label in ("leak", "clean"):
        ordered = sorted((c for c in cases if c["label"] == label), key=lambda c: (c["kind"], c["id"]))
        for index, case in enumerate(ordered):
            (tune if index % 2 == 0 else holdout).append(case)
    return tune, holdout


def build_prompt(allow_list: str, texts: list[tuple[str, str]]) -> str:
    """Render the checker's input message."""
    parts = [f"ALLOW LIST\n{allow_list.strip() or '(empty)'}\n"]
    for label, text in texts:
        parts.append(f"<<<TEXT {label}>>>\n{text}\n<<<END {label}>>>")
    return "\n".join(parts) + "\n"


def parse_results(output: str, labels: list[str]) -> dict[str, Verdict]:
    """Read each label's verdict from the first non-empty line of its result block."""
    results: dict[str, Verdict] = {}
    for label in labels:
        tag = re.escape(label)
        if len(re.findall(rf"<<<RESULT {tag}>>>", output)) != 1:
            results[label] = "error"
            continue
        match = re.search(rf"<<<RESULT {tag}>>>(.*?)<<<END {tag}>>>", output, re.DOTALL)
        if not match:
            results[label] = "error"
            continue
        first = next((ln for ln in match.group(1).splitlines() if ln.strip()), "")
        normalised = re.sub(r"[*_]", "", first).strip().lower()
        normalised = re.sub(r"\s+", " ", normalised)
        results[label] = VERDICT_LINES.get(normalised, "error")
    return results


def tool_calls(events: list[dict]) -> list[str]:
    """Names of every tool_use item in assistant events."""
    names: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        names.extend(
            str(item.get("name"))
            for item in content
            if isinstance(item, dict) and item.get("type") == "tool_use"
        )
    return names


@dataclass
class CaseResult:
    id: str
    verdict: Verdict
    tools: list[str] = field(default_factory=list)
    detail: str = ""


def _run_claude(argv: list[str], stdin: str, timeout: float) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as cwd:
        return subprocess.run(
            argv, input=stdin, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )


def _argv(model: str | None) -> list[str]:
    argv = [str(REPO_ROOT) if part == "<repo>" else part for part in RUNNER_COMMAND]
    if model:
        argv += [MODEL_OVERRIDE, model]
    return argv


def run_case(
    case: dict,
    allow_list: str,
    model: str | None,
    timeout: float,
    runner: Callable[[list[str], str, float], subprocess.CompletedProcess] = _run_claude,
) -> CaseResult:
    """Run one case through the checker with one claude call."""
    label = case["id"]
    prompt = build_prompt(allow_list, [(label, case["text"])])
    try:
        proc = runner(_argv(model), prompt, timeout)
    except subprocess.TimeoutExpired:
        return CaseResult(label, "error", [], f"timed out after {timeout}s")
    except OSError as exc:
        return CaseResult(label, "error", [], f"could not run claude: {exc}")
    if proc.returncode != 0:
        return CaseResult(label, "error", [], f"exit {proc.returncode}: {(proc.stderr or '').strip()[:300]}")
    events: list[dict] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return CaseResult(label, "error", [], "unparseable stream-json line")
        if isinstance(event, dict):
            events.append(event)
    tools = tool_calls(events)
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            init_tools = event.get(INIT_EVENT_TOOLS_KEY) or []
            tools = [f"init:{name}" for name in init_tools] + tools
    result_event = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result_event is None or not isinstance(result_event.get("result"), str):
        return CaseResult(label, "error", tools, "no result event")
    verdict = parse_results(result_event["result"], [label])[label]
    detail = "" if verdict != "error" else "could not read a verdict: " + result_event["result"][:300]
    return CaseResult(label, verdict, tools, detail)


@dataclass
class Report:
    missed_leaks: list[str]
    false_positives: list[str]
    errors: list[str]
    tool_call_cases: list[str]
    total: int


def score(cases: list[dict], results: list[CaseResult]) -> Report:
    labels = {c["id"]: c["label"] for c in cases}
    report = Report([], [], [], [], len(cases))
    for r in results:
        if r.tools:
            report.tool_call_cases.append(r.id)
        if r.verdict == "error":
            report.errors.append(r.id)
        elif r.verdict == "cleared" and labels[r.id] == "leak":
            report.missed_leaks.append(r.id)
        elif r.verdict == "flagged" and labels[r.id] == "clean":
            report.false_positives.append(r.id)
    return report


def meets_bar(report: Report) -> bool:
    return (
        not report.missed_leaks
        and len(report.false_positives) <= 1
        and not report.errors
        and not report.tool_call_cases
    )


def _print_report(run: int, runs: int, half: str, report: Report) -> bool:
    ok = meets_bar(report)
    print(f"run {run}/{runs}: half={half} cases={report.total}")
    for name, ids in (
        ("missed leaks", report.missed_leaks),
        ("false positives", report.false_positives),
        ("errors", report.errors),
        ("tool calls", report.tool_call_cases),
    ):
        print(f"  {name}: {len(ids)}" + (f" ({', '.join(ids)})" if ids else ""))
    print("  bar met" if ok else "  bar not met")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the privacy-checker regression set.")
    parser.add_argument("--half", choices=("tune", "holdout", "all"), required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model", default=None)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)

    cases = load_cases(args.fixture)
    tune, holdout = split_cases(cases)
    selected = {"tune": tune, "holdout": holdout, "all": cases}[args.half]
    allow_list = ALLOW_LIST_PATH.read_text() if ALLOW_LIST_PATH.exists() else ""

    all_ok = True
    for run in range(1, args.runs + 1):
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(
                pool.map(
                    lambda c: run_case(c, allow_list, args.model, args.timeout),
                    selected,
                )
            )
        for r in results:
            if r.verdict == "error":
                print(f"  error in {r.id}: {r.detail}", file=sys.stderr)
        all_ok &= _print_report(run, args.runs, args.half, score(selected, results))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
