# Command: log a decision

- Use recent session context to draft a decision document
- Call `mcp__plugin_ai-workspace_threads__get_skill_file("templates/decision-template.md")` to get the template
- Create `threads/{name}/decisions/YYYYMMDD-title.md` with decision details. Fill in frontmatter: `title`, `status`, `summary`.
- Immediately update README.md Decisions section with a link — include a one-line description of what was decided
- Immediately update the current session log
- Show the relative path with `./` prefix (e.g., `./threads/foo/decisions/20260120-bar.md`) — user can cmd-click to review and edit directly
- Decision filename format: `YYYYMMDD-kebab-case-title.md`
