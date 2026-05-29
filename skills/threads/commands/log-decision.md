# Command: log a decision

- Use recent session context to draft a decision document
- Call `mcp__plugin_ai-workspace_threads__get_template(template_name="decision-template.md")` to get the template
- Create `threads/{name}/decisions/YYYYMMDD-title.md` with decision details. Fill in frontmatter: `title`, `status`, `summary`.
- Show relative path with `./` prefix (e.g., `./threads/foo/decisions/20260120-bar.md`) — user can cmd-click to review in editor
- After user confirms it's good:
  - Update README.md Quick Resume and the Decisions section with a link — include a one-line description of what was decided
  - Update current session log
- Decision filename format: `YYYYMMDD-kebab-case-title.md`
