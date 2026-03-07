# Contributing to AI Workspace Plugin

Thank you for contributing! This plugin helps developers organize long-running AI conversations with thread management and specialized agents.

## Development Setup

1. Clone the repository
2. Make your changes (skills, agents, templates, documentation)
3. Test with `--plugin-dir` flag (see Testing below)
4. Submit a pull request

## Prerequisites

- **Claude Code CLI** - Required to test the plugin
- **git** - Version control
- **uv** - Required to run the MCP server and tests (see https://docs.astral.sh/uv/getting-started/installation/)

## Project Structure

```
ai-workspace-plugin/
├── .claude-plugin/
│   └── plugin.json            # Plugin manifest
├── agents/                    # AI persona subagents
│   ├── proponent.md
│   └── skeptic.md
├── skills/
│   ├── common/
│   │   └── workspace_utils.py
│   └── threads/
│       ├── SKILL.md
│       └── scripts/
│           └── mcp_server.py
├── templates/                 # Thread templates
│   ├── thread-template.md
│   ├── settings.json.template
│   └── ...
├── tests/
│   └── test_mcp_server.py
├── README.md
├── CONTRIBUTING.md
├── AGENTS.md
└── LICENSE
```

## Testing the Plugin

### Unit Tests

```bash
# Run unit tests
uv run --with pytest --with mcp python3 -m pytest tests/ -v
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

### Testing Thread Management

```bash
cd /tmp/test-workspace
claude --plugin-dir ~/ai-workspace-plugin

# Create first thread (auto-creates structure)
/ai-workspace:threads create test-thread
# Verify: ls threads/       # Should show test-thread/
# Verify: ls .claude/       # Should show settings.json

# Test thread operations
/ai-workspace:threads
/ai-workspace:threads save
/ai-workspace:threads snapshot

# Clean up
cd ~
rm -rf /tmp/test-workspace
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
2. Add `SKILL.md` with skill definition
3. Add supporting scripts (Python, etc.) in `scripts/` subdirectory if needed
4. Update README.md to list the new skill
5. Test the skill works with `/ai-workspace:skill-name` command

## Pull Request Guidelines

- **Clear description**: Explain what changes and why
- **Update documentation**: If behavior changes, update relevant docs
- **No workspace/ files**: PRs must not include workspace/ content
- **Tests pass**: Run `uv run --with pytest --with mcp python3 -m pytest tests/ -v`

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
uv run --with pytest --with mcp python3 -m pytest tests/ -v

# Test the skill
/ai-workspace:threads
```

## Release Checklist

Before releasing a new version:

- [ ] Plugin loads with `claude --plugin-dir .`
- [ ] Auto-creation works in clean directory:
  - [ ] `threads/` directory created on first thread
  - [ ] `.claude/settings.json` created automatically
- [ ] Thread management works:
  - [ ] `/ai-workspace:threads create` works
  - [ ] `/ai-workspace:threads` lists threads
  - [ ] `/ai-workspace:threads save` works
  - [ ] `/ai-workspace:threads snapshot` works
- [ ] Documentation is up to date:
  - [ ] README.md Quick Start is accurate
  - [ ] CONTRIBUTING.md reflects current structure
  - [ ] plugin.json version bumped

## Questions?

Open an issue for discussion or reach out to maintainers!

## License

MIT - see [LICENSE](LICENSE) file for details.
