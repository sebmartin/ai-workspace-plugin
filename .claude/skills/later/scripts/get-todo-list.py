#!/usr/bin/env python3
"""Get the contents of a specific TODO list."""

import os
import re
import sys
from pathlib import Path


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


def parse_todo_items(content: str) -> tuple[int, int]:
    """Parse TODO items and return (completed, total) counts."""
    completed = 0
    total = 0

    # Match both checked and unchecked items
    for line in content.split("\n"):
        if re.match(r'^\s*- \[[ xX]\]', line):
            total += 1
            if re.match(r'^\s*- \[[xX]\]', line):
                completed += 1

    return completed, total


def format_todo_items(content: str) -> list[str]:
    """Format TODO items for display with checkmarks."""
    items = []

    for line in content.split("\n"):
        match = re.match(r'^\s*- \[([ xX])\]\s*(.+)', line)
        if match:
            status, text = match.groups()
            symbol = "✓" if status.lower() == "x" else "☐"
            items.append(f"  {symbol} {text.strip()}")

    return items


def get_todo_list(thread_name: str, list_name: str):
    """Get the contents of a specific TODO list."""
    threads_dir = get_workspace_dir() / "threads"

    # Add .md extension if not present
    if not list_name.endswith(".md"):
        list_name = f"{list_name}.md"

    todo_path = threads_dir / thread_name / "todos" / list_name

    if not todo_path.exists():
        print(f"TODO list '{list_name}' not found in thread '{thread_name}'", file=sys.stderr)
        sys.exit(1)

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
