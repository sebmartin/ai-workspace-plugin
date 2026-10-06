"""The todo list: which todos are next, and in what order.

Order is the order of the lines in `todos-index.md`. Nothing names a subset, so
every active todo is a next step and no todo can be in the list but absent from
the order.

Parked is the only thing that takes a todo out of Next steps. It means "for
later", so an unparked todo goes back at the end rather than to wherever it
used to sit.
"""

PARKED = "parked"

# Where the list stops being something a person can hold in their head. The
# tools report crossing it in their own output, so it does not depend on the
# skill being read between one call and the next.
COMFORTABLE = 5


def next_up(entries: list) -> list:
    """Every todo that is still a next step, in order."""
    return [e for e in entries if e.state != PARKED]


def parked(entries: list) -> list:
    return [e for e in entries if e.state == PARKED]


def crowded(entries: list) -> int:
    """How many todos are active, once that is more than five. Otherwise 0.

    Presence is the signal, so a comfortable list costs its caller nothing.
    """
    waiting = len(next_up(entries))
    return waiting if waiting > COMFORTABLE else 0


def index_of(entries: list, entry_id: str) -> int | None:
    found = (i for i, e in enumerate(entries) if e.id == entry_id)
    return next(found, None)


def to_top(entries: list, entry_id: str) -> None:
    """Move one todo to the front of the list."""
    _move(entries, entry_id, top=True)


def to_end(entries: list, entry_id: str) -> None:
    _move(entries, entry_id, top=False)


def _move(entries: list, entry_id: str, top: bool) -> None:
    """Take the todo out and put it back at one end. Unknown ids do nothing."""
    found = index_of(entries, entry_id)
    if found is None:
        return
    entry = entries.pop(found)
    entries.insert(0 if top else len(entries), entry)


def reordered(entries: list, ids: list[str], before: str | None = None,
              after: str | None = None) -> list:
    """The named todos moved together, in the order given; the rest keep theirs.

    The anchor is located in what is left once the named todos are taken out,
    not in the list they came from. The two differ whenever something above the
    anchor is one of the things moving.

    The caller has already checked that every id is known and distinct, that at
    most one anchor was named, and that the anchor is not itself moving, so this
    cannot drop a todo, list one twice, or fail to find the anchor.
    """
    by_id = {e.id: e for e in entries}
    named = set(ids)
    moving = [by_id[i] for i in ids]
    rest = [e for e in entries if e.id not in named]
    at = 0
    if anchor := (before or after):
        found = index_of(rest, anchor)
        if found is None:
            raise ValueError(f"anchor {anchor!r} is not in the list")
        at = found if before else found + 1
    return rest[:at] + moving + rest[at:]
