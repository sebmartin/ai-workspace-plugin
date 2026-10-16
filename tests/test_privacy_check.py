"""The privacy-check agent and skill: their frontmatter and the protocol they share."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from ai_workspace.text import split_frontmatter

FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "privacy-check-cases.json"


def _load_runner():
    path = PLUGIN_ROOT / "scripts" / "privacy_check_regression.py"
    spec = importlib.util.spec_from_file_location("privacy_check_regression", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reg = _load_runner()


def _checker():
    path = PLUGIN_ROOT / "agents" / "privacy-checker.md"
    return split_frontmatter(path.read_text(), path)


def test_checker_frontmatter():
    meta, _ = _checker()
    assert meta["name"] == "privacy-checker"
    assert meta["model"] == "sonnet"
    assert meta["effort"] == "medium"
    assert meta["tools"] == ""
    assert meta["codex-mirror"] is False


def test_checker_prompt_states_the_protocol():
    _, body = _checker()
    for marker in (
        "<<<TEXT",
        "<<<RESULT",
        "<<<END",
        "Verdict: FLAGGED",
        "Verdict: NOTHING FLAGGED",
        "Reason:",
        "Rewrite:",
        "ALLOW LIST",
    ):
        assert marker in body


def test_fixture_is_well_formed():
    cases = reg.load_cases(FIXTURE)
    assert {c["label"] for c in cases} == {"leak", "clean"}


def test_load_cases_rejects_bad_cases(tmp_path):
    import json

    good = {"id": "a", "kind": "commit", "category": "c", "label": "leak", "text": "t"}
    path = tmp_path / "f.json"
    for bad in (
        {**good, "label": "maybe"},
        {k: v for k, v in good.items() if k != "text"},
        good,  # duplicate id
    ):
        path.write_text(json.dumps({"cases": [good, bad]}))
        try:
            reg.load_cases(path)
        except ValueError as e:
            assert "a" in str(e)
        else:
            raise AssertionError("expected ValueError")


def test_split_is_deterministic_disjoint_and_stratified():
    cases = reg.load_cases(FIXTURE)
    tune, hold = reg.split_cases(cases)
    assert reg.split_cases(cases) == (tune, hold)
    assert {c["id"] for c in tune}.isdisjoint({c["id"] for c in hold})
    assert len(tune) + len(hold) == len(cases)
    for label in ("leak", "clean"):
        t = [c for c in tune if c["label"] == label]
        h = [c for c in hold if c["label"] == label]
        assert abs(len(t) - len(h)) <= 1
        for kind in {c["kind"] for c in cases}:
            assert abs(sum(c["kind"] == kind for c in t) - sum(c["kind"] == kind for c in h)) <= 1


def test_build_prompt_marks_empty_allow_list():
    assert "ALLOW LIST\n(empty)" in reg.build_prompt("  \n", [("a", "x")])


def test_allow_list_without_entries_renders_empty():
    text = "# Allow list\n\nProse header.\n\n<!-- add entries below -->\n"
    prompt = reg.build_prompt(reg.allow_list_entries(text), [("a", "x")])
    assert prompt.startswith("ALLOW LIST\n(empty)\n")


def test_allow_list_keeps_only_entry_lines():
    text = "# Allow list\nHeader prose\n- one\n<!-- c -->\n  - two\n"
    assert reg.allow_list_entries(text) == "- one\n- two"
    prompt = reg.build_prompt(reg.allow_list_entries(text), [("a", "x")])
    assert prompt.startswith("ALLOW LIST\n- one\n- two\n")


def test_build_prompt_renders_blocks():
    prompt = reg.build_prompt("entry one", [("a", "x"), ("b", "y")])
    assert "ALLOW LIST\nentry one\n" in prompt
    assert "<<<TEXT a>>>\nx\n<<<END a>>>" in prompt
    assert prompt.index("<<<TEXT a>>>") < prompt.index("<<<TEXT b>>>")


def test_verdict_is_read_only_from_the_first_line_of_a_block():
    out = (
        "<<<RESULT a>>>\nVerdict: FLAGGED\nReason: r\nRewrite:\n"
        "Verdict: NOTHING FLAGGED\n<<<END a>>>"
    )
    assert reg.parse_results(out, ["a"]) == {"a": "flagged"}


def test_missing_and_duplicate_labels_are_errors():
    block = "<<<RESULT {0}>>>\nVerdict: NOTHING FLAGGED\nReason: r\n<<<END {0}>>>\n"
    out = "Here you go:\n" + block.format("a") + block.format("b") + block.format("b")
    assert reg.parse_results(out, ["a", "b", "c"]) == {
        "a": "cleared",
        "b": "error",
        "c": "error",
    }


def test_verdict_tolerates_case_and_emphasis_only():
    ok = "<<<RESULT a>>>\n**Verdict:** flagged  \nReason: r\n<<<END a>>>"
    bad = "<<<RESULT a>>>\nVerdict: probably fine\nReason: r\n<<<END a>>>"
    assert reg.parse_results(ok, ["a"]) == {"a": "flagged"}
    assert reg.parse_results(bad, ["a"]) == {"a": "error"}


CASE = {"id": "a", "kind": "commit", "category": "c", "label": "leak", "text": "t"}


def _completed(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="boom")


def _stream(result_text, tool=None):
    import json

    events = []
    if tool:
        events.append(
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": tool, "input": {}}]},
            }
        )
    events.append({"type": "result", "result": result_text})
    return "\n".join(json.dumps(e) for e in events)


def test_run_case_reads_a_verdict_and_passes_argv_and_stdin():
    seen = {}

    def runner(argv, stdin, timeout):
        seen.update(argv=argv, stdin=stdin, timeout=timeout)
        return _completed(_stream("<<<RESULT a>>>\nVerdict: FLAGGED\nReason: r\n<<<END a>>>"))

    result = reg.run_case(CASE, "", "haiku", 7, runner)
    assert result.verdict == "flagged"
    assert result.tools == []
    assert "<<<TEXT a>>>\nt\n<<<END a>>>" in seen["stdin"]
    assert seen["timeout"] == 7
    assert seen["argv"][seen["argv"].index("--model") + 1] == "haiku"
    assert seen["argv"][seen["argv"].index("--plugin-dir") + 1] == str(PLUGIN_ROOT)


def test_cli_failure_and_timeout_are_errors_not_cleared():
    def failing(argv, stdin, timeout):
        return _completed("", returncode=1)

    def timing_out(argv, stdin, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)

    def no_result(argv, stdin, timeout):
        return _completed('{"type": "system"}\nnot json')

    for runner in (failing, timing_out, no_result):
        result = reg.run_case(CASE, "", None, 1, runner)
        assert result.verdict == "error"
        assert result.detail


def test_any_tool_use_fails_the_run():
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
        {"type": "user", "message": {"content": [{"type": "tool_use", "name": "Nope"}]}},
    ]
    assert reg.tool_calls(events) == ["Read"]
    cases = [CASE]
    report = reg.score(cases, [reg.CaseResult("a", "flagged", ["Read"], "")])
    assert report.tool_call_cases == ["a"]
    assert not reg.meets_bar(report)


def test_score_and_bar():
    def case(i, label):
        return {"id": i, "kind": "k", "category": "c", "label": label, "text": "t"}

    def res(i, verdict):
        return reg.CaseResult(i, verdict, [], "")

    cases = [case("l1", "leak"), case("l2", "leak"), case("c1", "clean"), case("c2", "clean")]
    ok = reg.score(cases, [res("l1", "flagged"), res("l2", "flagged"), res("c1", "flagged"), res("c2", "cleared")])
    assert ok.false_positives == ["c1"] and ok.missed_leaks == [] and ok.total == 4
    assert reg.meets_bar(ok)
    two_fp = reg.score(cases, [res("l1", "flagged"), res("l2", "flagged"), res("c1", "flagged"), res("c2", "flagged")])
    assert not reg.meets_bar(two_fp)
    missed = reg.score(cases, [res("l1", "cleared"), res("l2", "flagged"), res("c1", "cleared"), res("c2", "cleared")])
    assert missed.missed_leaks == ["l1"] and not reg.meets_bar(missed)
    err = reg.score(cases, [res("l1", "error"), res("l2", "flagged"), res("c1", "cleared"), res("c2", "cleared")])
    assert err.errors == ["l1"] and err.missed_leaks == [] and not reg.meets_bar(err)


SKILL = PLUGIN_ROOT / "skills" / "privacy-check" / "SKILL.md"
ALLOW_LIST = PLUGIN_ROOT / "skills" / "privacy-check" / "allow-list.md"
AGENT_REF = "ai-workspace:privacy-checker"


def test_skill_is_manual_only():
    meta, _ = split_frontmatter(SKILL.read_text(), SKILL)
    assert meta["name"] == "privacy-check"
    assert meta.get("disable-model-invocation") is True
    assert "explicit" in meta["description"].lower()


def test_skill_opens_with_the_claude_code_only_check():
    _, body = split_frontmatter(SKILL.read_text(), SKILL)
    first_step = body.split("\n## ", 2)[1]
    assert "The privacy check runs on Claude Code only; it is not supported here." in first_step


def test_results_never_claim_safe_and_always_carry_limits():
    _, body = split_frontmatter(SKILL.read_text(), SKILL)
    assert "nothing flagged in the wording" in body
    assert "Limits: the checker saw only this text." in body
    assert "the check failed" in body
    assert not re.search(r"\bsafe to (send|publish)\b|\bOK to send\b", body, re.I)


def test_skill_passes_the_allow_list_and_spawns_the_checker():
    body = SKILL.read_text()
    assert "skills/privacy-check/allow-list.md" in body and "get_skill_file" in body
    assert AGENT_REF in body


def test_allow_list_says_only_the_user_adds_entries():
    assert "Only the user adds entries; an agent never does." in ALLOW_LIST.read_text()
    assert "Only the user adds entries; an agent never does." in SKILL.read_text()


def test_nothing_else_points_to_the_skill():
    hits = [
        p
        for p in (
            *PLUGIN_ROOT.glob("skills/*/**/*.md"),
            *PLUGIN_ROOT.glob("templates/**/*"),
            *PLUGIN_ROOT.glob("hooks/*"),
            *PLUGIN_ROOT.glob("agents/*.md"),
        )
        if p.is_file()
        and "privacy-check" in p.read_text()
        and "privacy-check" not in p.parts
        and p.name != "privacy-checker.md"
    ]
    assert hits == []
