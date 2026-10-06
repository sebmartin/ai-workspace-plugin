"""The todo list: which todos are next, and in what order.

Order is the order of the lines in `todos-index.md`. Nothing names a subset, so
every active todo is a next step and no todo can be in the list but absent from
the order.

Parked is the only thing that takes a todo out of Next steps. It means "for
later", so an unparked todo goes back at the end rather than to wherever it
used to sit.
"""

from typing import NamedTuple

from ai_workspace.threads.v2.index import Entry

ACTIVE = "active"
STARTED = "started"
PARKED = "parked"

# How many todos Next steps shows, and so where the list stops being something
# a person can hold in their head. The tools report crossing it in their own
# output, so it does not depend on the skill being read between one call and
# the next.
COMFORTABLE = 5


def next_up(entries: list[Entry]) -> list[Entry]:
    """Every todo that is still a next step, in order."""
    return [e for e in entries if e.state != PARKED]


def parked(entries: list[Entry]) -> list[Entry]:
    return [e for e in entries if e.state == PARKED]


def window(entries: list[Entry]) -> list[Entry]:
    """What Next steps shows: the top of the list, bounded.

    A slice rather than a stored subset. There is nothing to drift from the
    list it is drawn from, nothing to refill when a todo is retired, since the
    sixth moves up by itself, and the README keeps its size as the thread runs
    for months. Changing what is shown is changing the order, which is one
    gesture rather than two.
    """
    return next_up(entries)[:COMFORTABLE]


def crowded(entries: list[Entry]) -> int:
    """How many todos are active, once that is more than five. Otherwise 0.

    Presence is the signal, so a comfortable list costs its caller nothing.
    """
    waiting = len(next_up(entries))
    return waiting if waiting > COMFORTABLE else 0


def index_of(entries: list[Entry], entry_id: str) -> int | None:
    found = (i for i, e in enumerate(entries) if e.id == entry_id)
    return next(found, None)


# The four forms of `place`. One argument rather than a flag per position, so
# there is no combination of arguments to disagree with itself.
PLACES = ("top", "end", "before:<id>", "after:<id>")


class Spot(NamedTuple):
    """Where a `place` points in a particular list, or why it does not.

    `top` and `end` are read off the list at the moment of the write, so a
    caller that has not looked at the list for hours still lands where it
    meant. Only the anchored forms depend on the caller knowing an id.
    """

    at: int | None = None
    error: str = ""
    detail: str = ""


def spot(entries: list[Entry], place: str) -> Spot:
    """Resolve `place` against this list. A malformed form and an anchor that
    is not in the list are different faults, so they get different codes.

    Both halves are stripped and the position is matched without regard to
    case. A space after the colon reads as part of the anchor and would refuse
    as a todo that is not there, sending the reader after the id rather than the
    space; a capital would refuse the position outright. Both are what anyone
    writes, and the four positions are a closed set, so neither costs anything
    to accept. The anchor's own case is left alone, since it is an id.
    """
    sense, _, anchor = place.partition(":")
    sense, anchor = sense.strip().lower(), anchor.strip()
    if sense == "top" and not anchor:
        return Spot(0)
    if sense == "end" and not anchor:
        return Spot(len(entries))
    if sense not in ("before", "after") or not anchor:
        return Spot(error="PLACE_UNKNOWN", detail=place)
    found = index_of(entries, anchor)
    if found is None:
        return Spot(error="NO_SUCH_ENTRY", detail=anchor)
    return Spot(found if sense == "before" else found + 1)


def start(entries: list[Entry], entry_id: str) -> None:
    """Make this the started todo, and the only one, and put it on top.

    Exactly one, because the state names what is being worked on now. A second
    one leaves the label meaning nothing once a few sessions have each marked
    something. The others keep their place and lose only the label.
    """
    for entry in entries:
        if entry.id != entry_id and entry.state == STARTED:
            entry.state = ACTIVE
    to_top(entries, entry_id)


def to_top(entries: list[Entry], entry_id: str) -> None:
    """Move one todo to the front of the list."""
    _move(entries, entry_id, top=True)


def to_end(entries: list[Entry], entry_id: str) -> None:
    _move(entries, entry_id, top=False)


def _move(entries: list[Entry], entry_id: str, top: bool) -> None:
    """Take the todo out and put it back at one end. Unknown ids do nothing."""
    found = index_of(entries, entry_id)
    if found is None:
        return
    entry = entries.pop(found)
    entries.insert(0 if top else len(entries), entry)


def staying(entries: list[Entry], ids: list[str]) -> list[Entry]:
    """The list without the todos being moved, which is what `place` resolves
    against. Resolving against the list they are still in puts the whole move
    one place out whenever something above the anchor is one of the movers."""
    named = set(ids)
    return [e for e in entries if e.id not in named]


def reordered(entries: list[Entry], ids: list[str], at: int) -> list[Entry]:
    """The named todos inserted together at `at`, in the order given.

    `at` indexes `staying(entries, ids)`, and the caller has already resolved
    it there and checked that every id is known and distinct, so this cannot
    drop a todo or list one twice.
    """
    by_id = {e.id: e for e in entries}
    rest = staying(entries, ids)
    return rest[:at] + [by_id[i] for i in ids] + rest[at:]
