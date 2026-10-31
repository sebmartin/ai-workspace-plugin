---
name: init
description: Initialize the ai-workspace plugin in the current directory. Creates threads/ and AGENTS.md, then offers to allow the plugin's tools in the user's global settings. Safe to re-run, skips files that already exist.
---

# Init Skill

Initialize the ai-workspace plugin in the current working directory.

## What It Creates

1. `threads/` — directory where conversation threads will be stored
2. `AGENTS.md` — a pointer to the plugin, read by both Claude Code and Codex CLI

All steps are skipped if the file or directory already exists. Safe to re-run.

**No rules and no permissions go into the workspace.** How to work with threads is in the
threads skill, which loads wherever a thread is resumed from, and the permissions go in
the user's global settings, which apply from any directory. A file in the workspace loads
only when a session starts in that directory, which most sessions do not, so a rule kept
there was missing exactly when a thread was resumed from somewhere else.

`AGENTS.md` carries no rules. It tells a reader, and Codex, that this directory is an
ai-workspace and which commands reach the plugin.

Both files work for Claude Code and Codex CLI. No vendor detection needed.

## Steps

### 1. Create `threads/`

```bash
mkdir -p threads
```

Skip if `threads/` already exists.

### 2. Create `AGENTS.md`

Check if `AGENTS.md` exists. If not, call `mcp__plugin_ai-workspace_threads__get_skill_file("templates/AGENTS.md.template")` and write the result to `AGENTS.md`.

### 3. Offer the permissions

Offer to allow the plugin's tools in the user's **global** CLI settings, so they are not
prompted again and the allowance holds from any directory. Allow all
`mcp__plugin_ai-workspace_threads__*` tools and Read/Edit/Write on `{workspace}/**`, using
the absolute path of the workspace. Tell the user what was written and that a restart may
be needed.

Don't write a settings file inside the workspace. It would only apply to sessions that
start there.

### 4. Codex subagent install (Codex CLI only)

This step only applies on Codex CLI. **Detect the CLI before doing anything**: you know which CLI you are. If you are Claude Code, skip this entire step — Claude loads the `proponent` and `skeptic` agents directly from the plugin's `agents/` directory; nothing to copy.

If you are Codex CLI: Codex plugin manifests cannot bundle subagents directly, so the `.toml` files have to be copied into the user's home `agents/` directory:

```bash
mkdir -p ~/.codex/agents
cp <plugin-root>/.codex-plugin/agents/*.toml ~/.codex/agents/
```

Resolve `<plugin-root>` from the location of this SKILL.md (three directories up: `..` → `..` → `..`). Skip files that already exist in `~/.codex/agents/` unless the user asks to overwrite.

## Output

Report what was created vs skipped:

```
Initialized ai-workspace in /path/to/workspace

Created:
  threads/
  AGENTS.md

Skipped (already exists):
  (none)

Start your first thread:
  /ai-workspace:threads create my-first-thread   (Claude Code)
  $threads create my-first-thread                (Codex CLI)

On Claude Code, restart the CLI for the new permissions to take effect.
```

Use the actual absolute path of the current working directory, not a placeholder.

If the permissions were added, remind the user to restart Claude Code so they take effect. This restart is not needed on Codex.
