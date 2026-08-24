"""Migration safety check and the deterministic half of the conversion audit."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from ai_workspace.threads import _schema, marker, migrate
from ai_workspace.threads.v2 import index as idx


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


def _converted_from(v1_dir, ws, name="t-v2"):
    import shutil
    d = ws / "threads" / name
    shutil.copytree(v1_dir, d)
    marker.write(d, 2)
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
    def test_clean_conversion_reports_no_problems(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.append(conv, "sessions", idx.Entry("20260101-first", None, "First",
                                               "./sessions/20260101-first.md"))
        idx.append(conv, "decisions", idx.Entry("20260202-choice", "locked", "Choice",
                                                "./decisions/20260202-choice.md"))
        out = migrate.audit(v1, conv)
        assert "No missing files" in out and "PROBLEMS" not in out

    def test_unindexed_file_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        out = migrate.audit(v1, conv)
        assert "not in any index" in out
        assert "20260101-first.md" in out

    def test_missing_file_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        (conv / "sessions" / "20260101-first.md").unlink()
        assert "missing from the copy" in migrate.audit(v1, conv)

    def test_dangling_index_link_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.append(conv, "artifacts", idx.Entry("20260101-x", "current", "X",
                                                "./artifacts/nope.md"))
        assert "links to a missing file" in migrate.audit(v1, conv)

    def test_out_of_order_index_is_caught(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.append(conv, "artifacts", idx.Entry("20260301-b", "current", "B", "./artifacts/"))
        idx.append(conv, "artifacts", idx.Entry("20260101-a", "current", "A", "./artifacts/"))
        assert "not in date order" in migrate.audit(v1, conv)

    def test_unknown_dates_are_counted(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        idx.append(conv, "artifacts", idx.Entry("19700101-parked", "current", "Parked",
                                                "./artifacts/"))
        assert "no derivable date" in migrate.audit(v1, conv)

    def test_judgment_is_always_left_to_a_reader(self, tmp_path):
        v1 = _v1(tmp_path)
        conv = _converted_from(v1, tmp_path)
        assert "Still needs a reader" in migrate.audit(v1, conv)

    def test_attachments_are_checked_but_not_indexed(self, tmp_path):
        v1 = _v1(tmp_path)
        (v1 / "attachments" / "spec.pdf").write_text("x")
        conv = _converted_from(v1, tmp_path)
        out = migrate.audit(v1, conv)
        assert "spec.pdf" not in out
