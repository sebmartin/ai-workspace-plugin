#!/usr/bin/env python3
"""Generate Codex .toml agent files from canonical Claude .md agent files.

Reads each `agents/*.md` (Claude format: YAML frontmatter + markdown body),
emits a parallel `.codex-plugin/agents/{name}.toml` (Codex format: TOML with
`name`, `description`, and `developer_instructions` from the markdown body).

The markdown body is the single source of truth for persona prose. This script
keeps the Codex side in sync without manual duplication. Run it whenever an
agent .md file changes (e.g. as a pre-commit step or before release).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"
CODEX_AGENTS_DIR = REPO_ROOT / ".codex-plugin" / "agents"


def parse_md_agent(path: Path) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, markdown body) from a Claude agent file."""
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path} is missing YAML frontmatter")

    _, frontmatter_raw, body = text.split("---\n", 2)
    frontmatter: dict[str, str] = {}
    for line in frontmatter_raw.strip().splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()

    return frontmatter, body.lstrip("\n").rstrip() + "\n"


def toml_escape_triple_string(s: str) -> str:
    """Escape a string for use inside TOML triple-quoted literal."""
    # TOML basic multi-line strings use triple double-quotes. We need to escape
    # any standalone triple-quote sequence in the body. Backslashes inside basic
    # strings are escape characters, so escape those too.
    return s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def render_toml(name: str, description: str, developer_instructions: str) -> str:
    escaped_instructions = toml_escape_triple_string(developer_instructions)
    return (
        f'name = "{name}"\n'
        f'description = "{description}"\n'
        f'developer_instructions = """\n'
        f"{escaped_instructions}"
        f'"""\n'
    )


def sync_agent(md_path: Path) -> Path:
    frontmatter, body = parse_md_agent(md_path)
    name = frontmatter.get("name") or md_path.stem
    description = frontmatter.get("description", "")
    toml_text = render_toml(name, description, body)

    CODEX_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CODEX_AGENTS_DIR / f"{md_path.stem}.toml"
    out_path.write_text(toml_text)
    return out_path


def main() -> int:
    if not AGENTS_DIR.is_dir():
        print(f"error: {AGENTS_DIR} does not exist", file=sys.stderr)
        return 1

    md_files = sorted(AGENTS_DIR.glob("*.md"))
    if not md_files:
        print(f"error: no .md agent files found in {AGENTS_DIR}", file=sys.stderr)
        return 1

    for md_path in md_files:
        out_path = sync_agent(md_path)
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
