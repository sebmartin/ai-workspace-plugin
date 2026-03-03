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
claude --plugin-dir ~/ai-workspace
/ai-workspace:threads create feature-work
```

The plugin auto-creates `threads/` and `.claude/settings.json` on first use.

## Architecture

### Directory Structure

```
ai-workspace/                      # Plugin repository
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── agents/                       # Specialized AI personas
│   ├── architect.md
│   ├── security-reviewer.md
│   ├── product-strategist.md
│   ├── tech-advisor.md
│   ├── cost-analyzer.md
│   └── devils-advocate.md
├── skills/                       # User-invocable skills
│   ├── common/
│   │   └── workspace_utils.py   # Shared utilities
│   └── threads/                 # Thread management skill
│       ├── SKILL.md             # Skill definition
│       └── scripts/
│           ├── list-threads.py
│           └── get-thread-status.py
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
- Plugin: Installed once at `~/ai-workspace` (this repository)
- Workspace: User's project directory (e.g., `~/my-project`)
- The plugin creates `threads/` directory in each workspace
- Each workspace gets its own auto-generated `.claude/settings.json`

**Skills:**
- Defined in `skills/` directory
- Each skill has a `SKILL.md` file (interpretive instructions for Claude)
- Supporting Python scripts in `scripts/` subdirectory
- Invoked with `/ai-workspace:skill-name` command

**Agents:**
- Specialized AI personas in `agents/` directory
- Invoked automatically by Claude's Task tool when needed
- Each agent has specific expertise (architecture, security, etc.)

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

### Testing Changes

```bash
# Test in a temporary directory
mkdir /tmp/test-workspace
cd /tmp/test-workspace
claude --plugin-dir ~/ai-workspace

# Test thread creation (should auto-create structure)
/ai-workspace:threads create test
# Verify: ls threads/ .claude/

# Test thread operations
/ai-workspace:threads
/ai-workspace:threads save
/ai-workspace:threads snapshot

# Clean up
cd ~ && rm -rf /tmp/test-workspace
```

### Common Tasks

**Adding a new skill:**
1. Create `skills/skill-name/` directory
2. Add `SKILL.md` with skill definition
3. Add scripts in `scripts/` subdirectory if needed
4. Update README.md to document the skill
5. Test with `/ai-workspace:skill-name`

**Modifying a template:**
1. Edit file in `templates/` directory
2. Test by creating a workspace and using the template
3. Verify the template renders correctly

**Updating workspace utilities:**
1. Edit `skills/common/workspace_utils.py`
2. Ensure backward compatibility
3. Test auto-creation behavior
4. Run tests to verify thread operations still work

**Adding a new agent:**
1. Create `agents/agent-name.md`
2. Follow existing agent structure (expertise, approach, output format)
3. Document the agent in README.md
4. Test by having Claude delegate work to it

## Key Patterns

### Auto-creation System

The plugin uses lazy initialization:
- `get_threads_dir()` - Auto-creates `threads/` directory on first call
- `ensure_settings()` - Auto-creates `.claude/settings.json` from template
- No separate initialization step required - just start using threads

**Implementation:**
```python
def get_threads_dir() -> Path:
    """Get threads directory, auto-creating if needed."""
    workspace_dir = get_workspace_dir()  # Returns Path.cwd()
    threads_dir = workspace_dir / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    ensure_settings()  # Also create settings on first thread operation
    return threads_dir
```

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

### Plugin Script Paths

When invoking plugin scripts from skills, use `${CLAUDE_PLUGIN_ROOT}` environment variable and pass workspace directory as a literal path:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/threads/scripts/list-threads.py "/absolute/path/to/workspace"
```

**Why this matters:**
- Plugin is at: `~/ai-workspace/` (or in Claude's plugin cache)
- User workspace is at: `~/my-project/`
- Scripts run from plugin directory but need to access user's workspace
- Pass the current working directory path as first argument so scripts know where the workspace is
- Use literal path (e.g., `/Users/user/my-project`), not command substitution like `$(pwd)` (avoids permission prompts)

**Example:**
```bash
# ❌ Wrong - script can't find workspace
python3 ${CLAUDE_PLUGIN_ROOT}/skills/threads/scripts/list-threads.py
# Script uses cwd (plugin dir), looks for threads in wrong place

# ✅ Correct - pass workspace directory as literal path
python3 ${CLAUDE_PLUGIN_ROOT}/skills/threads/scripts/list-threads.py "/Users/user/my-project"
# Script receives workspace path, finds threads at /Users/user/my-project/threads/
```

## Verification Practices

**Before referencing project resources:**
- ✅ Use `list-threads.py` to list threads before naming them
- ✅ Use Read/Glob/Bash to verify file existence
- ✅ Read files before describing their contents
- ✅ Check scripts exist before referencing them

**When working with threads (as a user would):**
- Threads are in the user's workspace, not the plugin repo
- Use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/threads/scripts/list-threads.py "/path/to/workspace"` to see available threads (pass actual path)
- Read `threads/{name}/README.md` for thread details
- Never assume thread content - always verify

## Code Conventions

### Python
- Follow PEP 8 style
- Use type hints for function signatures
- Keep functions focused and small
- Use `error_exit()` for user-facing errors
- Scripts should be executable with `#!/usr/bin/env python3`

### Markdown
- Use ATX-style headers (`#` not underlines)
- Code blocks with language specification
- Keep line length reasonable but not strict

### Bash
- Scripts should be executable (`chmod +x`)
- Use `set -euo pipefail` for safety
- Prefer Python scripts over bash for complexity

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
- Users install the plugin once (`git clone` to `~/ai-workspace`)
- Plugin is loaded with `--plugin-dir ~/ai-workspace` flag
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
