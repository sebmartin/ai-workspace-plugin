#!/usr/bin/env python3
"""Set the last active thread."""

import os
import sys
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


def set_last_active_thread(thread_name: str):
    """Write the thread name to .last-active-thread."""
    workspace_dir = get_workspace_dir()
    last_active_file = workspace_dir / ".last-active-thread"

    last_active_file.write_text(thread_name)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: set-last-active-thread.py <thread-name>", file=sys.stderr)
        sys.exit(1)

    set_last_active_thread(sys.argv[1])
