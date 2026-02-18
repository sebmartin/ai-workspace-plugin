"""Shared utilities for parsing and formatting TODO items."""

import re


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
