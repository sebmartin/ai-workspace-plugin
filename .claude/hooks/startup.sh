#!/bin/bash
# Startup hook - show recent threads on Claude Code launch

echo "Recent threads:"
echo ""
.claude/skills/threads/scripts/list-threads.py
echo ""
echo "Reply with a number to resume, or use /threads create for a new thread."
