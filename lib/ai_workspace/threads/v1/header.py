"""Reading a README's link lines and About section, from its text alone.

Both schemas keep the three link lines in the README header and an About
section in the body, so schema 2 imports this rather than parsing them again.
Nothing here opens a file or looks at another thread.
"""

import re
from typing import NamedTuple

_ROLES = {
    "**Parent Thread**": "Parent",
    "**Child Threads**": "Child",
    "**Related Threads**": "Related",
}
_LINK = re.compile(r"\[([^\]]*)\]\(\.\./([^/)\s]+)/README\.md\)")
_NOTE = re.compile(r"[ \t]*(?:[\u2014\u2013][ \t]*|-[ \t]+)")

# Stop at the next heading or at a horizontal rule: the last section would
# otherwise swallow the footer that follows it.
_SECTION_RE = r"(?m)^##[ \t]+{name}[ \t]*$\n(.*?)(?=^##[ \t]|^---[ \t]*$|\Z)"


class Link(NamedTuple):
    role: str  # "Parent", "Child" or "Related"
    name: str | None  # the linked thread's directory; None for text that is not a thread link
    text: str  # the link text, or the unresolved text as written
    note: str  # the trailing note with its dash stripped; "" when none


def section(text: str, name: str) -> str:
    """The body of a `## name` section, stripped, or "" when there is none."""
    m = re.search(_SECTION_RE.format(name=re.escape(name)), text, re.DOTALL)
    return m.group(1).strip() if m else ""


def about_section(readme: str) -> str:
    return section(readme, "About")


def _unresolved(role: str, text: str) -> list[Link]:
    pieces = (p.strip() for p in re.split(r"[,·]", text))
    return [Link(role, None, p, "") for p in pieces if p]


def _links_in(role: str, value: str) -> list[Link]:
    if not value or value.lower() == "none":
        return []
    found = [m for m in _LINK.finditer(value) if m.group(2) not in (".", "..")]
    out: list[Link] = []
    pos = 0
    for i, m in enumerate(found):
        out += _unresolved(role, value[pos : m.start()])
        end = found[i + 1].start() if i + 1 < len(found) else len(value)
        rest = value[m.end() : end]
        note = ""
        if dash := _NOTE.match(rest):
            note = rest[dash.end() :].strip(" \t,·")
            rest = ""
        out.append(Link(role, m.group(2), m.group(1), note))
        out += _unresolved(role, rest)
        pos = end
    out += _unresolved(role, value[pos:])
    return out


def parse_links(readme: str) -> list[Link]:
    """The links in the header's Parent, Child and Related lines, in order."""
    out: list[Link] = []
    for line in readme.splitlines():
        if line.startswith("## "):
            break
        for prefix, role in _ROLES.items():
            if line.startswith(prefix):
                out += _links_in(role, line.partition(":")[2].strip())
    return out
