---
name: init
description: Initialize a new AI workspace in the current directory with proper structure, templates, and git hooks
---

# Init Skill

Initializes a new AI workspace in the current directory.

## What It Does

1. Creates `workspace/` directory structure (threads, templates)
2. Copies templates from plugin
3. Creates `.gitignore` for workspace privacy
4. Sets up `.claude/settings.local.json` with correct paths
5. Installs pre-commit hooks for workspace protection
6. Creates initial README.md

## Usage

```bash
mkdir ~/my-workspace && cd ~/my-workspace
claude
/ai-workspace:init
```

After initialization, run `./setup.sh` to install git hooks.

## Multiple Workspaces

You can create multiple workspaces that share the same plugin:

```bash
# Work workspace
mkdir ~/work-ai && cd ~/work-ai
/ai-workspace:init

# Personal workspace
mkdir ~/personal-ai && cd ~/personal-ai
/ai-workspace:init
```

Each workspace has:
- Own `workspace/` directory (private threads/context)
- Own `.claude/settings.local.json` (custom permissions)
- Shared plugin (installed once, used by both)

## Implementation

Run `scripts/init-workspace.py` which handles all setup steps automatically.

## What Gets Created

```
my-workspace/
├── workspace/
│   ├── threads/           # Discussion threads
│   └── templates/         # Templates copied from plugin
├── .claude/
│   └── settings.local.json  # Local configuration (gitignored)
├── .gitignore             # Protects settings.local.json
├── .pre-commit-config.yaml  # Pre-commit hooks config
├── setup.sh               # Git hooks installer
└── README.md              # Workspace documentation
```

## Environment Variable

After initialization, the workspace directory will be at `./workspace/`. To use a different location, set:

```bash
export AI_WORKSPACE_DIR=/path/to/workspace
```
