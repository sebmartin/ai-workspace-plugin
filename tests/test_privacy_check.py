"""The privacy-check agent and skill: their frontmatter and the protocol they share."""

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))

from ai_workspace.text import split_frontmatter


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
