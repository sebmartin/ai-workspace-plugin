"""Which workspace, and where things live inside it.

Answers "where": which directory is the workspace, and where its threads and
archive sit within it. What those directories mean is the concept's business,
in threads/.
"""

import json
from pathlib import Path, PurePosixPath

from ai_workspace.config import read_config, write_config


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


def thread_path(workspace: Path, thread_name: str) -> Path:
    """Where a thread lives inside a resolved workspace."""
    return workspace / "threads" / thread_name


def archive_path(workspace: Path, thread_name: str) -> Path:
    """Where an archived thread lives inside a resolved workspace."""
    return workspace / "archive" / thread_name


def thread_dir(workspace_dir: str, thread_name: str) -> tuple[Path | None, Path | None, str | None]:
    """Resolve a workspace and the directory one of its threads occupies."""
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return None, None, _no_workspace_message(workspace_dir)
    return workspace, thread_path(workspace, thread_name), None


def threads_dir(workspace_dir: str) -> tuple[Path | None, Path | None, str | None]:
    """Resolve a workspace and the directory holding its threads."""
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return None, None, _no_workspace_message(workspace_dir)
    return workspace, workspace / "threads", None


def archive_dir(workspace_dir: str) -> tuple[Path | None, Path | None, str | None]:
    """Resolve a workspace and the directory holding its archives."""
    workspace, _ = _resolve_workspace(workspace_dir)
    if workspace is None:
        return None, None, _no_workspace_message(workspace_dir)
    return workspace, workspace / "archive", None


def resolve_for_create(workspace_dir: str) -> tuple[Path | None, str | None]:
    """Resolve where something new should be created.

    Unlike _resolve_workspace this never silently falls back to the configured
    default, because creating in the wrong workspace is not recoverable by
    retrying. Returns a status the LLM must put to the user instead.
    """
    ws_path = Path(workspace_dir)
    if (ws_path / "threads").is_dir():
        return ws_path, None

    config = read_config()
    default = config.get("default_workspace")
    if default and (Path(default) / "threads").is_dir():
        return None, (
            "Status: AMBIGUOUS_WORKSPACE\n"
            f"No threads/ directory at {workspace_dir}, but a configured workspace "
            f"exists at {default}.\n"
            f'Ask the user: "Create the new thread in the configured '
            f'workspace at {default}, or initialize a new workspace here '
            f'at {workspace_dir}?"\n'
            f"- If they pick the configured workspace, retry create_thread "
            f"with workspace_dir={default}.\n"
            f'- If they pick "here", run the ai-workspace:init skill at '
            f"{workspace_dir}, then retry."
        )
    return None, (
        "Status: NEEDS_INIT\n"
        "No threads workspace found.\n"
        f'Ask the user: "Initialize a new workspace at {workspace_dir}, or use one '
        f'elsewhere?"\n'
        f'- If "here", run the ai-workspace:init skill at {workspace_dir}, then '
        f"retry.\n"
        f'- If "elsewhere", get the path from the user, call '
        f"set_default_workspace, then retry."
    )


def names_one_directory(thread_name: str) -> bool:
    """Whether a name refers to a single directory inside threads/.

    All an existing thread needs. Deliberately not validate_thread_name: that
    enforces the kebab-case convention, which is right for a name being chosen
    and wrong for one already on disk. Workspaces predate the convention and
    hold directories like Q3_planning, and refusing to open them would strand
    the thread while list_threads still advertised it.
    """
    if not thread_name or thread_name in {".", ".."}:
        return False
    if thread_name.startswith(("/", "~")) or "\\" in thread_name:
        return False
    return len(PurePosixPath(thread_name).parts) == 1 and ".." not in thread_name


def _bad_name(thread_name: str) -> str:
    return (
        f"Error: Invalid thread name '{thread_name}'. "
        "A thread name is a single directory inside threads/."
    )


LEGACY_ARCHIVE_DOC = "skills/threads/commands/unpack-legacy-archive.md"


def _thread_name_of(tarball: Path) -> str:
    """The thread name inside a pre-3.0 archive filename.

    Those were named {year}-{thread}.tar.gz. The year prefix existed to keep two
    archives of one thread apart, which a move makes impossible.
    """
    stem = tarball.name[: -len(".tar.gz")]
    head, sep, rest = stem.partition("-")
    return rest if sep and head.isdigit() else stem


ACTIVE = "ACTIVE"
ARCHIVED = "ARCHIVED"
NOT_FOUND = "NOT_FOUND"


def _legacy_archive_of(archives: Path, thread_name: str) -> Path | None:
    """The pre-3.0 tarball holding this thread, if there is one."""
    return next(
        (t for t in archives.glob("*.tar.gz") if _thread_name_of(t) == thread_name),
        None,
    )


def thread_state(workspace: Path, thread_name: str) -> str:
    """Whether a thread of this name is live, archived, or neither.

    A live directory wins. It is the more recent copy, and what sits under
    archive/ with the same name does not decide anything.

    ARCHIVED covers both formats. A pre-3.0 tarball is an archive of that
    thread, so the name is taken; creating over it would leave one name holding
    two archives of two unrelated threads.
    """
    if thread_path(workspace, thread_name).is_dir():
        return ACTIVE
    if archive_path(workspace, thread_name).is_dir():
        return ARCHIVED
    if _legacy_archive_of(workspace / "archive", thread_name) is not None:
        return ARCHIVED
    return NOT_FOUND


def _legacy_archives(archives: Path, threads_root: Path) -> list[Path]:
    """Pre-3.0 tarballs that do not already exist as a thread somewhere.

    A tarball survives being restored, because extracting is a copy where a
    directory restore is a move. Listing it beside the thread it produced is
    the confusing state, so it is hidden once the thread exists either live or
    as a directory archive.
    """
    if not archives.is_dir():
        return []
    out = []
    for tarball in sorted(archives.glob("*.tar.gz")):
        name = _thread_name_of(tarball)
        if (threads_root / name).is_dir() or (archives / name).is_dir():
            continue
        out.append(tarball)
    return out


def _move(source: Path, target: Path, what: str) -> str | None:
    """Rename a directory, or explain why it did not happen. None on success.

    A rename either succeeds whole or raises, so a failure leaves no half-moved
    thread to detect or recover from. shutil.move would instead fall back to
    copying the tree and deleting the source, which is unusable over a network
    volume and can fail partway through the delete.

    A workspace whose archive/ is symlinked to another filesystem gets EXDEV
    here and archiving refuses. That is the intended outcome: the error reaches
    the user, who can decide whether they want a copy.

    The destination is checked first because a rename onto an existing empty
    directory replaces it without complaint.
    """
    if target.exists():
        return f"Error: {what} already exists at {target}."
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
    except OSError as e:
        return f"Error: Could not move {source.name}: {e}. {source.name} is untouched."
    return None


def archive(workspace_dir: str, thread_name: str) -> str:
    """Move a thread out of threads/ and into archive/."""
    if not names_one_directory(thread_name):
        return _bad_name(thread_name)
    workspace, source, error = thread_dir(workspace_dir, thread_name)
    if error:
        return error

    state = thread_state(workspace, thread_name)
    if state == ARCHIVED:
        return f"Error: Thread '{thread_name}' is already archived."
    if state == NOT_FOUND:
        return f"Error: Thread '{thread_name}' not found."

    failure = _move(source, archive_path(workspace, thread_name),
                    f"An archived thread '{thread_name}'")
    return failure or (
        f"Archived '{thread_name}' to archive/{thread_name}/. "
        f"It is read-only there; restore it to work on it again."
    )


def restore(workspace_dir: str, thread_name: str) -> str:
    """Move an archived thread back into threads/."""
    if not names_one_directory(thread_name):
        return _bad_name(thread_name)
    workspace, archives, error = archive_dir(workspace_dir)
    if error:
        return error

    state = thread_state(workspace, thread_name)
    if state == ACTIVE:
        return f"Error: A thread named '{thread_name}' is already in threads/."
    if state == NOT_FOUND:
        return f"Error: No archived thread named '{thread_name}'."

    source = archive_path(workspace, thread_name)
    tarball = None if source.is_dir() else _legacy_archive_of(archives, thread_name)
    if tarball is not None:
        return (
            f"Status: LEGACY_ARCHIVE\n"
            f"'{thread_name}' is archived as {tarball.name}, a tarball from before 3.0, "
            f"which this plugin no longer unpacks.\n"
            f"Read {LEGACY_ARCHIVE_DOC} and follow it."
        )

    failure = _move(source, thread_path(workspace, thread_name), f"A thread '{thread_name}'")
    return failure or f"Restored '{thread_name}' to threads/{thread_name}/."


def list_archived_threads(workspace_dir: str) -> str:
    """List archived threads. Read-only; restore one to work on it."""
    workspace, archives, error = archive_dir(workspace_dir)
    if error:
        return error
    if not archives.is_dir():
        return "No archived threads."

    names = sorted(p.name for p in archives.iterdir() if p.is_dir())
    legacy = _legacy_archives(archives, workspace / "threads")
    if not names and not legacy:
        return "No archived threads."

    lines = [f"{i}. {name}" for i, name in enumerate(names, 1)]
    for tarball in legacy:
        lines.append(
            f"{len(lines) + 1}. {_thread_name_of(tarball)} "
            f"(tarball from before 3.0; see {LEGACY_ARCHIVE_DOC} to restore it)"
        )
    lines.append("")
    lines.append("Archived threads are read-only. Restore one before working on it.")
    return "\n".join(lines)


def list_threads(workspace_dir: str) -> str:
    """List threads, most recently touched first.

    Ordering is the README's modification time, which is an approximation and
    is allowed to be. It is wrong after a workspace is copied and after a bulk
    migration, and it repairs itself the moment a thread is saved, so what stays
    wrong is the tail nobody reads. Asking each schema instead would cost an
    operation on every schema forever to be exact where nobody looks.
    """
    workspace, directory, error = threads_dir(workspace_dir)
    if error:
        return error

    if not directory.exists():
        return "No threads directory found. Use /threads create to start one."

    entries = []
    for item in sorted(directory.iterdir()):
        readme = item / "README.md"
        if item.is_dir() and readme.exists():
            entries.append((item.name, readme.stat().st_mtime))

    if not entries:
        return "No threads found. Use /threads create to start one."

    entries.sort(key=lambda pair: pair[1], reverse=True)
    return "\n".join(f"{i}. {name}" for i, (name, _) in enumerate(entries, 1))
