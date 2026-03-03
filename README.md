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

```bash
# Clone the repository
git clone https://github.com/sebmartin/ai-workspace-plugin ~/ai-workspace

# Load the plugin when starting Claude
cd ~/my-workspace
claude --plugin-dir ~/ai-workspace
```

### Create Your First Thread

```bash
# Navigate to your project directory
cd ~/my-project

# Load the plugin and create a thread
claude --plugin-dir ~/ai-workspace
/ai-workspace:threads create my-first-thread
# ✓ Created threads/my-first-thread/
```

The `threads/` directory is created automatically on first use.

## Available Skills

All skills are namespaced under `ai-workspace:`:

| Skill | Command | Purpose |
|-------|---------|---------|
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
cd ~/work-ai
claude --plugin-dir ~/ai-workspace
/ai-workspace:threads create ...

# Personal workspace
cd ~/personal-ai
claude --plugin-dir ~/ai-workspace
/ai-workspace:threads create ...
```

Each workspace has:
- Own `threads/` directory (private threads/context)
- Own `.claude/settings.json` (auto-generated on first use)
- Shared plugin (installed once, used by both)

## Directory Structure

After creating your first thread, your workspace will have:

```
my-project/
├── threads/                 # Your discussion threads
│   └── {thread-name}/
│       ├── README.md        # Thread overview
│       ├── sessions/        # Session logs
│       ├── decisions/       # Decision docs
│       ├── attachments/     # Input files
│       └── artifacts/       # Generated outputs
└── .claude/
    └── settings.json        # Auto-generated settings
```

**Optional:** Add `.gitignore` to protect thread privacy:
```
threads/
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

**Thread privacy:**
- Threads are stored locally in `threads/` directory
- Not committed to git by default (no .gitignore created)
- Add `.gitignore` manually if you want git protection

**Recommended .gitignore:**
```
threads/
.claude/settings.json
```

## Plugin Development

### Directory Structure

```
ai-workspace/
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
│   │   ├── workspace_utils.py  # Shared utilities
│   │   └── resources/
│   │       └── settings.json.template
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
