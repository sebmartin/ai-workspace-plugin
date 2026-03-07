---
name: init
description: Initialize the ai-workspace plugin in the current directory. Creates threads/, .claude/settings.json, and CLAUDE.md. Safe to re-run — skips files that already exist.
---

# Init Skill

Initialize the ai-workspace plugin in the current working directory.

## What It Creates

1. `.claude/settings.json` — permission allowlist for plugin operations
2. `threads/` — directory where conversation threads will be stored
3. `CLAUDE.md` — workspace instructions for Claude

All steps are skipped if the file or directory already exists. Safe to re-run.

## Steps

### 1. Create `.claude/settings.json`

Check if `.claude/settings.json` exists. If not:

```bash
mkdir -p .claude
```

Then call `mcp__plugin_ai-workspace_threads__get_template(template_name="settings.json.template")` and write the result to `.claude/settings.json`.

### 2. Create `threads/`

```bash
mkdir -p threads
```

Skip if `threads/` already exists.

### 3. Create `CLAUDE.md`

Check if `CLAUDE.md` exists. If not, call `mcp__plugin_ai-workspace_threads__get_template(template_name="workspace-claude.md")` and write the result to `CLAUDE.md`.

## Output

Report what was created vs skipped:

```
Initialized ai-workspace in /path/to/workspace

Created:
  threads/
  .claude/settings.json
  CLAUDE.md

Skipped (already exists):
  (none)

Start your first thread:
  /ai-workspace:threads create my-first-thread

Restart Claude for the new permissions to take effect.
```

Use the actual absolute path of the current working directory, not a placeholder.

If `.claude/settings.json` was newly created, remind the user to restart Claude so the permission allowlist takes effect.
