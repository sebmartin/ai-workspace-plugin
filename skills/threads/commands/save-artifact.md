# Command: artifact

Create a named artifact — a summary, analysis, spec, diagram, or any output worth keeping and linking from the thread.

Artifacts are for content that needs to persist beyond the conversation: something to share, reference later, or hand off. If the user asks to summarize something for someone else, produce a design, write a spec, or capture an analysis — that's an artifact.

## Naming

```
YYYYMMDD-{type}-{kebab-keywords}.md
```

- `{type}` = kind of artifact (e.g., `spec`, `analysis`, `diagram`, `comparison`, `summary`)
- `{kebab-keywords}` = short descriptive phrase
- Examples: `20260316-summary-auth-flow.md`, `20260308-analysis-db-migration-options.md`

This convention also applies to `decisions/` and `sessions/`.

## Subdirectories

Use subdirectories within `artifacts/` when generating multiple related files. Don't force it for a single file.

## Registration (REQUIRED)

Every time you create an artifact, immediately:

1. Add it to the session log under `### Created Artifacts` (create the section if missing)
2. Add it to the thread's README.md under `### Artifacts` in Resources (create the section if missing)

Format for README entry:
```
 - [Artifact Title](./artifacts/YYYYMMDD-filename.md) -- one-line description of what it contains
```

The description is required — never add a bare link.
