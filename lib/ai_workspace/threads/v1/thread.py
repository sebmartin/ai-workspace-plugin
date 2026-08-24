"""Schema 1 thread operations: the README is the thread."""

import re
from datetime import date
from pathlib import Path

from workspace_utils import get_template_path, read_config, validate_thread_name

from ai_workspace.workspace import _no_workspace_message, _resolve_workspace, _with_focus


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
