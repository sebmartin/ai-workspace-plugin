"""Schema 1 thread operations: the README is the thread.

Everything a schema 1 thread knows about itself is in README.md, so resume is
a file read and create is a directory plus that file. No marker is written:
this schema predates versioning, and its threads are identified by not having
one.

Archiving is here too, because the parts of it that are not tar plumbing are
exactly the parts that read this layout: the dates come out of the README, and
a restore is recorded by dropping a file into sessions/.
"""

import re
import shutil
import tarfile
from datetime import date
from pathlib import Path

from ai_workspace.plugin import get_template_path
from ai_workspace.threads.tarball import _emit_summary_yaml, _find_symlinks, _verify_archive
from ai_workspace.text import _extract_body, _extract_yaml_field

SUBDIRS = ("sessions", "decisions", "attachments", "artifacts")


def resume(thread) -> str:
    """The whole README, which for this schema is the whole thread."""
    return (thread.dir / "README.md").read_text()


def create(thread) -> str:
    """Lay out a new thread directory and its README."""
    for subdir in SUBDIRS:
        (thread.dir / subdir).mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    template = get_template_path("thread-template.md").read_text()
    readme = re.sub(r"\[Thread Name\]", thread.name, template)
    readme = re.sub(r"\[YYYY-MM-DD\]", today, readme)
    (thread.dir / "README.md").write_text(readme)

    return f"Created thread '{thread.name}' at {thread.dir}"


def _parse_readme_dates(readme_path: Path, thread_dir: Path) -> tuple[str, str]:
    started = None
    last_active = None
    if readme_path.exists():
        text = readme_path.read_text()
        m = re.search(r"^\*\*Started\*\*:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        if m:
            started = m.group(1)
        m = re.search(r"^\*\*Last Session\*\*:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        if m:
            last_active = m.group(1)
    if not started:
        started = date.fromtimestamp(thread_dir.stat().st_ctime).isoformat()
    if not last_active:
        mtimes = [p.stat().st_mtime for p in thread_dir.rglob("*") if p.is_file()]
        last_active = date.fromtimestamp(
            max(mtimes) if mtimes else thread_dir.stat().st_mtime
        ).isoformat()
    return started, last_active


def archive(thread, summary: str, keywords: list, body: str) -> str:
    """Compress the thread, write a searchable summary, delete the original."""
    thread_dir = thread.dir
    readme_path = thread_dir / "README.md"

    symlinks = _find_symlinks(thread_dir)
    if symlinks:
        rels = ", ".join(
            str(p.relative_to(thread_dir)) if p != thread_dir else "."
            for p in symlinks[:5]
        )
        more = f" (+{len(symlinks) - 5} more)" if len(symlinks) > 5 else ""
        return (
            f"Error: Thread '{thread.name}' contains symlinks: {rels}{more}. "
            "Remove or resolve them before archiving. Symlinks would leak "
            "out-of-thread paths into the archive."
        )

    normalised_keywords = list(
        dict.fromkeys(k.strip().lower() for k in (keywords or []) if k and k.strip())
    )

    started, last_active = _parse_readme_dates(readme_path, thread_dir)
    archived = date.today().isoformat()

    base = f"{date.today().year}-{thread.name}"
    archive_dir = thread.workspace / "archive"
    archive_path = archive_dir / f"{base}.tar.gz"
    summary_path = archive_dir / f"{base}.md"

    if summary_path.exists() or archive_path.exists():
        return f"Error: Archive '{base}' already exists."

    archive_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(archive_path, "w:gz") as t:
            t.add(thread_dir, arcname=thread.name)
    except OSError as e:
        archive_path.unlink(missing_ok=True)
        return f"Error: Failed to write archive: {e}"

    err = _verify_archive(archive_path, thread.name)
    if err:
        archive_path.unlink(missing_ok=True)
        return f"Error: {err}"

    try:
        summary_text = _emit_summary_yaml(
            thread_name=thread.name,
            started=started,
            last_active=last_active,
            archived=archived,
            archive_file=f"{base}.tar.gz",
            summary=summary,
            keywords=normalised_keywords,
            body=body,
        )
        summary_path.write_text(summary_text)
    except OSError as e:
        archive_path.unlink(missing_ok=True)
        return f"Error: Failed to write summary: {e}"

    shutil.rmtree(thread_dir)

    return (
        f"Archived '{thread.name}' to archive/{base}.tar.gz "
        f"(summary: archive/{base}.md)"
    )


def note_restore(thread, summary_path: Path) -> str | None:
    """Record the restore as a session file inside the thread.

    Pulls summary, body, and archive dates from summary_path's frontmatter.
    Returns an error message on failure, None on success. Missing summary_path
    is non-fatal: restore should still succeed.
    """
    if not summary_path.exists():
        return None
    try:
        text = summary_path.read_text()
    except OSError as e:
        return f"Failed to read archive summary: {e}"

    archived_date = _extract_yaml_field(text, "archived") or "?"
    last_active = _extract_yaml_field(text, "last_active") or "?"
    summary = _extract_yaml_field(text, "summary") or ""
    body = _extract_body(text)

    sessions_dir = thread.dir / "sessions"
    try:
        sessions_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return f"Failed to create sessions/ in restored thread: {e}"

    today_compact = date.today().strftime("%Y%m%d")
    session_name = f"{today_compact}-restored.md"
    session_path = sessions_dir / session_name
    n = 2
    while session_path.exists():
        session_path = sessions_dir / f"{today_compact}-restored-{n}.md"
        n += 1

    content = (
        "# Session: Restored from archive\n\n"
        f"**Date**: {date.today().isoformat()}\n"
        f"**Archived**: {archived_date}\n"
        f"**Last active before archive**: {last_active}\n\n"
        "## Summary at archive time\n\n"
        f"{summary or '(no summary recorded)'}\n\n"
        "## Archive notes\n\n"
        f"{body if body else '(no body recorded)'}\n"
    )
    try:
        session_path.write_text(content)
    except OSError as e:
        return f"Failed to write restored-session file: {e}"
    return None
