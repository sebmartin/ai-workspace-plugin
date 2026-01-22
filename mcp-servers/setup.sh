#!/bin/bash
# One-time setup for all AI Workspace MCP servers

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Setting up AI Workspace MCP Servers..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate and install dependencies
echo ""
echo "Installing dependencies..."
source "$SCRIPT_DIR/venv/bin/activate"
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"
echo ""

echo "════════════════════════════════════════════════════════════"
echo "✓ Setup complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "MCP servers are configured in .mcp.json at the project root."
echo "Restart Claude Code to load the MCP servers."
echo ""
echo "Available servers:"
echo "  - threads: List and manage discussion threads"
echo ""
