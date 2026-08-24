"""Threads: the concept, and everything the plugin knows about them.

This module is the API. Every operation a caller can perform on a thread is a
named function here; each one resolves the thread, reads which schema it uses,
and hands off to that schema's implementation. Past the hand-off nothing
branches on a version.

Locating a thread is not this module's job. The workspace is what decides that
threads live under threads/{name}, so workspace.py answers "where" and this
module answers "which schema, and what can it do". That split is what lets a
workspace get versioned on its own axis later without touching anything here.

Archiving lives in workspace.py, not here. Moving a thread between threads/ and
archive/ never opens it, so it needs nothing from any schema.
"""

import re

from ai_workspace import workspace as ws
from ai_workspace.workspace import names_one_directory  # noqa: F401  (re-exported)
from ai_workspace.threads.schema import (  # noqa: F401  (re-exported)
    CURRENT_SCHEMA,
    MARKER,
    MIN_READABLE_SCHEMA,
    SCHEMAS,
    Thread,
    at,
    read_schema,
    implementation,
)

__all__ = [
    "create",
    "resume",
    "names_one_directory",
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
    if not names_one_directory(thread_name):
        return None, ws._bad_name(thread_name)

    workspace, directory, error = ws.thread_dir(workspace_dir, thread_name)
    if error:
        return None, error
    if not (directory / "README.md").exists():
        if ws.thread_state(workspace, thread_name) == ws.ARCHIVED:
            return None, (
                f"Error: Thread '{thread_name}' is archived, and an archived thread is "
                f"read-only.\nRestore it before working on it."
            )
        return None, f"Error: Thread '{thread_name}' not found."
    return at(workspace, thread_name, directory)


def _focus(thread: Thread, body: str) -> str:
    """Prefix a response with the headers that set the session's focus.

    Used only by operations that shift the session to a specific thread. The
    LLM tracks Workspace, Thread and Schema across the session and uses them
    for follow-up calls. The schema rides here rather than on every response
    for the same reason the workspace path does: it is established when focus
    is set and remembered afterwards.
    """
    return (
        f"Workspace: {thread.workspace}\n"
        f"Thread: {thread.dir}\n"
        f"Schema: {thread.schema}\n"
        f"\n{body}"
    )


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

    state = ws.thread_state(workspace, thread_name)
    if state == ws.ACTIVE:
        return f"Error: Thread '{thread_name}' already exists."
    if state == ws.ARCHIVED:
        return (
            f"Error: '{thread_name}' is the name of an archived thread.\n"
            f"Restore it to work on it again, or choose another name."
        )

    directory = ws.thread_path(workspace, thread_name)
    thread = Thread(workspace, thread_name, directory, CURRENT_SCHEMA)
    return _focus(thread, implementation(thread).create(thread))
