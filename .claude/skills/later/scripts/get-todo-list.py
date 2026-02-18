#!/usr/bin/env python3
"""Get the contents of a specific TODO list."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from workspace_utils import get_threads_dir, error_exit
from todo_utils import parse_todo_items, format_todo_items


def get_todo_list(thread_name: str, list_name: str):
    """Get the contents of a specific TODO list."""
    # Add .md extension if not present
    if not list_name.endswith(".md"):
        list_name = f"{list_name}.md"

    todo_path = get_threads_dir() / thread_name / "todos" / list_name

    if not todo_path.exists():
        error_exit(f"TODO list '{list_name}' not found in thread '{thread_name}'")

    content = todo_path.read_text()
    completed, total = parse_todo_items(content)

    print(f"{list_name} ({completed} of {total} complete):")
    print()
    for item in format_todo_items(content):
        print(item)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: get-todo-list.py <thread-name> <list-name>", file=sys.stderr)
        sys.exit(1)
    
    get_todo_list(sys.argv[1], sys.argv[2])
