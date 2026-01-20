# AI Workspace Setup

This is a template for AI-assisted development with Claude Code.

## Quick Start

### 1. Clone the template

```bash
git clone <this-repo-url> my-ai-workspace
cd my-ai-workspace
```

### 2. Set up your workspace

Create a separate git repo for your content and link it:

```bash
# Create your workspace repo (wherever you want)
mkdir ~/my-workspace
cd ~/my-workspace
git init
mkdir threads
git add .
git commit -m "Initial workspace"

# Optional: Push to a private remote for backup
git remote add origin <your-private-repo-url>
git push -u origin main

# Link it to the template
cd /path/to/my-ai-workspace
ln -s ~/my-workspace workspace
```

### 3. Start using it

```bash
# Restart Claude Code to load skills, then:
/threads create
```

## Structure

**Template repo** (this one) - Skills, templates, docs. Share across contexts (personal/work).

**Workspace repo** (separate) - Your threads and content. Keep private, back up separately.

The symlink keeps them completely separate while making the workspace accessible to Claude Code.

## Syncing

**Pull template updates:**
```bash
cd my-ai-workspace
git pull
```

**Backup your workspace:**
```bash
cd ~/my-workspace  # or wherever your workspace is
git add .
git commit -m "Update threads"
git push
```

## Available Skills

- `/threads` - Manage discussion threads
- `/todos` - Track tasks
- `/architect`, `/devils-advocate`, `/product-strategist`, `/tech-advisor`, `/cost-analyzer`, `/security-reviewer` - AI personas

See [README.md](README.md) for full documentation.

## License

MIT
