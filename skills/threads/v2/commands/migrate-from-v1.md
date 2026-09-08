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

### 1. Replace the README first, before any write tool

Overwrite the copy's `README.md` from `templates/v2/thread-template.md`. Not the
finished README; the skeleton. Every write tool re-renders `## Next steps` into
whatever README is there, and a schema 1 README has next steps as bold text
inside `## Quick Resume` rather than as a heading. Writing first and replacing
after produces one document with two diverging next-step lists.

The tools refuse rather than let that happen, so this is the step that unblocks
the rest. Status and About can be filled any time after.

### 2. Index the sessions

`index_file` with each session's path. Nothing else, and nothing before it.

Sessions are self-dating, from a `YYYYMMDD-` prefix and a `date:` in their own
frontmatter, so they need nothing looked up. Everything after this step can be
dated from them, and by then they have been migrated. **That ordering is what
keeps schema 2 from ever reading a schema 1 file, so do not reorder these.**

### 3. Index the decisions and artifacts

`index_file` again, one call per top-level file or directory. A subdirectory is
one artifact. Artifacts take a description: carry across the one-line
description from the v1 README's `### Artifacts` list, which is the only thing
in that list worth keeping and has no other home.

Everything else on the line is read off the file. The id takes a date found
anywhere in the filename, so `2026-01-20-initial-setup.md` and
`snapshot-20260303-parking-lot.md` both sort correctly without being renamed. A
file whose name states no date is dated from the earliest session that names it,
and failing that is marked `19700101`, meaning unknown. Never invent a plausible
date, and never use a filesystem timestamp, which records when bytes moved
rather than when something was written.

**Do not rename any file.** The id is derived; the file keeps its name and the
index line links to it. Renaming would break links from session logs into
decisions, from decision bodies into artifacts, from the README and from other
threads, none of which anything rewrites and none of which error when dangling.

**Substitute the status vocabulary before indexing a decision**, in the file's
own frontmatter: `decided`, `active`, `confirmed`, `adopted` and `Accepted`
become `locked`; `mostly-locked` becomes `partially-locked`; `open` becomes
`proposed`. `index_file` reads `status:` off the file and refuses anything
outside that vocabulary, so a decision you have not converted will say so.

Decisions with no status need reading. So do any whose prose describes
supersession, to tell which superseded which — the live one declares
`supersedes`.

### 4. The rest

**Extract todos** from Next steps, Parked and Open Questions. Each needs a link:
the session it came from when it has nothing of its own. Parked entries that are
already resolved should be retired rather than carried over. Then `set_window`
with about five, in priority order.

**Collapse Quick Resume into Status** — a few sentences for a person. Everything
else it held is now a todo, a decision or a session.

`attachments/` is copied across and left alone. It has no index, because an
attachment is a file the user dropped in and there is no moment where a
description gets authored.
