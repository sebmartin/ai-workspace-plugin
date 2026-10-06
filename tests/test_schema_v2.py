"""Schema 2 primitives: schema detection, indexes, rendering, sessions, dates."""

import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.threads import marker, schema
from ai_workspace.threads.v2 import ids, render, session
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import thread as v2
from ai_workspace.threads.v2 import todos as todos_mod


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "_config"))


def _todos(thread_dir, *pairs):
    """Write the todos index in the order given, which is what order means."""
    idx.write(thread_dir, "todos", [
        idx.Entry(f"20260101-{slug}", state, slug.upper(), f"./todos/{slug}.md")
        for slug, state in pairs
    ])


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
        thread = schema.at(tmp_path, "t", d)
        assert not isinstance(thread, str)
        assert thread.schema == 2
        assert schema.implementation(thread) is schema.SCHEMAS[2]

    def test_future_schema_is_refused_not_downgraded(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("99\n")
        err = schema.at(tmp_path, "t", d)
        assert isinstance(err, str)
        assert "SCHEMA_TOO_NEW" in err and "99" in err

    def test_refusal_names_schemas_never_a_plugin_version(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("99\n")
        err = schema.at(tmp_path, "t", d)
        assert isinstance(err, str)
        assert "3.0" not in err and "plugin version" not in err.lower()

    def test_garbage_marker_is_an_error_not_a_guess(self, tmp_path):
        d = tmp_path / "t"
        d.mkdir()
        (d / "schema-version").write_text("banana\n")
        err = schema.at(tmp_path, "t", d)
        assert isinstance(err, str) and "UNREADABLE_SCHEMA" in err

    def test_readable_range_covers_every_registered_schema(self):
        """The refusal quotes what is registered, not the create-time counter.

        Those diverge on this branch: schema 2 is readable while create still
        writes schema 1, so a message built from CURRENT_SCHEMA would understate
        what the plugin accepts.
        """
        err = json.loads(schema.unsupported_message("t", 99))
        assert err["reads"] == [min(schema.SCHEMAS), max(schema.SCHEMAS)]
        assert err["error"] == "SCHEMA_TOO_NEW"


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
        assert idx.read(d, "decisions") == []

    def test_index_is_created_on_first_write(self, tmp_path):
        d = _v2_thread(tmp_path)
        assert not idx.index_path(d, "todos").exists()
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        assert idx.index_path(d, "todos").exists()

    def test_a_description_round_trips(self, tmp_path):
        """Only artifacts carry one, and the line is its only home."""
        d = _v2_thread(tmp_path)
        idx.add(d, "artifacts", idx.Entry(
            "20260316-notes", "current", "20260316-notes",
            "./artifacts/20260316-notes.md", "What the auth flow does"))
        line = idx.index_path(d, "artifacts").read_text().strip()
        assert line.endswith(" -- What the auth flow does")
        assert idx.read(d, "artifacts")[0].description == "What the auth flow does"

    def test_a_line_without_one_reads_as_no_description(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "decisions", idx.Entry("20260101-a", "locked", "A", "./decisions/a.md"))
        assert idx.read(d, "decisions")[0].description == ""

    def test_round_trip(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "decisions", idx.Entry("20260101-a", "locked", "A", "./decisions/a.md"))
        idx.add(d, "decisions", idx.Entry("20260102-b", "proposed", "B", "./decisions/b.md"))
        entries = idx.read(d, "decisions")
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
        entries = idx.read(d, "sessions")
        assert entries[0].state is None

    def test_a_newer_entry_goes_on_the_end(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "decisions", idx.Entry("20260101-a", "locked", "A", "./decisions/a.md"))
        first = idx.index_path(d, "decisions").read_text()
        idx.add(d, "decisions", idx.Entry("20260102-b", "locked", "B", "./decisions/b.md"))
        assert idx.index_path(d, "decisions").read_text().startswith(first)

    def test_a_retired_todo_goes_where_its_date_puts_it(self, tmp_path):
        """The live list is written whole, by the tool that knows the order.
        `add` only ever appends to the retired index, which is a chronology."""
        d = _v2_thread(tmp_path)
        for slug in ("20260301-z", "20260101-a"):
            idx.add(d, "todos", idx.Entry(slug, "done", slug, f"./todos/{slug}.md"),
                    retired=True)
        assert [e.id for e in idx.read(d, "todos", retired=True)] == [
            "20260101-a", "20260301-z"]

    def test_an_older_entry_goes_where_its_date_puts_it(self, tmp_path):
        """A session recovered from a transcript after later ones were saved."""
        d = _v2_thread(tmp_path)
        for day in ("03", "05"):
            idx.add(d, "sessions", idx.Entry(f"202601{day}-s", None, day, f"./sessions/{day}.md"))
        idx.add(d, "sessions", idx.Entry("20260104-late", None, "late", "./sessions/late.md"))
        entries = idx.read(d, "sessions")
        assert [e.id for e in entries] == [
            "20260103-s", "20260104-late", "20260105-s"]

    def test_a_legacy_window_becomes_the_order_it_stood_for(self, tmp_path):
        """Indexes written before the list carried its own order open with a
        `windows:` block naming the todos Next steps showed. That is a priority
        the user set, so it survives as line order rather than being dropped."""
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"), ("b", "active"), ("c", "active"))
        path = idx.index_path(d, "todos")
        path.write_text(
            "---\nwindows:\n  next_steps: [20260101-c, 20260101-a]\n---\n"
            + path.read_text())
        assert [e.id for e in idx.read(d, "todos")] == [
            "20260101-c", "20260101-a", "20260101-b"]

    def test_a_legacy_window_survives_a_tab_no_parser_accepts(self, tmp_path):
        """One real thread's block is indented with a tab, which is why this is
        read with a pattern rather than a YAML parser."""
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"), ("b", "active"))
        path = idx.index_path(d, "todos")
        path.write_text("---\nwindows:\n\tnext_steps: [20260101-b]\n---\n"
                        + path.read_text())
        assert [e.id for e in idx.read(d, "todos")] == ["20260101-b", "20260101-a"]

    def test_the_next_write_leaves_the_block_behind(self, tmp_path):
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"))
        path = idx.index_path(d, "todos")
        path.write_text("---\nwindows:\n  next_steps: [20260101-a]\n---\n"
                        + path.read_text())
        idx.write(d, "todos", idx.read(d, "todos"))
        assert "windows" not in path.read_text()

    def test_only_a_live_todo_index_is_reordered_by_a_block(self, tmp_path):
        """Nothing ever wrote one anywhere else, and a retired index is a
        chronology, so reordering it would be wrong wherever it came from."""
        d = _v2_thread(tmp_path)
        idx.write(d, "todos", [
            idx.Entry("20260101-a", "done", "A", "./todos/a.md"),
            idx.Entry("20260102-b", "done", "B", "./todos/b.md"),
        ], retired=True)
        path = idx.index_path(d, "todos", retired=True)
        path.write_text("---\nwindows:\n  next_steps: [20260102-b]\n---\n"
                        + path.read_text())
        assert [e.id for e in idx.read(d, "todos", retired=True)] == [
            "20260101-a", "20260102-b"]

    def test_only_an_ordered_kind_is_reordered_by_a_block(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.write(d, "decisions", [
            idx.Entry("20260101-a", "locked", "A", "./decisions/a.md"),
            idx.Entry("20260102-b", "locked", "B", "./decisions/b.md"),
        ])
        path = idx.index_path(d, "decisions")
        path.write_text("---\nwindows:\n  next_steps: [20260102-b]\n---\n"
                        + path.read_text())
        assert [e.id for e in idx.read(d, "decisions")] == [
            "20260101-a", "20260102-b"]

    def test_a_window_naming_a_todo_that_is_gone_is_skipped(self, tmp_path):
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"))
        path = idx.index_path(d, "todos")
        path.write_text(
            "---\nwindows:\n  next_steps: [20260101-retired, 20260101-a]\n---\n"
            + path.read_text())
        assert [e.id for e in idx.read(d, "todos")] == ["20260101-a"]

    def test_retire_moves_the_line_and_sets_state(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        assert idx.retire(d, "todos", "20260101-a", "done") is None
        live = idx.read(d, "todos")
        gone = idx.read(d, "todos", retired=True)
        assert live == []
        assert (gone[0].id, gone[0].state) == ("20260101-a", "done")

    def test_retire_rejects_a_state_from_another_type(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        err = idx.retire(d, "todos", "20260101-a", "superseded")
        assert err == {"error": "STATE_UNKNOWN", "detail": "superseded",
                       "allowed": ["done", "dropped"]}

    def test_sessions_do_not_retire(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "sessions", idx.Entry("20260101-s", None, "S", "./sessions/s.md"))
        err = idx.retire(d, "sessions", "20260101-s", "done")
        assert err == {"error": "NOT_RETIRABLE", "detail": "sessions"}


class TestRender:
    def test_only_next_steps_is_replaced(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "Do a thing", "./todos/a.md"))
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
        render.render(d)
        assert "HAND EDITED" in p.read_text()

    def test_render_is_idempotent(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        render.render(d)
        once = (d / "README.md").read_text()
        render.render(d)
        assert (d / "README.md").read_text() == once

    def test_next_steps_lists_the_active_todos(self, tmp_path):
        """Nothing to be promoted into: being near the top of the list is what
        puts a todo in Next steps."""
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"), ("b", "active"))
        render.render(d)
        text = (d / "README.md").read_text()
        assert "20260101-a" in text and "20260101-b" in text

    def test_next_steps_shows_at_most_a_window(self, tmp_path):
        """The README is a landing page, so this section cannot grow with the
        thread the way an index does."""
        d = _v2_thread(tmp_path)
        _todos(d, *((f"t{n}", "active") for n in range(8)))
        render.render(d)
        body = (d / "README.md").read_text()
        shown = [n for n in range(8) if f"20260101-t{n}" in body]
        assert shown == list(range(todos_mod.COMFORTABLE))

    def test_the_readme_says_how_many_it_is_not_showing(self, tmp_path):
        """A bounded section that hides the rest silently is worse for a reader
        than one that says there is more."""
        d = _v2_thread(tmp_path)
        _todos(d, *((f"t{n}", "active") for n in range(8)))
        render.render(d)
        assert "3 more" in (d / "README.md").read_text()

    def test_the_readme_says_so_when_everything_is_parked(self, tmp_path):
        """`- None` on its own reads as a thread with nothing left to do."""
        d = _v2_thread(tmp_path)
        _todos(d, *((f"t{n}", "parked") for n in range(7)))
        render.render(d)
        body = (d / "README.md").read_text()
        assert "- None" in body
        assert "7 parked in [todos](./todos-index.md)." in body

    def test_nothing_is_said_when_everything_is_shown(self, tmp_path):
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"))
        render.render(d)
        assert "more" not in (d / "README.md").read_text().split("## About")[0]

    def test_a_parked_todo_is_not_a_next_step(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        idx.add(d, "todos", idx.Entry("20260101-b", "parked", "B", "./todos/b.md"))
        render.render(d)
        text = (d / "README.md").read_text()
        assert "20260101-a" in text
        assert "20260101-b" not in text

    def test_line_order_is_what_is_shown_not_date_order(self, tmp_path):
        """A todo added today can belong above one from last year."""
        d = _v2_thread(tmp_path)
        idx.write(d, "todos", [
            idx.Entry("20260301-later", "active", "L", "./todos/l.md"),
            idx.Entry("20260101-older", "active", "O", "./todos/o.md"),
        ])
        render.render(d)
        body = (d / "README.md").read_text()
        assert body.index("20260301-later") < body.index("20260101-older")

    def test_no_active_todos_renders_a_placeholder(self, tmp_path):
        d = _v2_thread(tmp_path)
        render.render(d)
        assert "## Next steps\n\n- None" in (d / "README.md").read_text()

    def test_index_links_are_added_once(self, tmp_path):
        d = _v2_thread(tmp_path)
        render.render(d)
        render.render(d)
        assert (d / "README.md").read_text().count("**Indexes**:") == 1


class TestSessionFile:
    def test_a_session_gets_an_id_and_an_index_entry(self, tmp_path):
        d = _v2_thread(tmp_path)
        sid = session.ensure_stub(d, "my-topic", today=date(2026, 5, 4))
        assert sid == "20260504-my-topic"
        assert session.session_path(d, sid).exists()
        entries = idx.read(d, "sessions")
        assert entries[0].id == sid

    def test_a_session_file_is_created_once(self, tmp_path):
        d = _v2_thread(tmp_path)
        session.ensure_stub(d, "topic", today=date(2026, 5, 4))
        session.ensure_stub(d, "topic", today=date(2026, 5, 4))
        entries = idx.read(d, "sessions")
        assert len(entries) == 1

    def test_the_index_title_is_the_slug_as_the_id_spells_it(self, tmp_path):
        """Passed through raw, a slug carrying `]` wrote a line the index could
        not read back, losing the entry."""
        d = _v2_thread(tmp_path)
        sid = session.ensure_stub(d, "my [topic]", today=date(2026, 5, 4))
        entries = idx.read(d, "sessions")
        assert [(e.id, e.title) for e in entries] == [(sid, "my-topic")]


class TestIds:
    def test_id_shape(self):
        assert ids.make_id(date(2026, 7, 23), "Prep Ladder!") == "20260723-prep-ladder"

    def test_a_long_title_is_capped_at_a_word_boundary(self):
        """A todo titled from a sentence produced a 90-character id."""
        long = "Restart Claude Code so the .claude/settings.json permission allowlist takes effect"
        got = ids.make_id(date(2026, 9, 8), long)
        assert len(got) <= 9 + ids.MAX_SLUG
        assert got == "20260908-restart-claude-code-so-the-claude-settings-json"
        assert not got.endswith("-")

    def test_a_single_long_word_is_cut_rather_than_kept(self):
        got = ids.make_id(date(2026, 9, 8), "a" * 90)
        assert len(got) == 9 + ids.MAX_SLUG

    def test_a_title_with_nothing_sluggable_still_gets_an_id(self):
        assert ids.make_id(date(2026, 9, 8), "...") == "20260908-untitled"

    def test_accented_latin_keeps_its_letters(self):
        """Dropping the accented character whole made `café` into `caf`."""
        assert ids.slugify("café-notes") == "cafe-notes"
        assert ids.slugify("Réunion") == "reunion"
        assert ids.slugify("naïve façade") == "naive-facade"

    def test_a_name_with_no_latin_still_gets_a_usable_id(self):
        """Nothing transliterates, so the id is a placeholder and the link is
        what identifies the file. Two of them stay distinct."""
        taken = set()
        for _ in range(2):
            got = ids.unique_id(ids.make_id(date(2026, 1, 1), "日本語メモ"), taken)
            taken.add(got)
        assert taken == {"20260101-untitled", "20260101-untitled-2"}

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
        out = v2.compose(d, "t")
        for section in ("## Status", "## About", "## Next steps",
                        "## Decisions in force", "## Artifacts", "## Recent sessions"):
            assert section in out

    def test_the_heading_says_what_is_shown_and_what_exists(self, tmp_path):
        """A bounded section conceals nothing if the heading does the counting."""
        d = _v2_thread(tmp_path)
        _todos(d, *([(f"t{n}", "active") for n in range(7)] + [("p", "parked")]))
        assert "## Next steps (5 of 7 active, 1 parked)" in v2.compose(d, "t")

    def test_the_heading_counts_a_short_list_too(self, tmp_path):
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"), ("b", "active"), ("c", "parked"))
        assert "## Next steps (2 of 2 active, 1 parked)" in v2.compose(d, "t")

    def test_an_empty_list_does_not_read_as_an_empty_thread(self, tmp_path):
        """Nothing active while three sit parked is a choice, not a lost index."""
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "parked"), ("b", "parked"), ("c", "parked"))
        assert "## Next steps (0 of 0 active, 3 parked)\n\n- None" in v2.compose(d, "t")

    def test_parked_todos_are_listed_after_the_active_ones(self, tmp_path):
        d = _v2_thread(tmp_path)
        _todos(d, ("a", "active"), ("b", "parked"))
        out = v2.compose(d, "t")
        assert out.index("## Next steps") < out.index("## Parked")
        assert out.index("20260101-a") < out.index("20260101-b")

    def test_the_heading_is_the_only_thing_that_counts(self, tmp_path):
        """The line telling the agent to ask about parking belongs where the
        heading is not: in a tool reply. Under a heading that already says
        `5 of 6 active` it is the same sentence twice."""
        d = _v2_thread(tmp_path)
        _todos(d, *((f"t{n}", "active") for n in range(6)))
        out = v2.compose(d, "t")
        assert "## Next steps (5 of 6 active, 0 parked)" in out
        assert "ask the user which to park" not in out

    def test_nothing_parked_means_no_parked_section(self, tmp_path):
        d = _v2_thread(tmp_path)
        idx.add(d, "todos", idx.Entry("20260101-a", "active", "A", "./todos/a.md"))
        assert "## Parked" not in v2.compose(d, "t")

    def test_a_few_attachments_are_listed(self, tmp_path):
        """Cheap enough to be worth saving the caller a directory listing."""
        d = _v2_thread(tmp_path)
        for n in ("survey.pdf", "plan.png"):
            (d / "attachments" / n).write_bytes(b"x")
        (d / "attachments" / ".DS_Store").write_bytes(b"x")
        out = v2.compose(d, "t")
        assert "## Attachments (2)" in out
        assert "plan.png, survey.pdf" in out
        assert "DS_Store" not in out

    def test_many_attachments_are_counted_instead(self, tmp_path):
        """Eighty-six filenames was 15% of a real resume, and nobody read them."""
        d = _v2_thread(tmp_path)
        for i in range(30):
            (d / "attachments" / f"survey-scan-{i}.pdf").write_bytes(b"x")
        out = v2.compose(d, "t")
        assert "## Attachments (30)" in out
        assert "survey-scan-0.pdf" not in out
        assert "List `attachments/`" in out

    def test_decision_summaries_come_from_the_files(self, tmp_path):
        d = _v2_thread(tmp_path)
        (d / "decisions" / "20260101-x.md").write_text(
            "---\ntitle: X\nstatus: locked\nsummary: Chose X because it is simplest.\n---\n")
        idx.add(d, "decisions", idx.Entry("20260101-x", "locked", "X", "./decisions/20260101-x.md"))
        assert "Chose X because it is simplest." in v2.compose(d, "t")

    def test_one_unparseable_decision_does_not_break_the_thread(self, tmp_path):
        """A real thread had twenty-nine of these and would not have opened.

        An unquoted `summary:` containing ": " is invalid YAML, and schema 1
        never parsed it so nobody knew. Resume flags it rather than failing.
        """
        d = _v2_thread(tmp_path)
        (d / "decisions" / "20260619-lot.md").write_text(
            "---\ntitle: Lot\nstatus: locked\n"
            "summary: Lot 4 579 257 subdivides per NF plan: 6 736 633 and 6 736 634.\n"
            "---\nbody\n")
        idx.add(d, "decisions", idx.Entry(
            "20260619-lot", "locked", "20260619-lot", "./decisions/20260619-lot.md"))
        out = v2.compose(d, "t")
        assert "20260619-lot" in out
        assert "not valid YAML" in out

    def test_sessions_are_tailed(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in range(15):
            idx.add(d, "sessions", idx.Entry(f"202601{i:02d}-s", None, f"S{i}", f"./sessions/s{i}.md"))
        out = v2.compose(d, "t")
        assert "(10 of 15)" in out
        assert "20260100-s" not in out

    def test_memory_is_inlined_whole_and_first(self, tmp_path):
        """The one body the payload carries, ahead of anything it qualifies.

        Everything else is a line per record. Memory is inlined because a rule
        read after the work it governs has already been broken.
        """
        d = _v2_thread(tmp_path)
        (d / "memory.md").write_text(
            "## House rules\n\n"
            "- Never quote a decision id outside the workspace. [Seb, 2026-08-13]\n"
        )
        out = v2.compose(d, "t")
        assert "## Thread memory" in out
        assert "Never quote a decision id outside the workspace. [Seb, 2026-08-13]" in out
        assert out.index("## Thread memory") < out.index("## Status")

    def test_no_memory_file_means_no_section(self, tmp_path):
        """Absence is the empty case, so create writes no stub."""
        d = _v2_thread(tmp_path)
        assert not (d / "memory.md").exists()
        assert "Thread memory" not in v2.compose(d, "t")

    def test_an_emptied_memory_file_reads_as_none(self, tmp_path):
        """Pruning the last entry leaves a file. A heading over nothing would
        read as a section that failed to load."""
        d = _v2_thread(tmp_path)
        (d / "memory.md").write_text("\n\n")
        assert "Thread memory" not in v2.compose(d, "t")

    def test_a_thread_worth_opening_says_nothing_about_its_size(self, tmp_path):
        """Silence is the common case, so it is what costs nothing."""
        d = _v2_thread(tmp_path)
        assert "Thread size" not in v2.compose(d, "t")

    def test_an_expensive_thread_says_what_it_costs(self, tmp_path):
        d = _v2_thread(tmp_path)
        (d / "memory.md").write_text("word " * 12_000)
        out = v2.compose(d, "t")
        assert out.startswith("## Thread size")
        assert "tokens per resume" in out

    def test_the_notice_survives_a_truncated_tail(self, tmp_path):
        """Ahead of memory, which is otherwise first. A warning at the end of a
        payload big enough to be cut is a warning nobody receives."""
        d = _v2_thread(tmp_path)
        (d / "memory.md").write_text("word " * 12_000)
        out = v2.compose(d, "t")
        assert out.index("## Thread size") < out.index("## Thread memory")

    def test_the_figure_cannot_read_as_measured(self, tmp_path):
        """Two significant figures. It is chars divided by a constant, and the
        vendors' tokenizers disagree, so anything finer would be a claim we
        cannot make."""
        d = _v2_thread(tmp_path)
        (d / "memory.md").write_text("word " * 12_000)
        found = re.search(r"~([\d,]+) tokens", v2.compose(d, "t"))
        assert found, "the notice carries no token count"
        digits = found.group(1).replace(",", "")
        assert digits[2:] == "0" * len(digits[2:]), f"reported {digits}"

    def test_payload_is_far_smaller_than_a_v1_readme(self, tmp_path):
        d = _v2_thread(tmp_path)
        for i in range(35):
            idx.add(d, "decisions", idx.Entry(f"202601{i:02d}-d", "locked", f"D{i}", f"./decisions/d{i}.md"))
        assert len(v2.compose(d, "t").split()) < 700
