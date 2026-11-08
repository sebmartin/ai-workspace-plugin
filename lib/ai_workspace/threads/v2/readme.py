"""Editing the README's hand-written parts from a tool.

The renderer owns Todos; these are the fields a save or `set_about` writes that
are not derived from any index: Status, About and the header dates.
"""

import re
from datetime import date
from pathlib import Path

_STATUS_RE = re.compile(r"(?m)^##[ \t]+Status[ \t]*$\n.*?(?=^##[ \t]|^---[ \t]*$|\Z)", re.DOTALL)


MAX_ABOUT_WORDS = 50

# Same lookahead as thread._SECTION_RE: the section ends at the next heading, a
# horizontal rule or the end of the file.
_ABOUT_RE = re.compile(r"(?m)^##[ \t]+About[ \t]*$\n.*?(?=^##[ \t]|^---[ \t]*$|\Z)", re.DOTALL)
_FOOTER_RE = re.compile(r"(?m)^---[ \t]*\n+\*\*Indexes\*\*:")
_ENDS_SECTION_RE = re.compile(r"^(#{1,6}[ \t]|---[ \t]*$)")


def about_refusal(text: str) -> dict | None:
    """Why this text cannot be the About section, or None."""
    text = text.strip()
    if not text:
        return {"error": "ABOUT_EMPTY"}
    words = len(text.split())
    if words > MAX_ABOUT_WORDS:
        return {"error": "ABOUT_TOO_LONG", "limit": MAX_ABOUT_WORDS, "words": words}
    for line in text.splitlines():
        # A heading or a rule would end the section early for every reader.
        if _ENDS_SECTION_RE.match(line):
            return {"error": "ABOUT_UNREPRESENTABLE", "detail": line}
    return None


def write_about(thread_dir: Path, text: str) -> None:
    """Replace the About section, or add one above the Indexes footer."""
    readme = thread_dir / "README.md"
    current = readme.read_text() if readme.exists() else ""
    block = f"## About\n\n{text.strip()}\n\n"
    if _ABOUT_RE.search(current):
        # A function replacement, so a backslash in the text is not an escape.
        current = _ABOUT_RE.sub(lambda _: block, current, count=1)
    elif footer := _FOOTER_RE.search(current):
        current = current[: footer.start()] + block + current[footer.start():]
    else:
        current = current.rstrip() + "\n\n" + block
    readme.write_text(current)


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
    elif footer := _FOOTER_RE.search(text):
        text = text[: footer.start()] + block + text[footer.start():]
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
