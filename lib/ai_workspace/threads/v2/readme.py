"""Editing the README's hand-written parts from a tool.

The renderer owns Next steps; these are the fields a save has to touch that are
not derived from any index — the Status prose and the header dates.
"""

import re
from datetime import date
from pathlib import Path

_STATUS_RE = re.compile(r"(?m)^##[ \t]+Status[ \t]*$\n.*?(?=^##[ \t]|\Z)", re.DOTALL)


def set_status(thread_dir: Path, status: str) -> None:
    readme = thread_dir / "README.md"
    text = readme.read_text() if readme.exists() else ""
    block = f"## Status\n\n{status.strip()}\n\n"
    if _STATUS_RE.search(text):
        text = _STATUS_RE.sub(block, text, count=1)
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
