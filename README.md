# AI Workspace Plugin

Claude is great at long-running work: designing systems, researching decisions, planning projects. The problem is that sessions end. Context gets compacted. Next time you start fresh, you're re-explaining things you already figured out. Frontier models have memory features for this but they are opaque and stored on their infrastructure.

Threads aim to address that. A thread is a folder on disk: a README that stays current, session logs, decisions, and anything Claude generates. When you pick it back up, Claude reads what it needs and continues where you left off. Nothing lives only in a conversation window. And because threads are just Markdown files, any model can read them. No vendor lock-in, no proprietary format.

## Installation

The plugin ships for both Claude Code and OpenAI Codex CLI from a single source. Threads, MCP server, and templates are shared; each CLI installs through its native plugin system.

### Claude Code

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

Restart Claude Code after installing.

### Codex CLI (Beta)

> [!WARNING]
> Codex support is in beta. Core skills (init, threads, debate) work, but skill instruction-following varies by model — some commands may require natural language instead of slash commands. Please report issues.

```
codex plugin marketplace add sebmartin/ai-workspace-plugin
codex
/plugins
```

Select `ai-workspace` and install.

### Initialize a workspace

```bash
cd ~/my-workspace

# Claude Code
/ai-workspace:init

# Codex CLI
> initialize the ai-workspace
```

`init` creates `threads/`, `AGENTS.md` (read by both), `CLAUDE.md` (a one-line `@AGENTS.md` import for Claude), and `.claude/settings.json` (Claude-only permission allowlist; Codex ignores). All files are vendor-safe.

## Examples

Threads work for anything you'd want to revisit across sessions, not just code.

- [Planning and executing an architectural change](./docs/examples/architectural-change/README.md): planning across sessions, execution across repos
- [Tracking accomplishments for promo and weekly sync](./docs/examples/career-growth/README.md): custom skills, attachments, cross-thread context
- [Planning a cottage build](./docs/examples/cottage-build/README.md): bylaw expert from PDFs, decision logging, draft emails

## How threads work

```
my-workspace/
├── AGENTS.md                # Workspace instructions (read by Claude and Codex)
├── CLAUDE.md                # One-line "@AGENTS.md" import (Claude only)
├── threads/
│   └── {thread-name}/
│       ├── README.md        # Status, next steps, written for you, not the assistant
│       ├── schema-version   # Which on-disk schema this thread uses
│       ├── todos/           # Backlog items with room for their own notes
│       ├── sessions/        # One file per conversation
│       ├── decisions/       # Decisions with context and rationale
│       ├── attachments/     # Files you bring in (specs, docs, data)
│       ├── artifacts/       # Files the CLI generates (snapshots, reports, emails)
│       └── *-index.md       # One line per item; what the assistant reads
└── .claude/
    └── settings.json        # Claude-only permission allowlist
```

You can run Claude from your workspace or from any repo. The plugin finds your threads either way.

```bash
cd ~/my-project
claude
> resume the api-redesign thread
# → (Using threads from /Users/you/my-workspace)
```

### Context loads on demand

Thread files are organized as a hierarchy of linked Markdown documents. When resuming a thread, Claude only reads the main thread summary and then follows links as needed, loading more context on demand rather than all at once. A thread can grow large over time and still start light. This also reduces hallucinations: instead of working from a vague summary, Claude can follow a link to the actual source when precision matters.

### Start fresh, pick up where you left off

A good habit is to save the thread at a natural stopping point, then start a fresh Claude session. Resume the thread and ask "where were we?" Claude reads the thread summary and the last session log, giving you a clean starting point without the cruft that accumulates in long conversations: failed attempts, tangents, superseded ideas. The important things are saved. Everything else is gone. This keeps token usage down and the context window clean.

## Debate

When you have a proposal worth stress-testing, run a debate. A proponent makes the strongest honest case for the idea and refines it under pressure. A skeptic challenges specific assumptions, surfaces blind spots, and backs off when concerns are addressed. The result is saved as a thread artifact. See it used in the [architectural change example](./docs/examples/architectural-change/README.md).

```bash
/ai-workspace:debate        # 2 rounds (default)
/ai-workspace:debate 3      # more rounds
```

Both agents can call in specialist agents to validate claims, and will ask you directly when they're uncertain.

### Specialist Agents

Install the [`tech-expert-agents`](https://github.com/sebmartin/ai-marketplace/tree/main/plugins/tech-expert-agents) plugin for a ready-made set:

```
/plugin install tech-expert-agents@sebmartin
```

| Agent | Used for |
|-------|---------|
| **Architect** | System design and scalability assumptions |
| **Security Reviewer** | Security risks and threat modeling |
| **Tech Advisor** | Technology choice trade-offs |
| **Cost Analyzer** | Infrastructure cost and ROI assumptions |
| **Product Strategist** | User value and market assumptions |

On Codex CLI: Codex's plugin manifest cannot bundle subagents yet, so `tech-expert-agents` is not installable as a plugin. The `init` skill installs the proponent and skeptic agents directly into `~/.codex/agents/`; specialist personas can be added there manually as `.toml` files until plugin-agent distribution lands.

## Custom Skills

Skills placed inside a thread directory are discovered by Claude Code when you're working in that context. The [career-growth example](./docs/examples/career-growth/README.md) shows a skill that fetches activity from GitHub, Jira, and Slack. The [cottage-build example](./docs/examples/cottage-build/README.md) shows one built from PDF attachments that answers bylaw questions automatically.

```
threads/{thread-name}/.claude/skills/my-skill.md
```

Workspace-wide skills go in `.claude/skills/` at the workspace root.

Note: agents are only loaded from `.claude/agents/` at the workspace root or `~/.claude/agents/`. Nested agent discovery is not yet supported.

## Commands

You don't need to memorize these. You can tell Claude what you want in plain English. But they're here if you want them.

| Command | Purpose |
|---------|---------|
| `/ai-workspace:threads` | List all threads |
| `/ai-workspace:threads create <name>` | Start a new thread |
| `/ai-workspace:threads resume <name>` | Switch to a thread mid-session |
| `/ai-workspace:threads save` | Update thread context |
| `/ai-workspace:threads summarize this for <person>` | Write a standalone summary as an artifact |
| `/ai-workspace:threads log-decision` | Record a decision |
| `/ai-workspace:threads park "<topic>"` | Park a topic for later |
| `/ai-workspace:threads unpark "<topic>"` | Move a parked topic back to the active backlog |
| `/ai-workspace:threads parked` | List parked topics |
| `/ai-workspace:threads create-child <name>` | Create a child thread linked to the current thread |
| `/ai-workspace:threads link-parent <name>` | Set a parent thread (bidirectional) |
| `/ai-workspace:threads link-related <name>` | Link two threads as related |
| `/ai-workspace:threads open <name>` | Open the thread folder in the file manager |
| `/ai-workspace:threads set-workspace <path>` | Set default workspace for cross-directory access |
| `/ai-workspace:threads archive <name>` | Move a thread to archive/ |
| `/ai-workspace:threads restore <name>` | Move an archived thread back to threads/ |
| `/ai-workspace:threads list-archived` | Show archived threads |
| `/ai-workspace:threads unpack-legacy-archive <file>` | Restore a `.tar.gz` archive made before 3.0 |

## Archiving Old Threads

When a thread has run its course, move it out of the way:

```bash
/ai-workspace:threads archive my-old-project
# → Moves threads/my-old-project to archive/my-old-project
```

Nothing is compressed or deleted. An archived thread is read-only until it is restored. Browse archived threads with `/ai-workspace:threads list-archived`, and bring one back with:

```bash
/ai-workspace:threads restore my-old-project
# → Moves it back to threads/my-old-project
```

Archives made before 3.0 are `.tar.gz` files, which `restore` does not unpack. Use `/ai-workspace:threads unpack-legacy-archive` for those.

If you ask to resume or find a thread that isn't in your active threads, Claude will check the archive and offer to restore it if found.

On Codex CLI, invoke a skill with `$` and its name: `$threads`, `$threads create <name>`, and so on. Or just describe what you want in plain English, which also works for init: `> initialize the ai-workspace`.

## Migrating from the pre-plugin version

> [!NOTE]
> This section is only relevant if you used the previous template-based version before the plugin refactor.

Your threads live in `workspace/threads/` inside the cloned repo. Back up your threads first, then:

**1. Install the plugin**

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

**2. Create a new workspace and initialize it**

```bash
mkdir ~/my-workspace
cd ~/my-workspace
/ai-workspace:init
```

**3. Move your threads over**

```bash
mv ~/ai-workspace/workspace/threads/* ~/my-workspace/threads/
```

## Plugin Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development details.

## License

MIT
