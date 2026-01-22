# AI Workspace MCP Servers

Model Context Protocol (MCP) servers for AI workspace skills. Each server provides read-only tools that don't require permission prompts.

## Quick Start

**Clone and run:**
```bash
git clone <repo>
cd <repo>
./mcp-servers/setup.sh
# Restart Claude Code - that's it!
```

The repo includes `.mcp.json` with relative paths, so MCP servers work immediately after setup.

## Setup Details

The setup script:
1. Creates a Python virtual environment at `mcp-servers/venv/`
2. Installs shared dependencies from `requirements.txt`
3. MCP servers are configured in `.mcp.json` (already in repo)
4. Uses relative paths - no manual configuration needed

## Configuration

MCP servers are configured in **`.mcp.json`** at the project root (not in `.claude/settings.json`).

The existing `.mcp.json` uses relative paths:
```json
{
  "mcpServers": {
    "threads": {
      "command": "mcp-servers/venv/bin/python",
      "args": ["mcp-servers/threads/server.py"],
      "env": {
        "AI_WORKSPACE_DIR": "workspace"
      }
    }
  }
}
```

All paths are relative to the project root, including the venv Python interpreter.

## Available Servers

### Threads (`threads/server.py`)

Read-only tools for managing discussion threads.

**Tools:**
- `listThreads` - List all threads sorted by most recent activity
- `getThreadStatus` - Get the Quick Resume section from a thread
- `getMostRecentThread` - Get the most recently updated thread name

### Future Servers

More servers can be added for other skills:
- `later/` - TODO/task management tools
- `context/` - Workspace context tools
- etc.

Each new server shares the same venv and requirements.

## Benefits

- **Clone and go** - No manual configuration, relative paths work out of the box
- **No permission prompts** - Since you control the code, these tools are safe to use
- **Fast and efficient** - Direct file system access without LLM overhead
- **Consistent behavior** - Same output every time, no LLM interpretation needed
- **Easy to extend** - Add new servers as you add new skills
- **One setup** - All servers share the same Python environment

## Development

To add a new MCP server:

1. Create a new directory: `mcp-servers/new-skill/`
2. Add `server.py` with your tools
3. Add any new dependencies to `requirements.txt` (shared)
4. Add the server to `.mcp.json` with relative paths
5. Update this README with the new server's tools

## Troubleshooting

**Server not loading:**
- Run `./mcp-servers/setup.sh` to ensure venv exists and dependencies are installed
- Check `.mcp.json` syntax
- Restart Claude Code to reload MCP servers

**Import errors:**
- Activate the venv: `source mcp-servers/venv/bin/activate`
- Install/update dependencies: `pip install -r requirements.txt`

**Permission errors:**
- MCP servers are auto-approved via `enableAllProjectMcpServers: true` in `.claude/settings.json`
