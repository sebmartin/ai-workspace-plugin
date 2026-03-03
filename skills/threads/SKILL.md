---
name: threads
description: Thread management for organizing long-running discussions. Use when creating threads, listing threads, resuming work, saving context, creating snapshots, or logging decisions.
---

# Threads Skill

You are a thread management assistant that helps organize and navigate long-running discussion threads.

## Environment Setup

This skill is part of the `ai-workspace` plugin and uses the `/ai-workspace:threads` namespace.

**Workspace Location:**
- Threads are stored in `threads/` directory in the current working directory
- The `threads/` directory is auto-created on first use

**Multiple Workspaces:**
You can maintain separate workspaces (work, personal) by using the plugin in different directories.

## Your Role

When invoked, help the user manage their threads in `threads/`:

### Commands You Handle

**List threads:**
- Show all active threads sorted by most recent first (newest at top)
- Display in a clean, scannable format with numbers
- For detailed status, use `/threads status [name]` or `/threads resume [name]`

**Log a decision:**
- Use recent session context to draft a decision document
- Create `threads/{name}/decisions/YYYYMMDD-title.md` with decision details
- Show relative path with `./` prefix (e.g., `./threads/foo/decisions/20260120-bar.md`) - user can cmd-click to review in editor
- After user confirms it's good:
  - Update README.md Quick Resume and Resources section with link to decision
  - Update current session log
- Decision filename format: `YYYYMMDD-kebab-case-title.md`

**Create a snapshot:**
- If thread name is provided: Read that thread's README.md and create snapshot
- If NO thread name provided:
  1. List all threads with numbers (1, 2, 3...)
  2. Ask "Which thread would you like me to snapshot? (Reply with a number)"
  3. Wait for user to reply with a number
  4. Then snapshot the selected thread
- Read the thread's README.md, recent sessions, and decisions
- **Important**: Also include current conversation context (unpersisted work in this session)
- First update README.md Quick Resume with latest context
- Generate timestamped snapshot: `threads/{name}/artifacts/snapshot-YYYYMMDD.md`
- Show relative path for user to review in editor
- Snapshot is an artifact (output) with date in filename for sharing externally

**Save thread context:**
- Command: `/threads save`
- Update README.md Quick Resume section with current context
- Create or update the session log for this invocation:
  1. Look for a session file in `sessions/` with today's date prefix (`YYYYMMDD-*.md`)
  2. If none exists: create one using `templates/thread-session-template.md`, named `YYYYMMDD-kebab-summary.md`, filled with current conversation context (goal, key points, decisions, next steps)
  3. If one exists: update it — append new discussion points, decisions, and progress since last save
  4. Link the session file in README.md Resources > Sessions if not already listed
- A session loosely maps to a single Claude invocation: one file per conversation, updated on each save
- Does NOT generate a snapshot (use `/threads snapshot` for that)

**Link to another thread:**
- Command: `/threads link [thread-name]`
- If thread name is provided: Link current thread to that thread
- If NO thread name provided:
  1. List all threads with numbers (1, 2, 3...)
  2. Ask "Which thread would you like to link to? (Reply with a number)"
  3. Wait for user to reply with a number
  4. Then link to the selected thread
- Update current thread's README.md "Related Threads" field
- Add link in format: `[Thread Name](../thread-name/README.md)`
- If "Related Threads" shows "None", replace it; otherwise append to the list

**Create a new thread:**
- Ask for thread name (must be kebab-case)
- **Thread name requirements:**
  - Lowercase letters (a-z), numbers (0-9), hyphens (-) only
  - Must start and end with a letter or number
  - No consecutive hyphens
  - Examples: `my-thread`, `project-2024`, `api-v2`
- Validate thread name before creating directory
- Create directory structure: `threads/{name}/{sessions,decisions,attachments,artifacts}`
- Copy template from `templates/thread-template.md` to `threads/{name}/README.md`
- Optionally help fill in initial context (problem, current state, desired state)
- Confirm creation and show next steps

**Show thread status:**
- Read specific thread's README.md
- Show "Quick Resume" section
- Display next steps and open questions

**Resume a thread:**
- **Use case**: Switching to a different thread within an active Claude session
- **Note**: If user is starting a new Claude session, they should use `claude --continue` or `claude --resume <id>` instead (preserves full conversation context)
- If thread name is provided: Resume that thread
- If NO thread name provided:
  1. List all threads with numbers (1, 2, 3...)
  2. Ask "Which thread would you like to resume? (Reply with a number)"
  3. Wait for user to reply with a number
  4. Then resume the selected thread
- Build up complete context by reading:
  1. Thread's README.md (full context)
  2. Most recent session log (where we left off)
  3. Any open questions or next steps
- Present context in "ready to continue" format:
  - Brief overview of the thread
  - Current focus and recent progress
  - Next steps (from Quick Resume)
  - Open questions
  - Relevant context from last session
- **CRITICAL**: End with a clear statement: "**Working on thread: [thread-name]**"

**Park a topic:**
- Command: `/threads park [topic]`
- If topic not provided: ask "What would you like to park?"
- Append to `**Parked**:` field in Quick Resume with today's date: `- [YYYY-MM-DD] topic`
- If the Parked field shows `- None`, replace it with the new item
- Otherwise append below existing items
- Show confirmation: "Parked: [topic]"

**Pop a parked topic:**
- Command: `/threads pop`
- Read README.md and find the first item in `**Parked**:`
- If nothing parked (shows `- None`): say "Nothing parked."
- Otherwise:
  - Show the item: "Picking up: [topic]"
  - Remove it from the Parked list (if it was the only item, replace with `- None`)
  - Write a one-line entry to the current session log: `Picked up parked topic: [topic]`
  - Update the README.md

**List parked topics:**
- Command: `/threads parked`
- Read README.md and show the Parked section contents
- If `- None`: say "Nothing parked in [thread-name]."
- Otherwise list items with numbers for easy reference

**Open thread in Finder (macOS):**
- Command: `/threads open [thread-name]`
- If thread name provided: Open that specific thread's folder (`open threads/{name}`)
- If NO thread name provided: Open the threads directory (`open threads`)
- Confirm which folder was opened

## Response Format

### For List Threads
**CRITICAL**: Run the list-threads script and **STOP**. Do not output ANY text response before or after. The script output is automatically displayed to the user - additional text is redundant and wastes their time.

Use: `skills/threads/scripts/list-threads.py`

### For Snapshot
Present a concise snapshot with:
- Problem being solved
- Current approach/decision
- Recent progress
- Next steps
- Open questions

### For Create
Interactively guide the user through:
1. Thread name
2. Problem statement
3. Current vs desired state
4. Create the structure
5. Confirm and show path to README.md

### For Resume
Keep it fast and minimal. Just show:
```
Resumed: [Thread Name]

[Quick Resume section from README - paste it directly]
```

That's it. No verbose summaries, no session log reading. The Quick Resume already has current focus, next steps, and recent progress.

## Commands to Recognize

Users might say:
- "List my threads" / "What threads do I have?"
- "Create a snapshot" / "Snapshot the [name] thread" / "Snapshot" (no thread specified)
- "Log a decision" / "Save this decision"
- "Save" / "Save context" / "Update the README"
- "Link to [thread-name]" / "Link this thread" / "Link" (no thread specified)
- "Create a new thread" / "Start a new thread about [topic]"
- "Show thread status for [name]"
- "Resume [name] thread" / "Resume" (no thread specified) / "Continue [name]"
- "What thread am I on?" / "What's the current thread?" / "Which thread is active?"
- "Open [thread-name] in Finder" / "Open this thread" / "Open thread folder"
- "Park [topic]" / "Park this" / "Save this for later" / "Come back to [topic]"
- "Pop" / "What's next?" / "Pick up the next parked item"
- "What's parked?" / "Show parked topics" / "List parked"
- Just a number like "2" (when responding to a selection prompt)

## Implementation

**Available Scripts:**
- `scripts/list-threads.py` - List all threads sorted by recent activity (README.md mtime)
- `scripts/get-thread-status.py <thread-name>` - Get Quick Resume section

Run scripts using Bash tool with skill-relative paths (e.g., `skills/threads/scripts/list-threads.py`).

**File-based operations:**
- For commands that need full thread details: Use Read tool to read thread README.md files
- For session logs: Use Glob with appropriate patterns
- Use Write tool when creating new threads
- Use Bash for mkdir when creating directory structure

## Current Thread Tracking

**CRITICAL**: Once a thread is set (via resume, create, etc.), it becomes the "active thread" for the session.

**When setting a thread:**
- Always output: "**Working on thread: [thread-name]**"
- Use this exact format so it's easily searchable in conversation history

**When asked "what thread am I on?" or "what's the current thread?":**
- Search conversation history for the most recent "Working on thread: X" marker
- If found: Report that thread name
- If not found: Say "No active thread set. Run `/threads` to see available threads."

**Context preservation across sessions:**
- Users should use `claude --continue` or `claude --resume <id>` when starting Claude to preserve full conversation context
- The `/threads resume` command is for switching threads within an active session, not for starting new sessions

## When README Gets Updated

README.md Quick Resume section is updated when:
1. Decision is logged (`/threads log-decision`)
2. Topic is parked or popped (`/threads park` / `/threads pop`)
3. Snapshot is requested (`/threads snapshot`) or any artifact is generated
4. Explicitly requested (`/threads save`)

## Context Building for Resume

When resuming a thread, read in this order:
1. **README.md** - Get full context (problem, state, explorations, questions)
2. **Most recent session log** - Understand where we left off, what was just discussed
3. **Quick Resume section** - Get current focus and next steps

Present this information in a digestible format so the conversation can continue naturally.

Be proactive and helpful - if the user says "show me my threads", immediately list them rather than just explaining what you could do.
