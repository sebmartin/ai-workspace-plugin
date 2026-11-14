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


@pytest.mark.parametrize("dash", ["\u2014", "\u2013"])
def test_an_unspaced_em_or_en_dash_starts_a_note(dash):
    line = f"**Related Threads**: [a](../a/README.md){dash}the thread this came out of, and more"
    assert parse_links(H.format(lines=line)) == [
        Link("Related", "a", "a", "the thread this came out of, and more"),
    ]


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


def test_v2_pre_set_about_placeholder_counts_as_none(tmp_path):
    (tmp_path / "threads").mkdir()
    assert not isinstance(threads.create(str(tmp_path), "old"), dict)
    readme = tmp_path / "threads" / "old" / "README.md"
    text = readme.read_text()
    current = text.split("## About\n\n")[1].split("\n")[0]
    readme.write_text(text.replace(current, "What this thread is about, and what it is for."))
    assert about_of(tmp_path, "old") == ""


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


# The linked-threads section of resume.

def _set_header(ws, name, parent="None", child="None", related="None"):
    readme = ws / "threads" / name / "README.md"
    text = readme.read_text()
    text = text.replace("**Parent Thread**: None", f"**Parent Thread**: {parent}")
    text = text.replace("**Child Threads**: None", f"**Child Threads**: {child}")
    text = text.replace("**Related Threads**: None", f"**Related Threads**: {related}")
    readme.write_text(text)


def _v2(ws, name, about=""):
    (ws / "threads").mkdir(exist_ok=True)
    out = threads.create(str(ws), name, about)
    assert not isinstance(out, dict) and not out.startswith("Error"), out


@pytest.fixture
def home(tmp_path):
    ws = tmp_path
    _v2(ws, "parent-project", "x")
    words = " ".join(f"w{i}" for i in range(1, 61))
    p = ws / "threads" / "parent-project" / "README.md"
    text = p.read_text()
    start = text.index("## About")
    p.write_text(text[:start] + f"## About\n\n{words}\n\nSecond paragraph.\n")
    _v1(ws, "old-one", "# old\n\n## About\n\nOld thread purpose.\n")
    (ws / "threads" / "old-one" / "schema-version").write_text("1")
    _v1(ws, "bare", "# bare\n\n## Quick Resume\n\nstuff\n")
    (ws / "threads" / "bare" / "schema-version").write_text("1")
    _v2(ws, "some-topic")
    (ws / "archive" / "shelved").mkdir(parents=True)
    _v1(ws, "odd", "# odd\n\n## About\n\nhidden\n")
    (ws / "threads" / "odd" / "schema-version").write_text("99")
    (ws / "threads" / "empty-dir").mkdir()
    _v2(ws, "fresh", "Short purpose.")
    _v2(ws, "home", "Home.")
    _set_header(
        ws, "home",
        parent="[Parent Project](../parent-project/README.md)",
        child="[old-one](../old-one/README.md) · [bare](../bare/README.md)",
        related=(
            "[some-topic](../some-topic/README.md) — the thread this tool came out of, "
            "[gone](../gone/README.md), [shelved](../shelved/README.md), typed-name, "
            "[odd](../odd/README.md), [empty-dir](../empty-dir/README.md), "
            "[fresh](../fresh/README.md), [parent-project](../parent-project/README.md)"
        ),
    )
    return ws


def test_every_kind_of_link(home):
    out = threads.resume(str(home), "home")
    assert "## Linked threads (10)\n\nBefore saying you don't know something" in out
    for line in [
        "- Parent: [parent-project](../parent-project/README.md) — " + " ".join(f"w{i}" for i in range(1, 51)) + "…",
        "- Child: [old-one](../old-one/README.md) — Old thread purpose.",
        "- Child: [bare](../bare/README.md) — (no About)",
        "- Related: [some-topic](../some-topic/README.md) (note: the thread this tool came out of) — (no About)",
        "- Related: [gone](../gone/README.md) — (not found)",
        "- Related: [shelved](../shelved/README.md) — (archived)",
        "- Related: typed-name",
        "- Related: [odd](../odd/README.md) — (unreadable schema)",
        "- Related: [empty-dir](../empty-dir/README.md) — (not found)",
        "- Related: [fresh](../fresh/README.md) — Short purpose.",
    ]:
        assert line + "\n" in out, line


def test_a_thread_named_twice_is_shown_once_under_its_first_role(home):
    out = threads.resume(str(home), "home")
    assert "- Related: [parent-project]" not in out
    assert out.count("(../parent-project/README.md) —") == 1


def test_the_section_is_last_and_the_header_keeps_its_links(home):
    out = threads.resume(str(home), "home")
    assert out.startswith("Workspace:") and out.rstrip().endswith("Short purpose.")
    assert "**Related Threads**: [some-topic](../some-topic/README.md)" in out


def test_no_links_means_no_section_and_no_cue(tmp_path):
    _v2(tmp_path, "solo", "Alone.")
    out = threads.resume(str(tmp_path), "solo")
    assert "Linked threads" not in out and "Before saying you don't know" not in out


def test_a_schema_1_thread_gets_the_section_too(tmp_path):
    _v2(tmp_path, "fresh", "Short purpose.")
    readme_text = "# old\n\n**Related Threads**: [fresh](../fresh/README.md)\n\n## About\n\nx\n"
    _v1(tmp_path, "old", readme_text)
    (tmp_path / "threads" / "old" / "schema-version").write_text("1")
    out = threads.resume(str(tmp_path), "old")
    assert readme_text in out and "## Linked threads (1)" in out


def test_refused_links_still_resume_and_say_so(tmp_path, monkeypatch):
    from ai_workspace.threads import v1

    readme_text = "# old\n\n**Related Threads**: [fresh](../fresh/README.md)\n\n## About\n\nx\n"
    _v1(tmp_path, "old", readme_text)
    (tmp_path / "threads" / "old" / "schema-version").write_text("1")
    monkeypatch.delattr(v1, "links")
    out = threads.resume(str(tmp_path), "old")
    assert readme_text in out and "## Linked threads" in out and "NEEDS_MIGRATION" in out


def test_resume_writes_nothing(home):
    ws = home
    before = {p: p.read_bytes() for p in Path(ws).rglob("*") if p.is_file()}
    threads.resume(str(ws), "home")
    assert before == {p: p.read_bytes() for p in Path(ws).rglob("*") if p.is_file()}


def test_cut_about():
    assert threads._cut_about("one\ntwo\n\nlater") == "one two"
    assert threads._cut_about(" ".join(["w"] * 60)) == " ".join(["w"] * 50) + "…"
