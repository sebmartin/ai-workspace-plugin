"""Unit tests for skills/threads/mcp_server.py business logic."""

import json
import sys
import time
from pathlib import Path

import pytest

# Add mcp_server's parent to path so we can import its functions
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

import mcp_server  # noqa: F401  (imported for its sys.path side effect)
from ai_workspace import workspace as ws_module
from ai_workspace.config import get_config_dir, read_config, write_config
from mcp_server import (
    archive_thread,
    create_thread,
    get_skill_file,
    list_archived_threads,
    list_threads,
    resolve_workspace,
    restore_thread,
    resume_thread,
    set_default_workspace,
)


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
            f"Workspace: {tmp_path}\n"
            f"Thread: {tmp_path / 'threads' / 'my-thread'}\n"
            f"Schema: 1\n\n"
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
        for sub in ("sessions", "decisions", "attachments", "artifacts", "todos"):
            assert (thread / sub).is_dir()

    def test_success_includes_workspace_and_thread_headers(self, tmp_path):
        (tmp_path / "threads").mkdir()
        result = create_thread(str(tmp_path), "headered")
        assert result.startswith(
            f"Workspace: {tmp_path}\n"
            f"Thread: {tmp_path / 'threads' / 'headered'}\n"
            f"Schema: 2\n\n"
        )

    def test_already_exists_error_has_no_headers(self, tmp_path):
        (tmp_path / "threads" / "dupe").mkdir(parents=True)
        (tmp_path / "threads" / "dupe" / "README.md").write_text("# x")
        result = create_thread(str(tmp_path), "dupe")
        assert not result.startswith("Workspace:")
        assert "already exists" in result

    def test_an_archived_name_is_not_free(self, tmp_path):
        """Taking it would strand the archive: no restore, no re-archive."""
        _make_thread(tmp_path, "shelved")
        archive_thread(str(tmp_path), "shelved")
        result = create_thread(str(tmp_path), "shelved")
        assert "archived thread" in result
        assert not result.startswith("Workspace:")
        assert "Restored 'shelved'" in restore_thread(str(tmp_path), "shelved")

    def test_a_name_held_by_a_pre_3_0_tarball_is_not_free(self, tmp_path):
        """Otherwise one name ends up with two archives in two formats."""
        (tmp_path / "threads").mkdir()
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "2026-shelved.tar.gz").write_bytes(b"stand-in")
        assert "archived thread" in create_thread(str(tmp_path), "shelved")

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
    def test_moves_the_directory(self, tmp_path):
        _make_thread(tmp_path, "old-work")
        result = archive_thread(str(tmp_path), "old-work")
        assert "Archived 'old-work'" in result
        assert not (tmp_path / "threads" / "old-work").exists()
        assert (tmp_path / "archive" / "old-work" / "README.md").exists()

    def test_says_the_archive_is_read_only(self, tmp_path):
        _make_thread(tmp_path, "old-work")
        assert "read-only" in archive_thread(str(tmp_path), "old-work")

    def test_contents_survive_untouched(self, tmp_path):
        d = _make_thread(tmp_path, "old-work")
        (d / "sessions" / "20260101-a.md").write_text("kept\n")
        archive_thread(str(tmp_path), "old-work")
        assert (tmp_path / "archive" / "old-work" / "sessions" / "20260101-a.md").read_text() == "kept\n"

    def test_missing_thread(self, tmp_path):
        (tmp_path / "threads").mkdir()
        assert "not found" in archive_thread(str(tmp_path), "nope")

    def test_traversal_name_is_refused(self, tmp_path):
        (tmp_path / "threads").mkdir()
        for name in ("../escape", "a/b", "/abs", ".."):
            assert "Invalid thread name" in archive_thread(str(tmp_path), name), name

    def test_unconventional_name_is_not_refused(self, tmp_path):
        """A thread already on disk is archived whatever it is called."""
        _make_thread(tmp_path, "Q3_planning")
        assert "Archived 'Q3_planning'" in archive_thread(str(tmp_path), "Q3_planning")

    def test_occupied_destination_refuses_rather_than_nesting(self, tmp_path):
        """shutil.move onto an existing directory would nest inside it."""
        _make_thread(tmp_path, "dupe")
        archive_thread(str(tmp_path), "dupe")
        _make_thread(tmp_path, "dupe")
        result = archive_thread(str(tmp_path), "dupe")
        assert "already exists" in result
        assert not (tmp_path / "archive" / "dupe" / "dupe").exists()
        assert (tmp_path / "threads" / "dupe").is_dir()

    def test_failure_leaves_the_thread_in_place(self, tmp_path, monkeypatch):
        """A rename either happens or does not; there is no half-moved thread."""
        _make_thread(tmp_path, "stuck")
        monkeypatch.setattr(
            Path, "rename",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("Device or resource busy")),
        )
        result = archive_thread(str(tmp_path), "stuck")
        assert "untouched" in result and "busy" in result
        assert (tmp_path / "threads" / "stuck" / "README.md").exists()
        assert not (tmp_path / "archive" / "stuck").exists()

    def test_already_archived_says_so(self, tmp_path):
        """Checking only threads/ made this report the thread as missing."""
        _make_thread(tmp_path, "gone")
        archive_thread(str(tmp_path), "gone")
        assert "already archived" in archive_thread(str(tmp_path), "gone")

    def test_a_thread_named_tmp_is_archived_like_any_other(self, tmp_path):
        """archive/tmp was a staging directory nothing creates any more."""
        _make_thread(tmp_path, "tmp")
        assert "Archived 'tmp'" in archive_thread(str(tmp_path), "tmp")
        assert "tmp" in list_archived_threads(str(tmp_path))


class TestRestoreThread:
    def test_round_trip(self, tmp_path):
        d = _make_thread(tmp_path, "back")
        (d / "sessions" / "20260101-a.md").write_text("kept\n")
        archive_thread(str(tmp_path), "back")
        assert "Restored 'back'" in restore_thread(str(tmp_path), "back")
        assert (tmp_path / "threads" / "back" / "sessions" / "20260101-a.md").read_text() == "kept\n"
        assert not (tmp_path / "archive" / "back").exists()

    def test_nothing_is_recorded_about_the_restore(self, tmp_path):
        """A move returns the thread as it was, so there is nothing to note."""
        _make_thread(tmp_path, "back")
        sessions = tmp_path / "threads" / "back" / "sessions"
        before = sorted(p.name for p in sessions.iterdir())
        archive_thread(str(tmp_path), "back")
        restore_thread(str(tmp_path), "back")
        assert sorted(p.name for p in sessions.iterdir()) == before

    def test_missing_archive(self, tmp_path):
        (tmp_path / "threads").mkdir()
        assert "No archived thread" in restore_thread(str(tmp_path), "nope")

    def test_a_live_thread_of_that_name_blocks_the_restore(self, tmp_path):
        _make_thread(tmp_path, "clash")
        archive_thread(str(tmp_path), "clash")
        _make_thread(tmp_path, "clash")
        result = restore_thread(str(tmp_path), "clash")
        assert "already in threads/" in result
        assert (tmp_path / "archive" / "clash").is_dir()

    def test_a_restored_tarball_leaves_the_thread_reachable(self, tmp_path):
        """Extracting is a copy, so the tarball outlives the restore it produced."""
        _make_thread(tmp_path, "ancient")
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "2026-ancient.tar.gz").write_bytes(b"stand-in")
        assert ws_module.thread_state(tmp_path, "ancient") == ws_module.ACTIVE
        assert "Quick Resume" in resume_thread(str(tmp_path), "ancient")

    def test_legacy_tarball_points_at_the_reference(self, tmp_path):
        (tmp_path / "threads").mkdir()
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "2026-ancient.tar.gz").write_bytes(b"not really a tarball")
        result = restore_thread(str(tmp_path), "ancient")
        assert "LEGACY_ARCHIVE" in result
        assert "unpack-legacy-archive.md" in result


class TestListArchivedThreads:
    def test_empty_returns_message(self, tmp_path):
        (tmp_path / "threads").mkdir()
        assert "No archived threads" in list_archived_threads(str(tmp_path))

    def test_lists_directories_and_says_they_are_read_only(self, tmp_path):
        _make_thread(tmp_path, "one")
        archive_thread(str(tmp_path), "one")
        result = list_archived_threads(str(tmp_path))
        assert "one" in result
        assert "read-only" in result

    def test_legacy_tarball_listed(self, tmp_path):
        (tmp_path / "threads").mkdir()
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "2026-ancient.tar.gz").write_bytes(b"x")
        result = list_archived_threads(str(tmp_path))
        assert "ancient" in result and "before 3.0" in result

    def test_legacy_tarball_hidden_once_its_thread_exists(self, tmp_path):
        """Extracting is a copy, so the tarball outlives a legacy restore.

        Listing it beside the thread it produced is the confusing state.
        """
        _make_thread(tmp_path, "ancient")
        (tmp_path / "archive").mkdir()
        (tmp_path / "archive" / "2026-ancient.tar.gz").write_bytes(b"x")
        assert "ancient" not in list_archived_threads(str(tmp_path))

        archive_thread(str(tmp_path), "ancient")
        result = list_archived_threads(str(tmp_path))
        assert result.count("ancient") == 1


class TestArchivedThreadsAreReadOnly:
    def test_resume_says_archived_not_missing(self, tmp_path):
        _make_thread(tmp_path, "shelved")
        archive_thread(str(tmp_path), "shelved")
        result = resume_thread(str(tmp_path), "shelved")
        assert "is archived" in result and "read-only" in result
        assert "not found" not in result


class TestGetSkillFile:
    def test_reads_existing_file(self):
        result = get_skill_file("skills/threads/v1/commands/save-thread.md")
        assert "save-thread" in result
        assert "Step 1" in result

    def test_missing_file_returns_error(self):
        result = get_skill_file("skills/threads/commands/nonexistent.md")
        assert "Error" in result

    def test_path_traversal_blocked(self):
        result = get_skill_file("../../etc/passwd")
        assert "Error" in result

    def test_directory_returns_error(self):
        result = get_skill_file("skills/threads/commands")
        assert "Error" in result
