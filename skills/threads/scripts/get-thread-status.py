#!/usr/bin/env python3
"""Get the Quick Resume section from a thread's README."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from workspace_utils import get_threads_dir, error_exit


def get_thread_status(thread_name: str, workspace_dir: Path = None):
    """Get the Quick Resume section from a thread's README.

    Args:
        thread_name: Name of the thread
        workspace_dir: Optional workspace directory path. If None, uses current working directory.
    """
    readme_path = get_threads_dir(workspace_dir) / thread_name / "README.md"

    if not readme_path.exists():
        error_exit(f"Thread '{thread_name}' not found")

    # Read the README and extract Quick Resume section
    content = readme_path.read_text()

    # Find the Quick Resume section
    lines = content.split("\n")
    in_quick_resume = False
    quick_resume_lines = []

    for line in lines:
        if line.strip() == "## Quick Resume":
            in_quick_resume = True
            continue
        elif in_quick_resume and line.startswith("## "):
            # Hit the next section
            break
        elif in_quick_resume:
            # Skip the purpose comment line
            if not line.strip().startswith("> **Purpose**"):
                quick_resume_lines.append(line)

    if not quick_resume_lines:
        error_exit(f"No Quick Resume section found in {thread_name}")

    # Remove leading/trailing empty lines
    while quick_resume_lines and not quick_resume_lines[0].strip():
        quick_resume_lines.pop(0)
    while quick_resume_lines and not quick_resume_lines[-1].strip():
        quick_resume_lines.pop()

    print("\n".join(quick_resume_lines))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: get-thread-status.py <workspace-dir> <thread-name>", file=sys.stderr)
        sys.exit(1)

    # Accept workspace directory as first argument, thread name as second
    workspace_dir = Path(sys.argv[1]) if len(sys.argv) > 2 else None
    thread_name = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]

    get_thread_status(thread_name, workspace_dir)
