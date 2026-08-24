"""Which workspace, and where things live inside it.

Answers "where": which directory is the workspace, and where its threads and
archive sit within it. What those directories mean is the concept's business,
in threads/.
"""

import json
from pathlib import Path

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
