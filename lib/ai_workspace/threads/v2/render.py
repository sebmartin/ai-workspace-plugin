"""Rendering the README's one derived section.

The README is mostly hand-written. The renderer owns Next steps and nothing
else, replacing it from its heading to the next heading and leaving the rest of
the file untouched.

That boundary is load-bearing for `link-thread`, which maintains
`**Parent Thread**` / `**Child Threads**` / `**Related Threads**` by editing the
README of both threads it connects, and is the one operation that inherently
spans schemas since either side may be schema 1 or 2.
"""

import re
from pathlib import Path

from ai_workspace.threads.v2 import index as idx

NEXT_STEPS = "Next steps"

_SECTION_RE_TEMPLATE = r"(?m)^##[ \t]+{name}[ \t]*$.*?(?=^##[ \t]|\Z)"


def _pattern() -> re.Pattern[str]:
    return re.compile(_SECTION_RE_TEMPLATE.format(name=re.escape(NEXT_STEPS)), re.DOTALL)


def _links_line(thread_dir: Path) -> str:
    parts = []
    for kind in idx.TYPES:
        bits = [f"[{kind}](./{kind}-index.md)"]
        if kind in idx.RETIRED_TYPES:
            bits.append(f"[retired](./{kind}-retired.md)")
        parts.append(" ".join(bits))
    return "**Indexes**: " + " · ".join(parts)


def next_steps_body(thread_dir: Path) -> str:
    """The window, in window order, or a placeholder."""
    entries, fm = idx.read(thread_dir, "todos")
    ids = (fm.get("windows") or {}).get("next_steps") or []
    by_id = {e.id: e for e in entries}
    lines = [by_id[i].render() for i in ids if i in by_id]
    if not lines:
        return "- None\n"
    return "\n".join(lines) + "\n"


def blocked(thread_dir: Path) -> str | None:
    """Why this thread cannot be written to yet, or None.

    Asked before anything mutates, so a refusal leaves nothing behind and a
    retry after fixing the README is clean rather than a second entry.
    """
    readme = thread_dir / "README.md"
    text = readme.read_text() if readme.exists() else ""
    if _pattern().search(text):
        return None
    return (
        f"Error: {readme} has no `## {NEXT_STEPS}` heading, so it is not a "
        f"schema 2 README.\n"
        f"Replace it from templates/v2/thread-template.md, then retry. Nothing "
        f"was written."
    )


def render(thread_dir: Path) -> str | None:
    """Rewrite the Next steps section in place. None on success, else why not.

    A missing `## {NEXT_STEPS}` heading means this README is not schema 2
    shaped, and the only honest answer is to say so. It used to append the
    section instead, which on a schema 1 README stapled a second, immediately
    diverging next-step list onto an otherwise intact v1 document and reported
    success. That is the state a migration passes through, so the append branch
    fired exactly where it did the most damage.
    """
    readme = thread_dir / "README.md"
    text = readme.read_text() if readme.exists() else ""
    pattern = _pattern()
    if not pattern.search(text):
        return blocked(thread_dir)
    section = f"## {NEXT_STEPS}\n\n{next_steps_body(thread_dir)}\n"
    text = pattern.sub(section, text, count=1)
    if "**Indexes**:" not in text:
        text = text.rstrip() + "\n\n---\n\n" + _links_line(thread_dir) + "\n"
    readme.write_text(text)
    return None
