# Git Hooks

This directory contains versioned git hook scripts that protect workspace/ privacy.

## Purpose

The hooks prevent accidentally committing or pushing private workspace/ content to the public template repository. This is critical for maintaining user privacy when using this template.

## Hooks

**`check-workspace-files.sh`** - Workspace protection hook
- Runs at both pre-commit and pre-push stages
- Blocks any workspace/ files except:
  - `workspace/.keep` (version control marker)
  - `workspace/README.md` (template documentation)
- Provides clear error messages with remediation steps

## How It Works

### Pre-commit Stage
Checks files staged for commit (`git diff --cached --name-only`) and blocks if any workspace/ files are staged (except allowed ones).

### Pre-push Stage
Checks all tracked files (`git ls-files workspace/`) and blocks push if any workspace/ files exist in the repository (except allowed ones).

## Installation

Hooks are automatically installed when you run `./setup.sh` in the project root.

The setup script:
1. Installs the pre-commit framework using `uv`
2. Configures pre-commit to run these hooks
3. Installs hooks into `.git/hooks/`

## Manual Installation

If needed, you can manually install pre-commit hooks:

```bash
# Install pre-commit tool (if not already installed)
uv pip install pre-commit

# Install hooks
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Testing

To verify the hooks work correctly:

```bash
# This should be BLOCKED
echo "test" > workspace/test.txt
git add workspace/test.txt
git commit -m "test"  # Should fail with error message

# This should SUCCEED
git add workspace/.keep
git commit -m "keep file"  # Should succeed

# Run all hooks manually
pre-commit run --all-files
```

## Troubleshooting

**Hooks not running?**
- Verify pre-commit is installed: `pre-commit --version`
- Check hook installation: `ls -la .git/hooks/`
- Reinstall: `pre-commit install --install-hooks`

**Need to bypass (emergency only)?**
```bash
# Skip hooks for one commit (USE WITH CAUTION)
git commit --no-verify -m "message"

# Skip hooks for one push (USE WITH CAUTION)
git push --no-verify
```

**Warning**: Bypassing hooks can leak private workspace/ data to the public repository!

## Development

When modifying hook scripts:
1. Edit the script in `hooks/`
2. Run `pre-commit run block-workspace-files --all-files` to test
3. Run `pre-commit run --all-files` to verify
4. Commit changes to the hook scripts (they're version controlled)

The hooks will automatically update for all users when they pull changes and run `pre-commit install` again.
