"""Schema 2 thread operations: the indexes are the record, the README is a view."""

import re
from pathlib import Path

from ai_workspace.text import _extract_yaml_field
from ai_workspace.threads import marker, v1
from ai_workspace.threads.v2 import index as idx

SESSION_WINDOW = 10

_SECTION_RE = r"(?m)^##[ \t]+{name}[ \t]*$\n(.*?)(?=^##[ \t]|\Z)"


def _section(text: str, name: str) -> str:
    m = re.search(_SECTION_RE.format(name=re.escape(name)), text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _header(text: str) -> str:
    """The bold key/value block above the first heading."""
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            break
        if line.startswith("**") and ":" in line:
            lines.append(line)
    return "\n".join(lines)


SCHEMA = 2

SUBDIRS = ("sessions", "decisions", "attachments", "artifacts", "todos")


def create(thread) -> str:
    """Lay out a new schema 2 thread.

    v1's layout plus todos/, which is a schema 2 concept, plus the marker.
    Index files are not pre-created: a missing index is an empty index, and the
    marker is what declares the schema, so there is nothing for their absence
    to be confused with.
    """
    result = v1.create(thread)
    for subdir in SUBDIRS:
        (thread.dir / subdir).mkdir(parents=True, exist_ok=True)
    marker.write(thread.dir, SCHEMA)
    return result


def resume(thread) -> str:
    """The composed payload, built from the indexes rather than the README."""
    return compose(thread.dir, thread.name)


def compose(thread_dir: Path, thread_name: str) -> str:
    """The whole resume payload in one call.

    Decision bodies are never opened here; their one-line `summary:` frontmatter
    is, which is what the schema 1 resume already did. That keeps one copy of the
    summary, in the file, with nothing to reconcile against a duplicate.
    """
    readme = (thread_dir / "README.md")
    text = readme.read_text() if readme.exists() else ""
    out = [_header(text)]

    status = _section(text, "Status")
    out.append("\n## Status\n\n" + (status or "(empty)"))
    about = _section(text, "About")
    if about:
        out.append("\n## About\n\n" + about)

    todos, fm = idx.read(thread_dir, "todos")
    window = (fm.get("windows") or {}).get("next_steps") or []
    by_id = {e.id: e for e in todos}
    out.append("\n## Next steps\n")
    out.extend(by_id[i].render() for i in window if i in by_id)
    if not window:
        out.append("- None")

    parked = [e for e in todos if e.state == "parked"]
    backlog = [e for e in todos if e.id not in window and e.state != "parked"]
    out.append(f"\n## Todo backlog ({len(backlog)} active, {len(parked)} parked)\n")
    out.extend(e.render() for e in backlog + parked)

    decisions, _ = idx.read(thread_dir, "decisions")
    out.append(f"\n## Decisions in force ({len(decisions)})\n")
    for entry in decisions:
        summary = _decision_summary(thread_dir, entry)
        out.append(entry.render() + (f"\n  {summary}" if summary else ""))

    artifacts, _ = idx.read(thread_dir, "artifacts")
    out.append(f"\n## Artifacts ({len(artifacts)})\n")
    out.extend(e.render() for e in artifacts)

    sessions, _ = idx.read(thread_dir, "sessions")
    tail = sessions[-SESSION_WINDOW:]
    out.append(f"\n## Recent sessions ({len(tail)} of {len(sessions)})\n")
    out.extend(e.render() for e in tail)

    attachments = thread_dir / "attachments"
    names = sorted(p.name for p in attachments.iterdir()) if attachments.is_dir() else []
    if names:
        out.append(f"\n## Attachments ({len(names)})\n")
        out.append(", ".join(names))

    return "\n".join(out).rstrip() + "\n"


def _decision_summary(thread_dir: Path, entry: idx.Entry) -> str:
    path = thread_dir / entry.link.lstrip("./")
    if not path.is_file():
        return ""
    try:
        return _extract_yaml_field(path.read_text(errors="ignore")[:2000], "summary") or ""
    except OSError:
        return ""
