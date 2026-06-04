#!/usr/bin/env python3
"""Threads MCP Server - Tools for managing discussion threads.

Archive-related tools require Python 3.12+ (tarfile filter="data" support).
"""

import json
import re
import shutil
import sys
import tarfile
from datetime import date
from pathlib import Path

ARCHIVE_SCHEMA_VERSION = 1

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "lib"))

from mcp.server.fastmcp import FastMCP
from workspace_utils import (
    get_plugin_dir,
    get_template_path,
    read_config,
    validate_thread_name,
    write_config,
)

mcp = FastMCP("threads")


# ---------- Workspace resolution ----------

def _resolve_workspace(workspace_dir: str) -> tuple[Path | None, str]:
    """Resolve a directory hint to a workspace path.

    Probe order: (1) workspace_dir/threads/, (2) configured default_workspace/threads/.
    Returns (workspace_path, source) where source ∈ {"local", "config", "none"}.
    When source is "none" the path is None.
    """
    ws_path = Path(workspace_dir)
    if (ws_path / "threads").is_dir():
        return ws_path, "local"
    config = read_config()
    default = config.get("default_workspace")
    if default:
        default_path = Path(default)
        if (default_path / "threads").is_dir():
            return default_path, "config"
    return None, "none"


def _no_workspace_message(workspace_dir: str) -> str:
    """Stable text the skill teaches the LLM to recognize."""
    return (
        "Error: NO_WORKSPACE\n"
        f"No threads workspace found at {workspace_dir} or in saved settings.\n"
        "Ask the user for the path to their threads workspace, then call "
        "set_default_workspace with that path before retrying."
    )


def _with_focus(workspace: Path, thread_name: str, body: str) -> str:
    """Prefix a tool's success response with Workspace + Thread headers.

    Used only by tools that shift the session's focus to a specific thread
    (create_thread, resume_thread). The LLM tracks Workspace and Thread
    across the session and uses them for follow-up file ops.
    """
    return (
        f"Workspace: {workspace}\n"
        f"Thread: {workspace / 'threads' / thread_name}\n\n"
        f"{body}"
    )


# ---------- Archive helpers ----------

_ARCHIVE_BASE_RE = re.compile(r"^\d{4}-[a-z0-9][a-z0-9-]*$")


def _validate_archive_base(base: str) -> bool:
    if not base or ".." in base or "/" in base or "\\" in base or "--" in base:
        return False
    return bool(_ARCHIVE_BASE_RE.match(base))


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


def _find_symlinks(root: Path) -> list[Path]:
    """Return list of symlink paths (including the root itself) under root."""
    found = []
    if root.is_symlink():
        found.append(root)
    for p in root.rglob("*"):
        if p.is_symlink():
            found.append(p)
    return found


def _yaml_quote(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _emit_summary_yaml(
    thread_name: str,
    started: str,
    last_active: str,
    archived: str,
    archive_file: str,
    summary: str,
    keywords: list,
    body: str,
) -> str:
    lines = [
        "---",
        f"schema_version: {ARCHIVE_SCHEMA_VERSION}",
        f"thread: {thread_name}",
        f"started: {started}",
        f"last_active: {last_active}",
        f"archived: {archived}",
        f"archive_file: {archive_file}",
        f"summary: {_yaml_quote(summary)}",
    ]
    if keywords:
        lines.append("keywords:")
        for kw in keywords:
            lines.append(f"  - {_yaml_quote(kw)}")
    else:
        lines.append("keywords: []")
    lines.append("---")
    lines.append("")
    lines.append(body if body.endswith("\n") else body + "\n")
    return "\n".join(lines)


def _verify_archive(archive_path: Path, expected_top: str) -> str | None:
    """Return None on success, error string on failure."""
    try:
        with tarfile.open(archive_path, "r:gz") as t:
            names = t.getnames()
    except (tarfile.TarError, OSError) as e:
        return f"Archive integrity check failed: {e}"
    top_levels = {n.split("/")[0] for n in names if n}
    if top_levels != {expected_top}:
        return (
            f"Archive top-level mismatch: expected {{'{expected_top}'}}, "
            f"got {sorted(top_levels)}"
        )
    return None


def _is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _safe_extract(archive_path: Path, target: Path) -> str | None:
    """Extract archive into target, blocking path traversal. Returns None on success."""
    try:
        with tarfile.open(archive_path, "r:gz") as t:
            for m in t.getmembers():
                name = m.name
                if name.startswith("/") or "\\" in name or ".." in Path(name).parts:
                    return f"Refused to extract member '{name}': unsafe path"
                if not _is_within(target / name, target):
                    return f"Refused to extract member '{name}': escapes target"
            t.extractall(target, filter="data")
    except (tarfile.TarError, OSError) as e:
        return f"Extraction failed: {e}"
    return None


def _read_top_level(archive_path: Path) -> tuple[set, str | None]:
    """Return (top_level_names, error_or_None)."""
    try:
        with tarfile.open(archive_path, "r:gz") as t:
            names = t.getnames()
    except (tarfile.TarError, OSError) as e:
        return set(), f"Failed to read archive: {e}"
    return {n.split("/")[0] for n in names if n}, None


def _find_archive(archive_dir: Path, base: str) -> Path | None:
    tar_path = archive_dir / f"{base}.tar.gz"
    return tar_path if tar_path.exists() else None


@mcp.tool()
def list_threads(workspace_dir: str) -> str:
    """List all discussion threads sorted by most recent activity.

    Resolves the workspace from `workspace_dir` (local threads/ first, then configured
    default). Returns `Error: NO_WORKSPACE` if neither is available.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    threads_dir = workspace / "threads"

    if not threads_dir.exists():
        return "No threads directory found. Use /threads create to start one."

    entries = []
    for item in threads_dir.iterdir():
        if item.is_dir():
            readme = item / "README.md"
            if readme.exists():
                entries.append((item.name, readme.stat().st_mtime))

    if not entries:
        return "No threads found. Use /threads create to start one."

    entries.sort(key=lambda x: x[1], reverse=True)
    return "\n".join(f"{i}. {name}" for i, (name, _) in enumerate(entries, 1))


@mcp.tool()
def resume_thread(workspace_dir: str, thread_name: str) -> str:
    """Resolve the workspace and thread path, and return the full README content.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the thread (kebab-case).
    """
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    readme_path = workspace / "threads" / thread_name / "README.md"

    if not readme_path.exists():
        return f"Error: Thread '{thread_name}' not found."

    return _with_focus(workspace, thread_name, readme_path.read_text())


@mcp.tool()
def create_thread(workspace_dir: str, thread_name: str) -> str:
    """Create a new discussion thread with the standard directory structure.

    Resolves the workspace from `workspace_dir`. If `workspace_dir` has a threads/ dir, the thread
    is created there. If not, the tool may return a status the LLM must surface
    to the user:
    - `Status: AMBIGUOUS_WORKSPACE` when a configured default workspace exists
      (user picks between configured workspace vs initialising a new one here).
    - `Status: NEEDS_INIT` when no workspace exists anywhere (user picks between
      initialising here vs supplying a path).

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns a status question
            (AMBIGUOUS_WORKSPACE or NEEDS_INIT) if neither works.
        thread_name: Name of the thread (kebab-case: lowercase letters, numbers, hyphens).
    """
    if not validate_thread_name(thread_name):
        return (
            f"Error: Invalid thread name '{thread_name}'. "
            "Thread names must be kebab-case (lowercase letters, numbers, hyphens). "
            "Examples: my-thread, api-redesign, auth-refactor"
        )

    ws_path = Path(workspace_dir)
    if (ws_path / "threads").is_dir():
        workspace = ws_path
    else:
        config = read_config()
        default = config.get("default_workspace")
        if default and (Path(default) / "threads").is_dir():
            return (
                "Status: AMBIGUOUS_WORKSPACE\n"
                f"No threads/ directory at {workspace_dir}, but a configured workspace "
                f"exists at {default}.\n"
                f'Ask the user: "Create the new thread in the configured '
                f'workspace at {default}, or initialize a new workspace here '
                f'at {workspace_dir}?"\n'
                f"- If they pick the configured workspace, retry create_thread "
                f"with workspace_dir={default}.\n"
                f"- If they pick \"here\", run the ai-workspace:init skill at "
                f"{workspace_dir}, then retry."
            )
        return (
            "Status: NEEDS_INIT\n"
            "No threads workspace found.\n"
            f'Ask the user: "Initialize a new workspace at {workspace_dir}, or use one '
            f'elsewhere?"\n'
            f"- If \"here\", run the ai-workspace:init skill at {workspace_dir}, then "
            f"retry.\n"
            f"- If \"elsewhere\", get the path from the user, call "
            f"set_default_workspace, then retry."
        )

    thread_dir = workspace / "threads" / thread_name

    if thread_dir.exists():
        return f"Error: Thread '{thread_name}' already exists."

    # Create directory structure
    for subdir in ("sessions", "decisions", "attachments", "artifacts"):
        (thread_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Write README from template, substituting placeholders
    today = date.today().isoformat()
    template = get_template_path("thread-template.md").read_text()
    readme = re.sub(r"\[Thread Name\]", thread_name, template)
    readme = re.sub(r"\[YYYY-MM-DD\]", today, readme)
    (thread_dir / "README.md").write_text(readme)

    return _with_focus(
        workspace, thread_name, f"Created thread '{thread_name}' at {thread_dir}"
    )



@mcp.tool()
def get_skill_file(relative_path: str) -> str:
    """Return the contents of a file from the plugin directory.

    Use this to read skill reference files (e.g. commands/save-thread.md)
    without needing direct filesystem access. Paths are resolved relative
    to the plugin root and must not escape it.

    Args:
        relative_path: Path relative to the plugin root (e.g., "skills/threads/commands/save-thread.md").
    """
    plugin_root = get_plugin_dir().resolve()
    target = (plugin_root / relative_path).resolve()
    try:
        target.relative_to(plugin_root)
    except ValueError:
        return "Error: Path escapes plugin directory."
    if not target.exists():
        return f"Error: File '{relative_path}' not found in plugin."
    if not target.is_file():
        return f"Error: '{relative_path}' is not a file."
    return target.read_text()


@mcp.tool()
def resolve_workspace(workspace_dir: str) -> str:
    """Resolve which workspace directory to use for thread operations.

    Checks for a local threads/ directory first, then falls back to the
    configured default workspace. Kept as an optional diagnostic — operating
    tools (list_threads, create_thread, etc.) resolve internally now.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            caller's current working directory. The tool probes this directory
            for threads/, falls back to the configured default, and returns the
            result with its source ("local", "config", or "none").
    """
    workspace, source = _resolve_workspace(workspace_dir)
    return json.dumps(
        {
            "workspace_dir": str(workspace) if workspace is not None else None,
            "source": source,
        }
    )


@mcp.tool()
def set_default_workspace(workspace_path: str) -> str:
    """Set the default workspace directory for thread operations.

    This is used when running /threads from outside a workspace directory.
    The path is persisted in the plugin's global config.

    Args:
        workspace_path: Absolute path to a directory containing a threads/ folder.
    """
    ws_path = Path(workspace_path)

    if not ws_path.is_dir():
        return f"Error: Directory '{workspace_path}' does not exist."

    if not (ws_path / "threads").is_dir():
        return (
            f"Error: No threads/ directory found in '{workspace_path}'. "
            "The workspace must contain a threads/ directory."
        )

    config = read_config()
    config["default_workspace"] = str(ws_path.resolve())
    write_config(config)

    return f"Default workspace set to '{ws_path.resolve()}'."


@mcp.tool()
def archive_thread(
    workspace_dir: str,
    thread_name: str,
    summary: str,
    keywords: list,
    body: str,
) -> str:
    """Archive a thread: compress its directory, write a searchable summary, delete the original.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        thread_name: Name of the thread to archive (kebab-case).
        summary: One-line summary; goes into frontmatter `summary:` field.
        keywords: List of short keyword strings for search; normalised (lowercased, deduped).
        body: Topic-rich markdown narrative — the embedding payload. Cover what was discussed,
              decisions made, systems/files/people touched, key vocabulary and synonyms.
    """
    if not validate_thread_name(thread_name):
        return f"Error: Invalid thread name '{thread_name}'."

    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    thread_dir = workspace / "threads" / thread_name
    readme_path = thread_dir / "README.md"
    if not readme_path.exists():
        return f"Error: Thread '{thread_name}' not found."

    symlinks = _find_symlinks(thread_dir)
    if symlinks:
        rels = ", ".join(
            str(p.relative_to(thread_dir)) if p != thread_dir else "."
            for p in symlinks[:5]
        )
        more = f" (+{len(symlinks) - 5} more)" if len(symlinks) > 5 else ""
        return (
            f"Error: Thread '{thread_name}' contains symlinks: {rels}{more}. "
            "Remove or resolve them before archiving — symlinks would leak "
            "out-of-thread paths into the archive."
        )

    normalised_keywords = list(
        dict.fromkeys(k.strip().lower() for k in (keywords or []) if k and k.strip())
    )

    started, last_active = _parse_readme_dates(readme_path, thread_dir)
    archived = date.today().isoformat()

    base = f"{date.today().year}-{thread_name}"
    archive_dir = workspace / "archive"
    archive_path = archive_dir / f"{base}.tar.gz"
    summary_path = archive_dir / f"{base}.md"

    if summary_path.exists() or archive_path.exists():
        return f"Error: Archive '{base}' already exists."

    archive_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(archive_path, "w:gz") as t:
            t.add(thread_dir, arcname=thread_name)
    except OSError as e:
        archive_path.unlink(missing_ok=True)
        return f"Error: Failed to write archive: {e}"

    err = _verify_archive(archive_path, thread_name)
    if err:
        archive_path.unlink(missing_ok=True)
        return f"Error: {err}"

    try:
        summary_text = _emit_summary_yaml(
            thread_name=thread_name,
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
        f"Archived '{thread_name}' to archive/{base}.tar.gz "
        f"(summary: archive/{base}.md)"
    )


@mcp.tool()
def restore_thread(workspace_dir: str, archive_base: str) -> str:
    """Restore an archived thread back into threads/, deleting the archive on success.

    Writes a sessions/{YYYYMMDD}-restored.md file inside the restored thread
    capturing the archive-time summary and body, so the LLM's interpretation
    survives as thread history.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
        archive_base: Filename stem of the archive (e.g. '2026-last-months-project').
    """
    if not _validate_archive_base(archive_base):
        return f"Error: Invalid archive base '{archive_base}'."

    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    archive_dir = workspace / "archive"

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

    summary_path = archive_dir / f"{archive_base}.md"
    session_err = _write_restored_session(extracted, summary_path)
    if session_err:
        shutil.rmtree(staging, ignore_errors=True)
        return f"Error: {session_err}"

    threads_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(extracted), str(threads_dir / target_name))
    shutil.rmtree(staging, ignore_errors=True)

    archive_path.unlink()
    summary_path.unlink(missing_ok=True)

    suffix_note = ""
    if target_name != original_name:
        suffix_note = f" (renamed from '{original_name}' to avoid collision)"
    return f"Restored to threads/{target_name}{suffix_note}"


def _pick_restore_name(threads_dir: Path, original: str) -> str | None:
    if not (threads_dir / original).exists():
        return original
    base = f"{original}-restored"
    if not (threads_dir / base).exists():
        return base
    for i in range(2, 100):
        candidate = f"{base}-{i}"
        if not (threads_dir / candidate).exists():
            return candidate
    return None


def _write_restored_session(thread_root: Path, summary_path: Path) -> str | None:
    """Write a sessions/{YYYYMMDD}-restored.md file inside thread_root.

    Pulls summary, body, and archive dates from summary_path's frontmatter.
    Returns an error message on failure, None on success. Missing summary_path
    is non-fatal — restore should still succeed.
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

    sessions_dir = thread_root / "sessions"
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


def _extract_body(text: str) -> str:
    """Return the markdown body that follows the closing '---' of frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text.strip()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1:]).strip()
    return ""


@mcp.tool()
def list_archived_threads(workspace_dir: str) -> str:
    """List archived threads with metadata for quick search.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    archive_dir = workspace / "archive"
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


def _extract_yaml_field(text: str, field: str) -> str | None:
    m = re.search(rf'^{field}:\s*"?([^"\n]+?)"?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_yaml_keywords(text: str) -> list:
    inline = re.search(r"^keywords:\s*\[\s*\]\s*$", text, re.MULTILINE)
    if inline:
        return []
    block = re.search(
        r"^keywords:\s*\n((?:  - .+\n?)+)", text, re.MULTILINE
    )
    if not block:
        return []
    items = []
    for line in block.group(1).splitlines():
        m = re.match(r'^  - "?([^"]*)"?\s*$', line)
        if m:
            items.append(m.group(1).strip())
    return items


@mcp.tool()
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

    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    archive_dir = workspace / "archive"

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


@mcp.tool()
def purge_archive_tmp(workspace_dir: str) -> str:
    """Wipe archive/tmp/ entirely. Safe — every file in it is regeneratable from sibling archives.

    Args:
        workspace_dir: Directory hint for locating the workspace; typically the
            tracked workspace path from session context, or the caller's cwd on
            a fresh invocation. The tool probes this directory for threads/,
            falls back to the configured default, and returns NO_WORKSPACE if neither works.
    """
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return _no_workspace_message(workspace_dir)
    tmp_dir = workspace / "archive" / "tmp"
    if not tmp_dir.exists():
        return "archive/tmp/ is already clean."
    shutil.rmtree(tmp_dir)
    return "Purged archive/tmp/."


if __name__ == "__main__":
    mcp.run()
