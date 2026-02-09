#!/usr/bin/env python3
"""Get the Quick Resume section from a thread's README."""

import os
import sys
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


def get_thread_status(thread_name: str):
    """Get the Quick Resume section from a thread's README."""
    threads_dir = get_workspace_dir() / "threads"
    readme_path = threads_dir / thread_name / "README.md"

    if not readme_path.exists():
        print(f"Thread '{thread_name}' not found", file=sys.stderr)
        sys.exit(1)

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
        print(f"No Quick Resume section found in {thread_name}", file=sys.stderr)
        sys.exit(1)
    
    # Remove leading/trailing empty lines
    while quick_resume_lines and not quick_resume_lines[0].strip():
        quick_resume_lines.pop(0)
    while quick_resume_lines and not quick_resume_lines[-1].strip():
        quick_resume_lines.pop()
    
    print("\n".join(quick_resume_lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: get-thread-status.py <thread-name>", file=sys.stderr)
        sys.exit(1)
    
    get_thread_status(sys.argv[1])
