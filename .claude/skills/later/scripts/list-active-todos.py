#!/usr/bin/env python3
"""List all active TODO lists in a thread with completion counts."""

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


def list_active_todos(thread_name: str):
    """List all active TODO lists with completion counts."""
    threads_dir = get_workspace_dir() / "threads"
    todos_dir = threads_dir / thread_name / "todos"

    if not todos_dir.exists():
        print("No todos directory found", file=sys.stderr)
        sys.exit(1)

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
