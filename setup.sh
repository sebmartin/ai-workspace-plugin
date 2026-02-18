#!/usr/bin/env bash
# AI Workspace Template Setup
# One-time setup for git hooks and workspace verification

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "════════════════════════════════════════════════════════════"
echo "AI Workspace Template Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 1: Check for uv
# ═══════════════════════════════════════════════════════════════
echo "Step 1/4: Checking dependencies..."
echo ""

if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo ""
    echo "uv is required for managing Python dependencies."
    echo "Install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Or visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✓ uv found: $(uv --version)"

# ═══════════════════════════════════════════════════════════════
# Step 2: Set up Python environment
# ═══════════════════════════════════════════════════════════════
echo ""
echo "Step 2/4: Setting up Python environment..."
echo ""

cd "$SCRIPT_DIR"

# Create venv and install dependencies from lockfile
echo "Syncing environment (uv sync)..."
uv sync
echo "✓ Virtual environment and dependencies ready (pre-commit)"

# ═══════════════════════════════════════════════════════════════
# Step 3: Install git hooks
# ═══════════════════════════════════════════════════════════════
echo ""
echo "Step 3/4: Installing git hooks..."
echo ""

# Activate venv and install pre-commit hooks
source .venv/bin/activate
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
echo "✓ Git hooks activated (pre-commit, pre-push)"

# ═══════════════════════════════════════════════════════════════
# Step 4: Verify workspace directory
# ═══════════════════════════════════════════════════════════════
echo ""
echo "Step 4/4: Verifying workspace directory..."
echo ""

if [ -d "workspace" ]; then
    echo "✓ workspace/ directory exists"

    # Check what kind of workspace it is
    if [ -d "workspace/.git" ]; then
        echo "  ℹ workspace/ is a git repository (good for backups)"
    elif [ -L "workspace" ]; then
        echo "  ℹ workspace/ is a symlink (advanced setup detected)"
    else
        echo "  ℹ workspace/ is a regular directory"
        echo "    Consider making it a git repo for backups:"
        echo "    cd workspace && git init"
    fi
else
    echo "⚠ workspace/ directory not found!"
    echo "Creating workspace/ directory..."
    mkdir -p workspace/threads
    if [ -f "templates/workspace-readme-template.md" ]; then
        cp templates/workspace-readme-template.md workspace/README.md
    fi
    echo "✓ workspace/ created"
fi

# ═══════════════════════════════════════════════════════════════
# Done!
# ═══════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Run: /threads create"
echo ""
echo "Git hooks are now protecting workspace/ privacy!"
echo "  - Pre-commit: blocks staging workspace/ files"
echo "  - Pre-push: final safety check before pushing"
echo ""
