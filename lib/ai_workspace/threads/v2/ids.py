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

# An id is a handle, not a description: the title sits on the same index line
# and says what the thing is. Long enough to stay recognisable, short enough to
# read in a list and to retype into retire_todo without a slip. A todo titled
# from a sentence produced a 90-character id before this.
MAX_SLUG = 48
ID_RE = re.compile(r"^(\d{8})-([a-z0-9][a-z0-9-]*)$")

# A date anywhere in a filename, dashed or not. Older plugin versions wrote it
# in both forms and not always first, so neither the format nor the position is
# fixed.
_DATE_IN_NAME = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")

# A trailing file extension, kept short and alphanumeric on purpose. An artifact
# can be a directory, and `Path.stem` would cut `v1.2-notes` down to `v1`.
_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,4}$")


def slugify(text: str) -> str:
    """Kebab-case, capped at a word boundary so it never cuts mid-word."""
    slug = SLUG_RE.sub("-", text.lower()).strip("-")
    if len(slug) > MAX_SLUG:
        cut = slug[: MAX_SLUG + 1]
        slug = cut.rsplit("-", 1)[0] if "-" in cut[1:] else cut[:MAX_SLUG]
    return slug.strip("-") or "untitled"


def make_id(when: date | None, slug: str) -> str:
    """The id for something dated `when`, or dated UNKNOWN when nothing is known.

    A date rather than a string: the caller has one, and taking text meant
    accepting two formats and normalising inside, which put the question of
    what a valid date is in the wrong place. None is not a third format, it is
    the absence of an answer, and it renders as the epoch so every downstream
    parser handles it without a special case.
    """
    prefix = f"{when:%Y%m%d}" if when is not None else UNKNOWN
    return f"{prefix}-{slugify(slug)}"


def from_filename(name: str) -> tuple[date | None, str]:
    """The date a filename states, and what is left once it is taken out.

    Splitting them is what lets an id be rebuilt with the date first whatever
    order the name used. `snapshot-20260303-parking-lot.md` gives 2026-03-03 and
    `snapshot-parking-lot`, so its id sorts with March rather than with `s`.

    A name with no date gives None and the caller decides what that means. It
    never guesses one: a plausible date is worse than a visible gap.
    """
    stem = _EXTENSION.sub("", name)
    found = _DATE_IN_NAME.search(stem)
    if not found:
        return None, stem
    y, m, d = found.groups()
    try:
        when = date(int(y), int(m), int(d))
    except ValueError:
        return None, stem
    return when, stem[: found.start()] + stem[found.end():]


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
