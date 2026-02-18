# Contributing to AI Workspace Template

Thank you for contributing! This template helps developers maintain privacy while collaborating on AI-assisted projects with Claude Code.

## Development Setup

1. Clone the repository
2. Run `./setup.sh` to install dependencies and git hooks
3. Make your changes (skills, templates, documentation)
4. Test that hooks work correctly (see below)
5. Submit a pull request

## Prerequisites

- **uv** - Python package manager ([installation](https://docs.astral.sh/uv/getting-started/installation/))
- **git** - Version control

## Project Structure

```
ai-workspace/
├── .claude/skills/       # AI persona definitions (skills)
├── templates/            # Reusable templates
├── hooks/                # Git hook scripts (versioned)
├── tests/                # Test scripts
├── workspace/            # User's private content (gitignored)
├── .venv/                # Python virtual environment (gitignored)
├── setup.sh              # Main setup script
├── pyproject.toml        # Project metadata and dependencies
├── uv.lock               # Locked dependency versions
└── .pre-commit-config.yaml  # Hook configuration
```

## Testing Git Hooks

To verify the workspace protection works:

```bash
# This should be BLOCKED
echo "test" > workspace/test.txt
git add workspace/test.txt
git commit -m "test"  # Should fail with clear error message

# This should SUCCEED
echo "test" > templates/new-template.md
git add templates/new-template.md
git commit -m "Add new template"

# Run all hooks manually
pre-commit run --all-files
```

## Code Style

### Python
- **Formatting**: Black (automatic via pre-commit)
- **Skills**: Follow existing patterns in `.claude/skills/`

### Bash
- **Linting**: ShellCheck compliant (automatic via pre-commit)
- **Style**: Use `set -euo pipefail` for safety
- **Scripts**: Must be executable (chmod +x)

### Markdown
- Follow existing conventions
- Keep line length reasonable but not strict
- Use code blocks with language specification

## Adding New Skills

1. Create directory in `.claude/skills/<skill-name>/`
2. Add `SKILL.md` with skill definition
3. Add any supporting scripts in `scripts/` subdirectory
4. Update README.md to list the new skill
5. Test the skill works with `/skill-name` command

## Pull Request Guidelines

- **Clear description**: Explain what changes and why
- **Update documentation**: If behavior changes, update relevant docs
- **Test hooks**: Verify git hooks still work correctly
- **No workspace/ files**: PRs must not include workspace/ content
- **Code quality**: Pre-commit hooks must pass

## Common Tasks

### Update Python dependencies

```bash
uv add <package>    # add a dependency (updates pyproject.toml and uv.lock)
uv sync             # install from lockfile after editing pyproject.toml
```

### Update hook scripts

```bash
# Edit scripts in hooks/
vim hooks/check-workspace-files.sh

# Test changes
pre-commit run block-workspace-files --all-files

# Reinstall hooks
pre-commit install --install-hooks
```

### Run hooks manually

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run block-workspace-files

# Run on staged files only
pre-commit run
```

## Release Checklist

Before releasing a new version:

- [ ] `./setup.sh` runs without errors
- [ ] Git hooks installed and executable
- [ ] `pre-commit run --all-files` passes
- [ ] Can create workspace/test.txt
- [ ] Cannot commit workspace/test.txt (blocked with clear message)
- [ ] Can commit templates/test.txt
- [ ] `pre-commit run --all-files` passes
- [ ] Documentation is up to date
- [ ] SETUP.md mentions running setup.sh
- [ ] README.md Quick Start is accurate

## Questions?

Open an issue for discussion or reach out to maintainers!

## License

MIT - see [LICENSE](LICENSE) file for details.
