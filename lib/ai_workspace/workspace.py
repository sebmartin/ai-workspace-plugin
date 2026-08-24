"""Workspace resolution — shape-independent."""

import json
from pathlib import Path

from workspace_utils import read_config, write_config


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
