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
    implementation,
    needs_migration_message,
    read_schema,
)

__all__ = [
    "add_artifact",
    "add_todo",
    "create",
    "log_decision",
    "audit_migration",
    "migration_safety_check",
    "names_one_directory",
    "resume",
    "retire_artifact",
    "retire_decision",
    "retire_todo",
    "save_session",
    "set_todo_state",
    "set_window",
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


def _for(workspace_dir: str, thread_name: str, op: str):
    """Resolve the thread and its schema's implementation of `op`.

    Returns (thread, fn, error) with exactly one of fn and error set. A schema
    that never grew the operation simply has no attribute of that name, so a
    schema older than a feature refuses here rather than half-running.
    """
    thread, error = _locate(workspace_dir, thread_name)
    if error:
        return None, None, error
    fn = getattr(implementation(thread), op, None)
    if fn is None:
        return None, None, needs_migration_message(thread.name, thread.schema)
    return thread, fn, None


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
    thread, fn, error = _for(workspace_dir, thread_name, "resume")
    return error or _focus(thread, fn(thread))


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


def add_todo(workspace_dir: str, thread_name: str, title: str, link: str,
             state: str = "active", session_id: str | None = None) -> str:
    """Add a todo to the thread's backlog."""
    thread, fn, error = _for(workspace_dir, thread_name, "add_todo")
    return error or fn(thread, title, link, state, session_id)


def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped, removing it from any window."""
    thread, fn, error = _for(workspace_dir, thread_name, "retire_todo")
    return error or fn(thread, todo_id, state)


def set_todo_state(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Park or unpark a todo without retiring it."""
    thread, fn, error = _for(workspace_dir, thread_name, "set_state")
    return error or fn(thread, "todos", todo_id, state)


def set_window(workspace_dir: str, thread_name: str, entry_ids: list[str],
               section: str = "next_steps", kind: str = "todos") -> str:
    """Choose which entries the README shows, and in what order."""
    thread, fn, error = _for(workspace_dir, thread_name, "set_window")
    return error or fn(thread, kind, section, entry_ids)


def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, status: str = "proposed",
                 supersedes: list[str] | None = None,
                 session_id: str | None = None) -> str:
    """Write a decision file and index it."""
    thread, fn, error = _for(workspace_dir, thread_name, "log_decision")
    return error or fn(thread, title, summary, body, status, supersedes, session_id)


def retire_decision(workspace_dir: str, thread_name: str, decision_id: str,
                    state: str) -> str:
    """Retire a decision that was neither superseded nor is still in force."""
    thread, fn, error = _for(workspace_dir, thread_name, "retire_decision")
    return error or fn(thread, decision_id, state)


def add_artifact(workspace_dir: str, thread_name: str, title: str, link: str,
                 session_id: str | None = None) -> str:
    """Index a file the thread produced."""
    thread, fn, error = _for(workspace_dir, thread_name, "add_artifact")
    return error or fn(thread, title, link, session_id)


def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact that is superseded or no longer relevant."""
    thread, fn, error = _for(workspace_dir, thread_name, "retire_artifact")
    return error or fn(thread, artifact_id, state)


def save_session(workspace_dir: str, thread_name: str, slug: str, summary: str,
                 keywords: str, next_context: str, body: str | None = None,
                 status: str | None = None) -> str:
    """Write the session log and the Status paragraph in one call."""
    thread, fn, error = _for(workspace_dir, thread_name, "save_session")
    return error or fn(thread, slug, summary, keywords, next_context, body, status)


def migration_safety_check(workspace_dir: str, thread_name: str) -> str:
    """Report whether a thread is safe to convert in place.

    Not dispatched on a schema: it asks whether the workspace can recover if
    the conversion goes wrong, which is the same question for any schema.
    """
    from ai_workspace.threads import migrate

    workspace, _, error = ws.thread_dir(workspace_dir, thread_name)
    return error or migrate.safety_check(workspace, thread_name)


def audit_migration(workspace_dir: str, original_thread: str,
                    converted_thread: str) -> str:
    """Compare a converted copy against its original and report what it lost."""
    from ai_workspace.threads import migrate

    workspace, original, error = ws.thread_dir(workspace_dir, original_thread)
    if error:
        return error
    converted = ws.thread_path(workspace, converted_thread)
    for path, label in ((original, original_thread), (converted, converted_thread)):
        if not path.is_dir():
            return f"Error: Thread '{label}' not found."
    return migrate.audit(original, converted)
