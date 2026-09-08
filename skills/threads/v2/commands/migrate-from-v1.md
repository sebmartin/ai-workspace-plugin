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
7. Record the backup as a todo, and tell the user `{name}-v1` is theirs to
   remove or archive when they are satisfied

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

`index_directory` with `./sessions`. One call, however many there are: a thread
with sixty-six sessions is sixty-six round trips if you index them one at a
time. Nothing else, and nothing before it.

Sessions are self-dating, from a `YYYYMMDD-` prefix and a `date:` in their own
frontmatter, so they need nothing looked up. Everything after this step can be
dated from them, and by then they have been migrated. **That ordering is what
keeps schema 2 from ever reading a schema 1 file, so do not reorder these.**

### 3. Index the decisions and artifacts

`index_directory` with `./decisions`, then artifacts.

Decisions need their status vocabulary substituted first, in each file's own
frontmatter, because `index_file` reads `status:` off the file and refuses
anything this schema does not know. `index_directory` reports each refusal with
its filename and indexes the rest, so running it, fixing what it names, and
running it again is the expected loop; it never double-indexes what already
went in.

Artifacts split. Anything whose description you are carrying across from the v1
README's `### Artifacts` list needs `index_file` one at a time, because the
description is the only thing not read off the file and has no other home. Run
`index_directory` with `./artifacts` afterwards for whatever is left. A
subdirectory is one artifact either way.

**Shorten those descriptions to one sentence as you carry them.** A v1 README
holds them in a list nobody loads on resume; a schema 2 index line is read
every single time. One migration carried sixteen across at an average of 255
characters and they became 30% of the thread's resume. Say what the artifact
is, not what is in it.

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

**Collapse Quick Resume into Status** — a few sentences for a person, taken from
Current focus.

**Recent progress is the part that can be lost.** Next steps and Parked become
todos and Open Questions fold into them, but Recent progress is a log, and it
maps onto the sessions index only if every entry had a session behind it. Older
threads have entries that never did. Read them against the sessions you have
just indexed, and for anything with no session: put it in Status if it still
describes where things stand, and otherwise say plainly that you are dropping
it and what it said. It survives in `{name}-v1` either way, but only if someone
knows to look.

`attachments/` is copied across and left alone. It has no index, because an
attachment is a file the user dropped in and there is no moment where a
description gets authored.

**Leave the backup as a todo, not as a sentence.** A migration ends with exactly
one outstanding commitment, deciding what happens to `{name}-v1`, and saying it
in conversation loses it the moment the session ends. Write a `todos/` file for
it and put it in the window:

```
Title: Remove or archive threads/{name}-v1
Link:  ./todos/{date}-retire-the-v1-backup.md
```

A file rather than a link to the backup itself, because a link pointing outside
the thread is what `audit` reports as dangling. The todo is the user's decision
to make, not yours: never delete either directory, and never offer to.

**If the workspace is a git repository, say what a commit would include.** The
migration leaves the tree dirty: the README reads as an edit, and `{name}-v1`,
the indexes and the todos are untracked. Committing everything as-is puts a
complete duplicate of the thread into history. Say so, and leave the choice
alone — the recoverable state is the commit made before the migration started,
and that one is already safe.
