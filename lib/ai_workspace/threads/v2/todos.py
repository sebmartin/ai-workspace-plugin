"""The todo list: which todos are next, and in what order.

Order is the order of the lines in `todos-index.json`. Nothing names a subset, so
every active todo is a next step and no todo can be in the list but absent from
the order.

Parked is the only thing that takes a todo out of the Todos section. It means "for
later", so an unparked todo goes back at the end rather than to wherever it
used to sit.
"""

from typing import NamedTuple

from ai_workspace.threads.v2.index import Entry

ACTIVE = "active"
STARTED = "started"
PARKED = "parked"

# How many todos the Todos section shows, and so where the list stops being something
# a person can hold in their head. The tools report crossing it in their own
# output, so it does not depend on the skill being read between one call and
# the next.
COMFORTABLE = 5


class Located(NamedTuple):
    """Where a todo sits: the list holding it, its position, and its goal."""

    siblings: list[Entry]  # the top-level list or goal.children
    at: int  # its position in siblings
    goal: Entry | None  # its goal, or None at top level

    @property
    def entry(self) -> Entry:
        return self.siblings[self.at]


def locate(entries: list[Entry], todo_id: str) -> Located | None:
    """Find a todo at the top level or one level down, or None."""
    for i, entry in enumerate(entries):
        if entry.id == todo_id:
            return Located(entries, i, None)
        for j, child in enumerate(entry.children or []):
            if child.id == todo_id:
                assert entry.children is not None
                return Located(entry.children, j, entry)
    return None


def is_goal(entry: Entry) -> bool:
    """A goal is a todo with a children list, even an empty one."""
    return entry.children is not None


def next_up(entries: list[Entry]) -> list[Entry]:
    """Every todo that is still a next step, in order."""
    return [e for e in entries if e.state != PARKED]


def shown_state(entry: Entry) -> str | None:
    """The state to show for a todo. A goal whose own state is active shows
    started when a child is, so work under it is visible from the top level
    without storing a second copy of the fact."""
    if entry.state == ACTIVE and any(c.state == STARTED for c in entry.children or []):
        return STARTED
    return entry.state


def lines(entry: Entry) -> list[str]:
    """A todo's display lines: itself, then each child that is not parked,
    indented. A parked child is listed under Parked instead."""
    out = [entry.render(shown_state(entry))]
    out.extend("  " + c.render() for c in entry.children or [] if c.state != PARKED)
    return out


def window(entries: list[Entry]) -> list[Entry]:
    """What the Todos section shows: the top of the list, bounded.

    Whole goals are taken in order until `COMFORTABLE` lines or more are out,
    so a goal is never split and one larger than the window shows in full. A
    slice rather than a stored subset: nothing drifts from the list it is drawn
    from, nothing refills when a todo is retired, and the README keeps its size
    as the thread runs for months. Changing what is shown is changing the
    order, which is one gesture rather than two.
    """
    out: list[Entry] = []
    count = 0
    for entry in next_up(entries):
        if count >= COMFORTABLE:
            break
        out.append(entry)
        count += len(lines(entry))
    return out


def shown_lines(entries: list[Entry]) -> list[str]:
    return [line for entry in window(entries) for line in lines(entry)]


def active_count(entries: list[Entry]) -> int:
    """Every todo that is not parked, children included. The children of a
    parked goal are parked with it."""
    total = 0
    for e in entries:
        if e.state != PARKED:
            total += 1 + sum(1 for c in e.children or [] if c.state != PARKED)
    return total


def parked_count(entries: list[Entry]) -> int:
    """Every todo that is parked, or whose goal is."""
    total = 0
    for e in entries:
        if e.state == PARKED:
            total += 1 + len(e.children or [])
        else:
            total += sum(1 for c in e.children or [] if c.state == PARKED)
    return total


def parked_lines(entries: list[Entry]) -> list[str]:
    """The Parked section, in file order. A parked goal is listed whole. A
    parked child of a goal that is not parked names its goal, since nothing
    above it says whose it is."""
    out: list[str] = []
    for e in entries:
        if e.state == PARKED:
            out.append(e.render())
            out.extend("  " + c.render() for c in e.children or [])
        else:
            goal = " ".join(e.title.split())
            out.extend(f"{c.render()} ({goal})" for c in e.children or [] if c.state == PARKED)
    return out


def crowded(entries: list[Entry]) -> int:
    """How many todos are active, once that is more than five. Otherwise 0.

    Presence is the signal, so a comfortable list costs its caller nothing.
    """
    waiting = active_count(entries)
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


def start(entries: list[Entry], todo_id: str) -> list[Entry]:
    """Put a todo that has been started at the top of its own list.

    Several todos can be started at once, so nothing is taken off any other.
    For a child the goal goes to the top of `entries` as well, so the work is
    first at both levels, and a parked goal is made active, since work under it
    has begun. Returns the entries other than the todo whose state this
    changed: the goal, or nothing.
    """
    found = locate(entries, todo_id)
    if found is None:
        return []
    found.siblings.insert(0, found.siblings.pop(found.at))
    if found.goal is None:
        return []
    return raise_goal(entries, found.goal)


def raise_goal(entries: list[Entry], goal: Entry) -> list[Entry]:
    """Send a goal whose child has been started to the top of `entries`, and
    make it active if it was parked. Returns [goal] when its state changed."""
    entries.insert(0, entries.pop(entries.index(goal)))
    if goal.state == PARKED:
        goal.state = ACTIVE
        return [goal]
    return []


def apply_state(entries: list[Entry], todo_id: str, state: str) -> list[Entry]:
    """Set a todo's state with every move and cascade it implies.

    Parking a goal parks its children, and unparking it unparks them all and
    sends the goal to the end. A child parks and unparks alone, and unparking
    one under a parked goal brings the goal back, in its place, so the child is
    visible. Returns the named todo first, then each other entry whose state
    changed, so the caller can sync their files. An unknown id returns [].
    """
    found = locate(entries, todo_id)
    if found is None:
        return []
    entry = found.entry
    was, entry.state = entry.state, state
    changed = [entry]
    if state == STARTED:
        changed += start(entries, todo_id)
    if was == PARKED and state != PARKED:
        if is_goal(entry):
            for child in entry.children or []:
                if child.state == PARKED:
                    child.state = ACTIVE
                    changed.append(child)
            if state == ACTIVE:
                to_end(entries, todo_id)
        else:
            if state == ACTIVE:
                to_end(found.siblings, todo_id)
            if found.goal is not None and found.goal.state == PARKED:
                found.goal.state = ACTIVE
                changed.append(found.goal)
    elif state == PARKED and is_goal(entry):
        for child in entry.children or []:
            if child.state != PARKED:
                child.state = PARKED
                changed.append(child)
    return changed


def to_end(entries: list[Entry], todo_id: str) -> None:
    """Move a todo to the end of its own list. An unknown id does nothing."""
    found = locate(entries, todo_id)
    if found is not None:
        found.siblings.append(found.siblings.pop(found.at))


def same_list(entries: list[Entry], ids: list[str]) -> list[Entry] | None:
    """The list object (top-level or one goal's children) holding every id, or
    None when they are spread over several lists or any is unknown."""
    lists = [entries] + [e.children for e in entries if e.children is not None]
    wanted = set(ids)
    for candidate in lists:
        if wanted <= {e.id for e in candidate}:
            return candidate
    return None


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
