# Workspace

This workspace uses the [ai-workspace plugin](https://github.com/sebmartin/ai-workspace) for thread-based conversation management.

## Threads

Threads are organized conversations stored in `threads/`. Each thread has its own README, session logs, decisions, and artifacts.

```bash
/ai-workspace:threads create <name>   # Start a new thread
/ai-workspace:threads resume <name>   # Resume a thread mid-session
/ai-workspace:threads                 # List all threads
```

Or just describe what you want — Claude understands natural language.
