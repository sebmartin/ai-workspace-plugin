# Command: migrate a thread from schema 1 to schema 2

There is no migration tool. The shapes are close enough to read unaided, and
every write needed already exists. This is the procedure.

**Nothing is converted in place.** The original survives untouched until a
verified swap, and nothing is ever deleted.

**Everything this procedure carries across is already on the record**, so the
rule about adding to the record doesn't apply to it, nor to the backup todo in
step 7, which is part of the procedure the user asked for.

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
5. Call `audit_migration`. `clean: true` means nothing mechanical is wrong;
   anything else names what to fix. It never checks judgement, so read the
   converted README yourself as well
6. Rename `{name}-v2` to `{name}`
7. Record the backup as a todo, and tell the user `{name}-v1` is theirs to
   remove or archive when they are satisfied. Your report lists every star you
   created, with its trigger, so they can unstar any

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
say so: `{name}-v1` is the original thread, unchanged and still readable, and
`{name}-v2` is an inert directory the user can remove when they
choose. Say which is which and leave them both.

## Converting the copy

Read `{name}-v1/README.md` — the original, not the copy, which you are about to
overwrite.

### 1. Replace the README first, before any write tool

Overwrite the copy's `README.md` from `templates/v2/thread-template.md`. Not the
finished README; the skeleton. Every write tool re-renders `## Todos` into
whatever README is there, and a schema 1 README has its next steps as a bold `**Next steps**:` list inside `## Quick Resume` rather than as a heading. Writing first and replacing
after produces one document with two diverging next-step lists.

The tools refuse rather than let that happen, so this is the step that unblocks
the rest. Status can be filled any time after, by hand, and About through `set_about`.

### 2. Index the sessions

`index_directory` with `./sessions`. One call, however many there are: a thread
with sixty-six sessions is sixty-six round trips if you index them one at a
time. Nothing else, and nothing before it.

Sessions are self-dating, from a `YYYYMMDD-` prefix and a `date:` in their own
frontmatter, so they need nothing looked up. Index them first anyway: they are
where you will read the dates for everything else that has none.

### 3. Index the decisions and artifacts

`index_directory` with `./decisions`, then artifacts.

Decisions need the key renamed and its vocabulary substituted first, in each
file's own frontmatter, because `index_file` reads `state:` off the file and
refuses anything this schema does not know. A v1 file says `status:`, and some
state it only in a `> Status:` or `**Status**:` line in the body with nothing
in the frontmatter at all, so this is reading rather than a replace. `index_directory` reports each refusal with
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
is, not what is in it. Anything past 200 characters is refused, so rewrite it
and call again rather than looking for a way around the limit.

Calling `index_file` again on a file already indexed replaces its description
instead of adding a second entry, so a description you got wrong is fixable.

Everything else on the line is read off the file. The id takes a date found
anywhere in the filename, so `2026-01-20-initial-setup.md` and
`snapshot-20260303-parking-lot.md` both sort correctly without being renamed.

### 4. Date what came back undated

A file whose name states no date is indexed as `19700101`, meaning unknown, and
both indexing tools report which ones those are. Work through that list; it is
usually a handful, and on one real thread almost every artifact.

Find the date in the thread, not in the filesystem. The file's own first line
or frontmatter, the decision that established it, the session that produced it.
A directory-shaped artifact is often created by a decision and named in no
session at all, so look there before concluding nothing says. Then
`index_file` again on the same link with `date`, which re-dates the entry and
moves it to where that date puts it.

The id changes when you do this, and the reply gives you the old one as `was`.
Use the new id from then on.

Where nothing in the thread says, ask. Leave it unknown if the answer is not
available: unknown is visibly unknown and can be repaired any time, where a
plausible wrong date reads as fact and nothing will ever flag it. Never use a
filesystem timestamp, which records when bytes moved rather than when something
was written.

**Do not rename any file.** The id is derived; the file keeps its name and the
index line links to it. Renaming would break links from session logs into
decisions, from decision bodies into artifacts, from the README and from other
threads, none of which anything rewrites and none of which error when dangling.

**Rename the key and substitute its vocabulary before indexing a decision**,
in the file's own frontmatter. The key is `status:` in v1 and `state:` here.
The values: `decided`, `active`, `confirmed`, `adopted` and `Accepted` become
`locked`; `mostly-locked` becomes `partially-locked`; `open` becomes
`proposed`. `index_file` reads `state:` and refuses anything outside that
vocabulary, so a decision you have not converted will say so, with
`FILE_STATE_UNKNOWN` and an empty `detail` when the key is still the old one.

Decisions with no state in their frontmatter need reading, and so do the ones
that state it in a `> Status:` or `**Status**:` body line, where the value is
often prose rather than a word from any vocabulary. So do any whose prose describes
supersession, to tell which superseded which — the live one declares
`supersedes`.

### 5. The rest

**Extract todos** from the v1 README's **Next steps**, Parked and Open Questions. Write a file for
each one, `todos/YYYYMMDD-slug.md` from the todo template, and copy the v1 line
verbatim into **What**. That file is the record of this todo, which is what a
todo's link has to name. Do not summarise it and do not go hunting for what it
meant; that digging belongs to whoever picks the todo up. Say in the file that it
came from the v1 README on this date and that its context has not been reviewed,
so a later reader knows the one line is all anyone knows. Put the session it came
from, or an issue it names, under **## Links**, and leave that heading out when
there is nothing to put there.

A todo goes on the end of the list and the README's Todos section shows the top five, so add the
v1 Next steps items first, in the order the README listed them, and the rest after. Only carry
something over as parked if the v1 README had it parked, and retire a parked
entry that is already resolved rather than carrying it.

**Collapse Quick Resume into Status**: write Status by hand in the fixed layout
`save_session` writes, taken from Current focus and Recent progress:

```
## Status

**Recently**
- One to three items, newest first.

**Up next**
- Zero to three items, or `- None`.
```

Items are plain text. To mention a todo just added, name it in your own words,
such as "Tackle todo: <name>"; the tool resolves no ids. The next save rewrites
the section in the same layout.

**Write About through `set_about`**, from the v1 About, in 50 words or fewer. If
the v1 About holds more than a summary, carry the rest into an artifact as the
floor rule below says, rather than looking for a way past the limit. Star that artifact if it reads as
the thread's purpose rather than its history.

**A section the template does not define is the part most likely to be lost.**
Schema 1 said the README is the thread and to read it in full, so anyone could
add a heading and it would be read. Schema 2 composes from fixed slots, so a
custom section survives in the file and is never read again. `audit_migration`
lists them under `readme_sections_to_place`, and it cannot tell whether you
placed them, so that list is a checklist for you rather than a failure.

Memory is not a dumping ground. It loads on every resume, so it holds only what
you need in hand to be useful in this thread. A long section goes to an
artifact, starred if you need to know when to read it, and moving README
sections into memory wholesale only moves the bloat.

Place each by two questions. Who is it written for, and does it have to be
loaded before you can act?

| | you have to be holding it | you have to know when to read it | you only have to know it exists |
|---|---|---|---|
| **for you** | `memory.md` | a starred artifact (`star_artifact`) | a decision or an artifact: its index line loads, its body does not |
| **for the user** | Status, About and the Todos section | a starred artifact | a session log, an artifact |

The middle column is the default for a long custom section that matters but does
not need loading on every resume.

Anything still to do is a todo whichever row it came from. Where it sits in the
list decides whether the user meets it on resume, since the Todos section shows the
top five.

`memory.md` is the cell schema 1 had no file for, and that is why these sections
became custom headings in the first place. Schema 1 said the README was the
thread and to read it whole, so a heading was enough to guarantee it got read.
What passes SKILL.md's definition of memory goes there: what a session needs in
hand before it starts, such as house rules, who is who, or what a term means
here. Anything tied to one past task belongs in an artifact or a session log
instead. Carry
what goes into memory across verbatim, keep the attribution if the original had
one, and add one if you know it.

A choice that was made is a decision even where the prose is still arguing it,
which is a decision with `proposed` status. Its `summary:` loads on every
resume, so it needs no memory entry.

You star on your own judgement, without asking. A schema 1 README was loaded
whole on every resume, like `memory.md`, so migration runs the same path as
trimming memory: what still needs to be in hand stays in memory, what is too big
for that becomes a starred artifact, and what needs no trigger becomes a plain
artifact.

An artifact is the floor. Anything that fits no cell goes there verbatim, under
its own heading, indexed with a description saying what it was, because losing
it is the only outcome worse than filing it imprecisely. What must not happen is
a section that exists only in `{name}-v1/README.md` once the swap is done.

**Ask when the cell is genuinely unclear.** Guessing lazy is the expensive
mistake: the user carries on expecting you to be holding something, you are not,
and nothing announces the gap.

**Recent progress is the part that can be lost.** The v1 Next steps and Parked become
todos and Open Questions fold into them, but Recent progress is a log, and it
maps onto the sessions index only if every entry had a session behind it. Older
threads have entries that never did. Read them against the sessions you have
just indexed, and for anything with no session: put it in Status's Recently list if it still
describes where things stand, and otherwise say plainly that you are dropping
it and what it said. It survives in `{name}-v1` either way, but only if someone
knows to look.

`attachments/` is copied across and left alone. It has no index, because an
attachment is a file the user dropped in and there is no moment where a
description gets authored.

**Leave the backup as a todo, not as a sentence.** A migration ends with exactly
one outstanding commitment, deciding what happens to `{name}-v1`, and saying it
in conversation loses it the moment the session ends. Write a `todos/` file for it and
order it where it belongs:

```
Title: Remove or archive threads/{name}-v1
Link:  ./todos/{date}-retire-the-v1-backup.md
```

A file rather than a link to the backup itself, because a link pointing outside
the thread is what `audit` reports as dangling. The todo is the user's decision
to make, not yours: never delete either directory, and never offer to.
