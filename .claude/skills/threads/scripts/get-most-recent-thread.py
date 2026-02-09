#!/usr/bin/env python3
"""Get the name of the most recently updated thread."""

import os
import sys
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


def get_most_recent_thread():
    """Get the name of the most recently active thread.

    First checks for explicitly saved last active thread,
    then falls back to README.md modification time.
    """
    workspace_dir = get_workspace_dir()
    threads_dir = workspace_dir / "threads"
    last_active_file = workspace_dir / ".last-active-thread"

    if not threads_dir.exists():
        print("No threads directory found", file=sys.stderr)
        sys.exit(1)

    # Check for explicitly saved last active thread
    if last_active_file.exists():
        try:
            last_active = last_active_file.read_text().strip()
            thread_readme = threads_dir / last_active / "README.md"
            if thread_readme.exists():
                print(last_active)
                return
        except Exception:
            # Fall through to mtime-based detection
            pass

    # Fall back to README.md modification time
    most_recent = None
    most_recent_time = 0

    for item in threads_dir.iterdir():
        if item.is_dir():
            readme = item / "README.md"
            if readme.exists():
                mtime = readme.stat().st_mtime
                if mtime > most_recent_time:
                    most_recent_time = mtime
                    most_recent = item.name

    if not most_recent:
        print("No threads found", file=sys.stderr)
        sys.exit(1)

    print(most_recent)


if __name__ == "__main__":
    get_most_recent_thread()
