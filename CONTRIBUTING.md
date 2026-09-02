# Contributing to AI Workspace Plugin

Thank you for contributing! This plugin helps developers organize long-running AI conversations with thread management and specialized agents. It ships as a cross-vendor plugin for both Claude Code and OpenAI Codex CLI from a single source tree.

## Development Setup

1. Clone the repository
2. Make your changes (skills, agents, templates, documentation)
3. Regenerate the Codex agent TOMLs if you edited `agents/*.md`: `python3 scripts/sync-codex-agents.py`
4. Test with `--plugin-dir` flag on Claude Code (see Testing below); Codex testing requires a local marketplace stub
5. Submit a pull request

## Prerequisites

- **Claude Code CLI** - Required to test the Claude side
- **Codex CLI** (optional) - Required to test the Codex side
- **git** - Version control
- **uv** - Required to run the MCP server and tests (see https://docs.astral.sh/uv/getting-started/installation/)

## Project Structure

```
ai-workspace-plugin/
├── .claude-plugin/plugin.json       # Claude Code plugin manifest
├── .codex-plugin/
│   ├── plugin.json                  # Codex CLI plugin manifest
│   └── agents/                      # Generated from agents/*.md (do not edit)
├── agents/                          # Canonical persona source (Claude reads directly)
│   ├── proponent.md
│   └── skeptic.md
├── hooks/                           # Session-start hook
├── skills/                          # User-invocable skills (shared by both CLIs)
│   ├── debate/SKILL.md
│   ├── init/SKILL.md
│   └── threads/
│       ├── SKILL.md
│       └── scripts/mcp_server.py    # Tool declarations; delegates to lib/ai_workspace/
├── lib/ai_workspace/                # Where the server's work happens
│   ├── workspace.py                 # which workspace, where things live, archive/restore
│   ├── config.py                    # the user-global config.json
│   ├── plugin.py                    # plugin root, templates
│   ├── text.py                      # frontmatter and YAML helpers
│   └── threads/                     # the thread concept
│       ├── __init__.py              # the API: one function per operation
│       ├── schema.py                # schema -> module
│       └── v1/                      # schema 1: the README is the thread
├── templates/
│   ├── AGENTS.md.template           # Workspace instructions (vendor-neutral)
│   ├── CLAUDE.md.template           # One-line "@AGENTS.md" import for Claude
│   ├── settings.json.template       # Claude-only permission allowlist
│   └── ...
├── scripts/
│   └── sync-codex-agents.py         # Regenerates .codex-plugin/agents/*.toml
├── tests/test_mcp_server.py
├── docs/examples/                   # User walkthroughs
├── AGENTS.md                        # Repo instructions (vendor-neutral)
├── CLAUDE.md                        # One-line "@AGENTS.md" for Claude
├── README.md
└── LICENSE
```

## Testing the Plugin

### Unit Tests

```bash
# Run unit tests
uv run --with pytest --with-requirements skills/threads/scripts/mcp_server.py python3 -m pytest tests/ -v
```

### Basic Testing

Test your changes using the `--plugin-dir` flag:

```bash
# Navigate to your plugin repository
cd ~/ai-workspace-plugin

# Load the plugin in any directory
cd ~/some-other-directory
claude --plugin-dir ~/ai-workspace-plugin
```

### Testing Thread Management (Claude Code)

```bash
mkdir /tmp/test-workspace && cd /tmp/test-workspace
claude --plugin-dir ~/ai-workspace-plugin

# Initialize the workspace
/ai-workspace:init
# Verify: ls threads/ AGENTS.md CLAUDE.md .claude/settings.json

# Create a thread
/ai-workspace:threads create test-thread
# Verify: ls threads/test-thread/

# Test thread operations
/ai-workspace:threads
/ai-workspace:threads save
/ai-workspace:threads snapshot

# Clean up
cd ~ && rm -rf /tmp/test-workspace
```

### Testing on Codex CLI

Codex has no `--plugin-dir` flag. To test a local checkout, point a Codex marketplace at the plugin directory:

```bash
# (Once Codex marketplace stub is set up — TBD; see plan follow-ups)
codex plugin marketplace add /path/to/local/marketplace
codex
> initialize the ai-workspace
> create a thread called test-thread
```

## Code Style

### Python
- Follow PEP 8 style
- **Skills**: Follow existing patterns in `skills/`

### Bash
- **Style**: Use `set -euo pipefail` for safety
- **Scripts**: Must be executable (chmod +x)

### Markdown
- Follow existing conventions
- Keep line length reasonable but not strict
- Use code blocks with language specification

## Adding New Skills

1. Create directory in `skills/<skill-name>/`
2. Add `SKILL.md` with skill definition (keep frontmatter to `name` + `description`; Codex requires this and Claude accepts it)
3. Write prose vendor-neutrally: prefer "your CLI" or note Claude-vs-Codex differences explicitly. Avoid hard-coding `/ai-workspace:` namespace in user-facing examples (Codex uses bare `/skill-name`).
4. Add supporting scripts in `scripts/` subdirectory if needed
5. Update README.md to list the new skill
6. Test the skill works with `/ai-workspace:skill-name` (Claude) and `/skill-name` (Codex)

## Adding or Editing Agents

1. Edit `agents/{name}.md` (Claude format)
2. Regenerate Codex `.toml` mirrors:
   ```bash
   python3 scripts/sync-codex-agents.py
   ```
3. Commit both the `.md` source and the generated `.toml` files together. Do not hand-edit the `.toml` files; they are generated artifacts.
4. Write prose vendor-neutrally so the same persona works under both CLIs' subagent systems.

## Pull Request Guidelines

- **Clear description**: Explain what changes and why
- **Update documentation**: If behavior changes, update relevant docs
- **No workspace/ files**: PRs must not include workspace/ content
- **Tests pass**: Run `uv run --with pytest --with-requirements skills/threads/scripts/mcp_server.py python3 -m pytest tests/ -v`

## Common Tasks

### Update templates

```bash
# Edit templates in templates/
vim templates/thread-template.md

# Test by creating a workspace and using the template
cd /tmp/test-workspace
/ai-workspace:threads create test
```

### Modify skills

```bash
# Edit skill definition
vim skills/threads/SKILL.md

# Edit MCP server
vim skills/threads/scripts/mcp_server.py

# Run tests
uv run --with pytest --with-requirements skills/threads/scripts/mcp_server.py python3 -m pytest tests/ -v

# Test the skill
/ai-workspace:threads
```

## Release Checklist

Merging to `main` ships the plugin, so this is the pre-merge checklist for every PR, not a separate release event:

- [ ] Plugin loads with `claude --plugin-dir .`
- [ ] Plugin loads on Codex (via local marketplace install)
- [ ] Init works in a clean directory:
  - [ ] Creates `threads/`, `AGENTS.md`, `CLAUDE.md` (one-liner), and `.claude/settings.json`
  - [ ] On Codex, also copies `.codex-plugin/agents/*.toml` into `~/.codex/agents/`
  - [ ] Re-running skips existing files safely
- [ ] Thread management works (both CLIs):
  - [ ] `threads create` works
  - [ ] `threads` lists threads
  - [ ] `threads save` works
  - [ ] `threads snapshot` works
- [ ] Debate works (both CLIs):
  - [ ] Proponent and skeptic subagents spawn in isolated contexts
  - [ ] Final artifact is saved to the active thread
- [ ] Agents `.toml` mirrors regenerated if any `agents/*.md` changed (`python3 scripts/sync-codex-agents.py`)
- [ ] Documentation is up to date:
  - [ ] README.md Quick Start is accurate
  - [ ] CONTRIBUTING.md reflects current structure
- [ ] Both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` versions bumped in sync (required on every PR, since the merge is the release)

## Questions?

Open an issue for discussion or reach out to maintainers!

## License

MIT - see [LICENSE](LICENSE) file for details.
