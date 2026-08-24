# Command: create a thread

- Ask for thread name if not provided (must be kebab-case)
- Call `mcp__plugin_ai-workspace_threads__create_thread(workspace_dir, thread_name)` — handles validation, directory structure, and README creation. On `AMBIGUOUS_WORKSPACE` or `NEEDS_INIT`, put the choice to the user; the paths are in the reply and the skill says what each means.
- Optionally help fill in the About section (what this thread is about, goal or context)
- Confirm creation and show path to README.md
