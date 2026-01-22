#!/usr/bin/env python3
"""
Later MCP Server - Provides read-only tools for managing TODO lists in threads.
"""

import os
import re
from pathlib import Path
from typing import Any

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio


def get_workspace_dir() -> Path:
    """Get the workspace directory from environment or default."""
    workspace_dir = os.environ.get("AI_WORKSPACE_DIR", "workspace")
    return Path(workspace_dir)


server = Server("later")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="listActiveTodos",
            description="List all active TODO lists in the current thread with completion counts. Returns formatted output ready to display.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_name": {
                        "type": "string",
                        "description": "The name of the thread (e.g., 'ai-workspace-setup')",
                    }
                },
                "required": ["thread_name"],
            },
        ),
        types.Tool(
            name="getTodoList",
            description="Get the contents and completion status of a specific TODO list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_name": {
                        "type": "string",
                        "description": "The name of the thread (e.g., 'ai-workspace-setup')",
                    },
                    "list_name": {
                        "type": "string",
                        "description": "The name of the TODO list file (with or without .md extension)",
                    }
                },
                "required": ["thread_name", "list_name"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""

    if name == "listActiveTodos":
        if not arguments or "thread_name" not in arguments:
            raise ValueError("thread_name is required")
        return await list_active_todos(arguments["thread_name"])
    elif name == "getTodoList":
        if not arguments or "thread_name" not in arguments or "list_name" not in arguments:
            raise ValueError("thread_name and list_name are required")
        return await get_todo_list(arguments["thread_name"], arguments["list_name"])
    else:
        raise ValueError(f"Unknown tool: {name}")


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


async def list_active_todos(thread_name: str) -> list[types.TextContent]:
    """List all active TODO lists with completion counts."""
    threads_dir = get_workspace_dir() / "threads"
    todos_dir = threads_dir / thread_name / "todos"

    if not todos_dir.exists():
        return [types.TextContent(type="text", text="No todos directory found")]

    # Find all active TODO files (excluding complete/ subdirectory)
    todo_files = []
    for item in todos_dir.glob("*.md"):
        if item.is_file():
            content = item.read_text()
            completed, total = parse_todo_items(content)
            todo_files.append((item.name, completed, total, content))

    if not todo_files:
        result = "No active TODO lists"
    else:
        # Sort by name
        todo_files.sort(key=lambda x: x[0])

        lines = ["Active TODOs:", ""]
        for name, completed, total, content in todo_files:
            lines.append(f"{name} ({completed} of {total} complete):")
            lines.extend(format_todo_items(content))
            lines.append("")

        result = "\n".join(lines).rstrip()

    return [types.TextContent(type="text", text=result)]


async def get_todo_list(thread_name: str, list_name: str) -> list[types.TextContent]:
    """Get the contents of a specific TODO list."""
    threads_dir = get_workspace_dir() / "threads"

    # Add .md extension if not present
    if not list_name.endswith(".md"):
        list_name = f"{list_name}.md"

    todo_path = threads_dir / thread_name / "todos" / list_name

    if not todo_path.exists():
        return [types.TextContent(
            type="text",
            text=f"TODO list '{list_name}' not found in thread '{thread_name}'"
        )]

    content = todo_path.read_text()
    completed, total = parse_todo_items(content)

    lines = [f"{list_name} ({completed} of {total} complete):", ""]
    lines.extend(format_todo_items(content))

    result = "\n".join(lines)
    return [types.TextContent(type="text", text=result)]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="later",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
