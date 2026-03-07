# AI Workspace Plugin

Instructions for AI assistants working in this repository.

## Project Overview

This is a Claude Code plugin that organizes conversations with Claude into persistent threads for brainstorming, design discussions, research, and any topic you want to revisit across sessions.

**User workflow:**
```bash
cd ~/my-workspace
/ai-workspace:init
/ai-workspace:threads create feature-work
```

## Architecture

### Directory Structure

```
ai-workspace-plugin/               # Plugin repository
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── agents/                       # Specialized AI personas
│   ├── proponent.md
│   └── skeptic.md
├── skills/                       # User-invocable skills
│   ├── common/
│   │   └── workspace_utils.py   # Shared utilities
│   ├── debate/                  # Debate skill
│   │   └── SKILL.md
│   ├── init/                    # Workspace initialization skill
│   │   └── SKILL.md
│   └── threads/                 # Thread management skill
│       ├── SKILL.md
│       └── scripts/
│           └── mcp_server.py    # FastMCP server
├── templates/                    # Templates for threads
│   ├── thread-template.md
│   ├── thread-session-template.md
│   ├── snapshot-template.md
│   ├── adr-template.md
│   ├── settings.json.template
│   └── workspace-claude.md      # CLAUDE.md template for user workspaces
├── tests/
│   └── test_mcp_server.py
├── README.md
├── CONTRIBUTING.md
└── CLAUDE.md                     # This file
```

### Key Concepts

**Plugin vs Workspace:**
- Plugin: Installed once (this repository), loaded via `--plugin-dir` or marketplace
- Workspace: User's directory (e.g., `~/my-workspace`) — where threads live
- The plugin creates `threads/` in each workspace on first use
- Each workspace gets its own auto-generated `.claude/settings.json`

**Skills:**
- Defined in `skills/` directory, each with a `SKILL.md`
- Supporting scripts live in `scripts/` subdirectory
- Invoked with `/ai-workspace:skill-name` or natural language

**Agents:**
- Specialized AI personas in `agents/`
- `proponent` and `skeptic` are used together by the `/ai-workspace:debate` skill to pressure-test proposals
- Invoked automatically by Claude's Task tool when needed
- Additional specialist agents (architect, security-reviewer, etc.) are in the `tech-expert-agents` plugin (`/plugin install tech-expert-agents@sebmartin`)

**Templates:**
- All templates in `templates/`
- Accessed via `get_template_path()` in `skills/common/workspace_utils.py`

## Development Workflow

1. **Read before modifying** - Always read files before editing them
2. **Follow existing patterns** - Match the style and structure of existing code
3. **Test changes** - Load locally with `claude --plugin-dir .` and test with `/ai-workspace:init`
4. **Keep it simple** - Avoid over-engineering, only change what's needed

See CONTRIBUTING.md for testing procedures and PR guidelines.

## Key Patterns

### Template Access

```python
from workspace_utils import get_template_path

template_path = get_template_path("thread-template.md")
# Returns: plugin_dir / "templates" / "thread-template.md"
```

Never hardcode paths to templates. Always use `get_template_path()`.

### Thread Structure

```
threads/{thread-name}/
├── README.md           # From templates/thread-template.md
├── sessions/           # Session logs (one per conversation)
├── decisions/          # ADRs (YYYYMMDD-title.md)
├── attachments/        # Input files
└── artifacts/          # Output files (snapshots, reports)
```

### MCP Tool Invocation

The threads MCP server is declared in `.claude-plugin/plugin.json` and exposes tools via the `threads` server name:

```
mcp__threads__list_threads(workspace_dir="/absolute/path/to/workspace")
mcp__threads__get_thread_status(workspace_dir="/absolute/path/to/workspace", thread_name="my-thread")
```

- Plugin is at: `~/ai-workspace-plugin/` (or in Claude's plugin cache)
- User workspace is at: `~/my-workspace/`
- Pass the current working directory as `workspace_dir` (literal path, not `$(pwd)`)

## Verification Practices

**Before referencing project resources:**
- Call `mcp__threads__list_threads` to list threads before naming them
- Use Read/Glob to verify file existence
- Read files before describing their contents

**When working with threads (as a user would):**
- Threads are in the user's workspace, not the plugin repo
- Use `mcp__threads__list_threads(workspace_dir="/path/to/workspace")` to see available threads
- Read `threads/{name}/README.md` for thread details
- Never assume thread content — always verify

## Communication Style

- Be concise and direct
- Don't use emojis unless requested
- Don't use em dashes (—). Use a comma, period, or rewrite the sentence instead
- Show file paths with line numbers: `workspace_utils.py:45`

## Notes

**Init skill:**
- `/ai-workspace:init` creates `threads/`, `.claude/settings.json`, and `CLAUDE.md` in the user's workspace
- Run once per workspace after installing the plugin
- Skips files that already exist (safe to re-run)

**Settings file:**
- Auto-generated from `templates/settings.json.template`
- Created at `.claude/settings.json` in user's workspace
- Contains permission allowlist for plugin operations
