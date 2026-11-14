---
name: threads
description: Thread management for organizing long-running discussions. Use when creating threads, listing threads, resuming work, saving context, or logging decisions.
---

# Threads Skill

Threads organize long-running discussions so they can be picked up across sessions.

**Don't bring up the workspace's git state.** Uncommitted thread files and a workspace with no repository are both normal. Don't point them out or suggest committing or initialising anything for them. Answer if the user asks, and relay the migration safety check when migrating.

**Thread privacy is this plugin's invariant.** Where protecting it costs capability, brevity, elegance or the ability to show your work, privacy wins. Two things are private, and protecting one is not protecting the other:

- **The thread itself**: that it exists, its name, and the id or title of anything in it. `kitchen-reno`, `20260412-call-the-plumber`.
- **What it holds**: decision text, session logs, Status and About, `memory.md`, artifact contents, attachment filenames, the people named in it.

Neither reaches anyone who cannot open the workspace, which includes a doc, a code comment, a commit message, a pull request, an issue, an email, a chat message, a published artifact, a prompt you hand a subagent, and text you draft for the user to paste.

Citing as evidence is still citing. In anything written for someone who cannot open the workspace, say what you verified and what it showed, never where you got it: "a real index carrying a four-id block came out in that order", not which thread. When a reference carries an argument, such as why an approach was dropped, restate the argument. In doubt, leave it out.


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

**A path saved in the workspace is relative to the file that holds it, never absolute.** The same workspace is one string under one client and another under the next, so an absolute path is dead as soon as anything but this session opens the thread. A path printed in a reply is the opposite: resolve it so the user can open it, against the directory of the file it came out of, which for an index entry is the thread directory in the `Thread:` header. That is the form a client opens, where a relative one has no agreed base unless the session root happens to be the workspace.

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
| what a session needs in hand before it starts | `memory.md` |
| a choice that was made | a decision |
| something still to do | a todo |
| something established, produced, or worth keeping | an artifact |
| what happened this session | the session log |
| where things stand, and what the thread is for | Status and About |

When something fits none of these, say so and ask. Filing it where nothing reads it is the
failure this table exists to prevent.

**Check the thread before the web.** Its sessions, artifacts and decisions are the
record of what was already worked out here, and they answer a question about this
thread better than a search does.

### Shape

```
threads/{name}/
├── schema-version           "2"
├── README.md                for the human
├── memory.md                for you (optional; absent until there is something in it)
├── sessions/     + sessions-index.md
├── decisions/    + decisions-index.md, decisions-retired.md
├── artifacts/    + artifacts-index.md, artifacts-retired.md, artifacts-starred.md
├── attachments/  (no index; scan the directory when you need to know)
└── todos/        + todos-index.md, todos-retired.md
```

An artifact carries a one-line description on its index line. Nothing else does: a decision and a session keep their `summary:` in their own frontmatter.

These directories are the whole of a thread's layout. **Never add a top-level folder
inside a thread.** Anything you produce, an analysis, a spec, a model, a collection of
methods, is derived work and belongs in `artifacts/`, as `artifacts/<name>/` when it
needs a folder of its own. This constrains you rather than the plugin: folders the
plugin introduces or retires are its call.

### Reading another thread

Read its files directly, whenever another thread holds something you need. Do not resume it: resuming makes it your active thread, and you do not need a composed payload to answer one question about someone else's work.

| To learn | Open |
|---|---|
| where it stands, and what it is for | `README.md`, which is short |
| what it settled | `decisions-index.md` for ids and titles, then the decision file for its `summary:` and argument |
| what happened, and when | `sessions-index.md` |
| what it produced | `artifacts-index.md`, which carries a description per line |

A schema 1 thread keeps all of that inline in its README, so one read covers it.

**Write to another thread through the `ai-workspace:thread-writer` agent, never by resuming it.** A resume would leave that thread's status, decisions and sessions in this conversation, and a write made without them would not fit the thread. Start the agent with the workspace path, the thread's name, the user's request in their own words, and anything from this thread the write needs. It resumes the thread in its own context, makes the write, and reports only what it wrote or what stopped it. Pass that on and nothing more. Where you cannot start a subagent, ask the user to switch threads. A procedure that names the other thread as its target, such as linking two threads or migrating one, writes to it directly as that procedure says.

### What resume returns

`resume_thread` returns the whole thread in one call; its docstring lists what.

**Print About, Status and Todos**, in that order, with the counts from the Todos heading. Everything else is context you hold, not output. A list of thirty-five decisions is for you, not for the screen. Counts are not stored anywhere, so say them from what you read.

**Print each todo as a markdown link on its title**, so the user can open what it points at rather than asking you for it. An external URL goes as it is. Drop the id, which is for your calls rather than the screen, and name a state only when it is not `active`.

The payload carries the full text of the newest sessions, then summaries of the few before them, and the heading says how many it is not holding. Before answering a question about earlier work from memory, search `sessions/`, whose files carry `summary:` and `keywords:` frontmatter.

**Decision bodies are never opened on resume.** Open one when a constraint is challenged, or when you are about to extend or reverse it.

### Writing

**Adding to the record is the user's call.** Every index entry (a todo, a decision, an artifact, a star) and every `memory.md` entry is read on every resume from then on, so add one only when the user asked for it. The ask can be implicit: "write up your research" means write an artifact and index it, without checking first. When nobody asked and you think something belongs on the record, suggest it in your reply and add it once the user agrees.

**Declaring something settled is the user's call.** Don't call a draft, a decision or a section locked, final or done, and don't ask whether to lock it. Present the work and the reasoning, then wait. A tentative "maybe X" is not a decision.

**Say "saved", not "archived", when you have written a file.** Archiving is a different operation in this plugin: it retires a whole thread from the active list. Calling a save an archive tells the user their work was put away.

Never hand-edit an index, `artifacts-starred.md` or the README's Todos section; both are rendered from what the tools write, and a hand edit will be overwritten. Status is written only by `save_session`, on every save; never edit it by hand, since the next save overwrites it, except when migrating a thread as `migrate-from-v1.md` describes. About is written by `set_about`, never by hand. The header fields and `memory.md` have no tool; edit them directly.

A render replaces `## Todos` down to the next `##`, so never leave it as the last section of a README. Anything below it is swallowed without a word.

**Writing an artifact.** Put it in `artifacts/`, named `YYYYMMDD-kind-slug.md`: the
date it was written, a kind such as `spec`, `notes`, `report` or `bug`, and a short
slug. Write the file, then call `index_file` with a one-sentence description. The
id's date comes from the filename, so a name without one is indexed as undated
unless you pass `date`.

**Starring an artifact.** A star marks an artifact you need to know when to read.
Its line and trigger load on every resume, and its body only on demand. Star an
artifact that matters too much to be one line among many but is too long to hold
in memory. Star with `star_artifact`. Every star carries a trigger, one sentence on when
to read it, because a star without one tells you nothing. Propose stars and unstars, typically when
trimming memory or at save, and the user decides; the exception is a schema 1
migration, which follows its own guide. Unstar with `unstar_artifact` when the
artifact matters less. Retiring an artifact drops its star.

**A todo's link names the record of this todo.** When the work is tracked in
GitHub Issues or JIRA, link that item, because the item is the todo. Otherwise
write a file under `todos/` and link the file.

Never link something the todo merely relates to, such as a PR it mentions or the
session it came out of. Whoever follows that link lands on separate work, often
already finished, and still can't tell what this todo is asking for. Those
belong inside the todo file under `## Links`.

Name the file `todos/YYYYMMDD-slug.md` and start it from
`get_skill_file("templates/v2/todo-template.md")`. Write it before calling
`add_todo`, which refuses a thread path with no file behind it.

**Linking two threads has no tool.** The three link fields in the header are
hand-edited, and the work is judgement rather than mechanism: you have to look
at the thread on the other end, read what it already says, and decide whether it
can be written to at all. Fetch
`skills/threads/v2/link-thread.md` when the user asks for a link.

**A decision is a choice that was made.** Its summary loads on every resume, so do not even propose one whose rejected alternative you cannot name, or that dies with this task; that is a session log entry.

**The README's Todos section is the top of the todo list, bounded to five.** Parking takes a todo off the list, so it is the top five of what is active. The rest of the list is in `todos-index.md`, and resume counts it for you. Nothing promotes anything: retire the first todo and the sixth becomes fifth by itself.

**The order is the user's.** Propose one and apply it once they agree, and say where you put a new todo so they can move it.

**Starting on a todo marks it started, and nothing more.** Any request to start or resume a todo, in whatever words, first sets it to `started` with `set_todo_state`, and you tell the user you did. Then give a short summary of where it stands, propose a first or next step if one is clear, and stop until they say which step to take. Picking one from a list, naming it, and handing it to another skill to design or build all count as starting; the hand-off is the step they asked for.

### Memory

`memory.md` is prose. It holds context a session in this thread needs before it starts and that has no other slot: how the user wants this thread run, what a term means here, who is who. `resume_thread` loads all of it at the top of every resume, so it holds only what you need in hand to be useful in this thread: what you would otherwise get wrong, reason badly about, or have to ask the user again. It replaces the harness's project memory for anything about the thread, so it follows the thread to whichever machine resumes it. Don't write thread context to the harness's memory.

Knowledge itself goes in an artifact. When an entry runs past a few lines, move it to an artifact, and star the artifact if you need to know when to read it. Memory does not hold links to artifacts; that is what a star is for.

An entry belongs in `memory.md` only if it is both:

- **Durable**: still true in six months, and useful again whenever the same situation comes up in this thread, beyond the task at hand.
- **About this thread**: its subject, the people in it, what a term means here, or how the user wants this thread run.

Anything tied to the current session or task, such as a particular PR, stays out of `memory.md`. Keep it in mind while you work; if it is part of what happened, the session log records it. Guidance about how you should behave in general, which would apply in any thread, belongs in the user's own instructions, such as their `CLAUDE.md`; suggest it to them and leave that file to them. A choice that was made is a decision.

When you learn something of this kind, propose an entry. The user approves every one, so add or change an entry only when they ask you to remember something or agree to one you proposed. There is no tool; edit the file directly. Date and attribute each entry with the user's name, `[Name, 2026-08-13]`. When something new contradicts or narrows an entry, edit that entry instead of appending below it.

### Saving

A save writes the session log and the Status section, because todos, decisions and artifacts were written when they happened.

- At each save, look at the Recently and Up next you were shown on resume and pass what is now true as `recently` and `up_next`. Both are passed every time; passing the same items is a valid answer. Recently is the thread's recent work, newest first, not only this session: keep an earlier item that is still live. Items are plain text and nothing is looked up: to mention a todo, write it in your own words, such as "Tackle todo: <name>".
- On the first save of a thread whose Status is still a paragraph from before, there are no lists to carry forward: turn what is still true in the paragraph into Recently and Up next.
- When an Up next sentence was already there when you resumed and is still not done, suggest making it a todo, and add one only if the user agrees. Nothing stores past lists; what you saw on resume is the only history.
- Look at About too, and call `set_about` if it no longer fits the thread, is still the template's placeholder, or runs past 50 words.

It is also the moment to read `memory.md` through, if the thread has one, and propose dropping entries that are no longer true, entries now covered by a decision or an artifact, and entries that have grown into something better kept as an artifact, starred or not. A session that ends without a save leaves no log, and what it produced is still in the indexes.

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
