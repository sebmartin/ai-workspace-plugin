#!/usr/bin/env python3
"""List all discussion threads sorted by most recent activity."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from workspace_utils import get_threads_dir, error_exit


def list_threads():
    """List all threads sorted by most recent modification."""
    threads_dir = get_threads_dir()

    if not threads_dir.exists():
        error_exit("No threads directory found")

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
