"""Threads: the concept, and everything the plugin knows about them.

This module is the API. Every operation a caller can perform on a thread is a
named function here; each one resolves the thread, reads which schema it uses,
and hands off to that schema's implementation. Past the hand-off nothing
branches on a version.

Locating a thread is not this module's job. The workspace is what decides that
threads live under threads/{name}, so workspace.py answers "where" and this
module answers "which schema, and what can it do". That split is what lets a
workspace get versioned on its own axis later without touching anything here.

archives.py is plural on purpose: `archive` here is the verb, the operation a
thread's schema performs on itself, and archives.py holds the operations on the
collection those archives land in. A submodule sharing a name with a function
defined here would be shadowed by it.
"""

import re

from ai_workspace import workspace as ws
from ai_workspace.threads._schema import (  # noqa: F401  (re-exported)
    CURRENT_SCHEMA,
    MARKER,
    MIN_READABLE_SCHEMA,
    SCHEMAS,
    Thread,
    at,
    read_schema,
    implementation,
)
from ai_workspace.threads.archives import (  # noqa: F401  (re-exported)
    inspect_archive,
    list_archived_threads,
    purge_archive_tmp,
    restore,
)

__all__ = [
    "archive",
    "create",
    "inspect_archive",
    "list_archived_threads",
    "list_threads",
    "purge_archive_tmp",
    "restore",
    "resume",
    "validate_thread_name",
]


def validate_thread_name(name: str) -> bool:
    """
    Validate that a thread name follows kebab-case conventions.

    Valid names:
    - Lowercase letters (a-z)
    - Numbers (0-9)
    - Hyphens (-)
    - Must start with a letter or number (not a hyphen)
    - Must end with a letter or number (not a hyphen)
    - No consecutive hyphens

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    pattern = r"^[a-z0-9]+([a-z0-9-]*[a-z0-9]+)?$"

    if not re.match(pattern, name):
        return False

    if "--" in name:
        return False

    return True


def _locate(workspace_dir: str, thread_name: str) -> tuple[Thread | None, str | None]:
    """Resolve an existing thread and read its schema."""
    if not validate_thread_name(thread_name):
        return None, f"Error: Invalid thread name '{thread_name}'."

    workspace, directory, error = ws.thread_dir(workspace_dir, thread_name)
    if error:
        return None, error
    if not (directory / "README.md").exists():
        return None, f"Error: Thread '{thread_name}' not found."
    return at(workspace, thread_name, directory)


def _focus(thread: Thread, body: str) -> str:
    """Prefix a response with the headers that set the session's focus.

    Used only by operations that shift the session to a specific thread. The
    LLM tracks Workspace and Thread across the session and uses them for
    follow-up calls.
    """
    return f"Workspace: {thread.workspace}\nThread: {thread.dir}\n\n{body}"


def list_threads(workspace_dir: str) -> str:
    """List all discussion threads sorted by most recent activity.

    Enumerates rather than opening any thread, so it is the same for every
    schema.
    """
    workspace, directory, error = ws.threads_dir(workspace_dir)
    if error:
        return error

    if not directory.exists():
        return "No threads directory found. Use /threads create to start one."

    entries = []
    for item in directory.iterdir():
        if item.is_dir():
            readme = item / "README.md"
            if readme.exists():
                entries.append((item.name, readme.stat().st_mtime))

    if not entries:
        return "No threads found. Use /threads create to start one."

    entries.sort(key=lambda x: x[1], reverse=True)
    return "\n".join(f"{i}. {name}" for i, (name, _) in enumerate(entries, 1))


def resume(workspace_dir: str, thread_name: str) -> str:
    """Return the thread's context, in whatever form its schema keeps it."""
    thread, error = _locate(workspace_dir, thread_name)
    return error or _focus(thread, implementation(thread).resume(thread))


def create(workspace_dir: str, thread_name: str) -> str:
    """Create a thread at the schema this plugin currently writes."""
    if not validate_thread_name(thread_name):
        return (
            f"Error: Invalid thread name '{thread_name}'. "
            "Thread names must be kebab-case (lowercase letters, numbers, hyphens). "
            "Examples: my-thread, api-redesign, auth-refactor"
        )

    workspace, error = ws.resolve_for_create(workspace_dir)
    if error:
        return error

    directory = ws.thread_path(workspace, thread_name)
    if directory.exists():
        return f"Error: Thread '{thread_name}' already exists."

    thread = Thread(workspace, thread_name, directory, CURRENT_SCHEMA)
    return _focus(thread, implementation(thread).create(thread))


def archive(workspace_dir: str, thread_name: str, summary: str, keywords: list,
            body: str) -> str:
    """Archive a thread, the way its own schema knows how to."""
    thread, error = _locate(workspace_dir, thread_name)
    return error or implementation(thread).archive(thread, summary, keywords, body)
