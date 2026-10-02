"""Schema 1 thread operations: the README is the thread.

Everything a schema 1 thread knows about itself is in README.md, so resume is
a file read and create is a directory plus that file. No marker is written:
this schema predates versioning, and its threads are identified by not having
one.
"""

import re
from datetime import date

from ai_workspace.plugin import get_template_path

SUBDIRS = ("sessions", "decisions", "attachments", "artifacts")


def resume(thread) -> str:
    """The whole README, which for this schema is the whole thread."""
    return (thread.dir / "README.md").read_text()


def create(thread) -> str:
    """Lay out a new thread directory and its README."""
    for subdir in SUBDIRS:
        (thread.dir / subdir).mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    template = get_template_path("thread-template.md").read_text()
    readme = re.sub(r"\[Thread Name\]", thread.name, template)
    readme = re.sub(r"\[YYYY-MM-DD\]", today, readme)
    (thread.dir / "README.md").write_text(readme)

    return f"Created thread '{thread.name}' at {thread.dir}"
