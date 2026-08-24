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
- Show Quick Resume and Locked Decisions. Nothing else.

```
Resumed: [Thread Name]

[Quick Resume section, verbatim]

## Locked Decisions
[One line per decision: "**[title]** ([status]): [summary]"]
```

## Migration

A schema 1 thread cannot be saved with the current tools; every schema 2 write tool returns `Status: NEEDS_MIGRATION`. Say so when the thread is resumed rather than when a save is attempted, so a long session does not end in a surprise.

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
