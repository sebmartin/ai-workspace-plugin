"""Schema 2 primitives: schema detection, indexes, rendering, sessions, dates."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.threads import schema, marker
from ai_workspace.threads.v2 import ids, render, session
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import thread as v2


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "_config"))


def _v2_thread(tmp_path, name="t"):
    d = tmp_path / "threads" / name
    for sub in ("sessions", "decisions", "artifacts", "attachments", "todos"):
        (d / sub).mkdir(parents=True)
    (d / "README.md").write_text(
        "# Thread: t\n\n**Started**: 2026-01-01\n**Status**: Active\n"
        "**Last Session**: 2026-01-01\n**Related Threads**: None\n\n"
        "## Status\n\nWhere things stand.\n\n"
        "## Next steps\n\n- None\n\n"
        "## About\n\nWhat this is.\n"
    )
    marker.write(d, 2)
    return d


class TestSchemaDetection:
    def test_absent_marker_is_schema_1(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        assert marker.read(d) == 1

    def test_marker_is_read_not_inferred(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("7\n")
        assert marker.read(d) == 7

    def test_registered_schema_resolves_to_its_module(self, tmp_path):
        d = _v2_thread(tmp_path)
        thread, err = schema.at(tmp_path, "t", d)
        assert err is None
        assert thread.schema == 2
        assert schema.implementation(thread) is schema.SCHEMAS[2]

    def test_future_schema_is_refused_not_downgraded(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("99\n")
        thread, err = schema.at(tmp_path, "t", d)
        assert thread is None
        assert "SCHEMA_TOO_NEW" in err and "99" in err

    def test_refusal_names_schemas_never_a_plugin_version(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("99\n")
        _, err = schema.at(tmp_path, "t", d)
        assert "3.0" not in err and "plugin version" not in err.lower()

    def test_garbage_marker_is_an_error_not_a_guess(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("banana\n")
        thread, err = schema.at(tmp_path, "t", d)
        assert thread is None and "UNREADABLE_SCHEMA" in err

    def test_readable_range_covers_every_registered_schema(self):
        """The refusal quotes what is registered, not the create-time counter.

        Those diverge on this branch: schema 2 is readable while create still
        writes schema 1, so a message built from CURRENT_SCHEMA would understate
        what the plugin accepts.
        """
        err = schema.unsupported_message("t", 99)
        assert f"{min(schema.SCHEMAS)} to {max(schema.SCHEMAS)}" in err


    def test_last_section_does_not_swallow_the_footer(self, tmp_path):
        d = _v2_thread(tmp_path)
        render.render(d)
        out = v2.compose(d, "t")
        about = out.split("## About\n\n")[1].split("\n##")[0]
        assert "**Indexes**" not in about
        assert about.strip() == "What this is."


class TestIndex:
    def test_missing_index_is_empty_not_an_error(self, tmp_path):
        d = _v2_thread(tmp_path)
        entries, fm = idx.read(d, "decisions")
        assert entries == [] and fm == {}

    def test_index_is_created_on_first_write(self, tmp_path):
        d = _v2_thread(tmp_path)
        assert not idx.index_path(d, "todos").exists()
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        assert idx.index_path(d, "todos").exists()

    def test_round_trip(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "decisions", idx.Entry("20260101-a", "locked", "A", "./decisions/a.md"))
        idx.add(d, "decisions", idx.Entry("20260102-b", "proposed", "B", "./decisions/b.md"))
        entries, _ = idx.read(d, "decisions")
        assert [(e.id, e.state, e.title) for e in entries] == [
            ("20260101-a", "locked", "A"), ("20260102-b", "proposed", "B")]

    def test_id_grep_is_exact_because_colon_terminates_it(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "decisions", idx.Entry("20260101-prep", "locked", "P", "./decisions/p.md"))
        idx.add(d, "decisions", idx.Entry("20260101-prep-ladder", "locked", "PL", "./decisions/pl.md"))
        text = idx.index_path(d, "decisions").read_text()
        assert text.count("- 20260101-prep:") == 1

    def test_sessions_have_no_state(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "sessions", idx.Entry("20260101-s", None, "S", "./sessions/s.md"))
        assert ":" not in idx.index_path(d, "sessions").read_text().split("[")[0]
        entries, _ = idx.read(d, "sessions")
        assert entries[0].state is None

    def test_a_newer_entry_goes_on_the_end(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        first = idx.index_path(d, "todos").read_text()
        idx.add(d, "todos", idx.Entry("20260102-b", "active", "B", "./todos/b.md"))
        assert idx.index_path(d, "todos").read_text().startswith(first)

    def test_an_older_entry_goes_where_its_date_puts_it(self, tmp_path):
        """A session recovered from a transcript after later ones were saved."""
        d = _v2_thread(tmp_path)
        for day in ("03", "05"):
            idx.add(d, "sessions", idx.Entry(f"202601{day}-s", None, day, f"./sessions/{day}.md"))
        idx.add(d, "sessions", idx.Entry("20260104-late", None, "late", "./sessions/late.md"))
        entries, _ = idx.read(d, "sessions")
        assert [e.id for e in entries] == [
            "20260103-s", "20260104-late", "20260105-s"]

    def test_frontmatter_that_does_not_parse_names_the_file(self, tmp_path):
        """Loud, because the windows are what the README's Next steps is built
        from and a silent empty dict would just drop them."""
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        path = idx.index_path(d, "todos")
        path.write_text("---\nwindows:\n\tnext_steps: [20260101-a]\n---\n" + path.read_text())
        with pytest.raises(ValueError) as e:
            idx.read(d, "todos")
        assert "todos-index.md" in str(e.value)

    def test_retire_moves_the_line_and_sets_state(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        assert idx.retire(d, "todos", "20260101-a", "done") is None
        live, _ = idx.read(d, "todos")
        gone, _ = idx.read(d, "todos", retired=True)
        assert live == []
        assert (gone[0].id, gone[0].state) == ("20260101-a", "done")

    def test_retire_rejects_a_state_from_another_type(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        err = idx.retire(d, "todos", "20260101-a", "superseded")
        assert err and "not a retired state" in err

    def test_sessions_do_not_retire(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "sessions", idx.Entry("20260101-s", None, "S", "./sessions/s.md"))
        assert "do not retire" in idx.retire(d, "sessions", "20260101-s", "done")

    def test_window_round_trip(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in "ab":
            idx.add(d, "todos", idx.Entry(f"20260101-{i}", "active", i.upper(), f"./todos/{i}.md"))
        assert idx.set_window(d, "todos", "next_steps", ["20260101-b", "20260101-a"]) is None
        _, fm = idx.read(d, "todos")
        assert fm["windows"]["next_steps"] == ["20260101-b", "20260101-a"]

    def test_window_rejects_unknown_ids(self, tmp_path):
        d = _v2_thread(tmp_path)
        err = idx.set_window(d, "todos", "next_steps", ["nope"])
        assert err and "nope" in err

    def test_setting_a_window_preserves_entries(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-a"])
        entries, _ = idx.read(d, "todos")
        assert len(entries) == 1


class TestRender:
    def test_only_next_steps_is_replaced(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "Do a thing", "./todos/a.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-a"])
        render.render(d)
        text = (d / "README.md").read_text()
        assert "Do a thing" in text
        assert "**Started**: 2026-01-01" in text
        assert "**Related Threads**: None" in text
        assert "Where things stand." in text
        assert "What this is." in text

    def test_hand_edits_outside_next_steps_survive(self, tmp_path):
        d = _v2_thread(tmp_path)
        p = d / "README.md"
        p.write_text(p.read_text().replace("Where things stand.", "HAND EDITED"))
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-a"])
        render.render(d)
        assert "HAND EDITED" in p.read_text()

    def test_render_is_idempotent(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-a"])
        render.render(d)
        once = (d / "README.md").read_text()
        render.render(d)
        assert (d / "README.md").read_text() == once

    def test_window_order_is_preserved_not_index_order(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in "ab":
            idx.add(d, "todos", idx.Entry(f"20260101-{i}", "active", i.upper(), f"./todos/{i}.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-b", "20260101-a"])
        render.render(d)
        body = (d / "README.md").read_text()
        assert body.index("20260101-b") < body.index("20260101-a")

    def test_empty_window_renders_a_placeholder(self, tmp_path):
        d = _v2_thread(tmp_path)
        render.render(d)
        assert "## Next steps\n\n- None" in (d / "README.md").read_text()

    def test_index_links_are_added_once(self, tmp_path):
        d = _v2_thread(tmp_path)
        render.render(d)
        render.render(d)
        assert (d / "README.md").read_text().count("**Indexes**:") == 1


class TestSessionStub:
    def test_stub_created_with_index_entry(self, tmp_path):
        d = _v2_thread(tmp_path)
        sid = session.ensure_stub(d, "my-topic", today=date(2026, 5, 4))
        assert sid == "20260504-my-topic"
        assert session.session_path(d, sid).exists()
        entries, _ = idx.read(d, "sessions")
        assert entries[0].id == sid

    def test_stub_is_created_once(self, tmp_path):
        d = _v2_thread(tmp_path)
        session.ensure_stub(d, "topic", today=date(2026, 5, 4))
        session.ensure_stub(d, "topic", today=date(2026, 5, 4))
        entries, _ = idx.read(d, "sessions")
        assert len(entries) == 1

    def test_dead_session_still_records_what_it_touched(self, tmp_path):
        d = _v2_thread(tmp_path)
        sid = session.ensure_stub(d, "topic", today=date(2026, 5, 4))
        session.note_created(d, sid, "todo 20260504-a")
        assert "todo 20260504-a" in session.session_path(d, sid).read_text()


class TestIds:
    def test_id_shape(self):
        assert ids.make_id(date(2026, 7, 23), "Prep Ladder!") == "20260723-prep-ladder"

    def test_collisions_get_a_suffix(self):
        assert ids.unique_id("20260101-a", {"20260101-a"}) == "20260101-a-2"
        assert ids.unique_id("20260101-a", {"20260101-a", "20260101-a-2"}) == "20260101-a-3"

    def test_ids_sort_chronologically(self):
        assert sorted(["20260301-b", "20260101-a"])[0] == "20260101-a"


class TestCompose:
    def test_payload_has_every_section(self, tmp_path):
        d = _v2_thread(tmp_path)
        (d / "decisions" / "20260101-x.md").write_text(
            "---\ntitle: X\nstatus: locked\nsummary: Chose X because it is simplest.\n---\n")
        idx.add(d, "decisions", idx.Entry("20260101-x", "locked", "X", "./decisions/20260101-x.md"))
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        idx.set_window(d, "todos", "next_steps", ["20260101-a"])
        out = v2.compose(d, "t")
        for section in ("## Status", "## Next steps", "## Decisions in force",
                        "## Artifacts", "## Recent sessions", "## Todo backlog"):
            assert section in out

    def test_decision_summaries_come_from_the_files(self, tmp_path):
        d = _v2_thread(tmp_path)
        (d / "decisions" / "20260101-x.md").write_text(
            "---\ntitle: X\nstatus: locked\nsummary: Chose X because it is simplest.\n---\n")
        idx.add(d, "decisions", idx.Entry("20260101-x", "locked", "X", "./decisions/20260101-x.md"))
        assert "Chose X because it is simplest." in v2.compose(d, "t")

    def test_sessions_are_tailed(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in range(15):
            idx.add(d, "sessions", idx.Entry(f"202601{i:02d}-s", None, f"S{i}", f"./sessions/s{i}.md"))
        out = v2.compose(d, "t")
        assert "(10 of 15)" in out
        assert "20260100-s" not in out

    def test_payload_is_far_smaller_than_a_v1_readme(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in range(35):
            idx.add(d, "decisions", idx.Entry(f"202601{i:02d}-d", "locked", f"D{i}", f"./decisions/d{i}.md"))
        assert len(v2.compose(d, "t").split()) < 700
