"""Link parsing and the About read, per schema."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from ai_workspace import threads
from ai_workspace.threads import schema
from ai_workspace.threads.v1.header import Link, parse_links

H = "# t\n\n**Started**: 2026-01-01\n{lines}\n\n## About\n\nx\n"


def _record(ws, name):
    t = schema.at(ws, name, ws / "threads" / name)
    assert not isinstance(t, str), t
    return t


def about_of(ws, name):
    t = _record(ws, name)
    return schema.implementation(t).about(t)


def links_of(ws, name):
    t = _record(ws, name)
    return schema.implementation(t).links(t)


def _v1(ws, name, readme: str | bytes):
    d = ws / "threads" / name
    d.mkdir(parents=True)
    (d / "README.md").write_bytes(readme if isinstance(readme, bytes) else readme.encode())


def test_comma_separated_links():
    line = "**Related Threads**: [a](../a/README.md), [b](../b/README.md)"
    assert [x.name for x in parse_links(H.format(lines=line))] == ["a", "b"]


def test_middot_and_display_names():
    line = "**Child Threads**: [Some Name](../some-name/README.md) · [x](../x/README.md)"
    links = parse_links(H.format(lines=line))
    assert [(x.role, x.name, x.text) for x in links] == [
        ("Child", "some-name", "Some Name"),
        ("Child", "x", "x"),
    ]


@pytest.mark.parametrize("dash", ["\u2014", "\u2013", "-"])
def test_a_note_after_a_dash_keeps_its_commas(dash):
    line = (
        f"**Related Threads**: [some-topic](../some-topic/README.md) {dash} "
        "the thread this tool came out of, and more, [b](../b/README.md)"
    )
    a, b = parse_links(H.format(lines=line))
    assert a.note == "the thread this tool came out of, and more"
    assert (b.name, b.note) == ("b", "")


def test_text_after_a_separator_is_an_unresolved_name():
    line = "**Related Threads**: [a](../a/README.md), bare-name · other"
    assert parse_links(H.format(lines=line)) == [
        Link("Related", "a", "a", ""),
        Link("Related", None, "bare-name", ""),
        Link("Related", None, "other", ""),
    ]


def test_a_link_that_does_not_name_a_thread_readme_is_kept_as_written():
    line = "**Related Threads**: [x](../x/), [docs](https://e.org/a)"
    assert parse_links(H.format(lines=line)) == [
        Link("Related", None, "[x](../x/)", ""),
        Link("Related", None, "[docs](https://e.org/a)", ""),
    ]


@pytest.mark.parametrize("value", ["None", "", "none"])
def test_none_or_empty_is_no_links(value):
    assert parse_links(H.format(lines=f"**Parent Thread**: {value}")) == []


def test_roles_in_header_order_and_only_in_the_header():
    text = (
        H.format(lines="**Parent Thread**: [p](../p/README.md)\n**Child Threads**: [c](../c/README.md)")
        + "\n**Related Threads**: [late](../late/README.md)\n"
    )
    assert [(x.role, x.name) for x in parse_links(text)] == [("Parent", "p"), ("Child", "c")]


def test_crlf_header_parses():
    text = "**Related Threads**: [a](../a/README.md) — why\r\n\r\n## About\r\n"
    assert parse_links(text)[0].note == "why"


def test_v1_about_is_its_section_or_empty(tmp_path):
    _v1(tmp_path, "old", "# old\n\n## About\n\nOld purpose.\n")
    _v1(tmp_path, "quick", "# quick\n\n## Quick Resume\n\nstuff\n")
    assert about_of(tmp_path, "old") == "Old purpose."
    assert about_of(tmp_path, "quick") == ""


def test_v2_about_is_its_section(tmp_path):
    (tmp_path / "threads").mkdir()
    out = threads.create(str(tmp_path), "t2", "Short purpose.")
    assert not isinstance(out, dict), out
    assert about_of(tmp_path, "t2") == "Short purpose."


def test_v2_placeholder_about_counts_as_none(tmp_path):
    (tmp_path / "threads").mkdir()
    out = threads.create(str(tmp_path), "fresh")
    assert not isinstance(out, dict), out
    assert (tmp_path / "threads" / "fresh" / "README.md").exists()
    assert about_of(tmp_path, "fresh") == ""


def test_v2_links_come_from_the_readme_header(tmp_path):
    (tmp_path / "threads").mkdir()
    threads.create(str(tmp_path), "t2", "p")
    readme = tmp_path / "threads" / "t2" / "README.md"
    text = readme.read_text()
    assert "**Related Threads**" in text
    readme.write_text(text.replace("**Related Threads**: None", "**Related Threads**: [a](../a/README.md) — why"))
    assert links_of(tmp_path, "t2") == [Link("Related", "a", "a", "why")]


def test_about_and_links_tolerate_undecodable_bytes(tmp_path):
    _v1(tmp_path, "t", b"# t\n\n**Related Threads**: [a](../a/README.md)\n\n## About\n\nPurpose \xff here.\n")
    assert "Purpose" in about_of(tmp_path, "t")
    assert [x.name for x in links_of(tmp_path, "t")] == ["a"]
