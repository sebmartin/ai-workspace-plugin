# AI Workspace Template

A structured workspace for AI-assisted development with Claude Code. Manage long-running discussions, track decisions, and maintain context across sessions.

## Features

- **🧵 Thread-based discussions** - Organize work into self-contained threads that persist across days/weeks/months
- **🎭 Custom AI personas** - Switch perspectives with slash commands (`/architect`, `/product-strategist`, etc.)
- **📝 Decision tracking** - Log architectural decisions with automatic context updates
- **✅ TODO management** - Track tasks within threads with auto-archiving
- **📸 Snapshots** - Generate shareable summaries for teammates
- **🔗 Linked threads** - Connect related discussions

## Quick Start

See [SETUP.md](SETUP.md) for detailed installation instructions.

```bash
# 1. Clone this template
git clone <this-repo-url> my-ai-workspace
cd my-ai-workspace

# 2. Run setup
./setup.sh

# 3. Start a new thread!
/threads create
```

## Available Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| **Threads** | `/threads` | Create, resume, snapshot discussion threads |
| **TODOs** | `/later` | Track tasks within threads |
| Architect | `/architect` | System design, scalability, technical architecture |
| Devil's Advocate | `/devils-advocate` | Challenge ideas, find flaws |
| Product Strategist | `/product-strategist` | User value, market fit |
| Tech Advisor | `/tech-advisor` | Technology choices, frameworks |
| Cost Analyzer | `/cost-analyzer` | Infrastructure costs, ROI |
| Security Reviewer | `/security-reviewer` | Threat modeling, vulnerabilities |

## Workflow

### Start a new thread

```bash
# Create a new thread for your project
/threads create my-new-thread

# Add attachments - copy files into the thread's `attachments` directory to include into the thread context

# Work on it - context automatically persists

# Track tasks
/later create feature-implementation
/later add "Build API endpoint"
/later complete "Build API endpoint"

# Log important decisions
/threads log-decision

# Generate a snapshot to share
/threads snapshot

# Save persist the current thread context to disk
/threads save
```

**Manage threads with `/threads` commands:**
- `/threads` - List all available threads (when starting something new)
- `/threads resume <name>` - Switch to a different thread mid-session
- `/threads save` - Explicitly save current progress to thread README
- `/threads snapshot` - Generate a shareable summary

## Resuming Threads

Choose the right approach based on your scenario:

### When Starting Claude (Recommended)

**Use Claude Code's built-in session management to preserve full context:**

```bash
# Continue your last conversation (maintains full context including active thread)
claude --continue

# Or choose from previous sessions
claude --resume
```

**Why this works best:**
- ✅ Continues the entire conversation context, not just thread metadata
- ✅ Preserves your active thread across sessions automatically
- ✅ Much faster - no need to reload thread READMEs
- ✅ Works even after multiple context window compactions

### Within an Active Session

**Use `/threads resume` to switch between threads mid-session:**

```bash
# Switch to a different thread while Claude is running
/threads resume other-thread
```

**When to use:** You're already in a conversation and want to switch focus to a different thread.

### Anti-Pattern to Avoid

❌ **Don't:** Start a fresh Claude session, then immediately `/threads resume`

This loses the conversation context from your previous work. Instead, use `claude --continue` or `claude --resume <id>` when launching Claude.


## Directory Structure

```
ai-workspace/
├── .claude/skills/       # Custom AI personas
│   ├── threads/          # Thread management
│   ├── later/            # TODO tracking
│   ├── architect/
│   └── ...
├── templates/            # Reusable templates
├── workspace/            # Your private workspace (gitignored)
│   └── threads/
│       └── {thread-name}/
│           ├── README.md     # Thread overview
│           ├── sessions/     # Session logs
│           ├── decisions/    # Decision docs
│           ├── todos/        # Task lists
│           ├── attachments/  # Input files
│           └── artifacts/    # Generated outputs
├── SETUP.md
└── README.md             # This file
```

## Key Concepts

**Threads** - Self-contained discussions with their own README, sessions, decisions, and artifacts. Create one per project or major topic.

**README as Landing Page** - Each thread's README stays brief (problem, current focus, next steps). Detailed content lives in subdirectories.

**Snapshots vs README** - README is the living document. Snapshots are timestamped artifacts for sharing externally.

**Artifacts vs Attachments** - Attachments are inputs (your sketches, references). Artifacts are outputs (generated snapshots, refined diagrams).

**Auto-archiving** - Completed TODO lists automatically move to `todos/complete/` to keep your workspace clean.

## Privacy & Security

This template includes **automatic protection** for your private workspace:

### Git Hooks (via pre-commit)

Installed by `./setup.sh`, these hooks prevent:
- ✅ Committing workspace/ files to the public template
- ✅ Pushing workspace/ files accidentally
- ✅ Leaking private work to public repositories

### How It Works

**3-layer protection:**
1. `.gitignore` excludes `workspace/*` (except .keep and README.md)
2. Pre-commit hook blocks staging workspace/ files
3. Pre-push hook provides final safety check

**Automatic setup:**
```bash
./setup.sh  # Installs hooks using pre-commit framework
```

### Why Separate Workspace?

- **Privacy**: The `workspace/` directory is ignored by the public template repo
- **Clean updates**: Pull template updates without affecting your workspace contents
- **Optional backup**: Make `workspace/` a nested private git repo for version control
- **Separation**: Your workspace data never commits to the public template repo

## Contributing

This is a template - fork it and make it your own! Contributions welcome:
- New skills
- Better templates
- Workflow improvements

## License

MIT
