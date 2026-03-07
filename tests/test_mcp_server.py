"""Unit tests for skills/threads/mcp_server.py business logic."""

import sys
import time
from pathlib import Path

import pytest

# Add mcp_server's parent to path so we can import its functions
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "common"))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "threads" / "scripts"))

from mcp_server import get_thread_status, list_threads


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
