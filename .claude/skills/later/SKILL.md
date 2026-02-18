---
name: later
description: Persistent TODO list management for discussion threads. Use when creating task lists, adding tasks, completing items, or tracking work across sessions.
---

# Later Skill for managing TODO lists in Threads

You are a persistent task list manager for long-running discussion threads. This manages markdown-based TODO lists saved in `workspace/threads/{thread}/todos/` directories - distinct from Claude's ephemeral session todos.

## Your Role

When invoked, help the user manage persistent TODO lists stored in the current thread's `todos/` directory. These are saved as markdown files and persist across sessions.

### Commands You Handle

**List active TODOs:**
- Command: `/later list`
- Run `scripts/list-active-todos.py <thread-name>` via Bash tool
- The script returns formatted output with completion counts and checkmarks
- Let the output display automatically - **do not output any text response** (the output is already shown to the user)

**Create a new TODO list:**
- Command: `/later create [name]`
- If name provided: create `workspace/threads/{current-thread}/todos/{name}.md`
- If NO name provided: ask "What should we call this TODO list?"
- **TODO list name requirements:**
  - Lowercase letters (a-z), numbers (0-9), hyphens (-) only
  - Must start and end with a letter or number
  - No consecutive hyphens
  - Examples: `feature-work`, `bugs-2024`, `api-tasks`
- Validate list name before creating file
- After creating the file, ALWAYS prompt: "What items should I add to this TODO list? (You can provide multiple items, one per line or comma-separated)"
- Wait for user response, then populate the list with their items
- Use simple markdown checklist format:
  ```markdown
  # TODO: [List Name]

  - [ ] Item 1
  - [ ] Item 2
  ```
- Show relative path for user to review in editor
- Update README.md Quick Resume with latest context

**Add item to a TODO list:**
- Command: `/later add [list-name] [item]`
- If list-name provided: add item to that list
- If NO list-name provided: show numbered list of active TODO lists for selection
- Append new unchecked item: `- [ ] [item]`
- Show confirmation with relative path
- Update README.md Quick Resume

**Complete a TODO item:**
- Command: `/later complete [item-description]`
- Search across all active TODO lists for matching item
- If multiple matches: show numbered list for selection
- Mark as checked: `- [x] [item]`
- Check if ALL items in the list are now complete
- If all complete: automatically move list to `todos/complete/` (create directory if needed)
- Prompt: "Update README and session log with this progress?"
- If yes: update README.md Quick Resume and current session log
- Show confirmation with archive status if applicable

## Response Format

### For List
Run the list-active-todos script and let the output display automatically. **Do not output any text response** - the script output is already shown to the user.

Use: `.claude/skills/later/scripts/list-active-todos.py <thread-name>`

### For Create/Add
Show relative path with `./` prefix and confirmation:
```
Created: ./workspace/threads/my-thread/todos/new-feature.md
```

### For Complete
```
Marked complete: "Implement authentication" in feature-implementation.md

All items complete! Archived feature-implementation.md to todos/complete/

Update README and session log with this progress? (y/n)
```

Or if not all complete:
```
Marked complete: "Implement authentication" in feature-implementation.md (4 of 5 complete)

Update README and session log with this progress? (y/n)
```

## Commands to Recognize

Users might say:
- "List TODOs" / "What's on my TODO list?" / "Show tasks"
- "Create a TODO list" / "New TODO list for [name]"
- "Add [item] to TODOs" / "Add task: [item]"
- "Complete [item]" / "Mark [item] as done" / "Done with [item]"
- Just a number like "2" (when responding to a selection prompt)

## Implementation

**Available Scripts:**
- `scripts/list-active-todos.py <thread-name>` - List all active TODO lists with completion counts
- `scripts/get-todo-list.py <thread-name> <list-name>` - Get specific TODO list contents

Run scripts using Bash tool with skill-relative paths (e.g., `.claude/skills/later/scripts/list-active-todos.py`).

**File operations:**
- Use Read tool to read TODO list contents for editing
- Use Edit tool to update TODO lists (mark items complete)
- Use Bash to move files when archiving to `todos/complete/`
- Use Write tool when creating new TODO lists

## When README Gets Updated

README.md Quick Resume is updated when:
1. TODO list is created
2. Item is added to a list
3. Item is marked complete (with user confirmation)
4. TODO list is auto-archived (when last item completed)

This keeps the README current and provides natural checkpoints for persisting progress.

## Current Thread Detection

To determine which thread we're working in:
- Check conversation context for thread name
- If unclear, list available threads for user to select
- Once determined, work within that thread's `todos/` directory

## Notes

- TODO lists are markdown files with simple checklists
- Keep TODO lists focused and actionable
- Lists are automatically archived to `complete/` when all items are checked off
- Completing a TODO is a natural moment to update README and session log
- Auto-archiving keeps the active TODO view clean and focused
