# AI Workspace Setup

This is a template for AI-assisted development with Claude Code.

## Quick Start

### 1. Clone the template

```bash
git clone <this-repo-url> my-ai-workspace
cd my-ai-workspace
```

### 2. Set up your workspace

**Option A: Simple (workspace in template repo)**

Just create the workspace directory:

```bash
mkdir workspace
mkdir workspace/threads
```

**Option B: Separate repo (advanced)**

Keep your workspace in a separate git repo for better separation:

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

**If you chose Option B (symlink)**, you need to configure Claude Code settings:

Create `.claude/settings.local.json`:

```bash
cat > .claude/settings.local.json << 'EOF'
{
  "permissions": {
    "additionalDirectories": [
      "workspace",
      "/absolute/path/to/your/workspace"
    ]
  }
}
EOF
```

Replace `/absolute/path/to/your/workspace` with your actual workspace path (e.g., `/Users/yourname/my-workspace`). This allows Claude Code's Glob tool to follow the symlink.

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
- `/later` - Track tasks
- `/architect`, `/devils-advocate`, `/product-strategist`, `/tech-advisor`, `/cost-analyzer`, `/security-reviewer` - AI personas

See [README.md](README.md) for full documentation.

## License

MIT
