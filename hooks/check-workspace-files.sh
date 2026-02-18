#!/usr/bin/env bash
# Git hook to prevent committing workspace/ files to the public template
# This protects user privacy by ensuring workspace/ stays local-only
set -euo pipefail

# Allowed files in workspace/ (these are part of the template)
ALLOWED_PATTERN="^workspace/(\.keep|README\.md)$"

# Check for workspace files that shouldn't be committed
if [ "${PRE_COMMIT_FROM_REF:-}" != "" ] && [ "${PRE_COMMIT_TO_REF:-}" != "" ]; then
    # Pre-push stage: check tracked files
    WORKSPACE_FILES=$(git ls-files workspace/ | grep -vE "$ALLOWED_PATTERN" || true)
    STAGE="push"
else
    # Pre-commit stage: check staged files
    WORKSPACE_FILES=$(git diff --cached --name-only | grep -E '^workspace/' | grep -vE "$ALLOWED_PATTERN" || true)
    STAGE="commit"
fi

if [ -n "$WORKSPACE_FILES" ]; then
    echo ""
    echo "❌ $(echo $STAGE | tr '[:lower:]' '[:upper:]') BLOCKED: workspace/ is local-only and must not be committed"
    echo ""
    echo "The following workspace files were detected:"
    echo "$WORKSPACE_FILES" | sed 's/^/  - /'
    echo ""

    if [ "$STAGE" = "commit" ]; then
        echo "Fix by unstaging workspace files:"
        echo "  git restore --staged workspace/"
    else
        echo "Fix by removing from git history:"
        echo "  git rm --cached <file>"
        echo "  git commit --amend"
    fi

    echo ""
    echo "Note: workspace/ contains your private work and is excluded by .gitignore"
    echo "      Only workspace/.keep and workspace/README.md should be in the template"
    echo ""
    exit 1
fi

# Success - no unauthorized workspace files found
exit 0
