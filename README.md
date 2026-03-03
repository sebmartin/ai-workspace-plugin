# AI Workspace Plugin

A Claude Code plugin for managing long-running AI-assisted development projects with thread-based organization, specialized agents, and decision tracking.

## Features

- **🧵 Thread management** - Organize work into self-contained threads that persist across days/weeks/months
- **🎭 Specialized agents** - Get expert perspectives from architect, security-reviewer, product-strategist, and more
- **📝 Decision tracking** - Log architectural decisions with automatic context updates
- **📸 Snapshots** - Generate shareable summaries for teammates
- **🔗 Linked threads** - Connect related discussions
- **🚀 Multi-workspace support** - Share one plugin across work and personal projects

## Quick Start

### Installation

**Option 1: Direct from GitHub (coming soon)**
```bash
/plugin marketplace add yourusername/ai-workspace-plugin
/plugin install ai-workspace@yourusername-ai-workspace-plugin
```

**Option 2: Local development**
```bash
git clone <this-repo-url> ~/ai-workspace-plugin
export CLAUDE_PLUGIN_DIR=~/ai-workspace-plugin
```

### Create Your First Workspace

```bash
# Create a new workspace directory
mkdir ~/my-ai-workspace
cd ~/my-ai-workspace

# Initialize it
claude
/ai-workspace:init

# Install git hooks for workspace protection
./setup.sh

# Create your first thread
/ai-workspace:threads create my-project
```

## Available Skills

All skills are namespaced under `ai-workspace:`:

| Skill | Command | Purpose |
|-------|---------|---------|
| **Init** | `/ai-workspace:init` | Initialize a new workspace in current directory |
| **Threads** | `/ai-workspace:threads` | Create, resume, snapshot discussion threads |

### Thread Commands

```bash
# List all threads
/ai-workspace:threads

# Create a new thread
/ai-workspace:threads create my-thread

# Resume a thread (switch mid-session)
/ai-workspace:threads resume my-thread

# Save current progress
/ai-workspace:threads save

# Create a snapshot for sharing
/ai-workspace:threads snapshot

# Log an important decision
/ai-workspace:threads log-decision

# Park a topic for later
/ai-workspace:threads park "investigate performance issue"

# Pop the next parked topic
/ai-workspace:threads pop

# List parked topics
/ai-workspace:threads parked

# Open thread in Finder (macOS)
/ai-workspace:threads open my-thread
```

## Available Agents

Agents run automatically when Claude delegates work to them:

| Agent | Purpose |
|-------|---------|
| **Architect** | System design, scalability, technical architecture |
| **Security Reviewer** | Threat modeling, vulnerability identification |
| **Product Strategist** | User value, market fit, prioritization |
| **Tech Advisor** | Technology choices, frameworks, migration paths |
| **Cost Analyzer** | Infrastructure costs, scaling economics, ROI |
| **Devil's Advocate** | Critical thinking, finding flaws in proposals |

## Multi-Workspace Setup

Share the plugin across multiple workspaces (work + personal):

```bash
# Work workspace
mkdir ~/work-ai && cd ~/work-ai
claude
/ai-workspace:init

# Personal workspace
mkdir ~/personal-ai && cd ~/personal-ai
claude
/ai-workspace:init
```

Each workspace has:
- Own `workspace/` directory (private threads/context)
- Own `.claude/settings.local.json` (custom permissions)
- Shared plugin (installed once, used by both)

## Workspace Structure

After running `/ai-workspace:init`, your workspace will have:

```
my-workspace/
├── .claude/
│   └── settings.local.json  # Local config (gitignored)
├── workspace/
│   ├── threads/             # Your discussion threads
│   │   └── {thread-name}/
│   │       ├── README.md    # Thread overview
│   │       ├── sessions/    # Session logs
│   │       ├── decisions/   # Decision docs
│   │       ├── attachments/ # Input files
│   │       └── artifacts/   # Generated outputs
│   └── templates/           # Project templates
├── hooks/                   # Git hooks for privacy
├── .gitignore              # Protects workspace/
├── .pre-commit-config.yaml # Pre-commit configuration
├── setup.sh                # Git hooks installer
└── README.md               # Workspace documentation
```

## Environment Variables

- `AI_WORKSPACE_DIR` - Override workspace location (default: `./workspace/`)

```bash
export AI_WORKSPACE_DIR=/path/to/workspace
```

## Thread Workflow

### Starting a New Thread

```bash
/ai-workspace:threads create api-redesign

# Work on it - context automatically persists

# Log important decisions
/ai-workspace:threads log-decision

# Park items for later
/ai-workspace:threads park "investigate caching options"

# Generate a snapshot to share
/ai-workspace:threads snapshot

# Save context
/ai-workspace:threads save
```

### Resuming Threads

**When starting Claude (recommended):**
```bash
# Continue your last conversation (maintains full context)
claude --continue

# Or choose from previous sessions
claude --resume
```

**Within an active session:**
```bash
# Switch to a different thread
/ai-workspace:threads resume other-thread
```

## Privacy & Security

The plugin includes automatic workspace protection:

### Git Hooks
Installed by `./setup.sh`, these prevent:
- ✅ Committing workspace/ files
- ✅ Pushing workspace/ files accidentally
- ✅ Leaking private work

### 3-Layer Protection
1. `.gitignore` excludes `workspace/*`
2. Pre-commit hook blocks staging workspace/ files
3. Pre-push hook provides final safety check

## Plugin Development

### Directory Structure

```
ai-workspace-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── agents/                  # AI personas
│   ├── architect.md
│   ├── security-reviewer.md
│   ├── product-strategist.md
│   ├── tech-advisor.md
│   ├── cost-analyzer.md
│   └── devils-advocate.md
├── skills/
│   ├── common/
│   │   └── workspace_utils.py  # Shared utilities
│   ├── init/                   # Workspace initialization
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── init-workspace.py
│   │   └── resources/          # Templates for new workspaces
│   │       ├── gitignore.template
│   │       ├── settings.local.json.template
│   │       ├── setup.sh
│   │       ├── pre-commit-config.yaml
│   │       └── hooks/
│   └── threads/                # Thread management
│       ├── SKILL.md
│       └── scripts/
│           ├── list-threads.py
│           └── get-thread-status.py
└── templates/               # Thread templates
    ├── thread-template.md
    ├── thread-session-template.md
    ├── snapshot-template.md
    ├── adr-template.md
    └── feature-spec.md
```

## Contributing

Contributions welcome! This plugin is designed to be extensible:
- Add new skills in `skills/`
- Add new agents in `agents/`
- Improve templates in `templates/`
- Enhance workspace utilities in `skills/common/`

## License

MIT
