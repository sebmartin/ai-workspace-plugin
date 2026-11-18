#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=2", "python-frontmatter", "ruamel.yaml"]
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
    `memory.md` in full if there is one (a line on its size follows it when it
    has grown large), then starred artifacts in artifact index order, each with
    its description and when to read it, then the header, About, Status, the
    Todos window (goals shown whole with their children indented, taken in
    priority order until at least five lines are out, so a goal is never split;
    a goal shows started when a child is; the heading counts lines shown, active
    and parked todos, and the counts include children), any parked todos
    (a parked child of a goal that is not parked names its goal), every in-force
    decision with its `summary:`, the artifacts index (starred artifacts are left
    out of it), and the recent sessions:
    the full log of the newest ones, as many as fit a fixed allowance and
    always at least the newest, then the `summary:` of the five before them,
    oldest first with the newest last; the heading counts how many are in full,
    how many summarized, and the total.
    Older sessions are not listed; their files under `sessions/` carry
    `summary:` and `keywords:` frontmatter to search. A `## Thread size`
    heading appears only when the thread has grown expensive to open.

    A `## Linked threads` section ends the payload when the header links other
    threads, giving each one's About (or why there is none: archived, not
    found, or a schema this plugin cannot read). It applies to schema 1 threads
    too.

    A thread this plugin cannot read returns `{"error": CODE, "thread": ...,
    "schema": <n>, "reads": [<low>, <high>]}`: `SCHEMA_TOO_NEW` (upgrade the
    plugin), `SCHEMA_RETIRED` (migrate it with a version that still reads it),
    or `UNREADABLE_SCHEMA` (its marker file is not an integer).

    An index that does not parse returns `{"error": "UNREADABLE_INDEX", "file",
    "detail", "fix"}` instead of the thread.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default.
        thread_name: Name of the thread (kebab-case).
    """
    return _threads.resume(workspace_dir, thread_name)


@mcp.tool()
def create_thread(workspace_dir: str, thread_name: str, about: str = "") -> str:
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
        about: What the thread is about and what it is for, 50 words or fewer. A blank
            `about` counts as left out. Otherwise it is checked as `set_about` checks it,
            and a refusal creates nothing. Leave it out when
            the thread's purpose is not clear yet; the placeholder stays until
            `set_about` replaces it.
    """
    return _threads.create(workspace_dir, thread_name, about)


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
             state: str = "active", place: str = "",
             parent: str | None = None) -> str:
    """Add a todo to the thread's Todos list.

    Every todo is read on every resume and commits the user to something, so
    add one only when the user asked for it or agreed to your suggestion. If
    you think something should be a todo, suggest it in your reply.

    Every todo carries a link, and it names the record of this todo. When the
    work is tracked in an external system, link its item there, because the
    item is the todo. Otherwise write a file under todos/ and link the file.

    Never link something the todo merely relates to, such as a PR it mentions
    or the session it came out of. Whoever follows that link lands on separate
    work, often already finished, and still can't tell what the todo is asking
    for. Those belong inside the todo file under `## Links`.

    Write the file before calling this. A `./` path with no file behind it is
    refused.

    The list is in priority order and the new todo goes at the end unless you
    place it. Say where you put it, so the user can move it. The README's Todos section shows
    the top five, so a todo added at the end is in the list without being on
    the README.

    Returns `{"id": ...}`, the minted todo id, which `order_todos` and the
    retire tools take. `active` is present only on the add that takes the list
    past five, carrying the count: tell the user and ask which to park. Later
    adds are quiet, and the resume heading keeps the count.

    A refusal returns `{"error": CODE, ...}` and writes nothing:
    `STATE_UNKNOWN` or `PLACE_UNKNOWN` with the `allowed` values,
    `TITLE_REQUIRED`, `LINK_REQUIRED`, `OUTSIDE_THREAD` for a link that is
    neither a `./` path under the thread nor an `http(s)` URL,
    `MISSING` for a `./` path with no file behind it, whose `detail` is the
    link: write the file first,
    `NO_SUCH_ENTRY` naming an anchor that is not in the list, or a `parent`
    that is not a todo, and `PARENT_IS_CHILD` when `parent` is itself a child,
    since a goal holds one level of children.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short label for the todo.
        link: The record of this todo. Either a path under the thread
            starting with `./`, such as ./todos/YYYYMMDD-slug.md, which must
            already exist, or the `http(s)` URL of the todo's own item in an
            external tracker. Anything else is refused, because the workspace
            is not mounted at the same place on every machine that resumes the
            thread, so an absolute path, a `~` and a bare relative path all
            resolve to nothing on the next one.
        state: `active`, `started` once work on it has begun, which matters
            more than todos not yet started and puts it at the top. It stays
            until the todo is retired, parked or set back to `active` by hand,
            and leaves any other started todo as it is. `parked` is for
            deliberately not now.
        place: Where it goes. `top` for something to do next, such as a piece
            of the task in hand. `before:<todo id>` or `after:<todo id>` for
            something that belongs beside a particular todo. `end`, or leave it
            out, for everything else. `top` and `end` are read off the list as
            it is now, so they are right even if you have not looked at it,
            where an id you believe is first may have been overtaken. With
            `parent`, it resolves within that goal's children, so an anchor
            must be one of them.
        parent: The id of a top-level todo to put this one under. It becomes
            a goal if it was a plain todo. Leave it out for a top-level todo,
            which is the usual case. A started child also moves its goal to
            the top of the list. A parked goal is allowed.
    """
    return _threads.add_todo(workspace_dir, thread_name, title, link, state, place, parent)


@mcp.tool()
def retire_todo(workspace_dir: str, thread_name: str, todo_id: str, state: str) -> str:
    """Retire a todo as done or dropped.

    When the todo's link names a file, its `state:` line is rewritten to
    match, so a finished todo found by grep does not still read
    `state: active`.

    Returns `{"id": ...}`, plus `file_unchanged` naming that file when its
    `state:` line could not be found. The index and the file then disagree,
    and the file is the copy a reader finds by grep. Nothing else reports it,
    so say so and name the file.

    A refusal returns `{"error": CODE, ...}` and writes nothing:
    `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

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

    Two of the states move the todo as well as labelling it. `started` means work
    on the todo has begun, so it matters more than todos not yet started. It
    stays until the todo is retired, parked or set back to `active` by hand, and
    several todos can be started at once. Starting moves the todo to the top of
    its list; for a child, its goal also goes to the top of the list, and a
    parked goal becomes active. Call it when the user asks to start or resume a
    todo. Unparking sends it to the end of its list, because parked meant for
    later.

    Parking a goal parks its open children too. Unparking a goal unparks every
    parked child and sends the goal to the end of the list. A child moves
    alone: parking it leaves its goal and siblings as they are, and unparking
    it sends it to the end of its goal's children, and makes its goal active
    if the goal was parked, so the child is visible.

    When the todo's link names a file, its `state:` line is rewritten to
    match, so a parked todo found by grep does not still read `state: active`.

    Returns `{"id": ...}`, with `goal` carrying the goal's id when the todo is
    a child, `active` carrying the count when unparking is
    what takes the list past five, and `file_unchanged` naming the todo's file
    when its `state:` line could not be found, and `files_unchanged` listing
    the same for any other todo the change cascaded to, only when there are
    some. The index and the file then disagree, and the file is the copy a
    reader finds by grep. Nothing else reports it, so say so and name the files.

    A refusal returns
    `{"error": "STATE_UNKNOWN", "allowed": [...]}` or
    `{"error": "NO_SUCH_ENTRY"}` and writes nothing.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_id: The id from the index line.
        state: `started` once work on it has begun, `parked` for
            deliberately not now, `active` for anything else.
    """
    return _threads.set_todo_state(workspace_dir, thread_name, todo_id, state)


@mcp.tool()
def order_todos(workspace_dir: str, thread_name: str, todo_ids: list[str],
                place: str = "") -> str:
    """Move the named todos together, in the order given.

    Every id must be in one list: all top-level todos, or all children of one
    goal. `place` resolves in that list, so an anchor from another list is not
    found. Everything else keeps its relative order, so naming the two that
    matter leaves the rest alone, and moving a goal moves its children with it.
    The order is the user's, so propose one and call
    this once they agree.

    This is also how what the README's Todos section shows changes, because what it shows is
    the top of the list. Nothing has to be promoted when a todo is retired:
    the sixth becomes the fifth by itself.

    Returns `{"ordered": <how many were named>}`. A refusal returns
    `{"error": CODE, "detail": ...}` and writes nothing: `NO_SUCH_ENTRY`
    naming the ids that are not in the list, including the anchor;
    `NOT_SAME_LIST` when the ids are not all in one list, whose `detail` is
    the ids given: order them in separate calls;
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
def set_parent(workspace_dir: str, thread_name: str, todo_ids: list[str],
               parent: str | None) -> str:
    """Nest todos under a goal, move them between goals, or take them back out.

    A goal is a top-level todo that holds child todos, one level deep. Pass a
    goal's id as `parent` to put the todos under it, which makes it a goal if
    it was a plain todo. `parent` is required so that a forgotten argument
    cannot un-nest anything: pass `null` to take the todos back to the top
    level. Giving a list lets a goal and its children be set up in one call.

    Nesting puts each todo last among the parent's children, in the order
    given, and a todo already under that parent keeps its place. `null` puts
    a child straight after its old goal in the top-level list, and several
    from the same goal go in the order given, each after the one before. A
    todo already at the top level is left alone.

    Returns `{"moved": [ids whose list changed, in the order given]}`, so a
    call that changed nothing returns `{"moved": []}`. A refusal returns
    `{"error": CODE, "detail": ...}` and writes nothing, checked in this
    order: `IDS_REQUIRED` when `todo_ids` is empty; `NO_SUCH_ENTRY` naming
    the ids that are not todos, `parent` included; `DUPLICATE_ID` naming
    an id given twice; `PARENT_IS_SELF` when `parent` is one of `todo_ids`;
    `PARENT_IS_CHILD` when `parent` is itself a child, since a goal holds one
    level; and `TODO_IS_GOAL` naming todos that are goals, since a goal cannot
    become a child.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        todo_ids: Ids of the todos to move, in the order they should come.
        parent: The id of the top-level todo to put them under, or `null` to
            take them back to the top level.
    """
    return _threads.set_parent(workspace_dir, thread_name, todo_ids, parent)


@mcp.tool()
def log_decision(workspace_dir: str, thread_name: str, title: str, summary: str,
                 body: str, state: str = "proposed",
                 supersedes: list[str] | None = None) -> str:
    """Write a decision file and index it.

    Every decision is read on every resume and shapes later sessions, so log
    one only when the user asked for it or agreed to your suggestion. If you
    think a decision should be logged, suggest it in your reply. Do not suggest
    one that dies with the task; the session log holds it.

    `summary` is read on every resume, so it carries real cost: one sentence,
    one subject, what was decided and not why. If it needs "and" twice, that is
    the signal to log several decisions instead.

    `supersedes` retires the decisions it names.

    Returns `{"id": ...}`, plus `superseded` listing what it retired. The file
    is at ./decisions/<id>.md.

    A refusal returns `{"error": CODE, ...}` and writes nothing:
    `STATE_UNKNOWN` with the `allowed` values, `NO_SUCH_ENTRY`,
    `LINK_REQUIRED`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        title: Short title for the decision.
        summary: One sentence, one subject. WHAT was decided, no rationale.
        body: Markdown body. Claim first, argument after.
        state: `proposed`, `partially-locked` or `locked`.
        supersedes: Ids of decisions this replaces; each is retired as superseded.
    """
    return _threads.log_decision(workspace_dir, thread_name, title, summary, body,
                                 state, supersedes)


@mcp.tool()
def retire_decision(workspace_dir: str, thread_name: str, decision_id: str,
                    state: str) -> str:
    """Retire a decision, updating the index and the file's own `state:` line.

    Returns `{"id": ...}`, plus `file_unchanged` naming the decision's file
    when its `state:` line could not be found, and `files_unchanged` listing
    the same for any other todo the change cascaded to, only when there are
    some. The index and the file then disagree, and the file is the copy a
    reader finds by grep. Nothing else reports it, so say so and name the files.

    A decision written before the field was named `state:` is the common
    cause, and the fix is to rename that one line in the file.

    A refusal returns `{"error": CODE, ...}` and writes nothing:
    `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

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
         "refused": {"FILE_STATE_UNKNOWN": ["20260301-old.md"]}}

    `undated` names anything given the 19700101 date because nothing said when
    it was from. It is indexed and usable; the id just sorts at the epoch.

    `refused` maps a code to the files it applies to. Fix those and run again.

    - `FRONTMATTER_UNPARSEABLE` — not valid YAML, so a decision's state cannot
      be read. Usually an unquoted value containing ": ". Call index_file on
      one of them for the parser's own message.
    - `FILE_STATE_UNKNOWN` — a decision file's `state:` is not one this
      schema uses, and `allowed` lists the ones it does. An empty `detail`
      means the file has no `state:` line at all, so add one; otherwise
      `detail` is what it declared, so replace that value. This is the file's
      fault, where `STATE_UNKNOWN` is the caller's.
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
               description: str = "", date: str = "") -> str:
    """Index a file that is already in the thread.

    It refuses a link that does not resolve, so write the file first.

    Everything on the index line is derived from the file. The kind comes from
    the directory, the id from a date found in the filename, and a decision's
    state from its `state:` frontmatter, which must already use this schema's
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
    and `DATE_INVALID`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        link: Path relative to the thread, e.g. ./artifacts/20260813-notes-x.md.
        description: One sentence saying what an artifact contains, refused
            beyond 200 characters. Artifacts
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

    Returns `{"id": ...}`. A starred artifact loses its star, and the reply then
    also carries `star_dropped`, the trigger it had, so you can star it again
    if the retire was a mistake. A refusal returns `{"error": CODE, ...}` and
    writes nothing: `STATE_UNKNOWN` with the `allowed` states, or `NO_SUCH_ENTRY`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        artifact_id: The id from the index line.
        state: `superseded` when something replaced it, `stale` when it no longer
            describes reality.
    """
    return _threads.retire_artifact(workspace_dir, thread_name, artifact_id, state)


@mcp.tool()
def star_artifact(workspace_dir: str, thread_name: str, artifact_id: str,
                  when: str) -> str:
    """Star an artifact, recording when it should be read.

    A star marks an artifact you need to know when to read. Its index line and
    trigger load on every resume under Starred artifacts, and its body is still
    read only on demand.

    Starring and unstarring are the user's call: you propose it, typically when
    trimming memory or at save. The one exception is migrating a schema 1
    thread, where the migration guide has you star on your own judgement.

    Starring an artifact that is already starred replaces its trigger.

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, ...}` and writes
    nothing: `WHEN_EMPTY`, `WHEN_TOO_LONG` with `detail` the limit, or
    `NO_SUCH_ENTRY` with `detail` the id (it is not a current artifact).

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        artifact_id: The id from the index line.
        when: One sentence on one line saying when to read the artifact, such
            as "the user asks about formatting or tone". Refused past 200
            characters.
    """
    return _threads.star_artifact(workspace_dir, thread_name, artifact_id, when)


@mcp.tool()
def unstar_artifact(workspace_dir: str, thread_name: str, artifact_id: str) -> str:
    """Remove an artifact's star.

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, "detail": the id}`
    and writes nothing: `NO_SUCH_ENTRY` (the id is not a current artifact) or
    `NOT_STARRED`.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        artifact_id: The id of the starred artifact.
    """
    return _threads.unstar_artifact(workspace_dir, thread_name, artifact_id)



@mcp.tool()
def save_session(workspace_dir: str, thread_name: str, slug: str, summary: str,
                 keywords: str, body: str,
                 recently: list[str], up_next: list[str]) -> str:
    """Save the session log and rewrite the thread's Status as two lists.

    One call writes the whole log. The body replaces everything the session
    file holds, including anything written to it earlier, so it must be the
    complete log.

    The README's Status section is rewritten on every save as two lists,
    **Recently** and **Up next**. Both lists are passed every time. Decide each
    time whether they changed; passing the same items as last time is a valid
    answer.

    Each item is written as given, as one bullet. Nothing is looked up, so an id
    stays an id. To mention a todo, write it in your own words, such as "Tackle
    todo: <name>".

    Returns `{"id": ...}`. A refusal returns `{"error": CODE, ...}` and writes
    nothing. `BODY_EMPTY` means the body was blank and the call needs the full
    log. `RECENTLY_EMPTY` means `recently` had no items. `TOO_MANY_ITEMS` means
    a list held more than 3 items, with `detail` naming the list and `limit` the
    maximum. `ITEM_EMPTY` means an item was blank and `ITEM_HAS_LINE_BREAK` that
    it spanned lines, with `detail` naming the list.

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread (kebab-case).
        slug: Short kebab-case topic for the session, used in its id, its
            filename and its index title, which is the slug as the id spells
            it and so is shortened past the id's length cap.
        summary: Up to 150 words on what was discussed and settled.
        keywords: Comma-separated terms to search for later.
        body: Full markdown body of the session log.
        recently: One to three items, newest first, describing the thread's
            recent work rather than only this session. Keep items from earlier
            sessions that are still live.
        up_next: Zero to three items, what should happen next. An empty list
            renders `- None`.
    """
    return _threads.save_session(workspace_dir, thread_name, slug, summary,
                                 keywords, body, recently, up_next)



@mcp.tool()
def set_about(workspace_dir: str, thread_name: str, about: str) -> str:
    """Replace the README's About section.

    About is printed to the user on every resume, so it says what the thread is
    about and what it is for, in 50 words or fewer. Call this when About is still
    the placeholder, has grown past 50 words, or no longer fits the thread. Never
    edit About by hand.

    Returns `{"words": n}`. A refusal writes nothing and returns one of
    `ABOUT_EMPTY`, `ABOUT_TOO_LONG` (with `limit` and `words`) or
    `ABOUT_UNREPRESENTABLE` (a heading or `---` line, which is the `detail`).

    Args:
        workspace_dir: The tracked workspace path from session context.
        thread_name: Name of the thread.
        about: The full new text of the About section.
    """
    return _threads.set_about(workspace_dir, thread_name, about)


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
