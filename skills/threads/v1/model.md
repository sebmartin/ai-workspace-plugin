# Schema 1 threads

The README is the thread. Everything lives in it, and the linked files hold the detail.

Applies to any thread whose directory has no `schema-version` file. `resume_thread` reports the schema in its focus headers.

## The README model

The README is a lean index — the complete map of a thread. It must be short enough to read in full and retain entirely.

**Read in full on resume.** Every section. Quick Resume gives current state, Decisions tell you what constraints exist, Resources tell you what is available.

**Pull linked files on demand.** Do not read them eagerly.

**Write discipline.** Fixed sections only. If content does not fit, create a linked artifact or decision. The README holds the link and a one-line description; the file holds the content.

**Quick Resume decay.** Keep "Recent progress" to the last 3–5 entries. If "Next steps" exceeds 10 items, ask whether any should be removed or parked.

## Resume

- Read the README in full — every section.
- Load session context using a recency gradient, without surfacing it: most recent session's `summary`/`keywords`/`next_context`, then `summary`/`date` for the next 2–4, then nothing. Skip sessions without frontmatter silently.
- Read the frontmatter of every file in `decisions/`. If one is missing `summary:`, read it, infer a one-sentence summary of WHAT was decided, and add it silently.
- Show the migration banner, Quick Resume and Locked Decisions. Nothing else.
- Close with the migration question, just above the **Working on thread** marker, and wait for an answer.

```
Resumed: [Thread Name]

> ⚠️ **This thread is schema 1 and cannot be saved.**
> Every save, decision, artifact and todo tool refuses it with
> `NEEDS_MIGRATION`. Migrating converts it to schema 2 and deletes nothing.

[Quick Resume section, verbatim]

## Locked Decisions
[One line per decision: "**[title]** ([status]): [summary]"]

**Migrate this thread to schema 2 now?** It takes a few minutes and leaves the
original in place. Saying no is fine; this session just cannot be saved.
```

The banner goes above Quick Resume, not below the decisions. Below, it reads
as a footnote to a wall of thread content and gets skipped, which is the whole
failure it exists to prevent.

## Migration

A schema 1 thread cannot be saved with the current tools; every schema 2 write tool returns `Status: NEEDS_MIGRATION`.

**Raise it on resume, as a question, not at save time.** The resume format
above carries both the banner and the ask. A session that discovers this at
save time has already done the work it cannot keep.

If the user declines, do not ask again unprompted, and do not migrate anything
on your own initiative. Raise it once more if they later try to save, since
that is the moment the refusal becomes concrete.

See `skills/threads/v2/commands/migrate-from-v1.md` when the user agrees to convert.

## Commands

| Command | Reference |
|---|---|
| `save-thread` | `skills/threads/v1/commands/save-thread.md` |
| `save-artifact` | `skills/threads/v1/commands/save-artifact.md` |
| `log-decision` | `skills/threads/v1/commands/log-decision.md` |
| `create-thread` | `skills/threads/v1/commands/create-thread.md` |
| `park-topic` | `skills/threads/v1/commands/park-topic.md` |
| `link-thread` | `skills/threads/v1/commands/link-thread.md` |
| `archive-thread` | `skills/threads/v1/commands/archive-thread.md` |
