#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=2", "python-frontmatter"]
# ///
"""Threads MCP Server - the tool surface.

Implementations live in lib/ai_workspace/. This module declares the tools, their
docstrings and their arguments, and delegates.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))

from mcp.server.mcpserver import MCPServer

from ai_workspace import plugin as _plugin
from ai_workspace import threads as _threads
from ai_workspace import workspace as _ws

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
    return _ws.list_threads(workspace_dir)


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
def archive_thread(workspace_dir: str, thread_name: str) -> str:
    """Archive a thread: move it out of threads/ and into archive/.

    Nothing is compressed and nothing is summarised. The thread keeps its shape
    and stays readable and greppable where it lands, which is why no summary is
    written for it. An archived thread is read-only; restore it to work on it.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the thread to archive.
    """
    return _ws.archive(workspace_dir, thread_name)



@mcp.tool()
def restore_thread(workspace_dir: str, thread_name: str) -> str:
    """Restore an archived thread: move it back from archive/ into threads/.

    Takes the thread's own name. Archives created before 3.0 are tarballs and
    are not unpacked by this tool; it returns `Status: LEGACY_ARCHIVE` naming
    the reference to follow.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the archived thread.
    """
    return _ws.restore(workspace_dir, thread_name)



@mcp.tool()
def list_archived_threads(workspace_dir: str) -> str:
    """List the threads under archive/, numbered.

    Archived threads are read-only; restoring one is what makes it writable
    again. A thread archived before 3.0 is listed as a tarball, with the
    reference to follow for unpacking it.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    return _ws.list_archived_threads(workspace_dir)





@mcp.tool()
def add_todo(workspace_dir: str, thread_name: str, title: str, link: str,
             state: str = "active") -> str:
    """Add a todo to the thread's backlog.

    Every todo carries a link, always. Use a file under todos/ when the item has
    state of its own, an external URL when there is an issue or PR, and
    otherwise the session it came out of. A bare line cannot be expanded later,
    which is the whole complaint about one-line next steps.

    Adding does not promote: the backlog is allowed to be long, and the README
    shows only what set_window selects.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short label for the todo.
        link: Path or URL. Never omit; use the originating session if nothing else.
        state: `active` or `parked`. Parked means deliberately not now.
    """
    return _threads.add_todo(workspace_dir, thread_name, title, link, state)


@mcp.tool()
def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped, removing it from any window.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_id: The id from the index line, e.g. 20260808-growcer-prep.
        state: `done` for something finished, `dropped` for something deliberately abandoned.
    """
    return _threads.retire_todo(workspace_dir, thread_name, todo_id, state)


@mcp.tool()
def set_todo_state(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Park or unpark a todo without retiring it.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_id: The id from the index line.
        state: `active` or `parked`.
    """
    return _threads.set_todo_state(workspace_dir, thread_name, todo_id, state)


@mcp.tool()
def set_window(workspace_dir: str, thread_name: str, entry_ids: list[str],
               section: str = "next_steps", kind: str = "todos") -> str:
    """Choose which entries the README shows, and in what order.

    This is the whole of priority. The backlog below the window is never ranked,
    because ordering the twentieth item against the twenty-first produces
    nothing. Aim for about five.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        entry_ids: Ids in the order they should appear.
        section: README section the window drives. Default `next_steps`.
        kind: Index the ids belong to. Default `todos`.
    """
    return _threads.set_window(workspace_dir, thread_name, entry_ids, section, kind)


@mcp.tool()
def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, status: str = "proposed",
                 supersedes: list[str] | None = None) -> str:
    """Write a decision file and index it.

    `summary` is read on every resume, so it carries real cost: one sentence,
    one subject, what was decided and not why. If it needs "and" twice, that is
    the signal to log several decisions instead.

    `supersedes` retires the decisions it names. That direction is deliberate —
    traversal starts from what is in force, so only live-to-dead pointers get
    followed.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short title for the decision.
        summary: One sentence, one subject. WHAT was decided, no rationale.
        body: Markdown body. Claim first, argument after.
        status: `proposed`, `partially-locked` or `locked`.
        supersedes: Ids of decisions this replaces; each is retired as superseded.
    """
    return _threads.log_decision(workspace_dir, thread_name, title, summary, body,
                                 status, supersedes)


@mcp.tool()
def retire_decision(workspace_dir: str, thread_name: str, decision_id: str,
                    state: str) -> str:
    """Retire a decision, updating both the index and the file's own status.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        decision_id: The id from the index line.
        state: `superseded` when something replaced it, `withdrawn` when it was
            abandoned with nothing taking its place.
    """
    return _threads.retire_decision(workspace_dir, thread_name, decision_id, state)


@mcp.tool()
def add_artifact(workspace_dir: str, thread_name: str, title: str, link: str) -> str:
    """Index an artifact that has been written into the thread.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short title for the artifact.
        link: Path relative to the thread, e.g. ./artifacts/20260813-notes-x.md.
    """
    return _threads.add_artifact(workspace_dir, thread_name, title, link)


@mcp.tool()
def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact so it stops appearing as current.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        artifact_id: The id from the index line.
        state: `superseded` when something replaced it, `stale` when it no longer
            describes reality.
    """
    return _threads.retire_artifact(workspace_dir, thread_name, artifact_id, state)


if __name__ == "__main__":
    mcp.run()
