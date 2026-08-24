"""Deriving a date for a file that has to be given an index id.

Order matters, and no filesystem timestamp appears in it. Measured on a real
thread, 20 of 128 dated markdown files report a filesystem time more than a week
after the date in their own filename, several landing exactly on the day the
workspace was copied to a NAS. Those timestamps record when the bytes moved.
mtime is last-modified, so an amended design document would sort as the newest
thing in its thread; `st_ctime` is inode change time on Unix, not creation.
"""

import re
from pathlib import Path

UNKNOWN = "19700101"

_FRONTMATTER_DATE_KEYS = ("date", "started", "last_active", "archived")
_DATE_RE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")
_FM_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*$", re.DOTALL | re.MULTILINE
)


def _valid(y: str, m: str, d: str) -> str | None:
    try:
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            return f"{y}{m}{d}"
    except ValueError:
        pass
    return None


def from_frontmatter(text: str) -> str | None:
    m = _FM_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip() in _FRONTMATTER_DATE_KEYS:
            found = _DATE_RE.search(value)
            if found:
                return _valid(*found.groups())
    return None


def from_name(name: str) -> str | None:
    found = _DATE_RE.search(name)
    return _valid(*found.groups()) if found else None


def build_session_reference_map(sessions_dir: Path) -> dict[str, str]:
    """Map a referenced filename to the earliest dated session mentioning it.

    Sessions register the artifacts they create, so a session that names a file
    dates it. Each session is read once here rather than per artifact: the naive
    form is sessions x artifacts, which is slow against a network volume.
    """
    refs: dict[str, str] = {}
    if not sessions_dir.is_dir():
        return refs
    for session in sorted(sessions_dir.glob("*.md")):
        session_date = from_name(session.name)
        if not session_date:
            continue
        try:
            text = session.read_text(errors="ignore")
        except OSError:
            continue
        # Any filename-shaped token, which catches both bare mentions and the
        # targets of markdown links. No capture group: re.findall would then
        # return the group instead of the match.
        for token in re.findall(r"[\w][\w.\-]*\.\w+", text):
            name = Path(token).name
            if name and (name not in refs or session_date < refs[name]):
                refs[name] = session_date
    return refs


def derive(path: Path, reference_map: dict[str, str] | None = None) -> tuple[str, bool]:
    """Return (YYYYMMDD, known). `known` is False when nothing could be found.

    The unknown value is the epoch rather than something like 00000000 so that
    every downstream parser handles it without a special case, and rather than
    the thread's start date so that a guess is never mistaken for a fact.
    """
    if path.is_file():
        try:
            found = from_frontmatter(path.read_text(errors="ignore")[:2000])
            if found:
                return found, True
        except OSError:
            pass
    found = from_name(path.name)
    if found:
        return found, True
    if reference_map:
        found = reference_map.get(path.name)
        if found:
            return found, True
    return UNKNOWN, False
