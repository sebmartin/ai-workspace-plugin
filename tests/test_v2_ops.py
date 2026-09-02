"""Schema 2 write tools: one line per call, always re-rendered, refused on schema 1."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.threads import marker
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import ops


def _only_id(thread_dir, kind):
    """Read the id back from the index rather than parsing a prose message."""
    entries, _ = idx.read(thread_dir, kind)
    return entries[-1].id
from mcp_server import (
    add_artifact, add_todo, log_decision, retire_artifact, retire_decision,
    retire_todo, set_todo_state, set_window,
)


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "_config"))


def _thread(tmp_path, name="t", schema=2):
    d = tmp_path / "threads" / name
    for sub in ("sessions", "decisions", "artifacts", "attachments", "todos"):
        (d / sub).mkdir(parents=True)
    (d / "README.md").write_text(
        "# Thread: t\n\n**Started**: 2026-01-01\n\n## Status\n\nx\n\n"
        "## Next steps\n\n- None\n\n## About\n\ny\n"
    )
    if schema == 2:
        marker.write(d, 2)
    return d


class TestRefusalOnSchema1:
    def test_every_write_tool_refuses(self, tmp_path):
        _thread(tmp_path, "old", schema=1)
        ws = str(tmp_path)
        calls = [
            add_todo(ws, "old", "t", "./x.md"),
            retire_todo(ws, "old", "i", "done"),
            set_todo_state(ws, "old", "i", "parked"),
            set_window(ws, "old", ["i"]),
            log_decision(ws, "old", "t", "s", "b"),
            retire_decision(ws, "old", "i", "superseded"),
            add_artifact(ws, "old", "t", "./x.md"),
            retire_artifact(ws, "old", "i", "stale"),
        ]
        assert all("NEEDS_MIGRATION" in c for c in calls), calls

    def test_refusal_does_not_touch_the_readme(self, tmp_path):
        d = _thread(tmp_path, "old", schema=1)
        before = (d / "README.md").read_text()
        add_todo(str(tmp_path), "old", "t", "./x.md")
        assert (d / "README.md").read_text() == before
        assert not idx.index_path(d, "todos").exists()



class TestTodos:
    def test_add_requires_a_link(self, tmp_path):
        d = _thread(tmp_path)
        assert "needs a link" in ops.add_todo(d, "Email the contractor", "")

    def test_add_then_window_then_render(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = add_todo(ws, "t", "Prep the coding round", "./sessions/20260101-s.md")
        todo_id = _only_id(d, "todos")
        assert set_window(ws, "t", [todo_id]).startswith("Window")
        assert "Prep the coding round" in (d / "README.md").read_text()

    def test_backlog_is_not_shown_until_promoted(self, tmp_path):
        d = _thread(tmp_path)
        add_todo(str(tmp_path), "t", "Someday thing", "./s.md")
        assert "Someday thing" not in (d / "README.md").read_text()

    def test_retiring_removes_it_from_the_window(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Chase the permit", "./s.md")
        todo_id = _only_id(d, "todos")
        set_window(ws, "t", [todo_id])
        assert "Chase the permit" in (d / "README.md").read_text()
        retire_todo(ws, "t", todo_id, "done")
        _, fm = idx.read(d, "todos")
        assert fm.get("windows", {}).get("next_steps") == []
        assert "Chase the permit" not in (d / "README.md").read_text()

    def test_park_and_unpark(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Well driller", "./s.md"); todo_id = _only_id(d, "todos")
        set_todo_state(ws, "t", todo_id, "parked")
        entries, _ = idx.read(d, "todos")
        assert entries[0].state == "parked"
        set_todo_state(ws, "t", todo_id, "active")
        entries, _ = idx.read(d, "todos")
        assert entries[0].state == "active"

    def test_bad_state_is_rejected(self, tmp_path):
        d = _thread(tmp_path)
        assert "not a todo state" in ops.add_todo(d, "A", "./s.md", "banana")


class TestDecisions:
    def test_file_and_index_entry_are_written(self, tmp_path):
        d = _thread(tmp_path)
        out = log_decision(str(tmp_path), "t", "Use Iceberg",
                           "Chose Iceberg for table format.", "# Body\n", "locked")
        did = _only_id(d, "decisions")
        assert (d / "decisions" / f"{did}.md").exists()
        entries, _ = idx.read(d, "decisions")
        assert entries[0].id == did and entries[0].state == "locked"

    def test_summary_lives_only_in_the_file(self, tmp_path):
        d = _thread(tmp_path)
        log_decision(str(tmp_path), "t", "Use Iceberg", "Chose Iceberg.", "b", "locked")
        assert "Chose Iceberg." not in idx.index_path(d, "decisions").read_text()
        assert "Chose Iceberg." in next((d / "decisions").glob("*.md")).read_text()

    def test_supersedes_retires_the_old_one(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        log_decision(ws, "t", "Use Parquet", "Chose Parquet.", "b", "locked"); old = _only_id(d, "decisions")
        log_decision(ws, "t", "Use Iceberg", "Chose Iceberg.", "b", "locked", [old])
        live, _ = idx.read(d, "decisions")
        gone, _ = idx.read(d, "decisions", retired=True)
        assert [e.id for e in live] == [e.id for e in live if e.id != old]
        assert gone[0].id == old and gone[0].state == "superseded"

    def test_retire_updates_the_file_status_too(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        log_decision(ws, "t", "X", "Chose X.", "b", "locked"); did = _only_id(d, "decisions")
        retire_decision(ws, "t", did, "withdrawn")
        assert "status: withdrawn" in (d / "decisions" / f"{did}.md").read_text()

    def test_bad_status_rejected(self, tmp_path):
        d = _thread(tmp_path)
        assert "not an in-force decision status" in ops.log_decision(d, "T", "s", "b", "locked-ish")


    @pytest.mark.parametrize("summary", [
        "Chose piles: soil ruled out footings",
        "[unresolved] pending the survey",
        'Kept the "temporary" name',
        r"Path is C:\notes\x",
    ])
    def test_a_summary_that_is_not_bare_yaml_reads_back(self, tmp_path, summary):
        """The reader refuses invalid frontmatter, so the writer must emit none.

        Every one of these was written unquoted once and came back as an
        unparseable file, which cost the decision its title and status too.
        """
        from ai_workspace.text import split_frontmatter

        d = _thread(tmp_path)
        log_decision(str(tmp_path), "t", "T", summary, "body", "locked")
        path = next((d / "decisions").glob("*.md"))
        fields, _ = split_frontmatter(path.read_text(), path)
        assert fields["summary"] == summary


class TestArtifacts:
    def test_add_and_retire(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_artifact(ws, "t", "Notes", "./artifacts/20260101-notes.md"); aid = _only_id(d, "artifacts")
        entries, _ = idx.read(d, "artifacts")
        assert entries[0].state == "current"
        retire_artifact(ws, "t", aid, "stale")
        live, _ = idx.read(d, "artifacts")
        gone, _ = idx.read(d, "artifacts", retired=True)
        assert live == [] and gone[0].state == "stale"


class TestInvariant:
    def test_readme_always_equals_the_projection(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md"); a = _only_id(d, "todos")
        add_todo(ws, "t", "B", "./s.md"); b = _only_id(d, "todos")
        set_window(ws, "t", [b, a])
        from ai_workspace.threads.v2 import render
        expected = render.next_steps_body(d)
        section = (d / "README.md").read_text().split("## Next steps\n\n")[1].split("\n\n")[0]
        assert section.strip() == expected.strip()
