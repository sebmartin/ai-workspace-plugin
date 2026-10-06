"""Schema 2 write tools: one line per call, always re-rendered, refused on schema 1."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.text import split_frontmatter
from ai_workspace.threads import marker
from ai_workspace.threads.v2 import index as idx


def _only_id(thread_dir, kind):
    """Read the id back from the index rather than parsing a prose message."""
    return idx.read(thread_dir, kind)[-1].id
from mcp_server import (
    add_todo,
    index_directory,
    index_file,
    log_decision,
    order_todos,
    retire_artifact,
    retire_decision,
    retire_todo,
    set_todo_state,
)


def _four_todos(ws):
    """A, B, C, D in the list, by title."""
    ids = {}
    for title in ("A", "B", "C", "D"):
        ids[title] = json.loads(add_todo(ws, "t", title, "./s.md"))["id"]
    return ids


def _reply(out):
    """Tool replies are JSON now; tests read the field they care about."""
    return json.loads(out)


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
            order_todos(ws, "old", ["i"]),
            log_decision(ws, "old", "t", "s", "b"),
            retire_decision(ws, "old", "i", "superseded"),
            index_file(ws, "old", "./artifacts/x.md"),
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
        _thread(tmp_path)
        assert _reply(add_todo(str(tmp_path), "t", "Email the contractor", ""))["error"] == "LINK_REQUIRED"

    def test_an_added_todo_reaches_next_steps(self, tmp_path):
        """The window needed a second call nothing told the agent to make, so a
        todo the user asked for never showed up."""
        d = _thread(tmp_path)
        add_todo(str(tmp_path), "t", "Prep the coding round", "./sessions/20260101-s.md")
        assert "Prep the coding round" in (d / "README.md").read_text()

    def test_the_window_refills_itself(self, tmp_path):
        """Nothing promotes the next todo, because nothing has to: the sixth is
        sixth in the list and becomes fifth when something above it goes."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = [json.loads(add_todo(ws, "t", f"T{n}", "./s.md"))["id"] for n in range(6)]
        assert "T5" not in (d / "README.md").read_text()
        retire_todo(ws, "t", ids[0], "done")
        assert "T5" in (d / "README.md").read_text()

    def test_a_title_that_cannot_be_read_back_is_refused(self, tmp_path):
        """A `]` ends the title field, so the line written is one the index
        cannot parse: it reported success and vanished on the next write."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "Fix [bug] in parser", "./sessions/s.md"))
        assert out["error"] == "UNREPRESENTABLE" and "]" in out["detail"]
        assert idx.read(d, "todos") == []

    def test_a_link_that_cannot_be_read_back_is_refused(self, tmp_path):
        """An ordinary Wikipedia URL ends the link field."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "Read the spec", "https://en.wikipedia.org/wiki/Merge_(SQL)"))
        assert out["error"] == "UNREPRESENTABLE" and ")" in out["detail"]
        assert idx.read(d, "todos") == []

    def test_a_newline_in_a_title_is_refused(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "Two\nlines", "./s.md"))
        assert out["error"] == "UNREPRESENTABLE"
        assert idx.read(d, "todos") == []

    def test_no_line_the_index_cannot_parse_is_ever_written(self, tmp_path):
        """The invariant the refusal exists to keep: a refused write leaves no
        line behind, so what is in the file is what reads back."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Fix [the] parser", "./sessions/s.md")
        add_todo(ws, "t", "Fix (bug) in the parser", "./sessions/s.md")
        written = [ln for ln in idx.index_path(d, "todos").read_text().splitlines() if ln]
        assert len(written) == len(idx.read(d, "todos")) == 1
        assert idx.read(d, "todos")[0].title == "Fix (bug) in the parser"

    def test_only_one_todo_is_started_at_a_time(self, tmp_path):
        """Every description of the state is singular, and a list where
        everything ever touched is marked started says nothing."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = {t: json.loads(add_todo(ws, "t", t, "./s.md"))["id"] for t in "ABCD"}
        set_todo_state(ws, "t", ids["B"], "started")
        set_todo_state(ws, "t", ids["C"], "started")
        entries = idx.read(d, "todos")
        assert [(e.title, e.state) for e in entries] == [
            ("C", "started"), ("B", "active"), ("A", "active"), ("D", "active")]

    def test_retiring_takes_it_out_of_next_steps(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Chase the permit", "./s.md")
        todo_id = _only_id(d, "todos")
        assert "Chase the permit" in (d / "README.md").read_text()
        retire_todo(ws, "t", todo_id, "done")
        assert "Chase the permit" not in (d / "README.md").read_text()

    def test_park_and_unpark(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Well driller", "./s.md"); todo_id = _only_id(d, "todos")
        set_todo_state(ws, "t", todo_id, "parked")
        assert idx.read(d, "todos")[0].state == "parked"
        set_todo_state(ws, "t", todo_id, "active")
        assert idx.read(d, "todos")[0].state == "active"

    def test_parking_takes_it_out_of_next_steps(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Call the surveyor", "./s.md")
        todo_id = _only_id(d, "todos")
        assert "Call the surveyor" in (d / "README.md").read_text()
        set_todo_state(ws, "t", todo_id, "parked")
        assert "Call the surveyor" not in (d / "README.md").read_text()
        set_todo_state(ws, "t", todo_id, "active")
        assert "Call the surveyor" in (d / "README.md").read_text()

    def test_a_todo_goes_on_the_end_by_default(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "First", "./s.md")
        add_todo(ws, "t", "Second", "./s.md")
        assert [e.title for e in idx.read(d, "todos")] == ["First", "Second"]

    def test_place_top_names_no_todo(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="top")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_place_top_is_read_at_write_time(self, tmp_path):
        """So a caller holding a list from hours ago, or holding none, still
        lands above everything."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        order_todos(ws, "t", [ids["D"]])
        add_todo(ws, "t", "E", "./s.md", place="top")
        assert [e.title for e in idx.read(d, "todos")] == ["E", "D", "A", "B", "C"]

    def test_place_end_is_the_default_said_out_loud(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="end")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B"]

    def test_place_before_an_anchor(self, tmp_path):
        """Breaking up the current task: the new piece comes first."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Ship the release", "./s.md")
        anchor = _only_id(d, "todos")
        add_todo(ws, "t", "Write the notes", "./s.md", place=f"before:{anchor}")
        assert [e.title for e in idx.read(d, "todos")] == ["Write the notes", "Ship the release"]

    def test_place_after_an_anchor(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "Ship the release", "./s.md")
        anchor = _only_id(d, "todos")
        add_todo(ws, "t", "Tag it", "./s.md")
        add_todo(ws, "t", "Announce it", "./s.md", place=f"after:{anchor}")
        assert [e.title for e in idx.read(d, "todos")] == [
            "Ship the release", "Announce it", "Tag it"]

    def test_spaces_around_the_colon_do_not_change_the_place(self, tmp_path):
        """A space after a colon is what anyone writes, and reading the anchor
        with it attached refuses as a missing todo rather than a spacing slip."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        a = _only_id(d, "todos")
        add_todo(ws, "t", "B", "./s.md", place=f"before : {a}")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_a_padded_position_is_still_that_position(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="  top  ")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_a_position_takes_no_anchor(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "A", "./s.md", place="top:20260101-a"))
        assert out["error"] == "PLACE_UNKNOWN"
        assert idx.read(d, "todos") == []

    def test_a_place_that_is_not_one_of_the_four_forms_is_refused(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "B", "./s.md", place="above:20260101-a"))
        assert out["error"] == "PLACE_UNKNOWN" and out["detail"] == "above:20260101-a"
        assert out["allowed"] == ["top", "end", "before:<id>", "after:<id>"]
        assert idx.read(d, "todos") == []

    def test_an_anchor_that_is_not_in_the_list_is_refused(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        out = _reply(add_todo(ws, "t", "B", "./s.md", place="after:20260101-nope"))
        assert out["error"] == "NO_SUCH_ENTRY" and out["detail"] == "20260101-nope"
        # The form was fine, so listing the forms would point at the wrong fix.
        assert "allowed" not in out
        assert idx.read(d, "todos") == []

    def test_a_todo_added_as_started_goes_to_the_top(self, tmp_path):
        """Otherwise `started` would label the last item on a long list."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", state="started")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_a_place_that_was_asked_for_beats_the_one_the_state_implies(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        a = _only_id(d, "todos")
        add_todo(ws, "t", "B", "./s.md", state="started", place=f"after:{a}")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B"]

    def test_starting_a_todo_moves_it_to_the_top(self, tmp_path):
        """So the bump does not depend on the agent making a second call."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md")
        b = _only_id(d, "todos")
        set_todo_state(ws, "t", b, "started")
        entries = idx.read(d, "todos")
        assert [e.title for e in entries] == ["B", "A"]
        assert entries[0].state == "started"

    def test_unparking_puts_it_at_the_end(self, tmp_path):
        """Parked means for later, so it comes back behind what is current."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        a = _only_id(d, "todos")
        add_todo(ws, "t", "B", "./s.md")
        set_todo_state(ws, "t", a, "parked")
        set_todo_state(ws, "t", a, "active")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_starting_a_parked_todo_brings_it_back_to_the_top(self, tmp_path):
        """Starting something says it is being worked on, parked or not."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md")
        b = _only_id(d, "todos")
        set_todo_state(ws, "t", b, "parked")
        set_todo_state(ws, "t", b, "started")
        entries = idx.read(d, "todos")
        assert [(e.title, e.state) for e in entries] == [("B", "started"), ("A", "active")]
        assert "B" in (d / "README.md").read_text()

    def test_a_blank_place_means_the_default(self, tmp_path):
        """What the tool passes when the model leaves the argument out."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B"]

    def test_order_todos_promotes_to_the_top_by_default(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = []
        for title in ("A", "B", "C", "D"):
            add_todo(ws, "t", title, "./s.md")
            ids.append(_only_id(d, "todos"))
        assert _reply(order_todos(ws, "t", [ids[2], ids[0]]))["ordered"] == 2
        assert [e.title for e in idx.read(d, "todos")] == ["C", "A", "B", "D"]

    def test_order_todos_can_send_them_to_the_end(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        order_todos(ws, "t", [ids["A"]], place="end")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "C", "D", "A"]

    def test_order_todos_before_an_anchor(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        out = _reply(order_todos(ws, "t", [ids["D"]], place=f"before:{ids['B']}"))
        assert out["ordered"] == 1
        assert [e.title for e in idx.read(d, "todos")] == ["A", "D", "B", "C"]

    def test_order_todos_after_an_anchor(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        order_todos(ws, "t", [ids["D"]], place=f"after:{ids['A']}")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "D", "B", "C"]

    def test_the_anchor_does_not_shift_under_what_moves_past_it(self, tmp_path):
        """Locating it in the original list puts the move one place out whenever
        something above the anchor is one of the things moving."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        order_todos(ws, "t", [ids["A"]], place=f"after:{ids['C']}")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "C", "A", "D"]

    def test_several_todos_move_together_in_the_order_given(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        order_todos(ws, "t", [ids["D"], ids["B"]], place=f"after:{ids['A']}")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "D", "B", "C"]

    def test_order_todos_refuses_a_place_it_cannot_read(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        out = _reply(order_todos(ws, "t", [ids["D"]], place="beneath:" + ids["A"]))
        assert out["error"] == "PLACE_UNKNOWN"
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B", "C", "D"]

    def test_order_todos_refuses_an_unknown_anchor(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        out = _reply(order_todos(ws, "t", [ids["D"]], place="after:20260101-nope"))
        assert out["error"] == "NO_SUCH_ENTRY" and out["detail"] == "20260101-nope"
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B", "C", "D"]

    def test_order_todos_refuses_an_anchor_it_is_also_moving(self, tmp_path):
        """Its position is what is being decided, so it cannot also fix one."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        ids = _four_todos(ws)
        out = _reply(order_todos(ws, "t", [ids["D"], ids["B"]], place=f"before:{ids['B']}"))
        assert out["error"] == "ANCHOR_IS_MOVING" and out["detail"] == ids["B"]
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B", "C", "D"]

    def test_order_todos_refuses_an_unknown_id(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        a = _only_id(d, "todos")
        out = _reply(order_todos(ws, "t", [a, "20260101-nope"]))
        assert out["error"] == "NO_SUCH_ENTRY" and "20260101-nope" in out["detail"]
        assert [e.title for e in idx.read(d, "todos")] == ["A"]

    def test_order_todos_refuses_a_repeated_id(self, tmp_path):
        """Silently de-duplicating would reorder the list differently from what
        was asked, and quietly."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        a = _only_id(d, "todos")
        assert _reply(order_todos(ws, "t", [a, a]))["error"] == "DUPLICATE_ID"

    def test_a_crowded_list_says_so_when_a_todo_is_added(self, tmp_path):
        """Deterministic, so it does not rely on the skill being remembered."""
        _thread(tmp_path)
        ws = str(tmp_path)
        for n in range(5):
            assert "active" not in _reply(add_todo(ws, "t", f"T{n}", "./s.md"))
        assert _reply(add_todo(ws, "t", "T5", "./s.md"))["active"] == 6

    def test_a_parked_todo_does_not_count_towards_crowding(self, tmp_path):
        _thread(tmp_path)
        ws = str(tmp_path)
        for n in range(6):
            add_todo(ws, "t", f"T{n}", "./s.md", state="parked")
        assert "active" not in _reply(add_todo(ws, "t", "T6", "./s.md"))

    def test_place_is_not_case_sensitive(self, tmp_path):
        """A model produces a capital as readily as the space the parser
        already forgives."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="TOP")
        assert [e.title for e in idx.read(d, "todos")] == ["B", "A"]

    def test_a_place_of_only_spaces_is_the_default(self, tmp_path):
        """`""` and `" "` both mean the argument was left out."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md", place="   ")
        assert [e.title for e in idx.read(d, "todos")] == ["A", "B"]

    def test_unparking_past_the_window_says_so(self, tmp_path):
        """The other way the list crosses the line, and the only one that was
        silent about it."""
        _thread(tmp_path)
        ws = str(tmp_path)
        ids = [json.loads(add_todo(ws, "t", f"T{n}", "./s.md"))["id"] for n in range(6)]
        set_todo_state(ws, "t", ids[0], "parked")
        assert _reply(set_todo_state(ws, "t", ids[0], "active"))["active"] == 6

    def test_a_comfortable_list_says_nothing_on_a_state_change(self, tmp_path):
        _thread(tmp_path)
        ws = str(tmp_path)
        a = json.loads(add_todo(ws, "t", "A", "./s.md"))["id"]
        assert "active" not in _reply(set_todo_state(ws, "t", a, "parked"))

    def test_retiring_refuses_with_a_code_like_every_other_todo_tool(self, tmp_path):
        """A caller parsing the documented contract throws on a bare sentence."""
        _thread(tmp_path)
        ws = str(tmp_path)
        a = json.loads(add_todo(ws, "t", "A", "./s.md"))["id"]
        bad_state = _reply(retire_todo(ws, "t", a, "started"))
        assert bad_state["error"] == "STATE_UNKNOWN"
        assert bad_state["allowed"] == ["done", "dropped"]
        assert _reply(retire_todo(ws, "t", "20260101-nope", "done"))["error"] == "NO_SUCH_ENTRY"

    def test_ordering_nothing_is_refused(self, tmp_path):
        """An empty list is a caller that built one by mistake, and reporting
        success touches both files for no change."""
        _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        assert _reply(order_todos(ws, "t", []))["error"] == "IDS_REQUIRED"

    def test_bad_state_is_rejected(self, tmp_path):
        _thread(tmp_path)
        assert _reply(add_todo(str(tmp_path), "t", "A", "./s.md", "banana"))["error"] == "STATE_UNKNOWN"


class TestDecisions:
    def test_file_and_index_entry_are_written(self, tmp_path):
        d = _thread(tmp_path)
        log_decision(str(tmp_path), "t", "Use Iceberg",
                           "Chose Iceberg for table format.", "# Body\n", "locked")
        did = _only_id(d, "decisions")
        assert (d / "decisions" / f"{did}.md").exists()
        entries = idx.read(d, "decisions")
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
        live = idx.read(d, "decisions")
        gone = idx.read(d, "decisions", retired=True)
        assert [e.id for e in live] == [e.id for e in live if e.id != old]
        assert gone[0].id == old and gone[0].state == "superseded"

    def test_retire_updates_the_file_status_too(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        log_decision(ws, "t", "X", "Chose X.", "b", "locked"); did = _only_id(d, "decisions")
        retire_decision(ws, "t", did, "withdrawn")
        assert "status: withdrawn" in (d / "decisions" / f"{did}.md").read_text()

    def test_bad_status_rejected(self, tmp_path):
        _thread(tmp_path)
        assert _reply(log_decision(
            str(tmp_path), "t", "T", "s", "b", "locked-ish"))["error"] == "STATUS_UNKNOWN"


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
    def _artifact(self, d, name="20260101-notes.md"):
        (d / "artifacts").mkdir(parents=True, exist_ok=True)
        (d / "artifacts" / name).write_text("# notes\n")
        return f"./artifacts/{name}"

    def test_index_and_retire(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        index_file(ws, "t", self._artifact(d)); aid = _only_id(d, "artifacts")
        entries = idx.read(d, "artifacts")
        assert entries[0].state == "current"
        retire_artifact(ws, "t", aid, "stale")
        live = idx.read(d, "artifacts")
        gone = idx.read(d, "artifacts", retired=True)
        assert live == [] and gone[0].state == "stale"

    def test_the_id_is_the_filename(self, tmp_path):
        """The claim ids.py makes about itself, which a made-up title broke."""
        d = _thread(tmp_path)
        index_file(str(tmp_path), "t", self._artifact(d))
        assert _only_id(d, "artifacts") == "20260101-notes"

    def test_a_description_is_carried_and_an_absent_one_is_not_invented(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        index_file(ws, "t", self._artifact(d), "What the auth flow does")
        index_file(ws, "t", self._artifact(d, "20260102-other.md"))
        entries = idx.read(d, "artifacts")
        assert [e.description for e in entries] == ["What the auth flow does", ""]

    def test_a_directory_is_one_artifact(self, tmp_path):
        """`audit` treats a subdirectory as a single artifact, so indexing must too."""
        d = _thread(tmp_path)
        shots = d / "artifacts" / "20260401-site-photos"
        shots.mkdir(parents=True)
        (shots / "a.png").write_bytes(b"x")
        out = index_file(str(tmp_path), "t", "./artifacts/20260401-site-photos", "from the visit")
        assert "20260401-site-photos" in out
        entry = idx.read(d, "artifacts")[0]
        assert entry.id == "20260401-site-photos"
        assert entry.description == "from the visit"

    def test_a_link_that_resolves_to_nothing_is_refused(self, tmp_path):
        """The boundary: this indexes, it never authors."""
        _thread(tmp_path)
        out = index_file(str(tmp_path), "t", "./artifacts/never-written.md")
        assert _reply(out)["error"] == "MISSING"

    def test_traversal_is_refused(self, tmp_path):
        _thread(tmp_path)
        for link in ("../../etc/passwd", "/etc/passwd", "./artifacts/../../x.md"):
            assert _reply(index_file(str(tmp_path), "t", link))["error"] == "OUTSIDE_THREAD", link

    def test_indexing_the_same_file_twice_amends_rather_than_duplicates(self, tmp_path):
        """It used to mint a second id and report success for both, which left
        two entries on one file and no way to correct a description."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        link = self._artifact(d)
        first = _reply(index_file(ws, "t", link, "The first description."))
        second = _reply(index_file(ws, "t", link, "Shorter."))
        assert first["id"] == second["id"] == "20260101-notes"
        entries = idx.read(d, "artifacts")
        assert len(entries) == 1
        assert entries[0].description == "Shorter."

    def test_re_indexing_without_a_description_keeps_the_one_there(self, tmp_path):
        """Empty means "not given" at this boundary, the way body does. Wiping
        it would make correcting anything else destroy the sentence."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        link = self._artifact(d)
        index_file(ws, "t", link, "What the auth flow does")
        index_file(ws, "t", link)
        assert idx.read(d, "artifacts")[0].description == "What the auth flow does"

    def test_a_retired_artifact_is_not_indexed_a_second_time(self, tmp_path):
        """Retired is still indexed. Minting again would put one file in two
        indexes under two ids, and only one of them would ever be retired."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        link = self._artifact(d)
        index_file(ws, "t", link)
        retire_artifact(ws, "t", "20260101-notes", "stale")
        assert _reply(index_file(ws, "t", link))["id"] == "20260101-notes"
        assert idx.read(d, "artifacts") == []
        assert len(idx.read(d, "artifacts", retired=True)) == 1

    def test_a_description_past_the_cap_is_refused(self, tmp_path):
        """Refused rather than cut. A sentence truncated at 200 characters reads
        as whole, so nobody learns and nobody can tell."""
        d = _thread(tmp_path)
        out = _reply(index_file(str(tmp_path), "t", self._artifact(d), "x" * 201))
        assert out["error"] == "DESCRIPTION_TOO_LONG"
        assert out["detail"] == "200"
        assert idx.read(d, "artifacts") == []

    def test_the_refusal_leaves_the_previous_description_intact(self, tmp_path):
        """The guard runs before anything mutates, so a rejected amendment is
        not half-applied."""
        d = _thread(tmp_path)
        ws = str(tmp_path)
        link = self._artifact(d)
        index_file(ws, "t", link, "A short one.")
        index_file(ws, "t", link, "y" * 400)
        assert idx.read(d, "artifacts")[0].description == "A short one."


class TestIndexDirectory:
    def _thread_with(self, tmp_path, kind, names):
        d = _thread(tmp_path)
        (d / kind).mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / kind / n).write_text("---\nstatus: locked\n---\nx\n")
        return d

    def test_indexes_a_whole_directory_in_one_call(self, tmp_path):
        """Sixty-six sessions was sixty-six round trips before this."""
        d = self._thread_with(tmp_path, "sessions",
                              [f"202601{i:02d}-s{i}.md" for i in range(1, 13)])
        # nothing to report when every file went in
        assert _reply(index_directory(str(tmp_path), "t", "./sessions")) == {}
        assert len(idx.read(d, "sessions")) == 12

    def test_the_readme_is_rendered_once_not_per_file(self, tmp_path):
        d = self._thread_with(tmp_path, "sessions", ["20260101-a.md", "20260102-b.md"])
        before = (d / "README.md").stat().st_mtime_ns
        index_directory(str(tmp_path), "t", "./sessions")
        assert (d / "README.md").stat().st_mtime_ns != before

    def test_a_hundred_files_all_fine_reports_nothing(self, tmp_path):
        """No news is good news: the caller asked for the directory, so silence
        is the answer that it got it."""
        d = self._thread_with(tmp_path, "sessions",
                              [f"2026{(i % 12) + 1:02d}{(i % 28) + 1:02d}-s{i}.md"
                               for i in range(100)])
        out = index_directory(str(tmp_path), "t", "./sessions")
        assert out == "{}"
        assert len(idx.read(d, "sessions")) == 100

    def test_only_the_failures_come_back(self, tmp_path):
        d = self._thread_with(tmp_path, "decisions",
                              [f"202608{(i % 28) + 1:02d}-ok-{i}.md" for i in range(95)])
        for i in range(5):
            (d / "decisions" / f"202607{i + 1:02d}-bad-{i}.md").write_text(
                "---\nstatus: decided\n---\nx\n")
        out = index_directory(str(tmp_path), "t", "./decisions")
        assert set(_reply(out)) == {"refused"}
        assert len(_reply(out)["refused"]["STATUS_UNKNOWN"]) == 5
        assert len(out) < 200, len(out)
        assert len(idx.read(d, "decisions")) == 95

    def test_running_it_twice_adds_nothing(self, tmp_path):
        d = self._thread_with(tmp_path, "sessions", ["20260101-a.md"])
        index_directory(str(tmp_path), "t", "./sessions")
        assert _reply(index_directory(str(tmp_path), "t", "./sessions")) == {}
        assert len(idx.read(d, "sessions")) == 1

    def test_a_refusal_reports_and_does_not_stop_the_rest(self, tmp_path):
        """A migrated thread full of v1 statuses is the reason this matters."""
        d = self._thread_with(tmp_path, "decisions", ["20260101-good.md"])
        (d / "decisions" / "20260102-old.md").write_text("---\nstatus: decided\n---\nx\n")
        r = _reply(index_directory(str(tmp_path), "t", "./decisions"))
        assert r == {"refused": {"STATUS_UNKNOWN": ["20260102-old.md"]}}
        assert [e.id for e in idx.read(d, "decisions")] == ["20260101-good"]

        (d / "decisions" / "20260102-old.md").write_text("---\nstatus: locked\n---\nx\n")
        index_directory(str(tmp_path), "t", "./decisions")
        assert len(idx.read(d, "decisions")) == 2

    def test_refusals_are_grouped_by_cause(self, tmp_path):
        """Per-file detail made a report of twenty-four broken decisions
        10,463 characters, nine tenths of it one sentence repeated."""
        d = _thread(tmp_path)
        (d / "decisions").mkdir(parents=True, exist_ok=True)
        for i in range(24):
            (d / "decisions" / f"202602{i + 1:02d}-broken-{i}.md").write_text(
                f"---\nstatus: locked\nsummary: Lot {i}: subdivides.\n---\nx\n")
        for i in range(3):
            (d / "decisions" / f"202603{i + 1:02d}-old-{i}.md").write_text(
                "---\nstatus: decided\n---\nx\n")
        out = index_directory(str(tmp_path), "t", "./decisions")

        # one key per cause however many files share it, and every file named
        r = _reply(out)
        assert set(r) == {"refused"}
        assert len(r["refused"]["FRONTMATTER_UNPARSEABLE"]) == 24
        assert len(r["refused"]["STATUS_UNKNOWN"]) == 3
        assert len(out) < 900, len(out)

    def test_one_file_still_gets_the_whole_message(self, tmp_path):
        """The batch names the files; index_file is where the detail lives."""
        d = _thread(tmp_path)
        (d / "decisions").mkdir(parents=True, exist_ok=True)
        (d / "decisions" / "20260201-x.md").write_text(
            "---\nstatus: locked\nsummary: Lot: subdivides.\n---\nx\n")
        out = index_file(str(tmp_path), "t", "./decisions/20260201-x.md")
        assert _reply(out)["error"] == "FRONTMATTER_UNPARSEABLE" and "line 3" in _reply(out)["detail"]

    def test_undated_entries_are_named_rather_than_buried(self, tmp_path):
        self._thread_with(tmp_path, "artifacts", ["orphan.md", "20260101-a.md"])
        assert _reply(index_directory(str(tmp_path), "t", "./artifacts"))["undated"] == ["orphan"]

    def test_a_path_outside_the_thread_is_refused(self, tmp_path):
        _thread(tmp_path)
        for link in ("../../etc", "/etc", "./sessions/nested", "./"):
            assert "error" in _reply(index_directory(str(tmp_path), "t", link)), link

    def test_filesystem_metadata_is_not_content(self, tmp_path):
        """A real thread carried fifty of these, and one took a session's id.

        `._20260125-x.md` sorts before `20260125-x.md`, so the AppleDouble file
        claimed that session's id and the real file was demoted to `-2`.
        """
        d = _thread(tmp_path)
        (d / "sessions").mkdir(parents=True, exist_ok=True)
        for n in ("20260125-real.md", ".DS_Store", "._20260125-real.md", "._.DS_Store"):
            (d / "sessions" / n).write_text("x\n")
        assert _reply(index_directory(str(tmp_path), "t", "./sessions")) == {}
        entries = idx.read(d, "sessions")
        assert [(e.id, e.link) for e in entries] == [
            ("20260125-real", "./sessions/20260125-real.md")]

    def test_a_decision_with_invalid_yaml_is_told_what_is_wrong(self, tmp_path):
        """Blaming a missing status sends the reader to the wrong fix: the
        status is fine, the file just cannot be parsed."""
        d = _thread(tmp_path)
        (d / "decisions").mkdir(parents=True, exist_ok=True)
        (d / "decisions" / "20260619-lot.md").write_text(
            "---\nstatus: locked\nsummary: Lot 4 579 subdivides: 6 736 633.\n---\nx\n")
        r = _reply(index_file(str(tmp_path), "t", "./decisions/20260619-lot.md"))
        assert r["error"] == "FRONTMATTER_UNPARSEABLE"
        # the parser's own complaint, with a position, rather than a guess
        assert "line 3" in r["detail"]

    def test_metadata_is_refused_even_when_named_explicitly(self, tmp_path):
        d = _thread(tmp_path)
        (d / "sessions").mkdir(parents=True, exist_ok=True)
        (d / "sessions" / ".DS_Store").write_text("x\n")
        assert _reply(index_file(str(tmp_path), "t", "./sessions/.DS_Store"))["error"] == "METADATA"

    def test_a_missing_directory_is_an_error_not_silence(self, tmp_path):
        """create lays all three down, so a missing one means something is wrong."""
        d = _thread(tmp_path)
        import shutil
        shutil.rmtree(d / "artifacts", ignore_errors=True)
        r = _reply(index_directory(str(tmp_path), "t", "./artifacts"))
        assert r["error"] == "NO_SUCH_DIRECTORY" and r["detail"] == "artifacts"

    def test_a_bad_kind_is_refused(self, tmp_path):
        _thread(tmp_path)
        assert _reply(index_directory(str(tmp_path), "t", "./todos"))["error"] == "NOT_INDEXABLE"


class TestReadmeShape:
    def test_a_v1_readme_is_refused_rather_than_appended_to(self, tmp_path):
        """The Frankenstein case: a real migration hit this and was told it worked.

        A v1 README has `**Next steps**:` as bold text inside `## Quick Resume`,
        not a heading, so the renderer used to staple a second next-step list
        onto an intact v1 document and return success.
        """
        d = _thread(tmp_path)
        (d / "README.md").write_text(
            "# Thread: t\n\n## Quick Resume\n\n**Next steps**:\n- something v1\n\n"
            "## Problem\n\nold format\n"
        )
        out = add_todo(str(tmp_path), "t", "New", "./todos/a.md")
        assert "not a schema 2 README" in out
        text = (d / "README.md").read_text()
        assert "## Next steps" not in text
        assert "**Indexes**:" not in text
        assert "old format" in text

    def test_a_refusal_writes_nothing_at_all(self, tmp_path):
        """Checked before anything mutates, so retrying is clean.

        Recording the entry and refusing the render left a real migration with
        two identical todos: the assistant fixed the README and repeated the
        call, which is what anyone would do.
        """
        d = _thread(tmp_path)
        (d / "README.md").write_text("# Thread: t\n\n## Quick Resume\n\nv1\n")
        add_todo(str(tmp_path), "t", "New", "./todos/a.md")
        assert idx.read(d, "todos") == []

        (d / "README.md").write_text("# t\n\n## Next steps\n\n- None\n\n## About\n\nx\n")
        add_todo(str(tmp_path), "t", "New", "./todos/a.md")
        assert [e.title for e in idx.read(d, "todos")] == ["New"]


class TestInvariant:
    def test_readme_always_equals_the_projection(self, tmp_path):
        d = _thread(tmp_path)
        ws = str(tmp_path)
        add_todo(ws, "t", "A", "./s.md")
        add_todo(ws, "t", "B", "./s.md")
        from ai_workspace.threads.v2 import render
        expected = render.next_steps_body(d)
        section = (d / "README.md").read_text().split("## Next steps\n\n")[1].split("\n\n")[0]
        assert section.strip() == expected.strip()


class TestSaveSession:
    def test_writes_session_status_and_dates(self, tmp_path):
        d = _thread(tmp_path)
        from mcp_server import save_session
        out = save_session(str(tmp_path), "t", "growcer-prep", "Prepped the round.",
                           "growcer, interview",
                           body="# Session\n\nWhat happened.\n",
                           status="Round 3 booked for Friday.")
        assert _reply(out)["status_written"] is True
        sid = _only_id(d, "sessions")
        assert _reply(out)["id"] == sid
        text = (d / "sessions" / f"{sid}.md").read_text()
        fields, _ = split_frontmatter(text)
        assert fields["summary"] == "Prepped the round."
        assert "What happened." in text
        readme = (d / "README.md").read_text()
        assert "Round 3 booked for Friday." in readme
        assert "**Last Session**:" in readme

    def test_the_body_replaces_the_stub(self, tmp_path):
        """The stub lists what the session created; the body is expected to
        cover it, so a save is one write rather than an append."""
        d = _thread(tmp_path)
        from ai_workspace.threads.v2 import session
        from mcp_server import save_session
        sid = session.ensure_stub(d, "topic")
        p = session.session_path(d, sid)
        session.note_created(d, sid, "todo 20260101-x")
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n\nWhat happened.\n")
        text = p.read_text()
        assert "Created during this session" not in text
        assert "What happened." in text
        assert split_frontmatter(text)[0]["summary"] == "s"

    def test_a_file_written_before_the_save_is_indexed(self, tmp_path):
        """A session file that exists before the save still gets an index
        entry, so resume lists it."""
        d = _thread(tmp_path)
        from datetime import date

        from ai_workspace.threads.v2 import ids, session
        from mcp_server import save_session
        sid = ids.make_id(date.today(), "topic")
        p = session.session_path(d, sid)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# Session: topic\n\nWritten directly.\n")
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n")
        assert [e.id for e in idx.read(d, "sessions")] == [sid]

    def test_a_blank_body_is_refused_and_the_file_kept(self, tmp_path):
        """A blank body would replace the file with frontmatter alone, so it is
        refused and the file is left as it was."""
        d = _thread(tmp_path)
        from datetime import date

        from ai_workspace.threads.v2 import ids, session
        from mcp_server import save_session
        p = session.session_path(d, ids.make_id(date.today(), "topic"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# Session: topic\n\nWritten directly.\n")
        for blank in ("", " \n"):
            reply = save_session(str(tmp_path), "t", "topic", "s", "k", blank)
            assert json.loads(reply) == {"error": "BODY_EMPTY"}
        assert p.read_text() == "# Session: topic\n\nWritten directly.\n"

    def test_saving_twice_indexes_once(self, tmp_path):
        d = _thread(tmp_path)
        from mcp_server import save_session
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n")
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n")
        assert len(idx.read(d, "sessions")) == 1

    def test_saving_clears_the_unsaved_marker(self, tmp_path):
        d = _thread(tmp_path)
        from ai_workspace.threads.v2 import session
        from mcp_server import save_session
        session.ensure_stub(d, "topic")
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n")
        sid = _only_id(d, "sessions")
        assert session.STUB_MARKER not in (d / "sessions" / f"{sid}.md").read_text()

    def test_last_session_survives_for_archive(self, tmp_path):
        """archive_thread greps this line; a render must never drop it."""
        d = _thread(tmp_path)
        from mcp_server import save_session
        save_session(str(tmp_path), "t", "topic", "s", "k", "# Session\n", status="x")
        import re
        assert re.search(r"(?m)^\*\*Last Session\*\*: \d{4}-\d{2}-\d{2}$",
                         (d / "README.md").read_text())

    def test_refused_on_schema_1(self, tmp_path):
        _thread(tmp_path, "old", schema=1)
        from mcp_server import save_session
        assert "NEEDS_MIGRATION" in save_session(
            str(tmp_path), "old", "s", "s", "k", "# Session\n")


class TestDating:
    """A file that does not say when it is from is dated by the caller or not at all.

    Nothing is inferred from other files in the thread. A session mentioning a
    filename was read as evidence of when it was made, which it is not, and a
    plausible wrong date is the one kind of error nothing downstream can see.
    """

    def _artifact(self, tmp_path, name):
        d = _thread(tmp_path)
        (d / "artifacts").mkdir(parents=True, exist_ok=True)
        (d / "artifacts" / name).write_text("x\n")
        return d

    def test_an_undated_file_is_marked_unknown(self, tmp_path):
        d = self._artifact(tmp_path, "orphan.md")
        (d / "sessions" / "20260607-real.md").write_text("wrote orphan.md today\n")
        reply = _reply(index_file(str(tmp_path), "t", "./artifacts/orphan.md"))
        assert reply["id"] == "19700101-orphan"
        assert reply["undated"] is True

    def test_a_supplied_date_is_used(self, tmp_path):
        self._artifact(tmp_path, "orphan.md")
        reply = _reply(index_file(
            str(tmp_path), "t", "./artifacts/orphan.md", date="2026-07-27"))
        assert reply["id"] == "20260727-orphan"
        assert "undated" not in reply

    def test_the_filename_wins_over_a_supplied_date(self, tmp_path):
        self._artifact(tmp_path, "20260101-dated.md")
        reply = _reply(index_file(
            str(tmp_path), "t", "./artifacts/20260101-dated.md", date="2026-07-27"))
        assert reply["id"] == "20260101-dated"

    def test_a_date_repairs_an_unknown_entry_and_reports_the_old_id(self, tmp_path):
        d = self._artifact(tmp_path, "orphan.md")
        index_file(str(tmp_path), "t", "./artifacts/orphan.md")
        reply = _reply(index_file(
            str(tmp_path), "t", "./artifacts/orphan.md", date="2026-07-27"))
        assert reply == {"id": "20260727-orphan", "was": "19700101-orphan"}
        assert [e.id for e in idx.read(d, "artifacts")] == ["20260727-orphan"]

    def test_a_repaired_entry_moves_to_where_its_date_puts_it(self, tmp_path):
        d = self._artifact(tmp_path, "orphan.md")
        (d / "artifacts" / "20260301-early.md").write_text("x\n")
        (d / "artifacts" / "20260901-late.md").write_text("x\n")
        index_directory(str(tmp_path), "t", "./artifacts")
        index_file(str(tmp_path), "t", "./artifacts/orphan.md", date="2026-06-01")
        assert [e.id for e in idx.read(d, "artifacts")] == [
            "20260301-early", "20260601-orphan", "20260901-late"]

    def test_a_repair_keeps_the_description(self, tmp_path):
        d = self._artifact(tmp_path, "orphan.md")
        index_file(str(tmp_path), "t", "./artifacts/orphan.md", "what it holds")
        index_file(str(tmp_path), "t", "./artifacts/orphan.md", date="2026-07-27")
        assert idx.read(d, "artifacts")[0].description == "what it holds"

    def test_an_unparseable_date_is_refused_and_writes_nothing(self, tmp_path):
        d = self._artifact(tmp_path, "orphan.md")
        reply = _reply(index_file(
            str(tmp_path), "t", "./artifacts/orphan.md", date="last July"))
        assert reply["error"] == "DATE_INVALID"
        assert not idx.index_path(d, "artifacts").exists()

    def test_redating_to_the_same_date_reports_no_change(self, tmp_path):
        self._artifact(tmp_path, "orphan.md")
        index_file(str(tmp_path), "t", "./artifacts/orphan.md", date="2026-07-27")
        reply = _reply(index_file(
            str(tmp_path), "t", "./artifacts/orphan.md", date="2026-07-27"))
        assert reply == {"id": "20260727-orphan"}
