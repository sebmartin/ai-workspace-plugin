#!/usr/bin/env python3
"""List all discussion threads sorted by most recent activity."""

import os
import sys
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


def list_threads():
    """List all threads sorted by most recent modification."""
    threads_dir = get_workspace_dir() / "threads"

    if not threads_dir.exists():
        print("No threads directory found", file=sys.stderr)
        sys.exit(1)

    # Find all thread README files
    thread_readmes = []
    for item in threads_dir.iterdir():
        if item.is_dir():
            readme = item / "README.md"
            if readme.exists():
                # Get modification time
                mtime = readme.stat().st_mtime
                thread_readmes.append((item.name, mtime))

    # Sort by modification time (most recent first)
    thread_readmes.sort(key=lambda x: x[1], reverse=True)

    # Format output
    if not thread_readmes:
        print("No threads found")
    else:
        for i, (name, _) in enumerate(thread_readmes, 1):
            print(f"{i}. {name}")


if __name__ == "__main__":
    list_threads()
