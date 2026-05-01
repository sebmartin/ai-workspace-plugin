# AI Workspace Plugin

A Claude Code plugin built around two ideas: **threads** for persisting long-running conversations across Claude sessions, and **debate** for forging stronger plans through structured agentic dialogue.

**Threads** keep your work alive across sessions. A thread is a persistent, topic-focused conversation stored as linked Markdown files on disk. Conversation history is written to disk and loaded selectively, not held in Claude's context window where details get lost to compaction. Each thread has its own README, session logs, decision records, and artifacts.

**Debate** helps you pressure-test a proposal before committing to it. Two agents run structured rounds of challenge and refinement: a proponent who stewards the idea and a skeptic who stress-tests it. Neither is trying to win. Both are trying to produce a stronger plan. The result is saved as a thread artifact you can act on.

> [!NOTE]
> This repo was recently refactored to support distribution as a Claude Code plugin. If you were using a prior version, follow the [migration plan](#migrating-from-the-pre-plugin-version) to move your threads over.

## Installation

Install via the Claude Code marketplace:

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

Restart Claude Code after installing for the plugin to take effect.

Then initialize a workspace:

```bash
cd ~/my-workspace
/ai-workspace:init
```

`/ai-workspace:init` creates `threads/`, `.claude/settings.json`, and `CLAUDE.md` in your workspace directory.

## Threads

A thread is a persistent, topic-focused workspace stored as linked Markdown files on disk. Instead of relying on Claude's context window (where details get lost to compaction), threads write conversation history, decisions, and artifacts to disk so they can be loaded selectively across sessions.

You don't need to memorize commands. You can use slash commands, or just tell Claude what you want in plain English. Claude knows which skill to invoke.

Start a thread for a design session:

```
/ai-workspace:threads create api-redesign
```
```
> start a new thread called api-redesign
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

Switch to a different thread mid-session (your first thread is preserved):

```
> resume the auth-refactor thread
```

Generate a shareable summary from any thread:

```bash
/ai-workspace:threads snapshot
# or: "create a snapshot"
```

Pick it back up days later:

```
> resume the api-redesign thread
```

Starting a fresh Claude session and resuming the thread gives you a clean context window with only the thread's state loaded in. This is often better than `claude --continue`, which restores the full prior conversation including stale context, failed attempts, and tangents that are no longer relevant. Threads capture the important parts (decisions, progress, next steps) and leave the noise behind.

### Thread Commands

| Command | Purpose |
|---------|---------|
| `/ai-workspace:threads` | List all threads |
| `/ai-workspace:threads create <name>` | Start a new thread |
| `/ai-workspace:threads create-child <name>` | Create a child thread linked to the current thread |
| `/ai-workspace:threads link-parent <name>` | Set a parent thread (bidirectional) |
| `/ai-workspace:threads link-related <name>` | Link two threads as related (bidirectional, symmetric) |
| `/ai-workspace:threads resume <name>` | Switch to a thread mid-session |
| `/ai-workspace:threads save` | Update thread context |
| `/ai-workspace:threads snapshot` | Generate a shareable summary |
| `/ai-workspace:threads log-decision` | Record an architectural decision |
| `/ai-workspace:threads park "<topic>"` | Park a topic for later |
| `/ai-workspace:threads pop` | Resume the next parked topic |
| `/ai-workspace:threads parked` | List parked topics |
| `/ai-workspace:threads status <name>` | Show a thread's Quick Resume |
| `/ai-workspace:threads open <name>` | Open thread in Finder (macOS) |
| `/ai-workspace:threads set-workspace <path>` | Set default workspace for cross-directory access |

## Two Ways to Work

You can run Claude Code from your workspace directory, or from any other repo. Both give you full access to your threads, but they suit different kinds of work.

### From the workspace: thinking and planning

Run Claude from your workspace when the work isn't tied to a single repo. Brainstorming, high-level architecture, multi-repo planning, career threads, research -- anything where the conversation is the primary output.

```bash
cd ~/my-workspace
claude
> resume the platform-architecture thread
```

Claude has direct access to all your threads, session logs, and artifacts. This is the natural home for open-ended thinking.

### From a repo: executing with thread context

Run Claude from a project repo when you're writing code but want the context of a thread. Maybe you planned an API redesign in a thread and now you're implementing it, or you captured decisions in a thread and need them while refactoring.

```bash
cd ~/my-project
claude
> resume the api-redesign thread
# → (Using threads from /Users/you/my-workspace)
# Claude now has the thread context AND your repo's code
```

The plugin automatically resolves your workspace. If the current directory has its own `threads/` folder, it uses that. Otherwise it falls back to your configured default. The first time you use threads from outside your workspace, the plugin will ask where your workspace is and remember it. You can change it later with `/ai-workspace:threads set-workspace <path>`.

## Debate

When you have a proposal worth pressure-testing, run a debate. The plugin invokes a **proponent** and a **skeptic** in alternating rounds. The proponent builds the strongest honest case for the idea and refines it under challenge. The skeptic counters specific assumptions, surfaces blind spots, and acknowledges when concerns are resolved. Both agents can invoke specialist agents (architect, security reviewer, etc.) to validate claims, and will pause to ask you directly when they are uncertain rather than making things up.

The debate extracts the proposal from your current thread or conversation. No setup needed.

```bash
/ai-workspace:debate        # 2 rounds (default)
/ai-workspace:debate 3      # more rounds
```

The result is saved as `threads/{name}/artifacts/debate-YYYYMMDD.md`. Requesting more rounds updates the same file rather than creating new ones.

### Specialist Agents

The debate agents will automatically draw on any subagents available in your Claude Code environment. Install the `tech-expert-agents` plugin for a ready-made set, or bring your own.

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

## Thread Structure

After creating a thread, your workspace will have:

```
my-workspace/
├── threads/
│   └── {thread-name}/
│       ├── README.md        # Thread index: current focus, open questions, links to everything else
│       ├── sessions/        # Log of each conversation session
│       ├── decisions/       # Recorded decisions with context and rationale
│       ├── attachments/     # Files you bring into the thread (specs, screenshots, exported data)
│       └── artifacts/       # Files Claude generates (snapshots, reports, diagrams)
└── .claude/
    └── settings.json        # Auto-generated settings
```

## Custom Agents and Skills

You can add your own agents and skills to any workspace. Claude Code loads `.claude/` directories based on scope, so placement controls who has access.

**Workspace-wide agents and skills**, available across all threads:

```
my-workspace/
└── .claude/
    ├── agents/
    │   └── my-agent.md
    └── skills/
        └── my-skill.md
```

**Thread-scoped skills.** Claude Code automatically discovers skills from nested `.claude/skills/` directories based on the current working directory. Skills placed inside a thread folder are picked up when you're working within that directory:

```
my-workspace/
└── threads/
    └── {thread-name}/
        └── .claude/
            └── skills/
                └── my-skill.md
```

Note: agents are only loaded from `.claude/agents/` at the workspace root (or `~/.claude/agents/` for user-level). Nested agent discovery is not yet supported.

## Migrating from the pre-plugin version

If you used the previous template-based version, your threads live in `workspace/threads/` inside the cloned repo. With the plugin model, your workspace is just a regular directory, not a clone of this repo.

Before starting, if you don't already have a backup of your threads, now is a good time to make one. Copy `workspace/threads/` somewhere safe or push it to a private repo.

**1. Install the plugin**

```
/plugin marketplace add sebmartin/ai-marketplace
/plugin install ai-workspace@sebmartin
```

Restart Claude Code after installing.

**2. Create a new workspace directory and initialize it**

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
