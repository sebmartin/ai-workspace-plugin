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
from collections.abc import Callable
from typing import NamedTuple

from ai_workspace import workspace as ws
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
from ai_workspace.workspace import names_one_directory

__all__ = [
    "add_artifact",
    "add_todo",
    "audit_migration",
    "create",
    "log_decision",
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

    return "--" not in name


def _locate(workspace_dir: str, thread_name: str) -> Thread | str:
    """Resolve an existing thread and read its schema."""
    if not names_one_directory(thread_name):
        return ws._bad_name(thread_name)

    located = ws.thread_dir(workspace_dir, thread_name)
    if isinstance(located, str):
        return located
    workspace, directory = located
    if not (directory / "README.md").exists():
        if ws.thread_state(workspace, thread_name) == ws.ARCHIVED:
            return (
                f"Error: Thread '{thread_name}' is archived, and an archived thread is "
                f"read-only.\nRestore it before working on it."
            )
        return f"Error: Thread '{thread_name}' not found."
    return at(workspace, thread_name, directory)


class Dispatch(NamedTuple):
    """A resolved thread and the schema function about to run on it."""

    thread: Thread
    fn: Callable[..., str]


def _for(workspace_dir: str, thread_name: str, op: str) -> Dispatch | str:
    """Resolve the thread and its schema's implementation of `op`.

    A schema that never grew the operation simply has no attribute of that
    name, so a schema older than a feature refuses here rather than
    half-running.
    """
    thread = _locate(workspace_dir, thread_name)
    if isinstance(thread, str):
        return thread
    fn = getattr(implementation(thread), op, None)
    if fn is None:
        return needs_migration_message(thread.name, thread.schema)
    return Dispatch(thread, fn)


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
    call = _for(workspace_dir, thread_name, "resume")
    if isinstance(call, str):
        return call
    return _focus(call.thread, call.fn(call.thread))


def create(workspace_dir: str, thread_name: str) -> str:
    """Create a thread at the schema this plugin currently writes."""
    if not validate_thread_name(thread_name):
        return (
            f"Error: Invalid thread name '{thread_name}'. "
            "Thread names must be kebab-case (lowercase letters, numbers, hyphens). "
            "Examples: my-thread, api-redesign, auth-refactor"
        )

    workspace = ws.resolve_for_create(workspace_dir)
    if isinstance(workspace, str):
        return workspace

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
    call = _for(workspace_dir, thread_name, "add_todo")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, title, link, state, session_id)


def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped, removing it from any window."""
    call = _for(workspace_dir, thread_name, "retire_todo")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, todo_id, state)


def set_todo_state(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Park or unpark a todo without retiring it."""
    call = _for(workspace_dir, thread_name, "set_state")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, "todos", todo_id, state)


def set_window(workspace_dir: str, thread_name: str, entry_ids: list[str],
               section: str = "next_steps", kind: str = "todos") -> str:
    """Choose which entries the README shows, and in what order."""
    call = _for(workspace_dir, thread_name, "set_window")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, kind, section, entry_ids)


def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, status: str = "proposed",
                 supersedes: list[str] | None = None,
                 session_id: str | None = None) -> str:
    """Write a decision file and index it."""
    call = _for(workspace_dir, thread_name, "log_decision")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, title, summary, body, status, supersedes, session_id)


def retire_decision(workspace_dir: str, thread_name: str, decision_id: str,
                    state: str) -> str:
    """Retire a decision that was neither superseded nor is still in force."""
    call = _for(workspace_dir, thread_name, "retire_decision")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, decision_id, state)


def add_artifact(workspace_dir: str, thread_name: str, title: str, link: str,
                 session_id: str | None = None) -> str:
    """Index a file the thread produced."""
    call = _for(workspace_dir, thread_name, "add_artifact")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, title, link, session_id)


def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact that is superseded or no longer relevant."""
    call = _for(workspace_dir, thread_name, "retire_artifact")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, artifact_id, state)


def save_session(workspace_dir: str, thread_name: str, slug: str, summary: str,
                 keywords: str, next_context: str, body: str | None = None,
                 status: str | None = None) -> str:
    """Write the session log and the Status paragraph in one call."""
    call = _for(workspace_dir, thread_name, "save_session")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, slug, summary, keywords, next_context, body, status)


def migration_safety_check(workspace_dir: str, thread_name: str) -> str:
    """Report whether a thread is safe to convert in place.

    Not dispatched on a schema: it asks whether the workspace can recover if
    the conversion goes wrong, which is the same question for any schema.
    """
    from ai_workspace.threads import migrate

    located = ws.thread_dir(workspace_dir, thread_name)
    if isinstance(located, str):
        return located
    return migrate.safety_check(located.workspace, thread_name)


def audit_migration(workspace_dir: str, original_thread: str,
                    converted_thread: str) -> str:
    """Compare a converted copy against its original and report what it lost."""
    from ai_workspace.threads import migrate

    located = ws.thread_dir(workspace_dir, original_thread)
    if isinstance(located, str):
        return located
    original = located.path
    converted = ws.thread_path(located.workspace, converted_thread)
    for path, label in ((original, original_thread), (converted, converted_thread)):
        if not path.is_dir():
            return f"Error: Thread '{label}' not found."
    return migrate.audit(original, converted)
