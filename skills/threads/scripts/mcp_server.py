#!/usr/bin/env python3
"""Threads MCP Server - the tool surface.

Implementations live in lib/ai_workspace/. This module declares the tools, their
docstrings and their arguments, and delegates. Archive-related tools require
Python 3.12+ (tarfile filter="data" support).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))

from mcp.server.mcpserver import MCPServer

from ai_workspace import plugin as _plugin
from ai_workspace import threads as _threads
from ai_workspace import workspace as _ws
from ai_workspace.threads.tarball import ARCHIVE_SCHEMA_VERSION  # noqa: F401  (re-export)

mcp = MCPServer("threads")


@mcp.tool()
def list_threads(workspace_dir: str) -> str:
    """List all discussion threads sorted by most recent activity.

    Resolves the workspace from `workspace_dir` (local threads/ first, then configured
    default). Returns `Error: NO_WORKSPACE` if neither is available.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    return _threads.list_threads(workspace_dir)


@mcp.tool()
def resume_thread(workspace_dir: str, thread_name: str) -> str:
    """Resolve the workspace and thread path, and return the full README content.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the thread (kebab-case).
    """
    return _threads.resume(workspace_dir, thread_name)


@mcp.tool()
def create_thread(workspace_dir: str, thread_name: str) -> str:
    """Create a new discussion thread with the standard directory structure.

    Resolves the workspace from `workspace_dir`. If `workspace_dir` has a threads/ dir, the thread
    is created there. If not, the tool may return a status the LLM must surface
    to the user:
    - `Status: AMBIGUOUS_WORKSPACE` when a configured default workspace exists
      (user picks between configured workspace vs initialising a new one here).
    - `Status: NEEDS_INIT` when no workspace exists anywhere (user picks between
      initialising here vs supplying a path).

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns a status question
            (AMBIGUOUS_WORKSPACE or NEEDS_INIT) if neither works.
        thread_name: Name of the thread (kebab-case: lowercase letters, numbers, hyphens).
    """
    return _threads.create(workspace_dir, thread_name)


@mcp.tool()
def get_skill_file(relative_path: str) -> str:
    """Return the contents of a file from the plugin directory.

    Use this to read skill reference files (e.g. commands/save-thread.md)
    without needing direct filesystem access. Paths are resolved relative
    to the plugin root and must not escape it.

    Args:
        relative_path: Path relative to the plugin root (e.g., "skills/threads/commands/save-thread.md").
    """
    return _plugin.get_skill_file(relative_path=relative_path)


@mcp.tool()
def resolve_workspace(workspace_dir: str) -> str:
    """Resolve which workspace directory to use for thread operations.

    Checks for a local threads/ directory first, then falls back to the
    configured default workspace. Kept as an optional diagnostic — operating
    tools (list_threads, create_thread, etc.) resolve internally now.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            caller's current working directory. The tool probes this directory
            for threads/, falls back to the configured default, and returns the
            result with its source ("local", "config", or "none").
    """
    return _ws.resolve_workspace(workspace_dir=workspace_dir)


@mcp.tool()
def set_default_workspace(workspace_path: str) -> str:
    """Set the default workspace directory for thread operations.

    This is used when running /threads from outside a workspace directory.
    The path is persisted in the plugin's global config.

    Args:
        workspace_path: Absolute path to a directory containing a threads/ folder.
    """
    return _ws.set_default_workspace(workspace_path=workspace_path)


@mcp.tool()
def archive_thread(
    workspace_dir: str,
    thread_name: str,
    summary: str,
    keywords: list,
    body: str,
) -> str:
    """Archive a thread: compress its directory, write a searchable summary, delete the original.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the thread to archive (kebab-case).
        summary: One-line summary; goes into frontmatter `summary:` field.
        keywords: List of short keyword strings for search; normalised (lowercased, deduped).
        body: Topic-rich markdown narrative — the embedding payload. Cover what was discussed,
              decisions made, systems/files/people touched, key vocabulary and synonyms.
    """
    return _threads.archive(workspace_dir, thread_name, summary, keywords, body)


@mcp.tool()
def restore_thread(workspace_dir: str, archive_base: str) -> str:
    """Restore an archived thread back into threads/, deleting the archive on success.

    Writes a sessions/{YYYYMMDD}-restored.md file inside the restored thread
    capturing the archive-time summary and body, so the LLM's interpretation
    survives as thread history.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        archive_base: Filename stem of the archive (e.g. '2026-last-months-project').
    """
    return _threads.restore(workspace_dir, archive_base)


@mcp.tool()
def list_archived_threads(workspace_dir: str) -> str:
    """List archived threads with metadata for quick search.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    return _threads.list_archived_threads(workspace_dir)


@mcp.tool()
def inspect_archive(workspace_dir: str, archive_base: str) -> str:
    """Extract an archive into archive/tmp/{base}/ for inspection without restoring.

    The original .md and .tar.gz are left in place. Repeated calls overwrite cleanly.
    Use /threads purge-tmp when done. The extraction target stays inside the workspace.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        archive_base: Filename stem of the archive (e.g. '2026-last-months-project').
    """
    return _threads.inspect_archive(workspace_dir, archive_base)


@mcp.tool()
def purge_archive_tmp(workspace_dir: str) -> str:
    """Wipe archive/tmp/ entirely. Safe — every file in it is regeneratable from sibling archives.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    return _threads.purge_archive_tmp(workspace_dir)


if __name__ == "__main__":
    mcp.run()
