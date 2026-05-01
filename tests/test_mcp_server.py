"""Unit tests for skills/threads/mcp_server.py business logic."""

import json
import sys
import time
from pathlib import Path

import pytest

# Add mcp_server's parent to path so we can import its functions
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from mcp_server import get_thread_status, list_threads, resolve_workspace, set_default_workspace
from workspace_utils import read_config, write_config


class TestListThreads:
    def test_no_threads_dir(self, tmp_path):
        result = list_threads(str(tmp_path))
        assert "No threads directory found" in result

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


class TestGetThreadStatus:
    def test_missing_thread(self, tmp_path):
        result = get_thread_status(str(tmp_path), "nonexistent")
        assert "not found" in result

    def test_extracts_quick_resume(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text(
            "# My Thread\n\n"
            "## Quick Resume\n\n"
            "**Focus**: current focus\n"
            "**Next**: next step\n\n"
            "## Other Section\n"
            "other content\n"
        )
        result = get_thread_status(str(tmp_path), "my-thread")
        assert "**Focus**: current focus" in result
        assert "**Next**: next step" in result
        assert "Other Section" not in result

    def test_no_quick_resume_section(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text("# My Thread\n\n## Overview\nsome content\n")
        result = get_thread_status(str(tmp_path), "my-thread")
        assert "No Quick Resume section found" in result

    def test_strips_blank_lines(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text(
            "## Quick Resume\n\n\n**Focus**: something\n\n\n"
        )
        result = get_thread_status(str(tmp_path), "my-thread")
        assert result == "**Focus**: something"

    def test_purpose_line_excluded(self, tmp_path):
        threads = tmp_path / "threads"
        threads.mkdir()
        thread = threads / "my-thread"
        thread.mkdir()
        (thread / "README.md").write_text(
            "## Quick Resume\n"
            "> **Purpose**: this is filtered\n"
            "**Focus**: kept\n"
        )
        result = get_thread_status(str(tmp_path), "my-thread")
        assert "> **Purpose**" not in result
        assert "**Focus**: kept" in result


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

        # Point plugin data dir to tmp_path for config
        data_dir = tmp_path / "plugin-data"
        data_dir.mkdir()
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

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
        data_dir = tmp_path / "plugin-data"
        data_dir.mkdir()
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        result = json.loads(resolve_workspace(str(tmp_path)))
        assert result["source"] == "none"
        assert result["workspace_dir"] is None

    def test_config_path_missing(self, tmp_path, monkeypatch):
        """Config points to a workspace that no longer exists."""
        data_dir = tmp_path / "plugin-data"
        data_dir.mkdir()
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

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

        data_dir = tmp_path / "plugin-data"
        data_dir.mkdir()
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))
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

        data_dir = tmp_path / "plugin-data"
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        result = set_default_workspace(str(workspace))
        assert "Default workspace set" in result

        config = json.loads((data_dir / "config.json").read_text())
        assert config["default_workspace"] == str(workspace.resolve())

    def test_rejects_missing_directory(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "plugin-data"
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        result = set_default_workspace("/nonexistent/path")
        assert "Error" in result
        assert "does not exist" in result

    def test_rejects_dir_without_threads(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "plugin-data"
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        result = set_default_workspace(str(tmp_path))
        assert "Error" in result
        assert "No threads/ directory" in result


class TestConfigHelpers:
    def test_read_missing_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(tmp_path / "nonexistent"))
        assert read_config() == {}

    def test_write_and_read_config(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "plugin-data"
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        write_config({"default_workspace": "/some/path"})
        config = read_config()
        assert config["default_workspace"] == "/some/path"

    def test_write_creates_directory(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "nested" / "plugin-data"
        monkeypatch.setenv("PLUGIN_DATA_DIR", str(data_dir))

        write_config({"key": "value"})
        assert data_dir.exists()
        assert (data_dir / "config.json").exists()
