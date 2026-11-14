"""The star file: which artifacts to surface on resume, and when to read them.

`artifacts-starred.md` sits beside the artifacts index rather than inside it,
so the index's line format is unchanged and an older plugin, which has never
heard of this file, never touches it.

Line format, written only here:

    - 20260801-guide-style -- when: the user asks about formatting or tone

An id and the trigger for reading that artifact. Anything that is not a star
line is skipped on read, as in the indexes.

A star is keyed by id and nothing checks it against the index here. Whether a
star's artifact still exists is the reader's question, and `drop` exists so a
star whose artifact is gone can still be cleared.
"""

import re
from pathlib import Path
from typing import NamedTuple

STARRED = "artifacts-starred.md"

_LINE_RE = re.compile(r"^- (?P<id>[^\s:]+) -- when: (?P<when>.+?)\s*$")


class Star(NamedTuple):
    id: str
    when: str


def path(thread_dir: Path) -> Path:
    return thread_dir / STARRED


def _render(star: Star) -> str:
    return f"- {star.id} -- when: {star.when}"


def read(thread_dir: Path) -> list[Star]:
    """The stars, in file order. A missing file is nothing starred."""
    file = path(thread_dir)
    if not file.exists():
        return []
    stars = []
    for line in file.read_text().splitlines():
        hit = _LINE_RE.match(line)
        if hit:
            stars.append(Star(hit["id"], hit["when"]))
    return stars


def write(thread_dir: Path, stars: list[Star]) -> None:
    """One line per star. An empty list leaves an empty file, as an index does."""
    lines = [_render(s) for s in stars]
    path(thread_dir).write_text("\n".join(lines) + ("\n" if lines else ""))


def unrepresentable(star: Star) -> str | None:
    """Which of this star's fields would not survive a line, or None.

    Rendered and read back, so the check is the pattern that does the reading
    and cannot disagree with it. A line break is tested first because `read`
    splits into lines before matching, so a break inside a field makes a line
    the pattern never sees.
    """
    fields = {"id": star.id, "when": star.when}
    for field, value in fields.items():
        if "\n" in value or "\r" in value:
            return f"{field} contains a line break"
    hit = _LINE_RE.match(_render(star))
    if hit is not None and (hit["id"], hit["when"]) == star:
        return None
    for field in fields:
        trial = Star(*(v if f != field else "x" for f, v in fields.items()))
        hit = _LINE_RE.match(_render(trial))
        if hit is not None and (hit["id"], hit["when"]) == trial:
            return f"{field} cannot be read back from a line"
    return "the line it makes cannot be read back"


def drop(thread_dir: Path, artifact_id: str) -> Star | None:
    """Remove a star and return it. Writes nothing when there is none."""
    stars = read(thread_dir)
    gone = next((s for s in stars if s.id == artifact_id), None)
    if gone is None:
        return None
    write(thread_dir, [s for s in stars if s is not gone])
    return gone


def rekey(thread_dir: Path, old_id: str, new_id: str) -> None:
    """Move a star to another id, keeping its place. No star, no change."""
    stars = read(thread_dir)
    if not any(s.id == old_id for s in stars):
        return
    write(thread_dir, [Star(new_id, s.when) if s.id == old_id else s for s in stars])
