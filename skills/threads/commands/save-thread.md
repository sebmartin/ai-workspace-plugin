# Command: save-thread

Execute ALL steps in order. Do not skip any step.

---

## Step 1: Update README Quick Resume (REQUIRED)

Read `{Thread}/README.md`. Update the Quick Resume section:

- **Current focus**: rewrite to reflect where things stand right now
- **Next steps**: reorder so most pressing is first. Ideal 5 items, max 10. If over 10, ask the user which to remove or park before continuing.
- **Recent progress**: prepend a new entry for this session. Keep only the 3–5 most recent entries — drop the oldest. Format: `- [brief summary] (YYYY-MM-DD)`

Update `**Last Session**: [YYYY-MM-DD]` in the header to today's date.

Write the updated README back to disk.

---

## Step 2: README hygiene (REQUIRED)

Still working in `{Thread}/README.md`:

- **Inline content**: if any section contains substantive content that belongs in a linked artifact (workflow descriptions, design notes, architecture details, risk registers), offer to move it. Ask first — do not move silently.
- **Old format detection**: if the README has any of these sections — `## Problem`, `## Current State`, `## Desired State`, `## Existing Infrastructure`, `## Resolved Questions`, `## Notes` — say: "This README uses an older format. Want me to migrate it?" Wait for confirmation before making any changes.

---

## Step 3: Create or update the session log (REQUIRED)

Look for a session file in `{Thread}/sessions/` with today's date prefix (`YYYYMMDD-*.md`).

**If none exists**: call `mcp__plugin_ai-workspace_threads__get_skill_file("templates/thread-session-template.md")` to get the template. Create `{Thread}/sessions/YYYYMMDD-kebab-summary.md`. Fill in:
- Frontmatter: `date`, `summary` (up to 150 words of what was discussed), `keywords`, `next_context`
- Body: goal, key discussion points, decisions made, outcomes, next steps

**If one exists**: append new discussion points, decisions, and progress since the last save. Update the frontmatter `summary` and `next_context` to reflect the full session so far.

If the conversation covered several distinct topics, create one session file per topic group instead of one long file.

---

## Step 4: Link session in README (REQUIRED)

In `{Thread}/README.md`, under `### Sessions` in Resources, add a link to the session file if not already listed:

```
- [YYYYMMDD-session-name.md](./sessions/YYYYMMDD-session-name.md) — one-line description
```

Write the updated README back to disk.

---

## Step 5: Check for unlogged decisions (REQUIRED)

Review the conversation context for decisions that were made but not yet logged as decision files in `{Thread}/decisions/`.

A decision worth logging is any choice that: settles a meaningful question, constrains future work, or would need to be recalled when resuming. Trivial choices don't need logging.

If you find unlogged decisions, ask: "I noticed a decision about [topic] — want me to log it?" Do not create decision files silently. If the user confirms, use the `log-decision` command to create them and update the README Decisions section — do not ask again before updating the README.

---

## Done

Confirm to the user: "Saved — README and session log updated." List any decisions you flagged.
