# AGENTS.md

This is the AI Workspace Plugin repository, which ships as a dual-target plugin for both Claude Code and Codex CLI from a single source tree.

For contribution guidelines, project structure, testing instructions, and pull request expectations, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Cross-vendor structure (quick reference)

- `.claude-plugin/plugin.json` — Claude Code plugin manifest
- `.codex-plugin/plugin.json` — Codex CLI plugin manifest
- `.codex-plugin/agents/*.toml` — Generated from `agents/*.md` via `scripts/sync-codex-agents.py`. Do not edit by hand.
- `agents/*.md` — Canonical persona source (read directly by Claude; regenerated for Codex)
- `skills/`, `templates/`, `skills/threads/scripts/mcp_server.py` — Shared between both vendors

## Working in this repo

When you edit `agents/*.md`, regenerate the Codex `.toml` mirrors:

```bash
python3 scripts/sync-codex-agents.py
```

Commit both the `.md` source and the generated `.toml` files together.
