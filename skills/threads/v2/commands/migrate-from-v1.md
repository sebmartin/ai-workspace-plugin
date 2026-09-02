# Command: migrate a thread from schema 1 to schema 2

There is no migration tool. The shapes are close enough to read unaided, and
every write needed already exists. This is the procedure.

**Nothing is converted in place.** The original survives untouched until a
verified swap, and nothing is ever deleted.

**Never delete anything, and never offer to.** Not the staging copy, not the
backup, not a file inside either. Leave both directories in place and tell the
user which one they can remove. Deleting a thread is a judgment call with no
undo, and an assistant that deletes the wrong one has destroyed work that only
existed there.

## Before anything

Call `migration_safety_check` and relay what it says. It reports whether the
thread is under version control and whether it has uncommitted changes. It is
advice, not a gate — the user can proceed without git — but say plainly that
the pre-migration state is not recoverable if the answer is no.

## The procedure

1. Rename `threads/{name}/` to `threads/{name}-v1/`
2. Deep-copy it to `threads/{name}-v2/`, preserving timestamps (`cp -a`, or
   `shutil.copytree` with `copy2`)
3. Write `schema-version` containing `2` into the copy
4. Convert the copy — below
5. Call `audit_migration`, read what it reports, and resolve anything real
6. Rename `{name}-v2` to `{name}`
7. Tell the user `{name}-v1` is theirs to remove or archive when they are satisfied

Renaming first means every directory states its version at every instant, and
there is never a `{name}` whose shape is ambiguous. The cutover is one rename
of a tree that has already been checked.

**The staging name is what says a conversion is unfinished.** A half-converted
copy and a finished one are byte-identical inside — a missing index is a valid
empty index — so the state lives in the name instead. While `{name}-v2` exists
there is no `{name}`, and the final rename is what completes the migration. That
needs no marker file and so nothing has to be deleted to finish.

If `{name}-v2` already exists when you start, a previous attempt was abandoned.
Stop and ask; do not overwrite it.

`{name}-v1` is terminal and never renamed back. To abandon a migration, stop and
say so: `{name}-v1` is already a working thread that every schema 1 tool
operates on, and `{name}-v2` is an inert directory the user can remove when they
choose. Say which is which and leave them both.

## Converting the copy

Read `{name}-v1/README.md` — the original, not the copy, which you are about to
overwrite.

**Build the indexes in date order.** Walk `sessions/` first and note which files
each session mentions; that map dates artifacts that carry no date of their own,
and it recovers most of them. Then walk `decisions/` and `artifacts/`, adding an
entry per top-level file or directory with `add_artifact` and `log_decision`.

The index places each entry by its id, so feeding them out of order is not
itself a problem. A date comes from frontmatter, then from the filename, then
from a session that references the file. Anything with none gets `19700101`, which
means unknown — never invent a plausible date, and never use a filesystem
timestamp, which records when bytes moved rather than when something was
written.

**Do not rename any file.** The derived date mints the index id; the file keeps
its name and the index line links to it. Renaming would break links from session
logs into decisions, from decision bodies into artifacts, from the README and
from other threads, none of which anything rewrites and none of which error when
dangling.

**Substitute the status vocabulary** as you go: `decided`, `active`,
`confirmed`, `adopted` and `Accepted` become `locked`; `mostly-locked` becomes
`partially-locked`; `open` becomes `proposed`. Decisions with no status need
reading. So do any whose prose describes supersession, to tell which superseded
which — the live one declares `supersedes`.

**Extract todos** from Next steps, Parked and Open Questions. Each needs a link:
the session it came from when it has nothing of its own. Parked entries that are
already resolved should be retired rather than carried over. Then `set_window`
with about five, in priority order.

**Collapse Quick Resume into Status** — a few sentences for a person. Everything
else it held is now a todo, a decision or a session.

`attachments/` is copied across and left alone. It has no index, because an
attachment is a file the user dropped in and there is no moment where a
description gets authored.
