# Artifact Conventions

## Naming

All generated files in `artifacts/` use a date prefix:

```
YYYYMMDD-{type}-{kebab-keywords}.md
```

- `{type}` = kind of artifact (e.g., `snapshot`, `spec`, `analysis`, `diagram`, `comparison`)
- `{kebab-keywords}` = short descriptive phrase
- Examples: `20260316-snapshot-auth-flow-design.md`, `20260308-analysis-db-migration-options.md`

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

The description is required — never add a bare link. This applies to ALL artifacts: snapshots, proposals, analyses, diagrams, specs.
