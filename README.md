# AI Workspace Plugin

A Claude Code plugin for managing long-running conversations with Claude.

**Threads** are the core concept. A thread is a persistent, topic-focused conversation — a brainstorming session, a design discussion, a research topic — that survives across multiple Claude sessions. Conversation history is stored as a set of linked Markdown files on disk rather than held in Claude's context window, where details get lost to compaction. The thread README acts as an index into session logs, decisions, and artifacts. Claude loads only what it needs, keeping the active context small without sacrificing detail over time.

## Installation

Install via the Claude Code marketplace:

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

Then initialize a workspace:

```bash
cd ~/my-workspace
/ai-workspace:init
```

`/ai-workspace:init` creates `threads/`, `.claude/settings.json`, and `CLAUDE.md` in your workspace directory.

## Usage

You can use explicit commands or just describe what you want in plain English — Claude understands both.

Start a thread for a design session:

```bash
/ai-workspace:threads create api-redesign
# or: "start a new thread called api-redesign"
```

Work with Claude, then manage context as you go:

```bash
# Log an important decision
/ai-workspace:threads log-decision
# or: "log this decision"

# Park a follow-up to handle later
/ai-workspace:threads park "investigate caching options"
# or: "park caching options for later"

# Save context before ending the session
/ai-workspace:threads save
# or: "save the thread"
```

Switch to a second thread mid-session (your first thread is preserved):

```bash
/ai-workspace:threads create auth-refactor
# or: "create a new thread for the auth refactor"
```

Generate a shareable summary from any thread:

```bash
/ai-workspace:threads snapshot
# or: "create a snapshot"
```

Pick it back up days later:

```bash
# Continue your last session (full context restored)
claude --continue

# Or reload a specific thread in a new context window
claude
/ai-workspace:threads resume api-redesign
# or: "resume the api-redesign thread"
```

Each thread maintains its own README, session logs, decision docs, and artifacts — all in `threads/` in your workspace directory.

## Thread Commands

| Command | Purpose |
|---------|---------|
| `/ai-workspace:threads` | List all threads |
| `/ai-workspace:threads create <name>` | Start a new thread |
| `/ai-workspace:threads resume <name>` | Switch to a thread mid-session |
| `/ai-workspace:threads save` | Update thread context |
| `/ai-workspace:threads snapshot` | Generate a shareable summary |
| `/ai-workspace:threads log-decision` | Record an architectural decision |
| `/ai-workspace:threads park "<topic>"` | Park a topic for later |
| `/ai-workspace:threads pop` | Resume the next parked topic |
| `/ai-workspace:threads parked` | List parked topics |
| `/ai-workspace:threads open <name>` | Open thread in Finder (macOS) |

## Agents

Agents run automatically when Claude delegates work to them:

| Agent | Purpose |
|-------|---------|
| **Architect** | System design, scalability, technical architecture |
| **Security Reviewer** | Threat modeling, vulnerability identification |
| **Product Strategist** | User value, market fit, prioritization |
| **Tech Advisor** | Technology choices, frameworks, migration paths |
| **Cost Analyzer** | Infrastructure costs, scaling economics, ROI |
| **Devil's Advocate** | Critical thinking, finding flaws in proposals |

## Thread Structure

After creating a thread, your workspace will have:

```
my-workspace/
├── threads/
│   └── {thread-name}/
│       ├── README.md        # Thread overview and current focus
│       ├── sessions/        # Session logs
│       ├── decisions/       # Decision docs
│       ├── attachments/     # Input files
│       └── artifacts/       # Generated outputs (snapshots, reports)
└── .claude/
    └── settings.json        # Auto-generated settings
```

## Privacy

Threads are stored locally and not committed to git by default. To keep them private:

```
# .gitignore
threads/
.claude/settings.json
```

## Plugin Development

```
ai-workspace-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── agents/                  # AI personas
├── skills/
│   ├── common/
│   │   └── workspace_utils.py  # Shared utilities
│   ├── init/                # Workspace init skill
│   │   └── SKILL.md
│   └── threads/             # Thread management
│       ├── SKILL.md
│       └── scripts/
│           └── mcp_server.py   # FastMCP server
├── templates/               # Thread templates
└── tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development details.

## License

MIT
