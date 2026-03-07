#!/usr/bin/env python3
"""Threads MCP Server - Tools for managing discussion threads."""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from mcp.server.fastmcp import FastMCP
from workspace_utils import get_template_path, get_workspace_dir, validate_thread_name

mcp = FastMCP("threads")


@mcp.tool()
def list_threads(workspace_dir: str) -> str:
    """List all discussion threads sorted by most recent activity.

    Args:
        workspace_dir: Absolute path to the user's workspace directory.
    """
    workspace = get_workspace_dir(Path(workspace_dir))
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
def get_thread_status(workspace_dir: str, thread_name: str) -> str:
    """Get the Quick Resume section from a thread's README.

    Args:
        workspace_dir: Absolute path to the user's workspace directory.
        thread_name: Name of the thread (kebab-case).
    """
    workspace = get_workspace_dir(Path(workspace_dir))
    readme_path = workspace / "threads" / thread_name / "README.md"

    if not readme_path.exists():
        return f"Error: Thread '{thread_name}' not found."

    lines = readme_path.read_text().split("\n")
    in_section = False
    result = []

    for line in lines:
        if line.strip() == "## Quick Resume":
            in_section = True
            continue
        elif in_section and line.startswith("## "):
            break
        elif in_section and not line.strip().startswith("> **Purpose**"):
            result.append(line)

    if not result:
        return f"Error: No Quick Resume section found in thread '{thread_name}'."

    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()

    return "\n".join(result)


@mcp.tool()
def create_thread(workspace_dir: str, thread_name: str) -> str:
    """Create a new discussion thread with the standard directory structure.

    Args:
        workspace_dir: Absolute path to the user's workspace directory.
        thread_name: Name of the thread (kebab-case: lowercase letters, numbers, hyphens).
    """
    if not validate_thread_name(thread_name):
        return (
            f"Error: Invalid thread name '{thread_name}'. "
            "Thread names must be kebab-case (lowercase letters, numbers, hyphens). "
            "Examples: my-thread, api-redesign, auth-refactor"
        )

    workspace = get_workspace_dir(Path(workspace_dir))
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

    return f"Created thread '{thread_name}' at {thread_dir}"


@mcp.tool()
def get_template(template_name: str) -> str:
    """Return the contents of a plugin template file.

    Args:
        template_name: Filename of the template (e.g., "thread-template.md").
    """
    path = get_template_path(template_name)
    if not path.exists():
        templates_dir = get_template_path(".")
        available = [p.name for p in templates_dir.iterdir() if p.is_file()]
        return f"Error: Template '{template_name}' not found. Available: {', '.join(sorted(available))}"
    return path.read_text()


if __name__ == "__main__":
    mcp.run()
