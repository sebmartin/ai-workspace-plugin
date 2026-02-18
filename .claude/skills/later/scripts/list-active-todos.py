#!/usr/bin/env python3
"""List all active TODO lists in a thread with completion counts."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from workspace_utils import get_threads_dir, error_exit
from todo_utils import parse_todo_items, format_todo_items


def list_active_todos(thread_name: str):
    """List all active TODO lists with completion counts."""
    todos_dir = get_threads_dir() / thread_name / "todos"

    if not todos_dir.exists():
        error_exit("No todos directory found")

    # Find all active TODO files (excluding complete/ subdirectory)
    todo_files = []
    for item in todos_dir.glob("*.md"):
        if item.is_file():
            content = item.read_text()
            completed, total = parse_todo_items(content)
            todo_files.append((item.name, completed, total, content))

    if not todo_files:
        print("No active TODO lists")
    else:
        # Sort by name
        todo_files.sort(key=lambda x: x[0])

        print("Active TODOs:")
        print()
        for name, completed, total, content in todo_files:
            print(f"{name} ({completed} of {total} complete):")
            for item in format_todo_items(content):
                print(item)
            print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: list-active-todos.py <thread-name>", file=sys.stderr)
        sys.exit(1)
    
    list_active_todos(sys.argv[1])
