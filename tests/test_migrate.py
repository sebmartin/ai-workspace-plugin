"""Migration safety check and the deterministic half of the conversion audit."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.plugin import get_template_path
from ai_workspace.threads import marker, migrate
from ai_workspace.threads.v2 import index as idx
from mcp_server import add_todo, audit_migration, index_directory, list_todos, set_about


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "_config"))


def _v1(ws, name="t"):
    d = ws / "threads" / name
    (d / "sessions").mkdir(parents=True)
    (d / "decisions").mkdir()
    (d / "artifacts").mkdir()
    (d / "attachments").mkdir()
    (d / "README.md").write_text("# t\n\n## Quick Resume\n\n**Next steps**:\n- a\n")
    (d / "sessions" / "20260101-first.md").write_text("---\ndate: 2026-01-01\n---\nx\n")
    (d / "decisions" / "20260202-choice.md").write_text("---\nsummary: Chose x.\n---\n")
    return d


def _converted_from(v1_dir, ws, name="t-v2", readme=True):
    """The staging copy partway through a conversion.

    The README is replaced first, as the reference instructs, because every
    write tool renders into whatever README is there.
    """
    import shutil
    d = ws / "threads" / name
    shutil.copytree(v1_dir, d)
    marker.write(d, 2)
    if readme:
        (d / "README.md").write_text(
            "# Thread: t\n\n**Started**: 2026-01-01\n\n## Status\n\nx\n\n"
            "## Todos\n\n- None\n\n## About\n\nx\n"
        )
    return d


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)


class TestSafetyCheck:
    def test_no_repo_says_so_and_suggests_one(self, tmp_path):
        _v1(tmp_path)
        out = migrate.safety_check(tmp_path, "t")
        assert "No git repository" in out and "git init" in out

    def test_dirty_thread_is_reported(self, tmp_path):
        _v1(tmp_path)
        _git(["init"], tmp_path)
        out = migrate.safety_check(tmp_path, "t")
        assert "uncommitted change" in out and "not recoverable" in out

    def test_clean_thread_is_cleared(self, tmp_path):
        _v1(tmp_path)
        _git(["init"], tmp_path)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "add", "."], tmp_path)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x"], tmp_path)
        assert "Safe to migrate" in migrate.safety_check(tmp_path, "t")

    def test_scoped_to_the_thread_not_the_workspace(self, tmp_path):
        """An untidy workspace elsewhere must not drown the signal."""
        _v1(tmp_path)
        _git(["init"], tmp_path)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "add", "."], tmp_path)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x"], tmp_path)
        (tmp_path / "unrelated.md").write_text("noise\n")
        assert "Safe to migrate" in migrate.safety_check(tmp_path, "t")


class TestAudit:
    def test_the_audit_refuses_a_damaged_index(self, tmp_path):
        v1 = _v1(tmp_path)
        d = _converted_from(v1, tmp_path)
        (d / "sessions-index.md").write_text("oops\n")
        out = json.loads(migrate.audit(v1, d))
        assert out["error"] == "INDEX_UNREADABLE"

    def test_a_todo_cannot_vouch_for_the_sessions_index(self, tmp_path):
        """The union across indexes passed a thread with no sessions index at all.

        The reference tells you to link an orphan todo to the session it came
        from, so this fired on threads that followed the instructions.
        """
        v1 = _v1(tmp_path)
        d = _converted_from(v1, tmp_path)
        idx.add(d, "decisions", idx.Entry(
            "20260202-choice", "locked", "20260202-choice",
            "./decisions/20260202-choice.md"))
        idx.add(d, "todos", idx.Entry(
            "20260101-a", "active", "A", "./sessions/20260101-first.md"))
        out = migrate.audit(v1, d)
        assert json.loads(out)["unindexed"]["sessions"] == ["20260101-first.md"]

    def test_filesystem_metadata_is_not_reported_as_missing(self, tmp_path):
        """A real audit reported fifty of these, which is how a gate gets ignored."""
        v1 = _v1(tmp_path)
        for name in (".DS_Store", "._20260101-first.md"):
            (v1 / "sessions" / name).write_text("x\n")
        d = _converted_from(v1, tmp_path)
        idx.add(d, "sessions", idx.Entry(
            "20260101-first", None, "20260101-first", "./sessions/20260101-first.md"))
        idx.add(d, "decisions", idx.Entry(
            "20260202-choice", "locked", "20260202-choice", "./decisions/20260202-choice.md"))
        out = migrate.audit(v1, d)
        assert "DS_Store" not in out
        assert json.loads(out)["clean"] is True

    def test_a_custom_readme_section_is_reported(self, tmp_path):
        """A real thread carried twelve standing instructions in one, and the
        migration reported clean while they stopped being read."""
        v1 = _v1(tmp_path)
        (v1 / "README.md").write_text(
            (v1 / "README.md").read_text()
            + "\n## Standing Instructions\n\nDo not speculate outside your competence.\n")
        d = _converted_from(v1, tmp_path)
        idx.add(d, "sessions", idx.Entry(
            "20260101-first", None, "20260101-first", "./sessions/20260101-first.md"))
        idx.add(d, "decisions", idx.Entry(
            "20260202-choice", "locked", "20260202-choice", "./decisions/20260202-choice.md"))
        out = json.loads(migrate.audit(v1, d))
        assert out["readme_sections_to_place"] == ["Standing Instructions"]
        # named, not blocking: the audit cannot see whether it found a home,
        # and failing a correct migration is how a gate gets ignored
        assert out["clean"] is True

    def test_a_half_converted_readme_is_reported(self, tmp_path):
        """Every index can be complete while the README is still the old document."""
        v1 = _v1(tmp_path)
        d = _converted_from(v1, tmp_path, readme=False)
        out = migrate.audit(v1, d)
        assert "## Quick Resume" in json.loads(out)["v1_readme_sections"]

    def test_clean_conversion_reports_no_problems(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.add(conv, "sessions", idx.Entry("20260101-first", None, "First",
                                               "./sessions/20260101-first.md"))
        idx.add(conv, "decisions", idx.Entry("20260202-choice", "locked", "Choice",
                                                "./decisions/20260202-choice.md"))
        out = migrate.audit(v1, conv)
        assert json.loads(out)["clean"] is True

    def test_unindexed_file_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        out = migrate.audit(v1, conv)
        assert json.loads(out)["unindexed"]["sessions"] == ["20260101-first.md"]

    def test_missing_file_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        (conv / "sessions" / "20260101-first.md").unlink()
        assert "missing_from_copy" in json.loads(migrate.audit(v1, conv))

    def test_dangling_index_link_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.add(conv, "artifacts", idx.Entry("20260101-x", "current", "X",
                                                "./artifacts/nope.md"))
        assert "dangling" in json.loads(migrate.audit(v1, conv))

    def test_an_external_todo_link_is_not_dangling(self, tmp_path):
        """A todo tracked in an external system links its item there, which
        `add_todo` accepts, so the audit cannot resolve it as a path and call it
        lost. The audit is what says whether the original is safe to delete, so
        a false `clean: false` either stalls a correct migration or teaches the
        user to ignore it."""
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.add(conv, "todos", idx.Entry(
            "20260101-chase-it", "active", "Chase the upstream issue",
            "https://example.com/owner/repo/issues/16"))
        out = json.loads(migrate.audit(v1, conv))
        assert "todos" not in out.get("dangling", {})

    def test_out_of_order_index_is_caught(self, tmp_path):
        """Written directly, because idx.add would place them in order.

        The audit checks the converted thread however it was produced, which
        includes hand-edited index files.
        """
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.write(conv, "artifacts", [
            idx.Entry("20260301-b", "current", "B", "./artifacts/"),
            idx.Entry("20260101-a", "current", "A", "./artifacts/"),
        ])
        assert "out_of_date_order" in json.loads(migrate.audit(v1, conv))

    def test_a_todo_list_is_not_expected_in_date_order(self, tmp_path):
        """Its order is the priority the user put it in, so a migration that
        got it right would otherwise be reported as broken."""
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.write(conv, "todos", [
            idx.Entry("20260301-b", "active", "B", "./todos/b.md"),
            idx.Entry("20260101-a", "active", "A", "./todos/a.md"),
        ])
        assert "out_of_date_order" not in json.loads(migrate.audit(v1, conv))

    def test_unknown_dates_are_counted(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.add(conv, "artifacts", idx.Entry("19700101-parked", "current", "Parked",
                                                "./artifacts/"))
        assert json.loads(migrate.audit(v1, conv))["undated_entries"] >= 1

    def test_judgment_is_always_left_to_a_reader(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        assert "clean" in json.loads(migrate.audit(v1, conv))

    def test_attachments_are_checked_but_not_indexed(self, tmp_path):
        v1 = _v1(tmp_path)
        (v1 / "attachments" / "spec.pdf").write_text("x")
        conv = _converted_from(v1, tmp_path)
        out = migrate.audit(v1, conv)
        assert "spec.pdf" not in out


class TestGuideEndToEnd:
    def test_the_guide_s_calls_give_next_backlog_and_a_backup_in_next(self, tmp_path):
        """Runs the calls skills/threads/v2/migrate-from-v1.md tells a session to make."""
        import shutil
        ws = tmp_path
        t = ws / "threads" / "t"
        (t / "sessions").mkdir(parents=True)
        (t / "decisions").mkdir()
        (t / "README.md").write_text(
            "# t\n\n## Quick Resume\n\n**Next steps**:\n"
            + "".join(f"- S{n}\n" for n in range(1, 8))
            + "\n## Open Questions\n\n- Q1\n\n## Parked\n\n- P1\n")
        (t / "sessions" / "20260101-first.md").write_text(
            "---\ndate: 2026-01-01\nsummary: First.\n---\nx\n")
        (t / "decisions" / "20260202-choice.md").write_text(
            "---\nstate: locked\nsummary: Chose x.\n---\n")

        v1 = ws / "threads" / "t-v1"
        v2 = ws / "threads" / "t-v2"
        t.rename(v1)
        shutil.copytree(v1, v2)
        marker.write(v2, 2)
        (v2 / "README.md").write_text(
            get_template_path("v2/thread-template.md").read_text()
            .replace("[Thread Name]", "t").replace("[YYYY-MM-DD]", "2026-01-01"))
        index_directory(str(ws), "t-v2", "./sessions")
        index_directory(str(ws), "t-v2", "./decisions")

        template = get_template_path("v2/todo-template.md").read_text()
        (v2 / "todos").mkdir()

        def todo(thread_dir, title, **kwargs):
            slug = title.lower().replace(" ", "-").replace("/", "-")
            name = f"20260101-{slug}"
            (thread_dir / "todos" / f"{name}.md").write_text(
                template.replace("[Todo Title]", title))
            result = json.loads(add_todo(
                str(ws), thread_dir.name, title, f"./todos/{name}.md", **kwargs))
            assert "id" in result, result

        for n in range(1, 6):
            todo(v2, f"S{n}", state="next")
        todo(v2, "S6")
        todo(v2, "S7")
        todo(v2, "Q1")
        todo(v2, "P1", state="parked")
        set_about(str(ws), "t-v2", "short about")
        assert json.loads(audit_migration(str(ws), "t-v1", "t-v2"))["clean"] is True

        v2.rename(ws / "threads" / "t")
        todo(ws / "threads" / "t", "Remove or archive threads/t-v1", state="next")

        def titles(*states):
            return [x["title"] for x in
                    json.loads(list_todos(str(ws), "t", list(states)))["todos"]]

        assert titles("next") == ["S1", "S2", "S3", "S4", "S5",
                                  "Remove or archive threads/t-v1"]
        assert set(titles("backlog")) == {"S6", "S7", "Q1"}
        assert titles("parked") == ["P1"]
