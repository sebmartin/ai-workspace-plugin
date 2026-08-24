"""Operations on the workspace's archive/ directory.

Archiving a thread is a thread operation and lives in the schema, since it has
to read the thread's own layout. What is here works on archive/ itself:
restoring out of it, listing it, and cleaning its scratch space. Restore is
the odd one, because the thread does not exist to be dispatched on until it
has been extracted, so extraction happens first and the schema is consulted
afterwards, while the thread is still staged.
"""

import shutil
from datetime import date
from pathlib import Path

from ai_workspace import workspace as ws
from ai_workspace.text import _extract_yaml_field, _extract_yaml_keywords
from ai_workspace.threads._schema import at as _at, implementation
from ai_workspace.threads.tarball import (
    _find_archive,
    _is_within,
    _pick_restore_name,
    _read_top_level,
    _safe_extract,
    _validate_archive_base,
)


def restore(workspace_dir: str, archive_base: str) -> str:
    """Restore an archived thread back into threads/, deleting the archive on success.

    Extraction is schema-free, so it happens first; the schema is read from the
    extracted directory and asked to record the restore in whatever form it
    keeps history. That record is written while the thread is still staged, so
    a failure there leaves nothing in threads/.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        archive_base: Filename stem of the archive (e.g. '2026-last-months-project').
    """
    if not _validate_archive_base(archive_base):
        return f"Error: Invalid archive base '{archive_base}'."

    workspace, archive_dir, error = ws.archive_dir(workspace_dir)
    if error:
        return error

    archive_path = _find_archive(archive_dir, archive_base)
    if archive_path is None:
        return f"Error: Archive '{archive_base}' not found."

    if not _is_within(archive_path, archive_dir):
        return f"Error: Archive '{archive_base}' resolves outside workspace/archive/."

    top_levels, err = _read_top_level(archive_path)
    if err:
        return f"Error: {err}"
    if len(top_levels) != 1:
        return (
            f"Error: Archive must have a single top-level directory; "
            f"got {sorted(top_levels)}"
        )
    original_name = top_levels.pop()

    threads_dir = workspace / "threads"
    target_name = _pick_restore_name(threads_dir, original_name)
    if target_name is None:
        return (
            f"Error: Too many '-restored' collisions for '{original_name}'. "
            "Resolve manually."
        )

    staging = archive_dir / "tmp" / f"_restore_{archive_base}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    err = _safe_extract(archive_path, staging)
    if err:
        shutil.rmtree(staging, ignore_errors=True)
        return f"Error: {err}"

    extracted = staging / original_name
    if not extracted.is_dir():
        shutil.rmtree(staging, ignore_errors=True)
        return f"Error: Extracted archive missing expected top-level '{original_name}'."

    thread, err = _at(workspace, target_name, extracted)
    if err:
        shutil.rmtree(staging, ignore_errors=True)
        return err

    summary_path = archive_dir / f"{archive_base}.md"
    session_err = implementation(thread).note_restore(thread, summary_path)
    if session_err:
        shutil.rmtree(staging, ignore_errors=True)
        return f"Error: {session_err}"

    threads_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(extracted), str(ws.thread_path(workspace, target_name)))
    shutil.rmtree(staging, ignore_errors=True)

    archive_path.unlink()
    summary_path.unlink(missing_ok=True)

    suffix_note = ""
    if target_name != original_name:
        suffix_note = f" (renamed from '{original_name}' to avoid collision)"
    return f"Restored to threads/{target_name}{suffix_note}"


def list_archived_threads(workspace_dir: str) -> str:
    """List archived threads with metadata for quick search.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    workspace, archive_dir, error = ws.archive_dir(workspace_dir)
    if error:
        return error
    if not archive_dir.exists():
        return "No archived threads found."

    entries = []
    for md_path in archive_dir.glob("*.md"):
        base = md_path.stem
        if not _validate_archive_base(base):
            continue
        archive_path = _find_archive(archive_dir, base)
        if archive_path is None:
            continue
        text = md_path.read_text()
        started = _extract_yaml_field(text, "started") or "?"
        last_active = _extract_yaml_field(text, "last_active") or "?"
        archived = _extract_yaml_field(text, "archived") or "?"
        keywords = _extract_yaml_keywords(text)
        sort_key = archived if archived != "?" else "0"
        entries.append((sort_key, base, started, last_active, archived, keywords))

    if not entries:
        return "No archived threads found."

    entries.sort(key=lambda e: e[0], reverse=True)
    lines = []
    for _, base, started, last_active, archived, keywords in entries:
        kw_str = ", ".join(keywords) if keywords else "—"
        lines.append(
            f"{base} — started {started}, last active {last_active}, "
            f"archived {archived} [keywords: {kw_str}]"
        )
    return "\n".join(lines)


def inspect_archive(workspace_dir: str, archive_base: str) -> str:
    """Extract an archive into archive/tmp/{base}/ for inspection without restoring.

    The original .md and .tar.gz are left in place. Repeated calls overwrite cleanly.
    Use /threads purge-tmp when done. The extraction target stays inside the workspace.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        archive_base: Filename stem of the archive (e.g. '2026-last-months-project').
    """
    if not _validate_archive_base(archive_base):
        return f"Error: Invalid archive base '{archive_base}'."

    workspace, archive_dir, error = ws.archive_dir(workspace_dir)
    if error:
        return error

    archive_path = _find_archive(archive_dir, archive_base)
    if archive_path is None:
        return f"Error: Archive '{archive_base}' not found."

    if not _is_within(archive_path, archive_dir):
        return f"Error: Archive '{archive_base}' resolves outside workspace/archive/."

    top_levels, err = _read_top_level(archive_path)
    if err:
        return f"Error: {err}"
    thread_name = next(iter(top_levels), archive_base)

    target = archive_dir / "tmp" / archive_base
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    err = _safe_extract(archive_path, target)
    if err:
        shutil.rmtree(target, ignore_errors=True)
        return f"Error: {err}"

    return (
        f"Extracted to archive/tmp/{archive_base}/{thread_name}/ — read directly to inspect. "
        f"Use /threads restore {archive_base} to bring it back, "
        "or /threads purge-tmp when done."
    )


def purge_archive_tmp(workspace_dir: str) -> str:
    """Wipe archive/tmp/ entirely. Safe — every file in it is regeneratable from sibling archives.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    workspace, archive_dir, error = ws.archive_dir(workspace_dir)
    if error:
        return error
    tmp_dir = archive_dir / "tmp"
    if not tmp_dir.exists():
        return "archive/tmp/ is already clean."
    shutil.rmtree(tmp_dir)
    return "Purged archive/tmp/."
