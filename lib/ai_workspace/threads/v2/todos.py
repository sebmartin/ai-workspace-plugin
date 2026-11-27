"""The todo list: four tiers, held as states, in file order.

A todo is `started`, `next`, `backlog` or `parked`, and `todos-index.md` is
always grouped in that order, so a tier is a contiguous slice of the list and
the order inside it is the order of the lines. Several todos can be started.

Where a todo lands is one rule. One that moves to an earlier tier (promoted)
goes to the bottom of it, behind what was already there. One that moves to a
later tier (demoted) goes to the top. A new todo goes to the end of `started`
or `next`, and to the top of `backlog` or `parked`.
"""

from typing import NamedTuple

from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2.index import Entry

STARTED, NEXT, BACKLOG, PARKED = idx.IN_FORCE["todos"]
TIERS = idx.IN_FORCE["todos"]

# How many todos the Todos section shows, and so where the list stops being something
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
    """What the Todos section shows: the top of the list, bounded.

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


def just_crowded(before: list[Entry], after: list[Entry]) -> int:
    """The count, but only on the change that takes the list past the window.

    Reported on every change past it, this would instruct on each of the adds
    from six to twenty and be ignored by the twentieth. The bound is what keeps
    the README cheap, so one instruction is enough and the resume heading is
    what goes on reporting.
    """
    return 0 if crowded(before) else crowded(after)


def index_of(entries: list[Entry], entry_id: str) -> int | None:
    found = (i for i, e in enumerate(entries) if e.id == entry_id)
    return next(found, None)


def bounds(entries: list[Entry], state: str) -> tuple[int, int]:
    """The `[start, end)` slice of a tier in a grouped list. An empty tier is
    `start == end`, at the place it would occupy."""
    rank = TIERS.index(state)
    start = sum(1 for e in entries if e.state in TIERS[:rank])
    return start, start + sum(1 for e in entries if e.state == state)


def landing(entries: list[Entry], state: str) -> int:
    """Where a new todo with no `place` goes: the end of `started` and `next`,
    which are queues, and the top of `backlog` and `parked`, which are not."""
    start, end = bounds(entries, state)
    return end if state in (STARTED, NEXT) else start


# The four forms of `place`. One argument rather than a flag per position, so
# there is no combination of arguments to disagree with itself.
PLACES = ("top", "end", "before:<id>", "after:<id>")


class Spot(NamedTuple):
    """Where a `place` points in a particular list, or why it does not.

    `top` and `end` are read off the list at the moment of the write, so a
    caller that has not looked at the list for hours still lands where it
    meant. Only the anchored forms depend on the caller knowing an id. `tier`
    is the state the placed todos end up in; on an `ANCHOR_IN_OTHER_TIER`
    refusal it is the anchor's state instead.
    """

    at: int | None = None
    error: str = ""
    detail: str = ""
    tier: str = ""


def spot(entries: list[Entry], place: str, tier: str) -> Spot:
    """Resolve `place` inside `tier`. A malformed form, an anchor that is not
    in the list and an anchor in another tier are different faults, so they get
    different codes.

    Both halves are stripped and the position is matched without regard to
    case. A space after the colon reads as part of the anchor and would refuse
    as a todo that is not there, sending the reader after the id rather than the
    space; a capital would refuse the position outright. Both are what anyone
    writes, and the four positions are a closed set, so neither costs anything
    to accept. The anchor's own case is left alone, since it is an id.
    """
    sense, _, anchor = place.partition(":")
    sense, anchor = sense.strip().lower(), anchor.strip()
    if sense in ("top", "end") and not anchor:
        start, end = bounds(entries, tier)
        return Spot(start if sense == "top" else end, tier=tier)
    if sense not in ("before", "after") or not anchor:
        return Spot(error="PLACE_UNKNOWN", detail=place)
    found = index_of(entries, anchor)
    if found is None:
        return Spot(error="NO_SUCH_ENTRY", detail=anchor)
    if entries[found].state != tier:
        return Spot(error="ANCHOR_IN_OTHER_TIER", detail=anchor,
                    tier=entries[found].state or "")
    return Spot(found if sense == "before" else found + 1, tier=tier)


def moved(entries: list[Entry], entry_id: str, state: str) -> list[Entry]:
    """The list after one todo takes a new state: the boundary rule.

    Promoted (the new tier is earlier) goes to the bottom of it, demoted to the
    top. The same state returns the list unchanged. The entry's state is set
    here, since which way it moved depends on the state it had.
    """
    found = index_of(entries, entry_id)
    if found is None or entries[found].state == state:
        return entries
    entry = entries[found]
    promoted = TIERS.index(state) < TIERS.index(entry.state or PARKED)
    rest = entries[:found] + entries[found + 1:]
    entry.state = state
    start, end = bounds(rest, state)
    at = end if promoted else start
    return [*rest[:at], entry, *rest[at:]]


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


def destination(staying: list[Entry], movers: list[Entry], place: str) -> Spot:
    """Where `movers` go, and the tier they end up in. Blank `place` is `top`.

    An anchor puts them in the anchor's own tier, which is how a todo changes
    tier at an exact spot. `top` and `end` have no tier of their own, so they
    stay in the one the movers share and refuse `TIERS_DIFFER` when there are
    several, naming each mover's state in the order given.
    """
    place = place.strip() or "top"
    sense, _, anchor = place.partition(":")
    if sense.strip().lower() in ("top", "end") and not anchor.strip():
        states = {e.state for e in movers}
        if len(states) > 1:
            return Spot(error="TIERS_DIFFER",
                        detail=", ".join(f"{e.id}:{e.state}" for e in movers))
        return spot(staying, place, movers[0].state or PARKED)
    # Any tier will do for the first look: an anchor in another tier says
    # which one it is, and a malformed or missing one is refused the same way.
    probe = spot(staying, place, STARTED)
    if probe.error == "ANCHOR_IN_OTHER_TIER":
        return spot(staying, place, probe.tier)
    return probe
