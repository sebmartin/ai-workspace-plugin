"""Schema 1 thread operations: the README is the thread.

Everything a schema 1 thread knows about itself is in README.md, so resume is
a file read. This schema is readable but never written: a new thread is always
created at the current schema.
"""

from ai_workspace.threads.v1.header import Link, about_section, parse_links


def _readme(thread) -> str:
    try:
        return (thread.dir / "README.md").read_text(errors="replace")
    except FileNotFoundError:
        return ""


def resume(thread) -> str:
    """The whole README, which for this schema is the whole thread."""
    return (thread.dir / "README.md").read_text()


def links(thread) -> list[Link]:
    """The links in the README header."""
    return parse_links(_readme(thread))


def about(thread) -> str:
    """The README's About section, or "" when it has none."""
    return about_section(_readme(thread))

