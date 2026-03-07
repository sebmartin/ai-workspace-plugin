# AI Workspace Plugin - Agent Instructions

Instructions for AI assistants working in this repository.

## Project Overview

This is a Claude Code plugin that provides thread-based workspace management for long-running AI-assisted development projects. Users install this plugin once and use it across multiple projects.

**Key capabilities:**
- Thread management - Organize work into persistent discussion threads
- Specialized agents - Architect, security-reviewer, product-strategist, etc.
- Decision tracking - Log architectural decisions with automatic context
- Snapshots - Generate shareable summaries

**User workflow:**
```bash
cd ~/my-project
claude --plugin-dir ~/ai-workspace-plugin
/ai-workspace:threads create feature-work
```

The plugin auto-creates `threads/` and `.claude/settings.json` on first use.

## Architecture

### Directory Structure

```
ai-workspace-plugin/               # Plugin repository
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── agents/                       # Specialized AI personas
│   └── devils-advocate.md
├── skills/                       # User-invocable skills
│   ├── common/
│   │   └── workspace_utils.py   # Shared utilities
│   └── threads/                 # Thread management skill
│       ├── SKILL.md             # Skill definition
│       └── scripts/
│           └── mcp_server.py    # FastMCP server with list_threads, get_thread_status
├── templates/                    # Templates for threads
│   ├── thread-template.md
│   ├── thread-session-template.md
│   ├── snapshot-template.md
│   ├── settings.json.template
│   └── ...
├── README.md                     # User documentation
├── CONTRIBUTING.md               # Developer documentation
└── AGENTS.md                     # This file
```

### Key Concepts

**Plugin vs Workspace separation:**
- Plugin: Installed once at `~/ai-workspace-plugin` (this repository)
- Workspace: User's project directory (e.g., `~/my-project`)
- The plugin creates `threads/` directory in each workspace
- Each workspace gets its own auto-generated `.claude/settings.json`

**Skills:**
- Defined in `skills/` directory
- Each skill has a `SKILL.md` file (interpretive instructions for Claude)
- Supporting scripts (Python, etc.) live in `scripts/` subdirectory
- Invoked with `/ai-workspace:skill-name` command

**Agents:**
- Specialized AI personas in `agents/` directory
- Invoked automatically by Claude's Task tool when needed
- Additional specialist agents (architect, security-reviewer, product-strategist, tech-advisor, cost-analyzer) are in the `tech-expert-agents` plugin (`/plugin install tech-expert-agents@sebmartin`)

**Templates:**
- All templates live in `templates/` directory
- Accessed via `get_template_path()` in workspace_utils.py
- Include thread structure, sessions, decisions, snapshots, settings

## Development Workflow

### Making Changes

1. **Read before modifying** - Always read files before editing them
2. **Follow existing patterns** - Match the style and structure of existing code
3. **Test changes** - Use `--plugin-dir` flag to test locally
4. **Keep it simple** - Avoid over-engineering, only change what's needed

### Making Changes

See CONTRIBUTING.md for testing procedures, common tasks, and PR guidelines.

## Key Patterns

### Auto-creation System

The plugin uses lazy initialization:
- `ensure_settings()` - Auto-creates `.claude/settings.json` from template
- SKILL.md create flow handles `threads/` directory creation via Bash(mkdir:*)
- No separate initialization step required - just start using threads

### Template Access

All templates use `get_template_path()` helper:
```python
from workspace_utils import get_template_path

template_path = get_template_path("thread-template.md")
# Returns: plugin_dir / "templates" / "thread-template.md"
```

**Never** hardcode paths to templates. Always use `get_template_path()`.

### Thread Structure

When creating a thread, the structure is:
```
threads/{thread-name}/
├── README.md           # From templates/thread-template.md
├── sessions/           # Session logs (one per conversation)
├── decisions/          # ADRs (YYYYMMDD-title.md)
├── attachments/        # Input files
└── artifacts/          # Output files (snapshots, reports)
```

### Skill Invocation

Users invoke skills with `/ai-workspace:skill-name` command. When a skill is invoked:
1. Claude loads the skill's `SKILL.md` file
2. Claude follows the interpretive instructions in SKILL.md
3. Claude may call Python scripts using the Bash tool
4. Scripts use workspace_utils.py for common operations

### MCP Tool Invocation

Skills use MCP tools instead of Python scripts. The threads MCP server is declared in `.claude-plugin/plugin.json` and exposes tools via the `threads` server name:

```
mcp__threads__list_threads(workspace_dir="/absolute/path/to/workspace")
mcp__threads__get_thread_status(workspace_dir="/absolute/path/to/workspace", thread_name="my-thread")
```

**Why this matters:**
- Plugin is at: `~/ai-workspace-plugin/` (or in Claude's plugin cache)
- User workspace is at: `~/my-project/`
- Pass the current working directory as `workspace_dir` (literal path, not `$(pwd)`)
- MCP tools have typed signatures — no shell argument quoting issues

## Verification Practices

**Before referencing project resources:**
- ✅ Call `mcp__threads__list_threads` to list threads before naming them
- ✅ Use Read/Glob to verify file existence
- ✅ Read files before describing their contents

**When working with threads (as a user would):**
- Threads are in the user's workspace, not the plugin repo
- Use `mcp__threads__list_threads(workspace_dir="/path/to/workspace")` to see available threads
- Read `threads/{name}/README.md` for thread details
- Never assume thread content - always verify

## Communication Style

When working in this repository:
- Be concise and direct
- Use technical language appropriately
- Don't use emojis unless requested
- Show file paths with line numbers: `workspace_utils.py:45`
- When making changes, explain what and why briefly
- Focus on the change, not general commentary

## Project-Specific Notes

**Plugin installation model:**
- Users install the plugin once (`git clone` to `~/ai-workspace-plugin`)
- Plugin is loaded with `--plugin-dir ~/ai-workspace-plugin` flag
- Same plugin installation used across all user projects
- No per-workspace plugin installation needed

**No workspace/ directory anymore:**
- Old architecture: plugin had `workspace/` subdirectory for user content
- New architecture: user's entire project directory IS the workspace
- Threads live in `threads/` directly in user's project
- This change happened to simplify separation of plugin vs. user content

**No init skill:**
- Previously: `/ai-workspace:init` skill created workspace structure
- Now: Structure auto-created on first thread operation
- This removed dependency on uv, pre-commit, git hooks
- Zero-setup experience - just start using threads

**Settings file:**
- Auto-generated from `templates/settings.json.template`
- Created at `.claude/settings.json` in user's workspace
- Contains permission allowlist for plugin operations
- User can customize their copy if needed
