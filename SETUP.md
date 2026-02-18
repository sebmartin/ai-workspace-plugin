# AI Workspace Setup

This is a template for AI-assisted development with Claude Code.

## Prerequisites

**uv** - Fast Python package installer (required)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or visit: https://docs.astral.sh/uv/getting-started/installation/
```

## Quick Start

### 1. Clone the template

```bash
git clone <this-repo-url> my-ai-workspace
cd my-ai-workspace
```

### 2. Run setup script

The setup script will:
- Create Python virtual environment with `uv`
- Install MCP server dependencies
- Install pre-commit framework and git hooks
- Verify workspace directory exists

```bash
./setup.sh
```

This installs git hooks that **automatically protect your workspace/ privacy** by preventing accidental commits to the public template.

### 3. Set up your workspace (optional)

The `workspace/` directory is already present and ignored by the template repo's `.gitignore`.

**Option A: Simple (local only)**

The workspace is ready to use - just start creating threads.

**Option B: Private backup (recommended)**

Make `workspace/` a nested git repo for version control and backups:

```bash
cd workspace
git init
git add .
git commit -m "Initial workspace"

# Optional: Push to a private remote for backup
git remote add origin git@github.com:USER/private-workspace.git
git push -u origin main
```

Note: Replace `USER/private-workspace.git` with your actual private repository URL.

### 4. Start using it

```bash
# Restart Claude Code to load MCP servers, then:
/threads create
```

## Structure

**Template repo** (this one) - Skills, templates, docs. This is the public repository.

**Workspace directory** (`workspace/`) - Your threads and content. Ignored by the template repo's `.gitignore`. Optionally a nested private git repo for backups.

The gitignore keeps them completely separate - workspace changes never appear in the template repo's git status.

## Updating

### Pull template updates

```bash
cd my-ai-workspace
git pull

# If setup.sh changed, re-run it
./setup.sh
```

### Backup your workspace

If you initialized workspace/ as a git repo:

```bash
cd workspace
git add .
git commit -m "Update threads"
git push
```

## Updating from Previous Versions

If you cloned this template before the unified setup script was added:

```bash
cd my-ai-workspace
git pull
./setup.sh  # This will set up git hooks and consolidate the venv
```

This adds automatic git hook protection to prevent accidentally committing workspace/ files.

## Available Skills

- `/threads` - Manage discussion threads
- `/later` - Track tasks
- `/architect`, `/devils-advocate`, `/product-strategist`, `/tech-advisor`, `/cost-analyzer`, `/security-reviewer` - AI personas

See [README.md](README.md) for full documentation.

## License

MIT
