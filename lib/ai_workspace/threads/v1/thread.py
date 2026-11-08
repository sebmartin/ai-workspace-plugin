"""Schema 1 thread operations: the README is the thread.

Everything a schema 1 thread knows about itself is in README.md, so resume is
a file read. This schema is readable but never written: a new thread is always
created at the current schema.
"""


def resume(thread) -> str:
    """The whole README, which for this schema is the whole thread."""
    return (thread.dir / "README.md").read_text()

