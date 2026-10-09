---
name: threads
description: Thread management for organizing long-running discussions. Use when creating threads, listing threads, resuming work, saving context, or logging decisions.
---

# Threads Skill

Threads organize long-running discussions so they can be picked up across sessions.

**Don't bring up the workspace's git state.** Uncommitted thread files and a workspace with no repository are both normal. Don't point them out or suggest committing or initialising anything for them. Answer if the user asks, and relay the migration safety check when migrating.

**Anything that leaves the workspace must stand alone.** Text written for someone else, such as docs, code comments, commit messages, pull requests, issues, emails and chat messages, is read by a person who cannot open the workspace. That includes text you draft in the conversation for the user to paste. Never cite a thread, decision, session or artifact in it, by path, id or name. When a reference carries an argument, such as why an approach was dropped, restate the argument. Threads also hold candid and private material, so ask before carrying across anything that looks private.

## Workspace Resolution

Operating tools take a `workspace_dir` argument, a directory hint. The server probes that path for `threads/`, falls back to a persisted default, and either uses it or returns an error. You are responsible for remembering the resolved path across tool calls.

- **First call in a session**: pass the current working directory. The tool returns the resolved workspace in a `Workspace:` header.
- **Subsequent calls**: pass that resolved path, which skips the probe.

`create_thread` and `resume_thread` return these headers on success. Treat them as your tracked workspace and active thread:

```
Workspace: /path/to/workspace
Thread: /path/to/workspace/threads/<thread-name>
Schema: 2
```

**A path saved in the workspace is relative to the file that holds it, never absolute.** It will be read on another machine where `workspace_dir` is a different string, and an absolute one is dead there. A path printed in a reply is the opposite: resolve it against `workspace_dir` so the user can open it, which is safe because the reply is stored with a session whose `workspace_dir` does not change.

**Put a workspace error to the user and wait.** Each one names the choice in its reply. Don't guess a path.

## Thread schemas

Threads come in more than one on-disk schema. **Schema 2 is what this plugin creates, and the rest of this file assumes it.** The `Schema:` header says which one a thread uses.

| Schema | Read | Then load |
|---|---|---|
| 1 | the README is the whole thread | `skills/threads/v1/model.md` |

A `Schema: 2` header needs nothing loaded. Any other value, load that row's file and follow it wherever it contradicts what is here; it says at the top which sections it replaces.

**The schema belongs to the thread.** Check the `Schema:` header again every time you switch threads.

## Working with a schema 2 thread

The README is what a person reads. The indexes are the record, and they are what you read.

**Thread context belongs in the thread.** Not in `CLAUDE.md`, `AGENTS.md`, or your
harness's own project memory, such as Claude Code's auto memory under
`~/.claude/projects/<project>/memory/`. That memory stays on one machine and loads in every
session in the directory, including sessions on other threads, while a thread is resumed
from different machines and hosts and its files go with it. Every kind of context has a
slot here:

| what it is | where it goes |
|---|---|
| a standing instruction for this thread | `memory.md` |
| a choice that was made | a decision |
| something still to do | a todo |
| something established, produced, or worth keeping | an artifact |
| what happened this session | the session log |
| where things stand, and what the thread is for | Status and About |

When something fits none of these, say so and ask. Filing it where nothing reads it is the
failure this table exists to prevent.

### Shape

```
threads/{name}/
├── schema-version           "2"
├── README.md                for the human
├── memory.md                for you (optional; absent until there is something in it)
├── sessions/     + sessions-index.md
├── decisions/    + decisions-index.md, decisions-retired.md
├── artifacts/    + artifacts-index.md, artifacts-retired.md
├── attachments/  (no index; scan the directory when you need to know)
└── todos/        + todos-index.md, todos-retired.md
```

An artifact carries a one-line description on its index line. Nothing else does: a decision and a session keep their `summary:` in their own frontmatter.

### Reading another thread

Read its files directly, whenever another thread holds something you need. Do not resume it: resuming makes it your active thread, and you do not need a composed payload to answer one question about someone else's work.

| To learn | Open |
|---|---|
| where it stands, and what it is for | `README.md`, which is short |
| what it settled | `decisions-index.md` for ids and titles, then the decision file for its `summary:` and argument |
| what happened, and when | `sessions-index.md` |
| what it produced | `artifacts-index.md`, which carries a description per line |

A schema 1 thread keeps all of that inline in its README, so one read covers it.

**Never write to a thread you have not resumed.** The write tools take a thread name and will do it, so nothing stops you but this.

### What resume returns

`resume_thread` returns the whole thread in one call; its docstring lists what.

**Print only Status and Next steps**, with the counts from its heading. Everything else is context you hold, not output. A list of thirty-five decisions is for you, not for the screen. Counts are not stored anywhere, so say them from what you read.

**Print each todo as a markdown link on its title**, so the user can open what it points at rather than asking you for it. An external URL goes as it is. Drop the id, which is for your calls rather than the screen, and name a state only when it is not `active`.

**Decision bodies are never opened on resume.** Open one when a constraint is challenged, or when you are about to extend or reverse it.

### Writing

**Adding to the record is the user's call.** Every index entry (a todo, a decision, an artifact) and every `memory.md` entry is read on every resume from then on, so add one only when the user asked for it. The ask can be implicit: "write up your research" means write an artifact and index it, without checking first. When nobody asked and you think something belongs on the record, suggest it in your reply and add it once the user agrees.

Never hand-edit an index or the README's Next steps section; both are rendered from what the tools write, and a hand edit will be overwritten. Status is written by `save_session`'s `status` argument, or edited directly between saves. About, the header fields and `memory.md` have no tool; edit them directly.

A render replaces `## Next steps` down to the next `##`, so never leave it as the last section of a README. Anything below it is swallowed without a word.

**Writing an artifact.** Put it in `artifacts/`, named `YYYYMMDD-kind-slug.md`: the
date it was written, a kind such as `spec`, `notes`, `report` or `bug`, and a short
slug. Write the file, then call `index_file` with a one-sentence description. The
id's date comes from the filename, so a name without one is indexed as undated
unless you pass `date`.

**A todo with state of its own gets a file.** Name it `todos/YYYYMMDD-slug.md`,
start it from `get_skill_file("templates/v2/todo-template.md")`, and pass its path
as `add_todo`'s link.

**Linking two threads has no tool.** The three link fields in the header are
hand-edited, and the work is judgement rather than mechanism: you have to look
at the thread on the other end, read what it already says, and decide whether it
can be written to at all. Fetch
`skills/threads/v2/link-thread.md` when the user asks for a link.

**A decision is a choice that was made.** Logging one is the user's call, like any index entry. Do not even propose one whose rejected alternative you cannot name, or that dies with this task; that is a session log entry.

**Next steps is the top of the todo list, bounded to five.** The rest of the list is in `todos-index.md`, and resume counts it for you. Nothing promotes anything: retire the first todo and the sixth becomes fifth by itself.

**The order is the user's.** Propose one and apply it once they agree, and say where you put a new todo so they can move it. When the user says to work on something, set its state to `started`.

### Memory

`memory.md` holds standing instructions for this thread, and `resume_thread` loads all of it at the top of every resume. It replaces the harness's project memory for anything about the thread, so it follows the thread to whichever machine resumes it. Don't write thread context to the harness's memory. An entry belongs in `memory.md` only if it is both:

- **Durable**: still true in six months, and useful again whenever the same situation comes up in this thread, beyond the task at hand.
- **About this thread**: its subject, the people in it, what a term means here, or how the user wants this thread run.

Anything tied to the current session or task, such as a particular PR, stays out of `memory.md`. Keep it in mind while you work; if it is part of what happened, the session log records it. Guidance about how you should behave in general, which would apply in any thread, belongs in the user's own instructions, such as their `CLAUDE.md`; suggest it to them and leave that file to them. A choice that was made is a decision.

Add or change an entry only when the user asks you to remember something or agrees to an entry you proposed. There is no tool; edit the file directly. Date and attribute each entry with the user's name, `[Name, 2026-08-13]`. When something new contradicts or narrows an entry, edit that entry instead of appending below it.

### Saving

A save writes the session log and the Status paragraph, because todos, decisions and artifacts were written when they happened. It is also the moment to read `memory.md` through, if the thread has one, and propose dropping anything that no longer applies. A session that ends without a save leaves no log, and what it produced is still in the indexes.

Everything from here on applies whatever the schema, except where a schema's own file says otherwise.

## Resume a Thread

- If a thread name was given, resume it. If not, call `list_threads`, show them numbered, ask which, and wait.
- **Archive fallback**: if the name is not among active threads, call `list_archived_threads`. If it is there, say it is archived and offer to restore it. An archived thread is read-only until it is restored.
- Call `resume_thread` and read the `Schema:` header. Schema 2 is described above; anything older, load its file first.
- End that reply with "**Working on thread: [thread-name]**", adding "(schema N)" only when the thread is not on the current schema. Only in that reply.

## Commands

| Command | Description | Reference |
|---|---|---|
| `list` | Call `list_threads`, output directly, no commentary | inline |
| `resume` | See Resume a Thread | inline |
| `set-workspace` | Call `set_default_workspace` with the provided path, then make the permissions offer below | inline |
| `archive-thread` | Archive, restore, and list archived threads | `skills/threads/archive-thread.md` |
| `unpack-legacy-archive` | Restore a `.tar.gz` archive from before 3.0 | `skills/threads/unpack-legacy-archive.md` |

Saving, decisions, artifacts, todos and linking differ by schema. Schema 2's are under Working with a schema 2 thread; an older schema lists its own.

**The permissions offer.** After any call to `set_default_workspace`, including one that resolves a `NO_WORKSPACE` error, offer to add the threads tools to the user's global CLI settings so they are not prompted again from any directory. Allow all `mcp__plugin_ai-workspace_threads__*` tools and Read/Edit/Write on `{workspace}/**` in the global configuration file. Tell the user what was written and that a restart may be needed.

Reference files are loaded via `mcp__plugin_ai-workspace_threads__get_skill_file(relative_path)`. Pass the path relative to the plugin root. Example: `get_skill_file("skills/threads/v1/model.md")`.

## If the MCP tools are unavailable

Every tool is named `mcp__plugin_ai-workspace_threads__<name>`, and its arguments
and reply codes are in its own docstring. Nothing about calling one is repeated here.

**When none of them can be called at all:** The threads MCP server failed to start. Two likely causes:

1. **`uv` not installed**: direct the user to https://docs.astral.sh/uv/getting-started/installation/
2. **Dependency or version mismatch**: the server declares what it needs in a `# /// script` block at the top of `skills/threads/scripts/mcp_server.py`. Have the user run the launch command by hand to see the real error:
   ```
   uv run --script <plugin-root>/skills/threads/scripts/mcp_server.py
   ```
   An `ImportError`/`ModuleNotFoundError` on `mcp.server.*` means the resolved `mcp` version doesn't match what the server imports.
