#!/usr/bin/env python3
"""Threads MCP Server - Tools for managing discussion threads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from mcp.server.fastmcp import FastMCP
from workspace_utils import get_workspace_dir

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


if __name__ == "__main__":
    mcp.run()
