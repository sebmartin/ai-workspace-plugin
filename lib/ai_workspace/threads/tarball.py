"""Tar plumbing for archives. Knows nothing about a thread's schema.

Everything here treats a thread directory as bytes: compress it, verify it,
extract it safely, name it. What a thread's contents mean is the schema's
business, in threads/vN/.
"""

import re
import tarfile
from pathlib import Path

from ai_workspace.text import _yaml_quote


ARCHIVE_SCHEMA_VERSION = 1


_ARCHIVE_BASE_RE = re.compile(r"^\d{4}-[a-z0-9][a-z0-9-]*$")


def _validate_archive_base(base: str) -> bool:
    if not base or ".." in base or "/" in base or "\\" in base or "--" in base:
        return False
    return bool(_ARCHIVE_BASE_RE.match(base))


def _find_symlinks(root: Path) -> list[Path]:
    """Return list of symlink paths (including the root itself) under root."""
    found = []
    if root.is_symlink():
        found.append(root)
    for p in root.rglob("*"):
        if p.is_symlink():
            found.append(p)
    return found


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
