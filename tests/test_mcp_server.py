"""Unit tests for skills/threads/mcp_server.py business logic."""

import io
import json
import sys
import tarfile
import time
from pathlib import Path

import pytest

# Add mcp_server's parent to path so we can import its functions
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

import mcp_server
from mcp_server import (
    archive_thread,
    create_thread,
    resume_thread,
    inspect_archive,
    list_archived_threads,
    list_threads,
    purge_archive_tmp,
    resolve_workspace,
    restore_thread,
    set_default_workspace,
)
from workspace_utils import get_config_dir, read_config, write_config


@pytest.fixture(autouse=True)
def _isolated_config_dir(tmp_path, monkeypatch):
    """Keep tests deterministic by pointing AI_WORKSPACE_CONFIG_DIR at an empty per-test dir.

    Without this, tools that read config (now including every operating tool, since
    each does its own workspace resolution) could pick up a real default_workspace
    from the developer's machine.
    """
    monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "_config"))


def _make_thread(workspace, name, started="2026-01-15", last_session="2026-04-22"):
    """Helper: create a thread directory with README + a session file."""
    thread = workspace / "threads" / name
    thread.mkdir(parents=True)
    (thread / "README.md").write_text(
        f"# Thread: {name}\n\n"
        f"**Started**: {started}\n"
        f"**Status**: Active\n"
        f"**Last Session**: {last_session}\n\n"
        "## Quick Resume\n\n"
        "**Current focus**: testing\n"
    )
    (thread / "sessions").mkdir()
    (thread / "sessions" / "20260415-first.md").write_text("session content\n")
    (thread / "decisions").mkdir()
    return thread


class TestListThreads:
    def test_no_workspace_returns_error(self, tmp_path):
        """Bare dir + no config → NO_WORKSPACE."""
        result = list_threads(str(tmp_path))
        assert "Error: NO_WORKSPACE" in result

    def test_config_fallback_used(self, tmp_path):
        """Bare cwd but config points to a real workspace → resolve via config."""
        workspace = tmp_path / "workspace"
        (workspace / "threads").mkdir(parents=True)
        write_config({"default_workspace": str(workspace)})

        bare = tmp_path / "bare"
        bare.mkdir()
        result = list_threads(str(bare))
        # Workspace resolved via config and is empty → "No threads found".
        assert "No threads found" in result

    def test_empty_threads_dir(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = list_threads(str(tmp_path))
        assert "No threads found" in result

    def test_dirs_without_readme_excluded(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        (threads / "no-readme").mkdir()
        result = list_threads(str(tmp_path))
        assert "No threads found" in result

    def test_single_thread(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text("# My Thread")
        result = list_threads(str(tmp_path))
        assert "1. my-thread" in result

    def test_sorted_by_mtime_most_recent_first(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()

        older = threads / "older-thread"
        older.mkdir()
        readme_older = older / "README.md"
        readme_older.write_text("# Older")

        # Sleep briefly to ensure distinct mtimes
        time.sleep(0.01)

        newer = threads / "newer-thread"
        newer.mkdir()
        readme_newer = newer / "README.md"
        readme_newer.write_text("# Newer")

        result = list_threads(str(tmp_path))
        lines = result.strip().split("\n")
        assert lines[0].startswith("1. newer-thread")
        assert lines[1].startswith("2. older-thread")


class TestConfigDir:
    def test_uses_valid_config_dir_env(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(config_dir))

        assert get_config_dir() == config_dir

    def test_expands_user_in_config_dir_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv(
            "AI_WORKSPACE_CONFIG_DIR",
            "~/.config/ai-workspace",
        )

        assert get_config_dir() == tmp_path / ".config" / "ai-workspace"

    def test_default_uses_xdg_config_home(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AI_WORKSPACE_CONFIG_DIR", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        assert get_config_dir() == tmp_path / "xdg" / "ai-workspace"

    def test_default_falls_back_to_dot_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("AI_WORKSPACE_CONFIG_DIR", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        assert get_config_dir() == tmp_path / ".config" / "ai-workspace"


class TestResumeThread:
    def test_missing_thread(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = resume_thread(str(tmp_path), "nonexistent")
        assert "not found" in result

    def test_returns_full_readme(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text(
            "# My Thread\n\n"
            "## Quick Resume\n\n"
            "**Focus**: current focus\n\n"
            "## About\n\n"
            "This thread is about something.\n\n"
            "## Decisions\n\n"
            "- None\n"
        )
        result = resume_thread(str(tmp_path), "my-thread")
        assert "**Focus**: current focus" in result
        assert "## About" in result
        assert "## Decisions" in result

    def test_success_includes_workspace_and_thread_headers(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text("# My Thread\n**Focus**: x\n")
        result = resume_thread(str(tmp_path), "my-thread")
        assert result.startswith(
            f"Workspace: {tmp_path}\nThread: {tmp_path / 'threads' / 'my-thread'}\n\n"
        )

    def test_error_returns_no_headers(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = resume_thread(str(tmp_path), "nonexistent")
        assert not result.startswith("Workspace:")
        assert "not found" in result


class TestCreateThread:
    def test_creates_thread_in_local_workspace(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = create_thread(str(tmp_path), "my-feature")
        assert "Created thread 'my-feature'" in result
        thread = tmp_path / "threads" / "my-feature"
        assert (thread / "README.md").exists()
        for sub in ("sessions", "decisions", "attachments", "artifacts"):
            assert (thread / sub).is_dir()

    def test_success_includes_workspace_and_thread_headers(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = create_thread(str(tmp_path), "headered")
        assert result.startswith(
            f"Workspace: {tmp_path}\nThread: {tmp_path / 'threads' / 'headered'}\n\n"
        )

    def test_already_exists_error_has_no_headers(self, tmp_path):
        (tmp_path / "threads" / "dupe").mkdir(parents=True)
        (tmp_path / "threads" / "dupe" / "README.md").write_text("# x")
        result = create_thread(str(tmp_path), "dupe")
        assert not result.startswith("Workspace:")
        assert "already exists" in result

    def test_invalid_name_rejected_before_resolution(self, tmp_path):
        # Bare dir, but name validation runs first so we should see name error,
        # not NO_WORKSPACE.
        result = create_thread(str(tmp_path), "Bad Name")
        assert "Invalid thread name" in result
        assert "NO_WORKSPACE" not in result

    def test_ambiguous_when_config_default_exists(self, tmp_path):
        """Bare cwd + config default set → ask the user which to use."""
        workspace = tmp_path / "configured-workspace"
        (workspace / "threads").mkdir(parents=True)
        write_config({"default_workspace": str(workspace)})

        bare = tmp_path / "elsewhere"
        bare.mkdir()
        result = create_thread(str(bare), "new-thread")
        assert "Status: AMBIGUOUS_WORKSPACE" in result
        assert str(workspace) in result
        assert str(bare) in result
        # Thread must NOT have been created in either location.
        assert not (workspace / "threads" / "new-thread").exists()
        assert not (bare / "threads" / "new-thread").exists()

    def test_needs_init_when_no_workspace_anywhere(self, tmp_path):
        """Bare cwd + no config → ask the user to init here or supply a path."""
        bare = tmp_path / "fresh-dir"
        bare.mkdir()
        result = create_thread(str(bare), "first-thread")
        assert "Status: NEEDS_INIT" in result
        assert str(bare) in result
        assert not (bare / "threads").exists()

    def test_retry_with_configured_path_succeeds(self, tmp_path):
        """After AMBIGUOUS, retry with cwd=<configured> works as the response suggests."""
        workspace = tmp_path / "configured-workspace"
        (workspace / "threads").mkdir(parents=True)
        write_config({"default_workspace": str(workspace)})

        result = create_thread(str(workspace), "from-retry")
        assert "Created thread 'from-retry'" in result
        assert (workspace / "threads" / "from-retry" / "README.md").exists()


class TestResolveWorkspace:
    def test_local_threads_dir(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = json.loads(resolve_workspace(str(tmp_path)))
        assert result["source"] == "local"
        assert result["workspace_dir"] == str(tmp_path)

    def test_config_fallback(self, tmp_path, monkeypatch):
        # Set up a workspace with threads in a separate dir
        workspace = tmp_path / "workspace"
        (workspace / "threads").mkdir(parents=True)

        # Point config dir to tmp_path
        data_dir = tmp_path / "config"
        data_dir.mkdir()
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        # Write config with default_workspace
        config_path = data_dir / "config.json"
        config_path.write_text(json.dumps({"default_workspace": str(workspace)}))

        # cwd has no threads/
        cwd = tmp_path / "other-repo"
        cwd.mkdir()

        result = json.loads(resolve_workspace(str(cwd)))
        assert result["source"] == "config"
        assert result["workspace_dir"] == str(workspace)

    def test_no_workspace_found(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "config"
        data_dir.mkdir()
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        result = json.loads(resolve_workspace(str(tmp_path)))
        assert result["source"] == "none"
        assert result["workspace_dir"] is None

    def test_config_path_missing(self, tmp_path, monkeypatch):
        """Config points to a workspace that no longer exists."""
        data_dir = tmp_path / "config"
        data_dir.mkdir()
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        config_path = data_dir / "config.json"
        config_path.write_text(json.dumps({"default_workspace": "/nonexistent/path"}))

        result = json.loads(resolve_workspace(str(tmp_path)))
        assert result["source"] == "none"
        assert result["workspace_dir"] is None

    def test_local_takes_priority_over_config(self, tmp_path, monkeypatch):
        """Local threads/ dir wins even if config is set."""
        (tmp_path / "threads").mkdir()

        remote = tmp_path / "remote-workspace"
        (remote / "threads").mkdir(parents=True)

        data_dir = tmp_path / "config"
        data_dir.mkdir()
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))
        (data_dir / "config.json").write_text(
            json.dumps({"default_workspace": str(remote)})
        )

        result = json.loads(resolve_workspace(str(tmp_path)))
        assert result["source"] == "local"
        assert result["workspace_dir"] == str(tmp_path)


class TestSetDefaultWorkspace:
    def test_sets_workspace(self, tmp_path, monkeypatch):
        workspace = tmp_path / "workspace"
        (workspace / "threads").mkdir(parents=True)

        data_dir = tmp_path / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        result = set_default_workspace(str(workspace))
        assert "Default workspace set" in result

        config = json.loads((data_dir / "config.json").read_text())
        assert config["default_workspace"] == str(workspace.resolve())

    def test_rejects_missing_directory(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        result = set_default_workspace("/nonexistent/path")
        assert "Error" in result
        assert "does not exist" in result

    def test_rejects_dir_without_threads(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        result = set_default_workspace(str(tmp_path))
        assert "Error" in result
        assert "No threads/ directory" in result


class TestConfigHelpers:
    def test_read_missing_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(tmp_path / "nonexistent"))
        assert read_config() == {}

    def test_write_and_read_config(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        write_config({"default_workspace": "/some/path"})
        config = read_config()
        assert config["default_workspace"] == "/some/path"

    def test_write_creates_directory(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "nested" / "config"
        monkeypatch.setenv("AI_WORKSPACE_CONFIG_DIR", str(data_dir))

        write_config({"key": "value"})
        assert data_dir.exists()
        assert (data_dir / "config.json").exists()


class TestArchiveThread:
    def test_success_tar_gz(self, tmp_path):
        _make_thread(tmp_path, "scratch")
        result = archive_thread(
            str(tmp_path), "scratch",
            summary="Quick test thread.",
            keywords=["test", "scratch"],
            body="## Topics\n\nTest body content.\n",
        )
        assert "Archived 'scratch'" in result
        assert (tmp_path / "archive" / "2026-scratch.tar.gz").exists()
        assert (tmp_path / "archive" / "2026-scratch.md").exists()
        assert not (tmp_path / "threads" / "scratch").exists()

        summary = (tmp_path / "archive" / "2026-scratch.md").read_text()
        assert "thread: scratch" in summary
        assert "started: 2026-01-15" in summary
        assert "last_active: 2026-04-22" in summary
        assert 'summary: "Quick test thread."' in summary
        assert "keywords:" in summary
        assert '- "test"' in summary
        assert "Test body content." in summary

    def test_invalid_thread_name(self, tmp_path):
        result = archive_thread(str(tmp_path), "Bad Name", "s", [], "b")
        assert "Invalid thread name" in result

    def test_missing_thread(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = archive_thread(str(tmp_path), "ghost", "s", [], "b")
        assert "not found" in result

    def test_conflict_blocks_archive(self, tmp_path):
        _make_thread(tmp_path, "scratch")
        archive_thread(str(tmp_path), "scratch", "s", [], "b")
        _make_thread(tmp_path, "scratch")
        result = archive_thread(str(tmp_path), "scratch", "s", [], "b")
        assert "already exists" in result

    def test_mtime_fallback_when_readme_lacks_dates(self, tmp_path):
        thread = tmp_path / "threads" / "no-dates"
        thread.mkdir(parents=True)
        (thread / "README.md").write_text("# Thread\n\n**Status**: Active\n")
        result = archive_thread(str(tmp_path), "no-dates", "s", [], "b")
        assert "Archived" in result
        summary = (tmp_path / "archive" / "2026-no-dates.md").read_text()
        # Both dates present (ISO format YYYY-MM-DD), came from mtime fallback
        assert "started: " in summary
        assert "last_active: " in summary

    def test_schema_version_in_frontmatter(self, tmp_path):
        _make_thread(tmp_path, "ver")
        archive_thread(str(tmp_path), "ver", "s", [], "b")
        summary = (tmp_path / "archive" / "2026-ver.md").read_text()
        assert "schema_version: 1" in summary

    def test_symlink_in_thread_rejected(self, tmp_path):
        thread = _make_thread(tmp_path, "linky")
        (thread / "danger").symlink_to(tmp_path)
        result = archive_thread(str(tmp_path), "linky", "s", [], "b")
        assert "Error" in result
        assert "symlinks" in result.lower()
        # Original intact, no archive written
        assert thread.exists()
        assert not (tmp_path / "archive" / "2026-linky.tar.gz").exists()
        assert not (tmp_path / "archive" / "2026-linky.md").exists()

    def test_keyword_normalisation(self, tmp_path):
        _make_thread(tmp_path, "norm")
        archive_thread(
            str(tmp_path), "norm", "s",
            ["Auth", "  auth ", "OAuth", "oauth", ""],
            "b",
        )
        summary = (tmp_path / "archive" / "2026-norm.md").read_text()
        # Preserve order of first-seen, lowercase, dedup
        idx_auth = summary.index('- "auth"')
        idx_oauth = summary.index('- "oauth"')
        assert idx_auth < idx_oauth
        # No "Auth" or "OAuth" variants
        assert '- "Auth"' not in summary
        assert '- "OAuth"' not in summary

    def test_empty_keywords_emits_inline_list(self, tmp_path):
        _make_thread(tmp_path, "nokw")
        archive_thread(str(tmp_path), "nokw", "s", [], "b")
        summary = (tmp_path / "archive" / "2026-nokw.md").read_text()
        assert "keywords: []" in summary

    def test_summary_with_special_chars_escaped(self, tmp_path):
        _make_thread(tmp_path, "esc")
        archive_thread(
            str(tmp_path), "esc",
            'has: colons and "quotes"',
            [], "b",
        )
        summary = (tmp_path / "archive" / "2026-esc.md").read_text()
        assert 'summary: "has: colons and \\"quotes\\""' in summary

    def test_integrity_guard_rollback(self, tmp_path, monkeypatch):
        """If verify fails, archive deleted, original intact, no summary."""
        _make_thread(tmp_path, "guard")
        monkeypatch.setattr(
            mcp_server, "_verify_archive",
            lambda *a, **kw: "fake integrity failure",
        )
        result = archive_thread(str(tmp_path), "guard", "s", [], "b")
        assert "Error" in result and "fake integrity failure" in result
        assert (tmp_path / "threads" / "guard").exists()
        assert (tmp_path / "threads" / "guard" / "README.md").exists()
        assert not (tmp_path / "archive" / "2026-guard.tar.gz").exists()
        assert not (tmp_path / "archive" / "2026-guard.md").exists()

    def test_summary_write_failure_rollback(self, tmp_path, monkeypatch):
        """If summary write fails, archive deleted, original intact."""
        _make_thread(tmp_path, "sumfail")

        original_write_text = Path.write_text
        def boom(self, *args, **kwargs):
            if self.name.endswith(".md") and "archive" in self.parts:
                raise OSError("simulated disk full")
            return original_write_text(self, *args, **kwargs)
        monkeypatch.setattr(Path, "write_text", boom)

        result = archive_thread(str(tmp_path), "sumfail", "s", [], "b")
        assert "Error" in result
        assert (tmp_path / "threads" / "sumfail").exists()
        assert not (tmp_path / "archive" / "2026-sumfail.tar.gz").exists()


class TestRestoreThread:
    def _archive(self, tmp_path, name="rt"):
        _make_thread(tmp_path, name)
        archive_thread(str(tmp_path), name, "s", ["k"], "b")
        return f"2026-{name}"

    def test_round_trip_tar_gz(self, tmp_path):
        base = self._archive(tmp_path, "rt")
        result = restore_thread(str(tmp_path), base)
        assert "Restored to threads/rt" in result
        assert (tmp_path / "threads" / "rt" / "README.md").exists()
        assert (tmp_path / "threads" / "rt" / "sessions" / "20260415-first.md").exists()
        assert not (tmp_path / "archive" / f"{base}.tar.gz").exists()
        assert not (tmp_path / "archive" / f"{base}.md").exists()

    def test_restored_session_written(self, tmp_path):
        _make_thread(tmp_path, "rs")
        archive_thread(
            str(tmp_path), "rs",
            summary="The original summary.",
            keywords=["k1", "k2"],
            body="## Topics\n\nOriginal body content here.\n",
        )
        restore_thread(str(tmp_path), "2026-rs")
        sessions = list((tmp_path / "threads" / "rs" / "sessions").glob("*-restored.md"))
        assert len(sessions) == 1, f"expected exactly one restored-session, got {sessions}"
        text = sessions[0].read_text()
        assert "Restored from archive" in text
        assert "The original summary." in text
        assert "Original body content here." in text
        # Pre-existing sessions are preserved
        assert (tmp_path / "threads" / "rs" / "sessions" / "20260415-first.md").exists()

    def test_collision_appends_restored(self, tmp_path):
        base = self._archive(tmp_path, "coll")
        # Create a conflicting thread before restoring
        _make_thread(tmp_path, "coll")
        result = restore_thread(str(tmp_path), base)
        assert "threads/coll-restored" in result
        assert (tmp_path / "threads" / "coll-restored" / "README.md").exists()

    def test_double_collision_uses_numeric_suffix(self, tmp_path):
        base = self._archive(tmp_path, "dbl")
        _make_thread(tmp_path, "dbl")
        _make_thread(tmp_path, "dbl-restored")
        result = restore_thread(str(tmp_path), base)
        assert "threads/dbl-restored-2" in result
        assert (tmp_path / "threads" / "dbl-restored-2" / "README.md").exists()

    def test_triple_collision_keeps_incrementing(self, tmp_path):
        base = self._archive(tmp_path, "tri")
        _make_thread(tmp_path, "tri")
        _make_thread(tmp_path, "tri-restored")
        _make_thread(tmp_path, "tri-restored-2")
        result = restore_thread(str(tmp_path), base)
        assert "threads/tri-restored-3" in result

    def test_missing_archive(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = restore_thread(str(tmp_path), "2026-ghost")
        assert "not found" in result

    def test_invalid_archive_base_rejected(self, tmp_path):
        for bad in ["../../etc/passwd", "/abs/path", "no-year", "2026-Bad"]:
            result = restore_thread(str(tmp_path), bad)
            assert "Invalid archive base" in result, f"failed for {bad!r}"

    def test_malicious_tar_member_rejected(self, tmp_path):
        (tmp_path / "threads").mkdir()
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        tar_path = archive_dir / "2026-evil.tar.gz"
        with tarfile.open(tar_path, "w:gz") as t:
            # Add a benign top-level dir so single-top-level check passes
            info = tarfile.TarInfo("evil/")
            info.type = tarfile.DIRTYPE
            t.addfile(info)
            # Now a traversal member
            info = tarfile.TarInfo("evil/../../escape.txt")
            data = b"pwned"
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))

        result = restore_thread(str(tmp_path), "2026-evil")
        # Either the multi-top-level check or the traversal guard catches it.
        # In any case: no file written outside archive/tmp/_restore_*/
        # and no thread restored to threads/.
        assert "Error" in result
        assert not (tmp_path / "escape.txt").exists()
        assert not (tmp_path.parent / "escape.txt").exists()
        assert not (tmp_path / "threads" / "evil").exists()

    def test_multi_top_level_archive_rejected(self, tmp_path):
        (tmp_path / "threads").mkdir()
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        tar_path = archive_dir / "2026-multi.tar.gz"
        with tarfile.open(tar_path, "w:gz") as t:
            for top in ("a", "b"):
                info = tarfile.TarInfo(f"{top}/file.txt")
                data = b"x"
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
        result = restore_thread(str(tmp_path), "2026-multi")
        assert "single top-level" in result

    def test_staging_cleaned_up(self, tmp_path):
        base = self._archive(tmp_path, "clean")
        restore_thread(str(tmp_path), base)
        staging = tmp_path / "archive" / "tmp" / f"_restore_{base}"
        assert not staging.exists()


class TestListArchivedThreads:
    def test_empty_returns_message(self, tmp_path):
        (tmp_path / "threads").mkdir()
        assert "No archived threads" in list_archived_threads(str(tmp_path))

    def test_missing_archive_dir(self, tmp_path):
        (tmp_path / "threads").mkdir()
        assert "No archived threads" in list_archived_threads(str(tmp_path))

    def test_lists_archives_sorted_newest_first(self, tmp_path, monkeypatch):
        # Create two archives with different `archived:` dates
        _make_thread(tmp_path, "older")
        archive_thread(str(tmp_path), "older", "old", ["a", "b"], "x")
        # Tweak the older summary to backdate its archived: field
        older_md = tmp_path / "archive" / "2026-older.md"
        older_md.write_text(
            older_md.read_text().replace(
                "archived: ", "archived: 2025-01-01\n# was: "
            )
        )

        _make_thread(tmp_path, "newer")
        archive_thread(str(tmp_path), "newer", "new", ["c"], "y")

        result = list_archived_threads(str(tmp_path))
        lines = result.strip().split("\n")
        assert lines[0].startswith("2026-newer")
        assert lines[1].startswith("2026-older")
        assert "keywords: a, b" in lines[1]
        assert "keywords: c" in lines[0]

    def test_tmp_subdir_skipped(self, tmp_path):
        archive_dir = tmp_path / "archive"
        (archive_dir / "tmp" / "2026-extracted").mkdir(parents=True)
        # Create a stray .md in tmp that should be ignored (glob is non-recursive,
        # but just to be safe assert the result doesn't include tmp entries)
        (archive_dir / "tmp" / "stray.md").write_text("---\n---\n")
        result = list_archived_threads(str(tmp_path))
        assert "stray" not in result

    def test_orphan_md_without_archive_skipped(self, tmp_path):
        (tmp_path / "threads").mkdir()
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        (archive_dir / "2026-orphan.md").write_text(
            "---\nthread: orphan\n---\n"
        )
        result = list_archived_threads(str(tmp_path))
        assert "orphan" not in result

class TestInspectArchive:
    def _archive(self, tmp_path, name="ins"):
        _make_thread(tmp_path, name)
        archive_thread(str(tmp_path), name, "s", [], "b")
        return f"2026-{name}"

    def test_success(self, tmp_path):
        base = self._archive(tmp_path, "ins")
        result = inspect_archive(str(tmp_path), base)
        assert "Extracted to" in result
        assert (tmp_path / "archive" / "tmp" / base / "ins" / "README.md").exists()
        # Original archive + summary still in place
        assert (tmp_path / "archive" / f"{base}.tar.gz").exists()
        assert (tmp_path / "archive" / f"{base}.md").exists()

    def test_repeated_inspect_overwrites_cleanly(self, tmp_path):
        base = self._archive(tmp_path, "twice")
        inspect_archive(str(tmp_path), base)
        # Leave a stray file in the extract dir
        stray = tmp_path / "archive" / "tmp" / base / "stray.txt"
        stray.write_text("garbage")
        assert stray.exists()
        inspect_archive(str(tmp_path), base)
        assert not stray.exists()
        assert (tmp_path / "archive" / "tmp" / base / "twice" / "README.md").exists()

    def test_missing_archive(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = inspect_archive(str(tmp_path), "2026-ghost")
        assert "not found" in result

    def test_invalid_archive_base_rejected(self, tmp_path):
        result = inspect_archive(str(tmp_path), "../etc/passwd")
        assert "Invalid archive base" in result

    def test_malicious_archive_rejected(self, tmp_path):
        (tmp_path / "threads").mkdir()
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        tar_path = archive_dir / "2026-bad.tar.gz"
        with tarfile.open(tar_path, "w:gz") as t:
            info = tarfile.TarInfo("bad/")
            info.type = tarfile.DIRTYPE
            t.addfile(info)
            info = tarfile.TarInfo("bad/../../escape.txt")
            data = b"x"
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        result = inspect_archive(str(tmp_path), "2026-bad")
        assert "Error" in result
        assert not (tmp_path / "escape.txt").exists()


class TestPurgeArchiveTmp:
    def test_no_op_when_missing(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = purge_archive_tmp(str(tmp_path))
        assert "already clean" in result

    def test_removes_tmp_subtree(self, tmp_path):
        (tmp_path / "threads").mkdir()
        tmp_dir = tmp_path / "archive" / "tmp" / "2026-x" / "thread"
        tmp_dir.mkdir(parents=True)
        (tmp_dir / "file.txt").write_text("content")
        result = purge_archive_tmp(str(tmp_path))
        assert "Purged" in result
        assert not (tmp_path / "archive" / "tmp").exists()

    def test_does_not_touch_siblings(self, tmp_path):
        (tmp_path / "threads").mkdir()
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        (archive_dir / "2026-keep.md").write_text("---\nthread: keep\n---\n")
        (archive_dir / "2026-keep.tar.gz").write_bytes(b"fake-but-untouched")
        (archive_dir / "tmp").mkdir()
        (archive_dir / "tmp" / "x.txt").write_text("scratch")
        purge_archive_tmp(str(tmp_path))
        assert (archive_dir / "2026-keep.md").exists()
        assert (archive_dir / "2026-keep.tar.gz").exists()
        assert not (archive_dir / "tmp").exists()
