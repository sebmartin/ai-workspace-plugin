"""Editing the README's hand-written parts from a tool.

The renderer owns Todos; these are the fields a save or `set_about` writes that
are not derived from any index: Status, About and the header dates.
"""

import re
from datetime import date
from pathlib import Path

_STATUS_RE = re.compile(r"(?m)^##[ \t]+Status[ \t]*$\n.*?(?=^##[ \t]|\Z)", re.DOTALL)


def write_status(thread_dir: Path, recently: list[str], up_next: list[str]) -> None:
    """Replace the Status section with the two lists. Items are final bullet text."""
    readme = thread_dir / "README.md"
    text = readme.read_text() if readme.exists() else ""
    recent = "".join(f"- {item}\n" for item in recently)
    upcoming = "".join(f"- {item}\n" for item in up_next) or "- None\n"
    block = f"## Status\n\n**Recently**\n{recent}\n**Up next**\n{upcoming}\n"
    if _STATUS_RE.search(text):
        # A function replacement. A string one reads the items for `\1` and
        # `\d` escapes.
        text = _STATUS_RE.sub(lambda _: block, text, count=1)
    else:
        text = text.rstrip() + "\n\n" + block
    readme.write_text(text)


def touch_dates(thread_dir: Path, today: str | None = None) -> None:
    """Keep `**Last Session**` current.

    archive_thread greps this line out of the README, so it has to keep
    existing and keep meaning what it says; without it archiving falls back to
    a directory timestamp that reports the migration date for migrated threads.
    """
    today = today or date.today().isoformat()
    readme = thread_dir / "README.md"
    if not readme.exists():
        return
    text = readme.read_text()
    if re.search(r"(?m)^\*\*Last Session\*\*:", text):
        text = re.sub(r"(?m)^\*\*Last Session\*\*:.*$", f"**Last Session**: {today}", text)
    else:
        text = re.sub(r"(?m)^(\*\*Started\*\*:.*)$", rf"\1\n**Last Session**: {today}", text, count=1)
    readme.write_text(text)
