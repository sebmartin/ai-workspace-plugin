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

# 2. Set up your private workspace repo (see SETUP.md)
# Create/clone your workspace repo, then symlink it:
ln -s /path/to/your-workspace workspace

# 3. Restart Claude Code and start using it!
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

```bash
# Create a new thread for your project
/threads create

# Work on it - context automatically persists

# Track tasks
/later create feature-implementation
/later add "Build API endpoint"
/later complete "Build API endpoint"

# Log important decisions
/threads log-decision

# Generate a snapshot to share
/threads snapshot
```

## Directory Structure

```
ai-workspace/
├── .claude/skills/       # Custom AI personas
│   ├── threads/          # Thread management
│   ├── later/            # TODO tracking
│   ├── architect/
│   └── ...
├── templates/            # Reusable templates
├── workspace/            # Symlink to your private repo (gitignored)
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

## MCP Servers: Under the Hood

This workspace leverages **Model Context Protocol (MCP) servers** to make repeated operations efficient and consistent. Instead of Claude parsing natural language instructions every time you list threads or check TODO status, MCP servers provide direct procedure calls that:

- **Save LLM tokens** - Executing `mcp__threads__listThreads` uses ~10 tokens vs ~500+ tokens to explain, search, parse, and format the same information
- **Improve consistency** - Structured procedures return predictable results every time
- **Enable stateful features** - Thread sorting by modification time, TODO completion counts, and session tracking work reliably across invocations
- **Speed up common operations** - No need to re-explain formatting on every list/show command

Think of MCP servers as the "API layer" between Claude and your workspace - they turn repetitive natural language patterns into optimized procedure calls.

See `mcp-servers/` and `.mcp.json` for the `threads` and `later` servers that power `/threads` and `/later` skills.

## Why a Symlink?

- **Separation**: Keep your private work completely separate from the public template
- **Privacy**: Your workspace is a separate repository with sensitive user data - keep it private and don't leak private data out of this directory
- **Clean updates**: Pull template updates without affecting your workspace
- **Skills are symlink-aware**: All built-in skills handle symlinked workspaces automatically

## Contributing

This is a template - fork it and make it your own! Contributions welcome:
- New skills
- Better templates
- Workflow improvements

## License

MIT
