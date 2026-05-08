# AI Workspace Plugin

Claude is great at long-running work: designing systems, researching decisions, planning projects. The problem is that sessions end. Context gets compacted. Next time you start fresh, you're re-explaining things you already figured out. Frontier models have memory features for this but they are opaque and stored on their infrastructure.

Threads aim to address that. A thread is a folder on disk: a README that stays current, session logs, decisions, and anything Claude generates. When you pick it back up, Claude reads what it needs and continues where you left off. Nothing lives only in a conversation window. And because threads are just Markdown files, any model can read them. No vendor lock-in, no proprietary format.

## Installation

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

Restart Claude Code after installing, then initialize a workspace:

```bash
cd ~/my-workspace
/ai-workspace:init
```

## Examples

Threads work for anything you'd want to revisit across sessions, not just code.

- [Planning and executing an architectural change](./docs/examples/architectural-change/): planning across sessions, execution across repos
- [Tracking accomplishments for promo and weekly sync](./docs/examples/career-growth/): custom skills, attachments, cross-thread context
- [Planning a cottage build](./docs/examples/cottage-build/): bylaw expert from PDFs, decision logging, draft emails

## How threads work

```
my-workspace/
├── threads/
│   └── {thread-name}/
│       ├── README.md        # Current focus, next steps, links to everything else
│       ├── sessions/        # One file per conversation
│       ├── decisions/       # Decisions with context and rationale
│       ├── attachments/     # Files you bring in (specs, docs, data)
│       └── artifacts/       # Files Claude generates (snapshots, reports, emails)
└── .claude/
    └── settings.json
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

When you have a proposal worth stress-testing, run a debate. A proponent makes the strongest honest case for the idea and refines it under pressure. A skeptic challenges specific assumptions, surfaces blind spots, and backs off when concerns are addressed. The result is saved as a thread artifact. See it used in the [architectural change example](./docs/examples/architectural-change/).

```bash
/ai-workspace:debate        # 2 rounds (default)
/ai-workspace:debate 3      # more rounds
```

Both agents can call in specialist agents to validate claims, and will ask you directly when they're uncertain.

### Specialist Agents

Install the `tech-expert-agents` plugin for a ready-made set:

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

## Custom Skills

Skills placed inside a thread directory are discovered by Claude Code when you're working in that context. The [career-growth example](./docs/examples/career-growth/) shows a skill that fetches activity from GitHub, Jira, and Slack. The [cottage-build example](./docs/examples/cottage-build/) shows one built from PDF attachments that answers bylaw questions automatically.

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
| `/ai-workspace:threads snapshot` | Generate a shareable summary |
| `/ai-workspace:threads log-decision` | Record a decision |
| `/ai-workspace:threads park "<topic>"` | Park a topic for later |
| `/ai-workspace:threads pop` | Resume the next parked topic |
| `/ai-workspace:threads parked` | List parked topics |
| `/ai-workspace:threads status <name>` | Show a thread's Quick Resume |
| `/ai-workspace:threads create-child <name>` | Create a child thread linked to the current thread |
| `/ai-workspace:threads link-parent <name>` | Set a parent thread (bidirectional) |
| `/ai-workspace:threads link-related <name>` | Link two threads as related |
| `/ai-workspace:threads open <name>` | Open thread in Finder (macOS) |
| `/ai-workspace:threads set-workspace <path>` | Set default workspace for cross-directory access |

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
