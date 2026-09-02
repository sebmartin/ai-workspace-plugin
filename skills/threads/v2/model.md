# Schema 2 threads

The README is what a person reads. The indexes are the record, and they are what you read.

Applies to any thread whose directory has a `schema-version` file saying `2`. `resume_thread` and `create_thread` report it in their focus headers.

## Shape

```
threads/{name}/
├── schema-version           "2"
├── README.md                for the human
├── sessions/     + sessions-index.md
├── decisions/    + decisions-index.md, decisions-retired.md
├── artifacts/    + artifacts-index.md, artifacts-retired.md
├── attachments/  (no index — scan the directory when you need to know)
└── todos/        + todos-index.md, todos-retired.md
```

An index line is `- <id>:<state> [Title](./dir/file.md)`. Sessions have no state. There is no description: the index says what exists and what state it is in, the file says what it means.

A missing index is an empty index. Nothing pre-creates them.

## Resume

`resume_thread` returns everything in one call: Status, About, the header, the Next steps window, the todo backlog, every in-force decision with the `summary:` read from its file, the artifacts index, and the last ten sessions.

**Print only Status and Next steps.** Everything else is context you hold, not output. A list of thirty-five decisions is for you, not for the screen. Counts are not stored anywhere, so say them from what you read.

**Decision bodies are never opened on resume.** Open one when a constraint is challenged, or when you are about to extend or reverse it.

## Writing

Never hand-edit an index or the README's Next steps section; both are rendered from what the tools write, and a hand edit will be overwritten. Status, About and the header fields are yours to edit.

| To | Use |
|---|---|
| Add a backlog item | `add_todo` — always with a link |
| Finish or abandon one | `retire_todo` (`done` / `dropped`) |
| Park or unpark | `set_todo_state` (`parked` / `active`) |
| Choose what the README shows | `set_window` — about five, in priority order |
| Record a decision | `log_decision` |
| Retire one | `retire_decision` (`superseded` / `withdrawn`) |
| Index an artifact | `add_artifact` |
| Retire one | `retire_artifact` (`superseded` / `stale`) |
| Save | `save_session` |

**Every todo carries a link.** A file under `todos/` when it has state of its own, an external URL when there is an issue, otherwise the session it came out of. Never a bare line: the point is that you can expand it later.

**Next steps is the user's commitments, not your suggestions.** An idea you had belongs in the session log. The backlog is allowed to be long; the window is what is scarce.

**Propose, do not reorder on your own.** Change the window when the user says what is next, or when something completes and leaves a hole. Read the whole backlog when you do — the item that most needs promoting is usually the stale one, which recency hides.

## Decisions

`summary:` is read on every resume, so it costs something permanently. One sentence, one subject, WHAT was decided and not why. If it needs "and" twice, log several decisions.

Claim first in the body, argument after, so a reader who only needs the rule can stop.

`supersedes` on the new decision retires the ones it names. Never point from a retired decision to its replacement: traversal starts from what is in force.

## Saving

A save is only the session log and the Status paragraph, because todos, decisions and artifacts were written when they happened. A session that ends without a save still leaves its stub and a record of what it touched.

Pass `body` for an ordinary session log. For a long one, write the session file directly and call `save_session` without a body — a whole log in one tool call has to fit a single response.
