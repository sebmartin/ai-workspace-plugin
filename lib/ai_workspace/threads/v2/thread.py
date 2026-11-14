"""Schema 2 thread operations: the indexes are the record, the README is a view."""

import re
from datetime import date
from pathlib import Path

from frontmatter.default_handlers import YAMLHandler

from ai_workspace.plugin import get_template_path
from ai_workspace.text import split_frontmatter
from ai_workspace.threads import marker
from ai_workspace.threads.v2 import index as idx
from ai_workspace.threads.v2 import todos as todos_mod

# What resume spends on session bodies, in tokens. The newest sessions are shown
# in full, newest first, until the next one would not fit. The newest is always
# shown whole, however long: it is the discussion a resumed agent most needs.
# Never quoted to the model, which would reason about the figure.
SESSION_BODY_BUDGET = 4_000
# Sessions older than the full ones that still get their `summary:` line.
SESSION_SUMMARIES = 5
ATTACHMENT_WINDOW = 12

MEMORY = "memory.md"

# Where a thread stops being cheap to open. Not derived from any CLI's tool
# output limit: those differ per vendor and this plugin ships to two, and by the
# time one of them truncates the thread has been costly for a long while. Set to
# about three times the largest real thread we have, which leaves room to act.
# 40,000 before session bodies were embedded, plus the body budget (14,000
# characters), so a thread is not charged for the bodies it is meant to carry.
SIZE_NOTICE = 54_000

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


def create(thread, about: str = "") -> str | dict:
    """Lay out a new schema 2 thread.

    Its own template rather than v1's, because the README is a view here and
    the sections the renderer owns have to exist for it to fill in. Index files
    are not pre-created: a missing index is an empty index, and the marker is
    what declares the schema, so there is nothing for their absence to be
    confused with.

    Returns the success message, or a refusal as a dict, decided before
    anything is created.
    """
    from ai_workspace.threads.v2 import readme as readme_mod

    if about.strip() and (refusal := readme_mod.about_refusal(about)) is not None:
        return refusal
    for subdir in SUBDIRS:
        (thread.dir / subdir).mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    template = get_template_path("v2/thread-template.md").read_text()
    readme = re.sub(r"\[Thread Name\]", thread.name, template)
    readme = re.sub(r"\[YYYY-MM-DD\]", today, readme)
    (thread.dir / "README.md").write_text(readme)
    if about.strip():
        readme_mod.write_about(thread.dir, about)

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

    about = _section(text, "About")
    out.append("\n## About\n\n" + (about or "(empty)"))
    status = _section(text, "Status")
    out.append("\n## Status\n\n" + (status or "(empty)"))

    todos = idx.read(thread_dir, "todos")
    active, parked = todos_mod.next_up(todos), todos_mod.parked(todos)
    shown = todos_mod.window(todos)
    # Every count, because the section is bounded and each number answers a
    # different question: what is on screen, how much is waiting behind it, and
    # how much was set aside. Without the last two an empty list cannot be told
    # from a thread that is finished with.
    out.append(
        f"\n## Todos ({len(shown)} of {len(active)} active, "
        f"{len(parked)} parked)\n"
    )
    out.extend(e.render() for e in shown)
    if not shown:
        out.append("- None")

    # Its own section rather than a tail on the list above, because the skill
    # has the agent print the todos and parked todos are the ones the user
    # already said are not next.
    if parked:
        out.append("\n## Parked\n")
        out.extend(e.render() for e in parked)

    decisions = idx.read(thread_dir, "decisions")
    out.append(f"\n## Decisions in force ({len(decisions)})\n")
    for entry in decisions:
        summary = _summary(thread_dir, entry)
        if summary is None:
            summary = "(frontmatter is not valid YAML, so no summary; worth fixing)"
        out.append(entry.render() + (f"\n  {summary}" if summary else ""))

    artifacts = idx.read(thread_dir, "artifacts")
    out.append(f"\n## Artifacts ({len(artifacts)})\n")
    out.extend(e.render() for e in artifacts)

    sessions = idx.read(thread_dir, "sessions")
    bodies = [_session_body(thread_dir, e) for e in sessions]
    n_full, n_sum = session_window(
        [len(b) for b in bodies], int(SESSION_BODY_BUDGET * CHARS_PER_TOKEN), SESSION_SUMMARIES)
    out.append(
        f"\n## Recent sessions ({n_full} in full, {n_sum} summarized, of {len(sessions)})\n")
    # Summaries first and the full sessions after, each oldest first, so the
    # newest session is the last thing in the payload.
    first_full = len(sessions) - n_full
    for entry in sessions[first_full - n_sum:first_full]:
        summary = _summary(thread_dir, entry)
        out.append(entry.render() + (f"\n  {summary}" if summary else ""))
    for i in range(first_full, len(sessions)):
        out.append(f"{sessions[i].render()}\n\n{_demote(bodies[i]).strip()}\n")

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


def session_window(sizes: list[int], budget_chars: int, summaries: int) -> tuple[int, int]:
    """How many sessions to show in full and how many to summarize.

    `sizes` is each session's body length, oldest first. Counted back from the
    newest: the newest is always in full, however long, then each older one
    while it fits in what is left of the budget. The first that does not fit
    ends the run, so a small old session is never pulled forward past a large
    one and the full sessions are always a contiguous recent stretch.
    """
    n_full, left = 0, budget_chars
    for size in reversed(sizes):
        if n_full and size > left:
            break
        n_full += 1
        left -= size
    return n_full, min(summaries, len(sizes) - n_full)


def _session_body(thread_dir: Path, entry: idx.Entry) -> str:
    """A session file's text after its frontmatter, or "" if it cannot be read.

    Split on the delimiters, never parsed, so a file whose frontmatter is not
    valid YAML still yields its body. Uses `frontmatter`'s own boundary so this
    and `split_frontmatter` agree about where the body starts.
    """
    path = thread_dir / entry.link.lstrip("./")
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    handler = YAMLHandler()
    if handler.detect(text):
        try:
            return handler.split(text)[1]
        except ValueError:  # opened but never closed: no frontmatter to drop
            return text
    return text


_HEADING = re.compile(r"#{1,6}\s")
_FENCE = re.compile(r"\s{0,3}(`{3,}|~{3,})")


def _demote(body: str) -> str:
    """Push every heading two levels down, so none can pass for a payload section.

    A session body is free prose and may carry a `## Todos` of its own. Capped
    at six `#`, and fenced code is left alone since a `#` there is a comment.
    """
    out, fence = [], None
    for line in body.split("\n"):
        m = _FENCE.match(line)
        if m:
            marker_ = m.group(1)
            if fence is None:
                fence = marker_
            elif marker_[0] == fence[0] and len(marker_) >= len(fence):
                fence = None
        elif fence is None and _HEADING.match(line):
            hashes = len(line) - len(line.lstrip("#"))
            line = "#" * min(6, hashes + 2) + line[hashes:]
        out.append(line)
    return "\n".join(out)


def _summary(thread_dir: Path, entry: idx.Entry) -> str | None:
    """The file's `summary:`; "" when absent or unreadable; None when the
    frontmatter does not parse."""
    path = thread_dir / entry.link.lstrip("./")
    if not path.is_file():
        return ""
    try:
        fields, _ = split_frontmatter(path.read_text(errors="ignore"), path)
    except OSError:
        return ""
    except ValueError:
        # Loud but not fatal. Frontmatter written before anything parsed it can
        # be invalid YAML (an unquoted summary containing ": " is the common
        # one), and raising here makes a whole thread unresumable over a single
        # legacy file. Callers decide how to say so.
        return None
    return str(fields.get("summary") or "")
