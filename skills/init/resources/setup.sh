#!/usr/bin/env bash
# AI Workspace Setup
# One-time setup for git hooks and workspace verification

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "════════════════════════════════════════════════════════════"
echo "AI Workspace Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 1: Check for uv
# ═══════════════════════════════════════════════════════════════
echo "Step 1/3: Checking dependencies..."
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
echo "Step 2/3: Setting up Python environment..."
echo ""

cd "$SCRIPT_DIR"

# Create venv with pre-commit
echo "Creating Python environment..."
uv venv
source .venv/bin/activate
uv pip install pre-commit
echo "✓ Virtual environment ready"

# ═══════════════════════════════════════════════════════════════
# Step 3: Install git hooks
# ═══════════════════════════════════════════════════════════════
echo ""
echo "Step 3/3: Installing git hooks..."
echo ""

# Initialize git if not already a repo
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Install pre-commit hooks
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
echo "✓ Git hooks activated (pre-commit, pre-push)"

# ═══════════════════════════════════════════════════════════════
# Done!
# ═══════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Run: /ai-workspace:threads create"
echo ""
echo "Git hooks are now protecting workspace/ privacy!"
echo "  - Pre-commit: blocks staging workspace/ files"
echo "  - Pre-push: final safety check before pushing"
echo ""
