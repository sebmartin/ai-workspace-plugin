---
name: init
description: Initialize the ai-workspace plugin in the current directory. Creates threads/, AGENTS.md, CLAUDE.md, and .claude/settings.json. Safe to re-run, skips files that already exist.
---

# Init Skill

Initialize the ai-workspace plugin in the current working directory.

## What It Creates

1. `threads/` — directory where conversation threads will be stored
2. `AGENTS.md` — workspace instructions read by both Claude Code and Codex CLI
3. `CLAUDE.md` — one-line pointer to `AGENTS.md` (Claude Code reads this natively)
4. `.claude/settings.json` — permission allowlist for plugin operations on Claude Code

All steps are skipped if the file or directory already exists. Safe to re-run.

The same files work for both Claude Code and Codex CLI. Codex ignores `CLAUDE.md` and `.claude/`; Claude ignores files it doesn't recognize. No vendor detection needed.

## Steps

### 1. Create `threads/`

```bash
mkdir -p threads
```

Skip if `threads/` already exists.

### 2. Create `AGENTS.md`

Check if `AGENTS.md` exists. If not, call `mcp__plugin_ai-workspace_threads__get_template(template_name="AGENTS.md.template")` and write the result to `AGENTS.md`.

### 3. Create `CLAUDE.md`

Check if `CLAUDE.md` exists. If not, call `mcp__plugin_ai-workspace_threads__get_template(template_name="CLAUDE.md.template")` and write the result to `CLAUDE.md`. The template is a single `@AGENTS.md` line so Claude imports the AGENTS.md content without content duplication.

### 4. Create `.claude/settings.json`

Check if `.claude/settings.json` exists. If not:

```bash
mkdir -p .claude
```

Then call `mcp__plugin_ai-workspace_threads__get_template(template_name="settings.json.template")` and write the result to `.claude/settings.json`.

This file is Claude-Code-specific. It is harmless on Codex; Codex ignores it.

### 5. Codex subagent install (Codex CLI only)

This step only applies on Codex CLI. **Detect the CLI before doing anything**: run

```bash
printenv CLAUDE_PLUGIN_ROOT
```

If it prints a value, you are on Claude Code — **skip this entire step**. Claude loads the `proponent` and `skeptic` agents directly from the plugin's `agents/` directory; nothing to copy.

If it prints nothing, you are on Codex CLI. Codex plugin manifests cannot bundle subagents directly, so the `.toml` files have to be copied into the user's home `agents/` directory:

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
  CLAUDE.md
  .claude/settings.json

Skipped (already exists):
  (none)

Start your first thread:
  /ai-workspace:threads create my-first-thread   (Claude Code)
  /threads create my-first-thread                (Codex CLI)

On Claude Code, restart the CLI for the new permissions to take effect.
```

Use the actual absolute path of the current working directory, not a placeholder.

If `.claude/settings.json` was newly created, remind the user to restart Claude Code so the permission allowlist takes effect. This restart is not needed on Codex.
