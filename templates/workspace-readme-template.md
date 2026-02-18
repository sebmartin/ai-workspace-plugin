# AI Workspace

This is your private workspace directory - keep your work here!

## What Lives Here

All your personal AI-assisted work:
- `threads/` - Your discussion threads, one per project/topic
- Context, notes, and artifacts from AI sessions

## Privacy Protection

Git hooks automatically prevent committing workspace/ files to the public template repository. This ensures your private work stays private.

**Protected by:**
- `.gitignore` (excludes workspace/* from git)
- Pre-commit hook (blocks staging workspace files)
- Pre-push hook (final safety check)

## Usage

### Thread Management

```bash
# Create a new thread
/threads create my-project

# List all threads
/threads

# Resume a thread
/threads resume my-project

# Or resume the most recent
/threads resume last

# Create a snapshot to share
/threads snapshot
```

### Task Tracking

```bash
# Create a todo list
/later create feature-work

# Add tasks
/later add "Build API endpoint"
/later add "Write tests"

# Complete tasks
/later complete "Build API endpoint"

# List all todos
/later
```

## Backup (Optional but Recommended)

Consider making this directory a git repository for version control and backups:

```bash
cd workspace
git init
git add .
git commit -m "Initial workspace"

# Push to a private remote
git remote add origin git@github.com:YOUR-USERNAME/private-workspace.git
git push -u origin main
```

**Important**: Keep this repository **private** - it contains your personal work!

## Directory Structure

```
workspace/
├── README.md          # This file
├── threads/           # Discussion threads
│   └── {thread-name}/
│       ├── README.md      # Thread overview
│       ├── sessions/      # Session logs
│       ├── decisions/     # Decision documents
│       ├── todos/         # Task lists
│       ├── attachments/   # Input files
│       └── artifacts/     # Generated outputs
└── .keep              # Git marker file
```

## Getting Started

1. Run `/threads create` to start your first thread
2. Work with Claude Code on your project
3. Context automatically persists across sessions
4. Use `/threads save` to update the thread README
5. Share progress with `/threads snapshot`

## Tips

- **One thread per topic**: Create separate threads for different projects or major features
- **Regular saves**: Use `/threads save` after significant progress
- **Track tasks**: Use `/later` to keep track of what needs to be done
- **Log decisions**: Use `/threads log-decision` to document important choices
- **Generate snapshots**: Use `/threads snapshot` when you need to share progress with others

Happy building! 🚀
