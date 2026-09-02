"""Index entry ids: YYYYMMDD-slug, always.

The id is assigned, not read off the filename. Older plugin versions did not
follow the dated-filename convention, so real threads contain names like
`2026-01-20-initial-setup.md`, `snapshot-20260303-parking-lot.md` and
`v1-remote-access-and-execution.md`. Sorting a directory listing is therefore
not chronological, and an id minted from a derived date is.

Files are never renamed to match. The index line carries the real path, so the
id and the basename coincide for anything created under schema 2 and may differ
for anything older.
"""

import re
from datetime import date

# The date prefix of an id whose date could not be derived. The epoch rather
# than something like 00000000 so every downstream parser handles it without a
# special case, and rather than the thread's start date so a guess is never
# mistaken for a fact.
UNKNOWN = "19700101"

SLUG_RE = re.compile(r"[^a-z0-9]+")
ID_RE = re.compile(r"^(\d{8})-([a-z0-9][a-z0-9-]*)$")


def slugify(text: str) -> str:
    slug = SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "untitled"


def make_id(when: date, slug: str) -> str:
    """The id for something dated `when`.

    A date rather than a string: the caller has one, and taking text meant
    accepting two formats and normalising inside, which put the question of
    what a valid date is in the wrong place.
    """
    return f"{when:%Y%m%d}-{slugify(slug)}"


def parse_id(entry_id: str) -> tuple[str, str] | None:
    m = ID_RE.match(entry_id)
    return (m.group(1), m.group(2)) if m else None


def unique_id(entry_id: str, taken: set[str]) -> str:
    """Append a numeric suffix until the id is free.

    Mirrors the collision handling restore_thread already uses for thread names,
    so two artifacts created the same day with the same slug both keep an id.
    """
    if entry_id not in taken:
        return entry_id
    n = 2
    while f"{entry_id}-{n}" in taken:
        n += 1
    return f"{entry_id}-{n}"
