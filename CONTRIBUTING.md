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

## Project Structure

```
ai-workspace-plugin/
├── .claude-plugin/
│   └── plugin.json            # Plugin manifest
├── agents/                    # AI persona subagents
│   ├── architect.md
│   ├── security-reviewer.md
│   ├── product-strategist.md
│   ├── tech-advisor.md
│   ├── cost-analyzer.md
│   └── devils-advocate.md
├── skills/                    # Slash-command skills
│   ├── common/               # Shared utilities
│   │   ├── workspace_utils.py
│   │   └── resources/
│   │       └── settings.json.template
│   └── threads/              # Thread management
│       ├── SKILL.md
│       └── scripts/
│           ├── list-threads.py
│           └── get-thread-status.py
├── templates/                 # Thread templates
│   ├── thread-template.md
│   ├── thread-session-template.md
│   ├── snapshot-template.md
│   ├── adr-template.md
│   └── feature-spec.md
├── README.md                  # Plugin documentation
├── CONTRIBUTING.md            # This file
├── AGENTS.md                  # Agent instructions
└── LICENSE                    # MIT license
```

## Testing the Plugin

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
- **Formatting**: Black (automatic via pre-commit)
- **Skills**: Follow existing patterns in `skills/`

### Bash
- **Linting**: ShellCheck compliant (automatic via pre-commit)
- **Style**: Use `set -euo pipefail` for safety
- **Scripts**: Must be executable (chmod +x)

### Markdown
- Follow existing conventions
- Keep line length reasonable but not strict
- Use code blocks with language specification

## Adding New Skills

1. Create directory in `skills/<skill-name>/`
2. Add `SKILL.md` with skill definition
3. Add any supporting scripts in `scripts/` subdirectory
4. Update README.md to list the new skill
5. Test the skill works with `/ai-workspace:skill-name` command

## Pull Request Guidelines

- **Clear description**: Explain what changes and why
- **Update documentation**: If behavior changes, update relevant docs
- **Test hooks**: Verify git hooks still work correctly
- **No workspace/ files**: PRs must not include workspace/ content
- **Code quality**: Pre-commit hooks must pass

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

# Edit supporting scripts
vim skills/threads/scripts/list-threads.py

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
