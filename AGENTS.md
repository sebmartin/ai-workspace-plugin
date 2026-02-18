# Agent Instructions

Global instructions for AI assistants working in this repository.

## Core Principles

### Never Hallucinate

**CRITICAL**: Always verify assumptions before stating them as facts.

- ✅ **Verify file existence** - Use Read, Glob, or Bash to check before claiming a file exists
- ✅ **Verify thread names** - Use list-threads.py or read workspace/threads/ before naming threads
- ✅ **Verify content** - Read actual files before describing their contents
- ✅ **Verify commands** - Check that scripts/tools exist before referencing them
- ✅ **Verify state** - Don't assume git status, process state, or system state - check it

**When you don't know something:**
- Say "Let me check..." and use tools to verify
- If a file doesn't exist, say "That file doesn't exist"
- If you're unsure, admit it - don't guess

**Never:**
- ❌ Invent file paths, thread names, or content
- ❌ Assume threads exist without checking
- ❌ Describe file contents without reading them
- ❌ Reference tools/scripts without verifying they exist
- ❌ Make up decision documents, logs, or artifacts

## Repository Context

This is an AI workspace template for organizing long-running discussions with thread management.

**Key directories:**
- `workspace/` - Private user content (gitignored, never commit)
- `.claude/skills/` - Custom AI personas and capabilities
- `templates/` - Reusable templates

**Privacy protection:**
- Git hooks prevent committing `workspace/` files (except .keep and README.md)
- Always respect workspace privacy - it contains user's private work

## Working with Threads

When asked about threads:
1. Use `.claude/skills/threads/scripts/list-threads.py` to list available threads
2. Read `workspace/threads/{name}/README.md` for thread details
3. Never assume thread content - always read the files

**Thread resuming:**
- When users launch Claude: They should use `claude --continue` or `claude --resume <id>` to preserve full conversation context
- Within a session: Use `/threads resume <name>` to switch between threads mid-conversation
- After creating/resuming a thread: Output "**Working on thread: [thread-name]**" for clarity

## Code Quality

- Follow existing patterns in the codebase
- Keep solutions simple - avoid over-engineering
- Only make changes that are directly requested
- Test changes before committing
- Use pre-commit hooks (they protect workspace privacy)

## Communication Style

- Be concise and direct
- Use technical language appropriately
- Don't use emojis unless requested
- Show file paths with line numbers: `file.py:123`
- When making changes, explain what and why briefly
