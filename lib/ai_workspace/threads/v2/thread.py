"""Schema 2 thread operations: the indexes are the record, the README is a view."""

import re
from datetime import date
from pathlib import Path

from ai_workspace.plugin import get_template_path
from ai_workspace.text import split_frontmatter
from ai_workspace.threads import marker
from ai_workspace.threads.v2 import index as idx

SESSION_WINDOW = 10
ATTACHMENT_WINDOW = 12

MEMORY = "memory.md"

# Where a thread stops being cheap to open. Not derived from any CLI's tool
# output limit: those differ per vendor and this plugin ships to two, and by the
# time one of them truncates the thread has been costly for a long while. Set to
# about three times the largest real thread we have, which leaves room to act.
SIZE_NOTICE = 40_000

# Markdown carrying this many ids, dates and table pipes runs near this. Only
# ever used to produce a hard-rounded figure, so the vendors' tokenizers
# disagreeing by 15% changes nothing about what it is read for.
CHARS_PER_TOKEN = 3.5


# Stop at the next heading or at a horizontal rule: the last section would
# otherwise swallow the footer that follows it.
_SECTION_RE = r"(?m)^##[ \t]+{name}[ \t]*$\n(.*?)(?=^##[ \t]|^---[ \t]*$|\Z)"


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

    Its own template rather than v1's, because the README is a view here and
    the sections the renderer owns have to exist for it to fill in. Index files
    are not pre-created: a missing index is an empty index, and the marker is
    what declares the schema, so there is nothing for their absence to be
    confused with.
    """
    for subdir in SUBDIRS:
        (thread.dir / subdir).mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    template = get_template_path("v2/thread-template.md").read_text()
    readme = re.sub(r"\[Thread Name\]", thread.name, template)
    readme = re.sub(r"\[YYYY-MM-DD\]", today, readme)
    (thread.dir / "README.md").write_text(readme)

    marker.write(thread.dir, SCHEMA)
    return f"Created thread '{thread.name}' at {thread.dir}"


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
    out = []

    # First, because it changes how everything below it is read. Every other
    # section is a line per record whose body is fetched on demand; this is the
    # one body the payload carries, because a rule read afterwards has already
    # been broken.
    if memory := _memory(thread_dir):
        out.append(f"## Thread memory\n\n{memory}\n")

    out.append(_header(text))

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
    # "beyond the window" earns its place: the count excludes what Next steps
    # already showed, so a thread whose todos are all windowed reads as
    # "0 active" directly under five active todos. A reader took that for a
    # corrupt index rather than a heading that did not say what it counted.
    out.append(
        f"\n## Todo backlog, beyond the window "
        f"({len(backlog)} active, {len(parked)} parked)\n"
    )
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

    # Listed while listing is cheap, counted once it is not. A few filenames
    # save a call; eighty-six of them cost a real thread 15% of every resume.
    # There is no index to window against, so the count is the whole choice.
    attachments = thread_dir / "attachments"
    names = sorted(p.name for p in attachments.iterdir() if idx.is_content(p)) \
        if attachments.is_dir() else []
    if names:
        out.append(f"\n## Attachments ({len(names)})\n")
        out.append(", ".join(names) if len(names) <= ATTACHMENT_WINDOW
                   else "Not indexed. List `attachments/` when you need one.")

    payload = "\n".join(out).rstrip() + "\n"
    return _size_notice(len(payload)) + payload


def _two_figures(n: int) -> int:
    """Round to two significant figures, so the estimate cannot read as measured."""
    if n < 100:
        return n
    scale = 10 ** (len(str(n)) - 2)
    return round(n / scale) * scale


def _size_notice(payload_chars: int) -> str:
    """What resuming this thread costs, once that is worth knowing. Else nothing.

    Reported in tokens because chars are a unit with nothing to compare against,
    where an agent can weigh tokens against the context it has. Rounded hard for
    the same reason the estimate is allowed at all: it decides whether to raise
    the subject, and it is not fit for anything finer.

    Its presence is the signal, the way a batch op returning {} means everything
    worked. Below the threshold this costs nothing, which is why the instruction
    sits here rather than in SKILL.md: there it would be charged to every thread
    in every workspace to describe a state almost none of them are in.

    Measures the payload without itself, since the notice is not the thread.
    """
    if payload_chars < SIZE_NOTICE:
        return ""
    tokens = _two_figures(int(payload_chars / CHARS_PER_TOKEN))
    return (
        f"## Thread size\n\n"
        f"~{tokens:,} tokens per resume. Expensive to open, and every session "
        f"pays it. Say so, break it down by section if asked, and leave "
        f"splitting or retiring to the user.\n\n"
    )


def _memory(thread_dir: Path) -> str:
    """The thread's agent-bound file, verbatim, or nothing.

    Absence is the empty case, so `create` writes no stub and a thread that
    never needed one carries no file. Nothing parses it: it is prose the agent
    wrote for itself, and imposing a shape on it would be a shape the agent has
    to maintain rather than one anything reads.

    Read whole and unwindowed, which is both the point of it and its whole
    cost. The skill makes pruning part of a save for that reason.
    """
    path = thread_dir / MEMORY
    try:
        return path.read_text(errors="ignore").strip() if path.is_file() else ""
    except OSError:
        return ""


def _decision_summary(thread_dir: Path, entry: idx.Entry) -> str:
    path = thread_dir / entry.link.lstrip("./")
    if not path.is_file():
        return ""
    try:
        fields, _ = split_frontmatter(path.read_text(errors="ignore")[:2000], path)
    except OSError:
        return ""
    except ValueError:
        # Loud but not fatal. Frontmatter written before anything parsed it can
        # be invalid YAML — an unquoted summary containing ": " is the common
        # one — and letting that raise here makes a whole thread unresumable
        # over a single legacy file. Saying so on the line is what gets it
        # fixed; refusing to open the thread is not.
        return "(frontmatter is not valid YAML, so no summary; worth fixing)"
    return str(fields.get("summary") or "")
