# Command: create a thread

- Ask for thread name if not provided (must be kebab-case)
- Call `mcp__plugin_ai-workspace_threads__create_thread(workspace_dir, thread_name)` — handles validation, directory structure, and README creation. Handle `Status: AMBIGUOUS_WORKSPACE` or `Status: NEEDS_INIT` by relaying the embedded question and following the suggested follow-up actions.
- Optionally help fill in the About section (what this thread is about, goal or context)
- Confirm creation and show path to README.md
