#!/usr/bin/env python3
"""Initialize a new AI workspace in the current directory."""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from workspace_utils import get_plugin_dir, error_exit


def init_workspace():
    """Initialize a new AI workspace in the current directory."""
    cwd = Path.cwd()
    plugin_dir = get_plugin_dir()

    print(f"Initializing AI workspace in: {cwd}")

    # 1. Check if already initialized
    if (cwd / "workspace").exists():
        response = input("workspace/ already exists. Reinitialize? (y/N) ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # 2. Create workspace structure
    workspace_dirs = [
        "workspace/threads",
        ".claude"
    ]
    for dir_path in workspace_dirs:
        (cwd / dir_path).mkdir(parents=True, exist_ok=True)

    print("✓ Created workspace structure")

    # 3. Copy templates to workspace
    templates_src = plugin_dir / "templates"
    templates_dest = cwd / "workspace" / "templates"
    if templates_src.exists():
        shutil.copytree(templates_src, templates_dest, dirs_exist_ok=True)
        print(f"✓ Copied templates from plugin")
    else:
        print(f"⚠ Warning: No templates directory found in plugin at {templates_src}")

    # 4. Copy setup resources
    resources = plugin_dir / "skills" / "init" / "resources"

    # Copy .gitignore
    gitignore_src = resources / "gitignore.template"
    if gitignore_src.exists():
        shutil.copy(gitignore_src, cwd / ".gitignore")
        print("✓ Created .gitignore")
    else:
        print(f"⚠ Warning: gitignore.template not found at {gitignore_src}")

    # Copy setup.sh
    setup_sh_src = resources / "setup.sh"
    if setup_sh_src.exists():
        shutil.copy(setup_sh_src, cwd / "setup.sh")
        os.chmod(cwd / "setup.sh", 0o755)
        print("✓ Created setup.sh")
    else:
        print(f"⚠ Warning: setup.sh not found at {setup_sh_src}")

    # Copy pre-commit config
    precommit_src = resources / "pre-commit-config.yaml"
    if precommit_src.exists():
        shutil.copy(precommit_src, cwd / ".pre-commit-config.yaml")
        print("✓ Created .pre-commit-config.yaml")
    else:
        print(f"⚠ Warning: pre-commit-config.yaml not found at {precommit_src}")

    # Copy hooks directory
    hooks_src = resources / "hooks"
    hooks_dest = cwd / "hooks"
    if hooks_src.exists():
        shutil.copytree(hooks_src, hooks_dest, dirs_exist_ok=True)
        # Make hook scripts executable
        for hook_file in hooks_dest.glob("*.sh"):
            os.chmod(hook_file, 0o755)
        print("✓ Created hooks/")
    else:
        print(f"⚠ Warning: hooks directory not found at {hooks_src}")

    # 5. Create settings.local.json
    settings_template_path = resources / "settings.local.json.template"
    settings_dest = cwd / ".claude" / "settings.local.json"

    if settings_template_path.exists():
        with open(settings_template_path) as f:
            settings_content = f.read().replace("${WORKSPACE_ROOT}", str(cwd))

        with open(settings_dest, 'w') as f:
            f.write(settings_content)
        print("✓ Created .claude/settings.local.json")
    else:
        print(f"⚠ Warning: settings.local.json.template not found at {settings_template_path}")

    # 6. Create workspace README
    readme_content = f"""# AI Workspace

Initialized: {datetime.now().strftime('%Y-%m-%d')}
Location: {cwd.name}

## Quick Start

1. Install git hooks: `./setup.sh`
2. Create your first thread: `/ai-workspace:threads create my-project`
3. View all threads: `/ai-workspace:threads`

## Directory Structure

- `workspace/threads/` - Your discussion threads
- `workspace/templates/` - Project templates
- `.claude/settings.local.json` - Local configuration (gitignored)

## Multiple Workspaces

To use multiple workspaces with the same plugin, set the `AI_WORKSPACE_DIR` environment variable:

```bash
export AI_WORKSPACE_DIR={cwd}/workspace
```

## Documentation

For full documentation, see the ai-workspace plugin README.
"""
    (cwd / "README.md").write_text(readme_content)
    print("✓ Created README.md")

    print("\n" + "="*60)
    print("✓ Workspace initialized!")
    print("="*60)
    print(f"\n  Location: {cwd}")
    print(f"  Workspace: {cwd / 'workspace'}")
    print("\nNext steps:")
    print("  1. Run ./setup.sh to install git hooks")
    print("  2. Create your first thread: /ai-workspace:threads create")


if __name__ == "__main__":
    try:
        init_workspace()
    except Exception as e:
        error_exit(f"Initialization failed: {e}")
