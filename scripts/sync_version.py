#!/usr/bin/env python3
"""
Version synchronization script for SomaFM TUI Player.

Updates version in all files from a single source (pyproject.toml or git tag).
This script is part of the automated versioning workflow.

## Usage

```bash
# Get version from pyproject.toml (default)
python scripts/sync_version.py

# Get version from latest git tag
python scripts/sync_version.py --from-tag

# Specify version explicitly
python scripts/sync_version.py 0.6.6
```

## Workflow

1. Reads version from source (pyproject.toml or git tag)
2. Validates version format (SemVer: MAJOR.MINOR.PATCH)
3. Updates pyproject.toml if version differs
4. Provides instructions for next steps

## Examples

```bash
# Before release - sync version from tag
python scripts/sync_version.py --from-tag

# After manual version bump in pyproject.toml
python scripts/sync_version.py

# Force specific version
python scripts/sync_version.py 0.7.0
```

## Related Files

- `scripts/release.sh` - Full release automation
- `docs/VERSIONING.md` - Complete versioning documentation
- `.github/workflows/auto-version-tag.yml` - Auto-tag creation on push

## Requirements

- Python 3.8+
- Git (for --from-tag option)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def get_version_from_git_tag() -> str:
    """Get version from latest git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        tag = result.stdout.strip()
        # Remove 'v' prefix if present
        return tag.lstrip("v")
    except subprocess.CalledProcessError:
        print("Warning: No git tags found", file=sys.stderr)
        return None


def get_version_from_pyproject() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "r") as f:
        content = f.read()
    
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    
    raise ValueError("Version not found in pyproject.toml")


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    return get_version_from_pyproject()


def update_pyproject_toml(new_version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "r") as f:
        content = f.read()
    
    # Update version line
    new_content = re.sub(
        r'^(version\s*=\s*)"[^"]+"',
        rf'\1"{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    
    with open(pyproject_path, "w") as f:
        f.write(new_content)
    
    print(f"✓ Updated pyproject.toml: version = \"{new_version}\"")


def create_git_tag(version: str) -> None:
    """Create git tag for version."""
    tag_name = f"v{version}"
    
    try:
        # Check if tag already exists
        subprocess.run(
            ["git", "rev-parse", f"refs/tags/{tag_name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"⚠ Tag {tag_name} already exists")
        return
    except subprocess.CalledProcessError:
        pass
    
    # Create tag
    subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
        check=True,
    )
    print(f"✓ Created git tag: {tag_name}")


def sync_version(target_version: str = None, from_tag: bool = False) -> None:
    """Synchronize version across all files."""
    if from_tag:
        version = get_version_from_git_tag()
        if not version:
            print("Error: Could not get version from git tag", file=sys.stderr)
            sys.exit(1)
        print(f"Using version from git tag: {version}")
    else:
        version = target_version or get_version_from_pyproject()
        print(f"Using version: {version}")
    
    # Validate version format (SemVer)
    if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$", version):
        print(f"Warning: Version '{version}' may not follow SemVer", file=sys.stderr)
    
    # Update pyproject.toml if version was from tag and differs
    if from_tag:
        current_version = get_current_version()
        if current_version != version:
            update_pyproject_toml(version)
        else:
            print(f"✓ pyproject.toml already has version {version}")
    
    print(f"\n✓ Version synchronized: {version}")
    print(f"\nNext steps:")
    print(f"  1. git add pyproject.toml")
    print(f"  2. git commit -m 'Bump version to {version}'")
    print(f"  3. git push && git push origin v{version}")
    print(f"  Or run: ./scripts/release.sh {version}")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize version across project files"
    )
    parser.add_argument(
        "--from-tag",
        action="store_true",
        help="Get version from latest git tag",
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Target version (default: from pyproject.toml)",
    )
    
    args = parser.parse_args()
    
    try:
        sync_version(target_version=args.version, from_tag=args.from_tag)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
