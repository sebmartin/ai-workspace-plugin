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
    default).

    Every operating tool answers a failed resolution the same way:
    `{"error": "NO_WORKSPACE", "tried": ...}`. Ask the user for their workspace
    path, call set_default_workspace, then retry the original call.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default.
    """
    return _ws.list_threads(workspace_dir)


@mcp.tool()
def resume_thread(workspace_dir: str, thread_name: str) -> str:
    """Resolve the workspace and thread path, and return the full README content.

    A thread this plugin cannot read returns `{"error": CODE, "thread": ...,
    "schema": <n>, "reads": [<low>, <high>]}`: `SCHEMA_TOO_NEW` (upgrade the
    plugin), `SCHEMA_RETIRED` (migrate it with a version that still reads it),
    or `UNREADABLE_SCHEMA` (its marker file is not an integer).

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default.
        thread_name: Name of the thread (kebab-case).
    """
    return _threads.resume(workspace_dir, thread_name)


@mcp.tool()
def create_thread(workspace_dir: str, thread_name: str) -> str:
    """Create a new discussion thread with the standard directory structure.

    Resolves the workspace from `workspace_dir`. If `workspace_dir` has a threads/ dir, the thread
    is created there. If not, the tool may return a status the LLM must surface
    to the user:
    - `{"error": "AMBIGUOUS_WORKSPACE", "tried": ..., "configured": ...}` when a
      configured default exists
      (user picks between configured workspace vs initialising a new one here).
    - `{"error": "NEEDS_INIT", "tried": ...}` when none exists anywhere (user picks between
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
            falls back to the configured default.
        thread_name: Name of the thread to archive.
    """
    return _ws.archive(workspace_dir, thread_name)



@mcp.tool()
def restore_thread(workspace_dir: str, thread_name: str) -> str:
    """Restore an archived thread: move it back from archive/ into threads/.

    Takes the thread's own name. Archives created before 3.0 are tarballs and
    are not unpacked by this tool; it returns
    `{"error": "LEGACY_ARCHIVE", "tarball": ..., "reference": ...}` naming
    the reference to follow.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default.
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
            falls back to the configured default.
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

    Returns `{"id": ...}`, the minted todo id. `set_window` and the retire
    tools take it.

    A refusal returns `{"error": CODE, ...}` and writes nothing: `STATE_UNKNOWN`
    or `STATUS_UNKNOWN` with the `allowed` values, `NO_SUCH_ENTRY`,
    `LINK_REQUIRED`.

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

    Returns `{"id": ...}`.

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

    Returns `{"id": ...}`.

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

    Returns `{"window": ..., "size": ...}`.

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

    Returns `{"id": ...}`, plus `superseded` listing what it retired. The file
    is at ./decisions/<id>.md.

    A refusal returns `{"error": CODE, ...}` and writes nothing: `STATE_UNKNOWN`
    or `STATUS_UNKNOWN` with the `allowed` values, `NO_SUCH_ENTRY`,
    `LINK_REQUIRED`.

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

    Returns `{"id": ...}`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        decision_id: The id from the index line.
        state: `superseded` when something replaced it, `withdrawn` when it was
            abandoned with nothing taking its place.
    """
    return _threads.retire_decision(workspace_dir, thread_name, decision_id, state)


@mcp.tool()
def index_directory(workspace_dir: str, thread_name: str, link: str) -> str:
    """Index every file in one directory that is not indexed yet.

    Use this instead of calling index_file once per file. A migration indexes
    whole directories, and for sessions and decisions there is nothing per-file
    to supply: everything on the line is read off the file. Only artifacts carry
    a description, so index those one at a time when the description matters.

    Idempotent, so a run that refused some files can be repeated once they are
    fixed without duplicating what went in. A refusal does not stop the rest.

    Returns JSON, and reports only deviations. `{}` means every file went in,
    including when there were none to do; you asked for the directory, so
    silence is the answer that it got them.

        {"undated": ["notes"],
         "refused": {"STATUS_UNKNOWN": ["20260301-old.md"]}}

    `undated` names anything given the 19700101 date because nothing said when
    it was from. It is indexed and usable; the id just sorts at the epoch.

    `refused` maps a code to the files it applies to. Fix those and run again.

    - `FRONTMATTER_UNPARSEABLE` — not valid YAML, so a decision's status cannot
      be read. Usually an unquoted value containing ": ". Call index_file on
      one of them for the parser's own message.
    - `STATUS_UNKNOWN` — a decision declares a status this schema does not use.
      Substitute the vocabulary in the file's frontmatter.
    - `UNREADABLE` — the file could not be opened.

    A bad request returns `{"error": CODE, "detail": ...}` and indexes nothing:
    `OUTSIDE_THREAD`, `NOT_INDEXABLE`, or `NO_SUCH_DIRECTORY` when the kind is
    valid but the thread has no such directory, which means it is malformed.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        link: Directory relative to the thread, e.g. ./sessions.
    """
    return _threads.index_directory(workspace_dir, thread_name, link)


@mcp.tool()
def index_file(workspace_dir: str, thread_name: str, link: str,
               description: str = "") -> str:
    """Index a file that is already in the thread.

    Use this once a file exists on disk: an artifact you have written, or a
    session, decision or artifact being brought into the index during a
    migration. It refuses a link that does not resolve, so write the file first.

    Everything on the index line is derived from the file. The kind comes from
    the directory, the id from a date found in the filename, and a decision's
    state from its `status:` frontmatter, which must already use this schema's
    vocabulary. A file whose name states no date is dated from the earliest
    session that names it, and failing that is marked unknown.

    Returns JSON: `{"id": "20260316-summary-auth-flow"}`, with `"undated": true`
    when nothing said what date the file is from, so it took 19700101.

    A refusal returns `{"error": CODE, "detail": ...}` and writes nothing. Same
    codes as index_directory, plus `MISSING` when the link resolves to nothing
    and `METADATA` for a dotfile, which is never content.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        link: Path relative to the thread, e.g. ./artifacts/20260813-notes-x.md.
        description: One line saying what an artifact contains. Artifacts only,
            and the only thing not read from the file: decisions and sessions
            carry a `summary:` in their own frontmatter, artifacts have nowhere
            to put one. It is read on every resume, so it costs something
            permanently, the same way a decision's summary does. One sentence.
            A thread whose sixteen artifacts averaged 255 characters spent 30%
            of its resume on them.
    """
    return _threads.index_file(workspace_dir, thread_name, link, description)


@mcp.tool()
def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact so it stops appearing as current.

    Returns `{"id": ...}`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        artifact_id: The id from the index line.
        state: `superseded` when something replaced it, `stale` when it no longer
            describes reality.
    """
    return _threads.retire_artifact(workspace_dir, thread_name, artifact_id, state)



@mcp.tool()
def save_session(workspace_dir: str, thread_name: str, slug: str, summary: str,
                 keywords: str, next_context: str, body: str = "",
                 status: str = "") -> str:
    """Save the session log and the thread's Status paragraph.

    Todos, decisions and artifacts are written when they happen, so a save is
    only the two things that need synthesising. Everything else is already on
    disk.

    `body` is optional. Leave it empty when the session file has already been
    written or extended directly — a long body in one tool call has to fit the
    model's output budget in a single response, where writing the file
    incrementally does not. With no body, this updates the frontmatter, the
    index entry and the dates and leaves the prose alone.

    Returns `{"id": ..., "status_written": ...}`. A refusal returns
    `{"error": CODE, ...}` and writes nothing.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        slug: Short kebab-case topic for the session, used in its id and filename.
        summary: Up to 150 words on what was discussed and settled.
        keywords: Comma-separated terms to search for later.
        next_context: One or two sentences on where things stand and what is next.
        body: Full markdown body. Omit to keep what the file already has.
        status: The thread's Status paragraph. Omit to leave it unchanged.
    """
    # The tool surface takes "" because MCP needs a concrete default; the
    # operation distinguishes "no body given" from "replace the body with
    # nothing", so the empty string has to become None here.
    return _threads.save_session(workspace_dir, thread_name, slug, summary,
                                 keywords, next_context, body or None,
                                 status or None)



@mcp.tool()
def migration_safety_check(workspace_dir: str, thread_name: str) -> str:
    """Report whether a thread could be recovered if its migration goes wrong.

    Call this before starting a migration and relay what it says. It is advice,
    not a gate: the plugin never commits, so the user decides. The migration
    keeps the original either way, but that only covers mistakes up to the
    swap.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread about to be migrated (kebab-case).
    """
    return _threads.migration_safety_check(workspace_dir, thread_name)


@mcp.tool()
def audit_migration(workspace_dir: str, original_thread: str,
                    converted_thread: str) -> str:
    """Compare a converted copy against the original and report what it lost.

    Run this after converting and before the swap. It checks the parts that are
    decidable — files present in one tree and not the other, index entries
    pointing at nothing, indexes out of date order, entries with no derivable
    date. It cannot tell you whether the Quick Resume prose survived as todos
    and Status; read that yourself.

    Returns JSON. `{"clean": true}` when nothing mechanical is wrong; branch on
    that before reading anything else. Otherwise the keys name what to fix:

    - `unindexed` — {kind: [filenames]} present in the original and in no index.
    - `missing_from_copy` — {kind: [filenames]} in the original, absent from the copy.
    - `dangling` — {kind: [links]} indexed but pointing at nothing.
    - `out_of_date_order` — [kind] whose index is not sorted by id.
    - `v1_readme_sections` — schema 1 headings still in the converted README.
    - `undated_entries` — how many took the 19700101 date. Not a problem by
      itself, so it does not clear `clean`.

    `clean` never covers judgement: whether Quick Resume survived as todos and
    Status is for a reader, and this tool does not look.

    Args:
        workspace_dir: The tracked workspace path from session context.
        original_thread: The untouched original, e.g. my-thread-v1.
        converted_thread: The converted copy, e.g. my-thread-v2.
    """
    return _threads.audit_migration(workspace_dir, original_thread, converted_thread)


if __name__ == "__main__":
    mcp.run()
