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

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from ai_workspace import workspace as ws
from ai_workspace.threads.schema import (  # noqa: F401  (re-exported)
    CURRENT_SCHEMA,
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
    "add_todo",
    "audit_migration",
    "create",
    "index_directory",
    "index_file",
    "log_decision",
    "migration_safety_check",
    "names_one_directory",
    "order_todos",
    "resume",
    "retire_artifact",
    "retire_decision",
    "retire_todo",
    "save_session",
    "set_about",
    "set_todo_state",
    "star_artifact",
    "unstar_artifact",
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
    fn: Callable[..., Any]


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


LINKED_ABOUT_WORDS = 50  # local so this layer names no schema module


def _cut_about(text: str) -> str:
    """The first paragraph on one line, cut to LINKED_ABOUT_WORDS words."""
    words = text.strip().split("\n\n")[0].split()
    if len(words) > LINKED_ABOUT_WORDS:
        return " ".join(words[:LINKED_ABOUT_WORDS]) + "…"
    return " ".join(words)


def _refusal_code(message: str) -> str:
    """The `error` of a JSON refusal, else the message's first line."""
    try:
        parsed = json.loads(message)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and "error" in parsed:
        return str(parsed["error"])
    return message.splitlines()[0] if message else ""


def _linked_about(workspace: Path, name: str) -> str:
    """What to show of a linked thread: its About, or why there is none."""
    state = ws.thread_state(workspace, name)
    if state == ws.ARCHIVED:
        return "(archived)"
    if state != ws.ACTIVE or not (ws.thread_path(workspace, name) / "README.md").exists():
        return "(not found)"
    result = _for(str(workspace), name, "about")
    if isinstance(result, str):
        return "(unreadable schema)"
    about = result.fn(result.thread)
    return _cut_about(about) if about.strip() else "(no About)"


def _linked_threads(thread: Thread) -> str:
    """The section naming the threads this one links, or "" when it links none."""
    call = _for(str(thread.workspace), thread.name, "links")
    if isinstance(call, str):
        return (
            f"\n## Linked threads\n\nThis thread's links could not be read "
            f"({_refusal_code(call)}).\n"
        )
    seen: set[str] = set()
    lines = []
    for link in call.fn(call.thread):
        if link.name is None:
            lines.append(f"- {link.role}: {link.text}")
            continue
        if link.name in seen:
            continue
        seen.add(link.name)
        note = f" (note: {link.note})" if link.note else ""
        about = _linked_about(thread.workspace, link.name)
        lines.append(
            f"- {link.role}: [{link.name}](../{link.name}/README.md){note} — {about}"
        )
    if not lines:
        return ""
    return (
        f"\n## Linked threads ({len(lines)})\n\n"
        "Before saying you don't know something, check whether one of these covers it. "
        "Read its README and indexes; don't resume it.\n\n"
        + "\n".join(lines) + "\n"
    )


def resume(workspace_dir: str, thread_name: str) -> str:
    """Return the thread's context, in whatever form its schema keeps it."""
    call = _for(workspace_dir, thread_name, "resume")
    if isinstance(call, str):
        return call
    return _focus(call.thread, call.fn(call.thread) + _linked_threads(call.thread))


def create(workspace_dir: str, thread_name: str, about: str = "") -> str:
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
    result = implementation(thread).create(thread, about)
    if isinstance(result, dict):
        return json.dumps(result)  # refused before anything was created
    return _focus(thread, result)


def add_todo(workspace_dir: str, thread_name: str, title: str, link: str,
             state: str = "active", place: str = "") -> str:
    """Add a todo at a chosen place in the thread's list."""
    call = _for(workspace_dir, thread_name, "add_todo")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, title, link, state, place)


def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped."""
    call = _for(workspace_dir, thread_name, "retire_todo")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, todo_id, state)


def set_todo_state(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Start, park or unpark a todo without retiring it."""
    call = _for(workspace_dir, thread_name, "set_state")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, "todos", todo_id, state)


def order_todos(workspace_dir: str, thread_name: str, todo_ids: list[str],
                place: str = "") -> str:
    """Move the named todos to a chosen place in the list, in the order given."""
    call = _for(workspace_dir, thread_name, "order_todos")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, todo_ids, place)


def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, state: str = "proposed",
                 supersedes: list[str] | None = None) -> str:
    """Write a decision file and index it."""
    call = _for(workspace_dir, thread_name, "log_decision")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, title, summary, body, state, supersedes)


def retire_decision(workspace_dir: str, thread_name: str, decision_id: str,
                    state: str) -> str:
    """Retire a decision that was neither superseded nor is still in force."""
    call = _for(workspace_dir, thread_name, "retire_decision")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, decision_id, state)


def index_directory(workspace_dir: str, thread_name: str, link: str) -> str:
    """Index everything in one directory that is not indexed yet."""
    call = _for(workspace_dir, thread_name, "index_directory")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, link)


def index_file(workspace_dir: str, thread_name: str, link: str,
               description: str = "", date: str | None = None) -> str:
    """Index a file that is already in the thread."""
    call = _for(workspace_dir, thread_name, "index_file")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, link, description, date)


def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact that is superseded or no longer relevant."""
    call = _for(workspace_dir, thread_name, "retire_artifact")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, artifact_id, state)


def star_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                  when: str) -> str:
    """Star an artifact so resume lists it with a trigger for reading it."""
    call = _for(workspace_dir, thread_name, "star_artifact")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, artifact_id, when)


def unstar_artifact(workspace_dir: str, thread_name: str, artifact_id: str) -> str:
    """Remove an artifact's star."""
    call = _for(workspace_dir, thread_name, "unstar_artifact")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, artifact_id)


def save_session(workspace_dir: str, thread_name: str, slug: str, summary: str,
                 keywords: str, body: str,
                 recently: list[str], up_next: list[str]) -> str:
    """Write the session log and the Status lists in one call."""
    call = _for(workspace_dir, thread_name, "save_session")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, slug, summary, keywords, body, recently, up_next)


def set_about(workspace_dir: str, thread_name: str, text: str) -> str:
    """Replace the thread's About section."""
    call = _for(workspace_dir, thread_name, "set_about")
    if isinstance(call, str):
        return call
    return call.fn(call.thread, text)


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
