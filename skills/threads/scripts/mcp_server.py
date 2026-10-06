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

from ai_workspace import plugin as _plugin
from ai_workspace import threads as _threads
from ai_workspace import workspace as _ws
from mcp.server.mcpserver import MCPServer

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
    """Resolve the workspace and thread path, and return the thread's context.

    On a schema 2 thread the reply is composed rather than read from a file:
    `memory.md` in full if there is one, then Status, About, the header, the
    Next steps, any parked todos, every in-force decision with the
    `summary:` read from its file, the artifacts index, and the last ten
    sessions. Next steps is the top of the todo list in priority order, bounded
    to five, and its heading counts what is shown, what is active and what is
    parked, so a long list is visible without being printed. A `## Thread size`
    heading appears only when the thread has grown expensive to open.

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

    Paths are resolved relative to the plugin root and must not escape it.

    Args:
        relative_path: Path relative to the plugin root (e.g., "skills/threads/v1/save-thread.md").
    """
    return _plugin.get_skill_file(relative_path=relative_path)


@mcp.tool()
def set_default_workspace(workspace_path: str) -> str:
    """Set the default workspace directory for thread operations.

    The path is persisted in the plugin's global config.

    Args:
        workspace_path: Absolute path to a directory containing a threads/ folder.
    """
    return _ws.set_default_workspace(workspace_path=workspace_path)


@mcp.tool()
def archive_thread(workspace_dir: str, thread_name: str) -> str:
    """Archive a thread: move it out of threads/ and into archive/.

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

    A thread archived before 3.0 is listed as a tarball, with the reference to
    follow for unpacking it.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default.
    """
    return _ws.list_archived_threads(workspace_dir)





@mcp.tool()
def add_todo(workspace_dir: str, thread_name: str, title: str, link: str,
             state: str = "active", place: str = "") -> str:
    """Add a todo to the thread's list of next steps.

    Every todo is read on every resume and commits the user to something, so
    add one only when the user asked for it or agreed to your suggestion. If
    you think something should be a todo, suggest it in your reply.

    Every todo carries a link, always. Use a file under todos/ when the item has
    state of its own, an external URL when there is an issue or PR, and
    otherwise the session it came out of.

    The list is in priority order and the new todo goes at the end unless you
    place it. Say where you put it, so the user can move it. Next steps shows
    the top five, so a todo added at the end is in the list without being on
    the README; that is what the backlog of a long list looks like here.

    Returns `{"id": ...}`, the minted todo id, which `order_todos` and the
    retire tools take. `active` is present only on the add that takes the list
    past five, carrying the count: tell the user and ask which to park. Later
    adds are quiet, and the resume heading keeps the count.

    A refusal returns `{"error": CODE, ...}` and writes nothing:
    `STATE_UNKNOWN` or `PLACE_UNKNOWN` with the `allowed` values,
    `TITLE_REQUIRED`, `LINK_REQUIRED`, `NO_SUCH_ENTRY` naming an anchor that is
    not in the list,
    and `UNREPRESENTABLE` when a field would not survive an index line, whose
    `detail` names the field. Reword that field; a title cannot contain `]`, a
    link cannot contain `)`, and nothing may contain a line break.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short label for the todo.
        link: Path or URL. Never omit; use the originating session if nothing else.
        state: `active`, `started` for what is being worked on now, which
            puts it at the top, or `parked` for deliberately not now.
        place: Where it goes. `top` for something to do next, such as a piece
            of the task in hand. `before:<todo id>` or `after:<todo id>` for
            something that belongs beside a particular todo. `end`, or leave it
            out, for everything else. `top` and `end` are read off the list as
            it is now, so they are right even if you have not looked at it,
            where an id you believe is first may have been overtaken.
    """
    return _threads.add_todo(workspace_dir, thread_name, title, link, state, place)


@mcp.tool()
def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped.

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, ...}` and writes
    nothing: `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_id: The id from the index line, e.g. 20260808-growcer-prep.
        state: `done` for something finished, `dropped` for something deliberately abandoned.
    """
    return _threads.retire_todo(workspace_dir, thread_name, todo_id, state)


@mcp.tool()
def set_todo_state(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Start, park or unpark a todo without retiring it.

    Two of the states move the todo as well as labelling it. `started` sends it
    to the top of the list and clears the label from whatever held it before,
    since it names the one thing being worked on; call it when the user says to
    work on something. Unparking sends it to the end, because parked meant for
    later.

    Returns `{"id": ...}`, with `active` carrying the count when unparking is
    what takes the list past five. A refusal returns
    `{"error": "STATE_UNKNOWN", "allowed": [...]}` or
    `{"error": "NO_SUCH_ENTRY"}` and writes nothing.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_id: The id from the index line.
        state: `started` for what is being worked on now, `parked` for
            deliberately not now, `active` for anything else.
    """
    return _threads.set_todo_state(workspace_dir, thread_name, todo_id, state)


@mcp.tool()
def order_todos(workspace_dir: str, thread_name: str, todo_ids: list[str],
                place: str = "") -> str:
    """Move the named todos together, in the order given.

    Everything else keeps its relative order, so naming the two that matter
    leaves the rest alone. The order is the user's, so propose one and call
    this once they agree.

    This is also how what Next steps shows changes, because what it shows is
    the top of the list. Nothing has to be promoted when a todo is retired:
    the sixth becomes the fifth by itself.

    Returns `{"ordered": <how many were named>}`. A refusal returns
    `{"error": CODE, "detail": ...}` and writes nothing: `NO_SUCH_ENTRY`
    naming the ids that are not in the list, including the anchor;
    `PLACE_UNKNOWN` with the `allowed` forms; `DUPLICATE_ID` naming one given
    twice; `ANCHOR_IS_MOVING` when the anchor is one of the todos being moved,
    so its place is the thing in question; and `IDS_REQUIRED` when no ids were
    given at all.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_ids: Todo ids, in the order they should come.
        place: Where they go, the same forms `add_todo` takes: `top`, `end`,
            `before:<todo id>` or `after:<todo id>`. Leaving it out means
            `top`, which is what reordering is usually for.
    """
    return _threads.order_todos(workspace_dir, thread_name, todo_ids, place)


@mcp.tool()
def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, status: str = "proposed",
                 supersedes: list[str] | None = None) -> str:
    """Write a decision file and index it.

    Every decision is read on every resume and shapes later sessions, so log
    one only when the user asked for it or agreed to your suggestion. If you
    think a decision should be logged, suggest it in your reply.

    `summary` is read on every resume, so it carries real cost: one sentence,
    one subject, what was decided and not why. If it needs "and" twice, that is
    the signal to log several decisions instead.

    `supersedes` retires the decisions it names.

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

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, ...}` and writes
    nothing: `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

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

    A description cannot be passed here, so an artifact that needs one is
    indexed by index_file instead.

    Idempotent, so a run that refused some files can be repeated once they are
    fixed without duplicating what went in. A refusal does not stop the rest.

    Returns JSON, and reports only deviations. `{}` means every file went in,
    including when there were none to do.

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
    - `UNREPRESENTABLE` — the filename carries a character an index line cannot
      hold, so the entry could not be read back. Rename the file.

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
               description: str = "", date: str = "") -> str:
    """Index a file that is already in the thread.

    It refuses a link that does not resolve, so write the file first.

    Everything on the index line is derived from the file. The kind comes from
    the directory, the id from a date found in the filename, and a decision's
    state from its `status:` frontmatter, which must already use this schema's
    vocabulary. A file whose name states no date takes the `date` you pass, and
    is marked unknown if you pass none.

    Calling it again on a file that is already indexed returns the id it
    already has rather than adding a second entry, and replaces the description
    if you pass a different one. That is the only way to correct an artifact
    description or repair an unknown date. Passing no description leaves the
    existing one alone.

    Returns JSON: `{"id": "20260316-summary-auth-flow"}`, with `"undated": true`
    when nothing said what date the file is from, so it took 19700101, and
    `"was"` carrying the previous id when a date changed it. Use the new one
    from then on: ids are what order_todos and the retire tools take.

    A refusal returns `{"error": CODE, "detail": ...}` and writes nothing. Same
    codes as index_directory, plus `MISSING` when the link resolves to nothing,
    `METADATA` for a dotfile, which is never content,
    `DESCRIPTION_TOO_LONG`, whose `detail` is the limit in characters,
    `UNREPRESENTABLE` when the link or the description would not survive an
    index line, whose `detail` names the field, and `DATE_INVALID`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        link: Path relative to the thread, e.g. ./artifacts/20260813-notes-x.md.
        description: One sentence saying what an artifact contains, refused
            beyond 200 characters or if it carries a line break. Artifacts
            only; decisions and sessions carry a `summary:` in their own
            frontmatter. It is read on every resume.
        date: `YYYY-MM-DD`, when the file is from. Only read when the filename
            states no date. Take it from the file's own contents, or from the
            decision or session that produced it, or ask. Leave it out rather
            than guessing: an unknown date can be repaired later, and a wrong
            one is never flagged.
    """
    return _threads.index_file(workspace_dir, thread_name, link, description, date or None)


@mcp.tool()
def retire_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                    state: str) -> str:
    """Retire an artifact so it stops appearing as current.

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, ...}` and writes
    nothing: `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

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
                 keywords: str, body: str,
                 status: str = "") -> str:
    """Save the session log and the thread's Status paragraph.

    One call writes the whole log. The body replaces everything the session
    file holds, including anything written to it earlier, so it must be the
    complete log.

    Returns `{"id": ..., "status_written": ...}`. A refusal returns
    `{"error": CODE, ...}` and writes nothing. `BODY_EMPTY` means the body was
    blank; nothing was saved, and the call needs the full log.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        slug: Short kebab-case topic for the session, used in its id, its
            filename and its index title, which is the slug as the id spells
            it and so is shortened past the id's length cap.
        summary: Up to 150 words on what was discussed and settled.
        keywords: Comma-separated terms to search for later.
        body: Full markdown body of the session log.
        status: The thread's Status paragraph. Omit to leave it unchanged.
    """
    return _threads.save_session(workspace_dir, thread_name, slug, summary,
                                 keywords, body, status or None)



@mcp.tool()
def migration_safety_check(workspace_dir: str, thread_name: str) -> str:
    """Report whether a thread could be recovered if its migration goes wrong.

    The result is advice for the user, who decides whether to go ahead; the
    plugin never commits. The migration keeps the original either way, but
    that only covers mistakes up to the swap. Relay what it says.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread about to be migrated (kebab-case).
    """
    return _threads.migration_safety_check(workspace_dir, thread_name)


@mcp.tool()
def audit_migration(workspace_dir: str, original_thread: str,
                    converted_thread: str) -> str:
    """Compare a converted copy against the original and report what it lost.

    It checks the parts that are decidable: files present in one tree and
    missing from the other, index entries pointing at nothing, indexes out of
    date order, entries with no derivable date. It cannot tell you whether the
    Quick Resume prose survived as todos and Status; read that yourself.

    Returns JSON. `{"clean": true}` when nothing mechanical is wrong; branch on
    that before reading anything else. Otherwise the keys name what to fix:

    - `unindexed` — {kind: [filenames]} present in the original and in no index.
    - `missing_from_copy` — {kind: [filenames]} in the original, absent from the copy.
    - `dangling` — {kind: [links]} indexed but pointing at nothing.
    - `out_of_date_order`: [kind] whose index is not sorted by id. Todos are
      exempt, since that list carries the user's priority rather than dates.
    - `v1_readme_sections` — schema 1 headings still in the converted README.

    - `undated_entries` — how many took the 19700101 date. Not a problem by
      itself, so it does not clear `clean`.
    - `readme_sections_to_place` — `##` headings the original README carried
      beyond the schema 1 template. A section left unplaced is never read
      again. Also does not clear `clean`, since whether each found a home is
      judgement.

    Args:
        workspace_dir: The tracked workspace path from session context.
        original_thread: The untouched original, e.g. my-thread-v1.
        converted_thread: The converted copy, e.g. my-thread-v2.
    """
    return _threads.audit_migration(workspace_dir, original_thread, converted_thread)


if __name__ == "__main__":
    mcp.run()
