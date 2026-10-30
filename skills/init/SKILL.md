---
name: init
description: Initialize the ai-workspace plugin in the current directory. Creates threads/ and AGENTS.md, then offers to allow the plugin's tools in the user's global settings. Safe to re-run, skips files that already exist.
---

# Init Skill

Initialize the ai-workspace plugin in the current working directory.

## What It Creates

1. `threads/` — directory where conversation threads will be stored
2. `AGENTS.md` — workspace instructions read by both Claude Code and Codex CLI

All steps are skipped if the file or directory already exists. Safe to re-run.

**Nothing the plugin needs is written to a file in the workspace.** The rules for working
with threads are in the threads skill, which loads wherever a thread is resumed from, and
the permissions go in the user's global settings, which apply from any directory. A
workspace file only loads when a session happens to start in that directory, so anything
that lived in one was missing from most sessions.

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
