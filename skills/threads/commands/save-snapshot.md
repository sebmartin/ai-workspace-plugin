# Commands: save, snapshot

## Save thread context (`/threads save`)

- Update README.md Quick Resume section with current context
- Create or update the session log for this invocation:
  1. Look for a session file in `sessions/` with today's date prefix (`YYYYMMDD-*.md`)
  2. If none exists: call `mcp__plugin_ai-workspace_threads__get_template(template_name="thread-session-template.md")` to get the template, then create `YYYYMMDD-kebab-summary.md` filled with current conversation context (goal, key points, decisions, next steps). Fill in the frontmatter: `date`, `summary`, `keywords`, `next_context`.
  3. If one exists: update it — append new discussion points, decisions, and progress since last save
  4. Link the session file in README.md Resources > Sessions if not already listed
- A session loosely maps to a single CLI invocation: one file per conversation, updated on each save
- If the conversation covered several distinct topics, split it into one session file per topic group rather than one long file — use a descriptive kebab-case name for each (`YYYYMMDD-topic-name.md`)
- Does NOT generate a snapshot (use `/threads snapshot` for that)
- **README hygiene on every save**:
  - **Next steps**: keep in logical execution order, most pressing first. Ideal is 5 items, max 10. If over 10, ask which to remove or park before saving.
  - **Recent progress**: newest entry first, oldest last. Keep the 3–5 most recent entries; drop the oldest when adding a new one — they already live in session logs.
  - **Inline content**: if any section contains more than a few sentences or bullet points of substantive content (workflow descriptions, design details, architecture notes, risk registers, etc.), offer to move it to a linked artifact. Do not do this silently — ask first.
  - **Old format detection**: if the README has sections from the old template (`## Problem`, `## Current State`, `## Desired State`, `## Existing Infrastructure`, `## Resolved Questions`, `## Notes`), flag it: "This README uses an older format. Want me to migrate it? I'll fold Problem/Current State/Desired State into an `## About` section, move any substantive content in other sections to artifacts, and remove the empty ones." Wait for confirmation before changing anything.

## Create a snapshot (`/threads snapshot`)

- If thread name is provided: use that thread. If not: list threads with numbers, ask which to snapshot, wait for reply.
- Read the thread's README.md, recent sessions, and decisions
- Also include current conversation context (unpersisted work in this session)
- First update README.md Quick Resume with latest context
- Generate: `threads/{name}/artifacts/YYYYMMDD-snapshot-{keywords}.md`
  - `{keywords}` = short kebab-case phrase (e.g., `auth-flow-design`, `mvp-scope`)
- Show relative path for user to review in editor
- Follow the Registration rule (see `commands/artifact-conventions.md`): add to session log and README immediately
