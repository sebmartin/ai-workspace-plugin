#!/usr/bin/env python3
"""
Threads MCP Server - Provides read-only tools for managing discussion threads.
"""

import os
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


server = Server("threads")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="listThreads",
            description="List all discussion threads sorted by most recent activity (by README.md modification time). Returns a numbered list of thread names.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="getThreadStatus",
            description="Get the Quick Resume section from a thread's README.md, showing current focus, next steps, and recent progress.",
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
            name="getMostRecentThread",
            description="Get the name of the most recently updated thread (by README.md modification time).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution."""

    if name == "listThreads":
        return await list_threads()
    elif name == "getThreadStatus":
        if not arguments or "thread_name" not in arguments:
            raise ValueError("thread_name is required")
        return await get_thread_status(arguments["thread_name"])
    elif name == "getMostRecentThread":
        return await get_most_recent_thread()
    else:
        raise ValueError(f"Unknown tool: {name}")


async def list_threads() -> list[types.TextContent]:
    """List all threads sorted by most recent modification."""
    threads_dir = get_workspace_dir() / "threads"

    if not threads_dir.exists():
        return [types.TextContent(type="text", text="No threads directory found")]

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
        result = "No threads found"
    else:
        lines = []
        for i, (name, _) in enumerate(thread_readmes, 1):
            lines.append(f"{i}. {name}")
        result = "\n".join(lines)

    return [types.TextContent(type="text", text=result)]


async def get_thread_status(thread_name: str) -> list[types.TextContent]:
    """Get the Quick Resume section from a thread's README."""
    threads_dir = get_workspace_dir() / "threads"
    readme_path = threads_dir / thread_name / "README.md"

    if not readme_path.exists():
        return [types.TextContent(
            type="text",
            text=f"Thread '{thread_name}' not found"
        )]

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
        result = f"No Quick Resume section found in {thread_name}"
    else:
        # Remove leading/trailing empty lines
        while quick_resume_lines and not quick_resume_lines[0].strip():
            quick_resume_lines.pop(0)
        while quick_resume_lines and not quick_resume_lines[-1].strip():
            quick_resume_lines.pop()
        result = "\n".join(quick_resume_lines)

    return [types.TextContent(type="text", text=result)]


async def get_most_recent_thread() -> list[types.TextContent]:
    """Get the name of the most recently updated thread."""
    threads_dir = get_workspace_dir() / "threads"

    if not threads_dir.exists():
        return [types.TextContent(type="text", text="No threads directory found")]

    # Find all thread README files
    most_recent = None
    most_recent_time = 0

    for item in threads_dir.iterdir():
        if item.is_dir():
            readme = item / "README.md"
            if readme.exists():
                mtime = readme.stat().st_mtime
                if mtime > most_recent_time:
                    most_recent_time = mtime
                    most_recent = item.name

    if not most_recent:
        result = "No threads found"
    else:
        result = most_recent

    return [types.TextContent(type="text", text=result)]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="threads",
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
