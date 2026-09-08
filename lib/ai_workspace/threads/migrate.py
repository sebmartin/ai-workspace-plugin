"""Checks that make a migration safe, and the audit that says whether it worked.

There is no migration tool. The two shapes are close, the assistant can read a
schema 1 README unaided, and every write it needs already exists. What is here
is the deterministic part: whether a safety net exists before starting, and
whether the converted copy actually kept everything.
"""

import subprocess
from pathlib import Path

from ai_workspace.threads.v2 import ids
from ai_workspace.threads.v2 import index as idx

STAGING_SUFFIX = "-v2"
BACKUP_SUFFIX = "-v1"


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, timeout=30)
        return proc.returncode, proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def safety_check(workspace: Path, thread_name: str) -> str:
    """Report whether the thread could be recovered if the migration goes wrong.

    Advice, never a gate. The plugin does not commit, so this states what is
    true and lets the user decide.
    """
    thread_dir = workspace / "threads" / thread_name
    code, _ = _git(["rev-parse", "--is-inside-work-tree"], thread_dir)
    if code != 0:
        return (
            "No git repository covers this thread.\n"
            "The migration keeps the original as "
            f"'{thread_name}{BACKUP_SUFFIX}' and never deletes anything, so it "
            "stays recoverable — but nothing protects against mistakes made "
            "after the swap.\n"
            "Cheapest fix: `git init` and commit the workspace, or copy the "
            "thread somewhere outside it, before continuing."
        )
    code, out = _git(["status", "--porcelain", "--", f"threads/{thread_name}"], workspace)
    if code != 0:
        return "A git repository is present but its status could not be read."
    if out:
        n = len(out.splitlines())
        return (
            f"{n} uncommitted change(s) in threads/{thread_name}.\n"
            "The pre-migration state is not recoverable until they are committed.\n"
            "Commit them first, then migrate."
        )
    return f"threads/{thread_name} is committed and clean. Safe to migrate."


# Sections a schema 1 README has and a schema 2 one does not. A half-converted
# README is the likeliest way a migration goes wrong and the hardest to see,
# since every index can be complete while the README is still the old document.
V1_README_MARKERS = (
    "## Quick Resume",
    "**Next steps**:",
    "## Open Questions",
    "### Resources",
)


def _indexed_targets(thread_dir: Path, kind: str) -> set[str]:
    """Filenames one kind's index accounts for, in force or retired.

    Per kind, not across all of them. Unioning every index meant a todo linking
    to ./sessions/foo.md vouched for foo.md being in the *sessions* index, and
    the migration reference tells you to link an orphan todo to the session it
    came from. So the false negative fired on exactly the threads that followed
    the instructions, and a thread with no sessions index at all passed.
    """
    names: set[str] = set()
    for retired in (False, True):
        entries, _ = idx.read(thread_dir, kind, retired)
        names.update(Path(e.link).name for e in entries)
    return names


def audit(original: Path, converted: Path) -> str:
    """Compare the original tree against the converted copy.

    Deterministic on purpose: files present in one and not the other, entries
    pointing at nothing, and entries out of date order are set and sort
    operations. Only whether the Quick Resume prose survived as todos and Status
    needs judgment, and that is left to a reader.
    """
    problems: list[str] = []

    for kind in ("sessions", "decisions", "artifacts", "attachments"):
        src, dst = original / kind, converted / kind
        if not src.is_dir():
            continue
        src_names = {p.name for p in src.iterdir() if idx.is_content(p)}
        dst_names = {p.name for p in dst.iterdir() if idx.is_content(p)} if dst.is_dir() else set()
        missing = sorted(src_names - dst_names)
        if missing:
            problems.append(f"{kind}: {len(missing)} file(s) missing from the copy: "
                            + ", ".join(missing[:5]))

    for kind in ("sessions", "decisions", "artifacts"):
        src = original / kind
        if not src.is_dir():
            continue
        indexed = _indexed_targets(converted, kind)
        # A subdirectory is one artifact, so compare top-level entries only, and
        # `.DS_Store` and its `._name` siblings are not entries at all. A real
        # thread had fifty of those, and reporting them as missing content is
        # how an audit teaches its reader to stop reading it.
        unindexed = sorted(
            p.name for p in src.iterdir()
            if idx.is_content(p) and p.name not in indexed
        )
        if unindexed:
            problems.append(f"{kind}: {len(unindexed)} entr(y/ies) not in any index: "
                            + ", ".join(unindexed[:5]))

    for kind in idx.TYPES:
        entries, _ = idx.read(converted, kind)
        for entry in entries:
            if not (converted / entry.link.lstrip("./")).exists():
                problems.append(f"{kind}: {entry.id} links to a missing file ({entry.link})")
        ordering = [e.id.split("-")[0] for e in entries]
        if ordering != sorted(ordering):
            problems.append(f"{kind}: index is not in date order")

    readme = converted / "README.md"
    residue = sorted(
        marker for marker in V1_README_MARKERS
        if readme.is_file() and marker in readme.read_text(errors="ignore")
    )
    if residue:
        problems.append(
            "README still holds schema 1 sections: " + ", ".join(residue)
        )

    unknown = sum(
        1 for kind in idx.TYPES
        for e in idx.read(converted, kind)[0]
        if e.id.startswith(ids.UNKNOWN)
    )

    lines = [f"Audit of {converted.name} against {original.name}:"]
    if unknown:
        lines.append(f"  {unknown} entr(y/ies) had no derivable date and are marked unknown.")
    if problems:
        lines.append("  PROBLEMS:")
        lines.extend(f"    - {p}" for p in problems)
    else:
        lines.append("  No missing files, no dangling links, indexes in order.")
    lines.append("  Still needs a reader: whether Quick Resume survived as todos and Status.")
    return "\n".join(lines)
