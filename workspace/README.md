# AI Workspace Content

This is your private workspace directory - a **separate git repo** symlinked from the public template.

## What lives here

All your personal work:
- `threads/` - Your discussion threads, one per project/topic

## Setup

If you're seeing this file in the template repo, you need to set up your workspace:

See [../SETUP.md](../SETUP.md) for setup instructions.

### Quick setup:

```bash
# Option 1: Remote repo (recommended for syncing across machines)
cd ~
git clone <your-workspace-repo-url> my-workspace-content
cd /path/to/template
ln -s ~/my-workspace-content workspace

# Option 2: Local repo (single machine only)
mkdir ~/my-workspace-content
cd ~/my-workspace-content
git init
mkdir threads
git add .
git commit -m "Initial workspace"
cd /path/to/template
ln -s ~/my-workspace-content workspace
```

## Usage

Use `/threads` commands to manage your threads:
- `/threads create` - Create a new thread
- `/threads list` - See all threads
- `/threads resume` - Resume a thread
- `/threads snapshot` - Generate shareable snapshot

## Syncing

```bash
# Commit and push your work (workspace is its own git repo)
cd workspace  # This is actually a symlink to your workspace repo
git add .
git commit -m "Update threads"
git push
```

No need to update the parent repo - the symlink keeps them completely separate!
