"""Frontmatter and YAML text helpers. Independent of any schema."""

import re


def _yaml_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _extract_yaml_field(text: str, field: str) -> str | None:
    m = re.search(rf'^{field}:\s*"?([^"\n]+?)"?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_yaml_keywords(text: str) -> list:
    inline = re.search(r"^keywords:\s*\[\s*\]\s*$", text, re.MULTILINE)
    if inline:
        return []
    block = re.search(
        r"^keywords:\s*\n((?:  - .+\n?)+)", text, re.MULTILINE
    )
    if not block:
        return []
    items = []
    for line in block.group(1).splitlines():
        m = re.match(r'^  - "?([^"]*)"?\s*$', line)
        if m:
            items.append(m.group(1).strip())
    return items


def _extract_body(text: str) -> str:
    """Return the markdown body that follows the closing '---' of frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text.strip()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1:]).strip()
    return ""
