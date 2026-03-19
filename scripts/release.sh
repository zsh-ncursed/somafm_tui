#!/bin/bash
#
# Release automation script for SomaFM TUI Player.
#
# Automates the complete release process:
# - Version bump in pyproject.toml
# - Test execution
# - Git commit and tag creation
# - Push to GitHub
# - GitHub Release creation
#
# This script is part of the automated versioning workflow.
#
# ## Usage
#
# ```bash
# # Release new version
# ./scripts/release.sh 0.6.6
#
# # Must be run from project root directory
# cd /path/to/somafm_tui
# ./scripts/release.sh 0.6.7
# ```
#
# ## Requirements
#
# - Bash 4.0+
# - Git
# - pytest (for running tests)
# - gh CLI (optional, for GitHub Release creation)
#
# ## What It Does
#
# 1. ✅ Checks you're on 'main' branch
# 2. ✅ Verifies no existing tag
# 3. ✅ Warns about uncommitted changes
# 4. ✅ Updates version in pyproject.toml
# 5. ✅ Runs pytest test suite
# 6. ✅ Creates git commit (includes ALL changes)
# 7. ✅ Creates annotated git tag
# 8. ✅ Pushes branch and tag to GitHub
# 9. ✅ Creates GitHub Release (if gh CLI installed)
#
# ## Post-Release
#
# After running this script:
# - GitHub Actions will run CI tests
# - If tests pass, packages will be published to:
#   - PyPI (https://pypi.org/project/somafm-tui/)
#   - AUR (https://aur.archlinux.org/packages/somafm_tui)
# - GitHub Release will be created automatically
#
# ## Related Files
#
# - `scripts/sync_version.py` - Version synchronization
# - `docs/VERSIONING.md` - Complete versioning documentation
# - `.github/workflows/auto-version-tag.yml` - Auto-tag creation
# - `.github/workflows/publish.yml` - PyPI publishing
# - `.github/workflows/publish-aur.yml` - AUR publishing
#
# ## Examples
#
# ```bash
# # Patch release (bugfix)
# ./scripts/release.sh 0.6.6
#
# # Minor release (new feature)
# ./scripts/release.sh 0.7.0
#
# # Major release (breaking change)
# ./scripts/release.sh 1.0.0
# ```
#
# ## Troubleshooting
#
# ### Tag already exists
# ```bash
# git tag -d v0.6.6
# git push origin :refs/tags/v0.6.6
# ./scripts/release.sh 0.6.6
# ```
#
# ### Tests failed
# ```bash
# pytest tests/ -v
# # Fix issues, then run release again
# ./scripts/release.sh 0.6.6
# ```
#
# ## See Also
#
# - Documentation: docs/VERSIONING.md
# - Quick Start: docs/QUICKSTART_VERSIONING.md
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version not specified${NC}"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.6.6"
    exit 1
fi

VERSION="$1"
TAG_NAME="v$VERSION"

echo -e "${GREEN}Starting release process for $VERSION${NC}"
echo "================================================"

# Step 0: Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: You're on branch '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo -e "${RED}Error: Tag $TAG_NAME already exists${NC}"
    exit 1
fi

# Step 2: Update version in pyproject.toml
echo -e "\n${YELLOW}Step 1: Updating version in pyproject.toml${NC}"
if grep -q "^version = " pyproject.toml; then
    # macOS-compatible sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    else
        sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    fi
    echo "✓ Updated pyproject.toml to version $VERSION"
else
    echo -e "${RED}Error: Could not find version in pyproject.toml${NC}"
    exit 1
fi

# Step 3: Add ALL changes to git (including pyproject.toml version bump)
echo -e "\n${YELLOW}Step 2: Staging ALL changes${NC}"
git add -A
echo "✓ Staged all changes"

# Step 4: Run tests
echo -e "\n${YELLOW}Step 3: Running tests${NC}"
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short || {
        echo -e "${RED}Error: Tests failed${NC}"
        echo "Reverting pyproject.toml..."
        git checkout -- pyproject.toml
        exit 1
    }
    echo "✓ Tests passed"
else
    echo -e "${YELLOW}Warning: pytest not found, skipping tests${NC}"
fi

# Step 5: Create commit with version
echo -e "\n${YELLOW}Step 4: Creating release commit${NC}"
git commit -m "Release $TAG_NAME" || {
    echo -e "${YELLOW}No changes to commit (version unchanged)${NC}"
}

# Step 6: Create git tag
echo -e "\n${YELLOW}Step 5: Creating git tag${NC}"
git tag -a "$TAG_NAME" -m "Release $TAG_NAME"
echo "✓ Created tag $TAG_NAME"

# Step 7: Push to GitHub
echo -e "\n${YELLOW}Step 6: Pushing to GitHub${NC}"
echo "Pushing branch and tag..."
git push origin main
git push origin "$TAG_NAME"
echo "✓ Pushed to GitHub"

# Step 8: Create GitHub Release
echo -e "\n${YELLOW}Step 7: Creating GitHub Release${NC}"
if command -v gh &> /dev/null; then
    # Delete existing release if exists
    gh release delete "$TAG_NAME" --yes 2>/dev/null || true
    
    gh release create "$TAG_NAME" \
        --title "Release $TAG_NAME" \
        --generate-notes \
        --verify-tag || {
        echo -e "${YELLOW}Warning: Could not create GitHub release via gh CLI${NC}"
        echo "You can create it manually at: https://github.com/zsh-ncursed/somafm_tui/releases/new"
    }
    echo "✓ GitHub Release created"
else
    echo -e "${YELLOW}Warning: gh CLI not found${NC}"
    echo "Create GitHub Release manually at:"
    echo "https://github.com/zsh-ncursed/somafm_tui/releases/new"
    echo "Tag: $TAG_NAME"
fi

# Summary
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✓ Release $VERSION completed successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "What happens next:"
echo "  1. GitHub Actions will run CI tests"
echo "  2. If tests pass, packages will be published to:"
echo "     - PyPI (https://pypi.org/project/somafm-tui/)"
echo "     - AUR (https://aur.archlinux.org/packages/somafm_tui)"
echo "  3. GitHub Release will be available at:"
echo "     https://github.com/zsh-ncursed/somafm_tui/releases/tag/$TAG_NAME"
echo ""
echo "Monitor the workflow at:"
echo "https://github.com/zsh-ncursed/somafm_tui/actions"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version not specified${NC}"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.6.6"
    exit 1
fi

VERSION="$1"
TAG_NAME="v$VERSION"

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: You're on branch '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo -e "${RED}Error: Tag $TAG_NAME already exists${NC}"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}Warning: Working directory has uncommitted changes${NC}"
    echo "Uncommitted changes:"
    git status --short
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Starting release process for $VERSION${NC}"
echo "================================================"

# Step 1: Update version in pyproject.toml
echo -e "\n${YELLOW}Step 1: Updating version in pyproject.toml${NC}"
if grep -q "^version = " pyproject.toml; then
    # macOS-compatible sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    else
        sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    fi
    echo "✓ Updated pyproject.toml to version $VERSION"
else
    echo -e "${RED}Error: Could not find version in pyproject.toml${NC}"
    exit 1
fi

# Step 2: Run tests
echo -e "\n${YELLOW}Step 2: Running tests${NC}"
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short || {
        echo -e "${RED}Error: Tests failed${NC}"
        echo "Reverting pyproject.toml..."
        git checkout pyproject.toml
        exit 1
    }
    echo "✓ Tests passed"
else
    echo -e "${YELLOW}Warning: pytest not found, skipping tests${NC}"
fi

# Step 3: Commit version change
echo -e "\n${YELLOW}Step 3: Committing version change${NC}"
git add pyproject.toml
git commit -m "Release $TAG_NAME" || {
    echo -e "${YELLOW}No changes to commit (version unchanged)${NC}"
}

# Step 4: Create git tag
echo -e "\n${YELLOW}Step 4: Creating git tag${NC}"
git tag -a "$TAG_NAME" -m "Release $TAG_NAME"
echo "✓ Created tag $TAG_NAME"

# Step 5: Push to GitHub
echo -e "\n${YELLOW}Step 5: Pushing to GitHub${NC}"
echo "Pushing branch and tag..."
git push origin main
git push origin "$TAG_NAME"
echo "✓ Pushed to GitHub"

# Step 6: Create GitHub Release
echo -e "\n${YELLOW}Step 6: Creating GitHub Release${NC}"
if command -v gh &> /dev/null; then
    gh release create "$TAG_NAME" \
        --title "Release $TAG_NAME" \
        --generate-notes \
        --verify-tag || {
        echo -e "${YELLOW}Warning: Could not create GitHub release via gh CLI${NC}"
        echo "You can create it manually at: https://github.com/zsh-ncursed/somafm_tui/releases/new"
    }
    echo "✓ GitHub Release created"
else
    echo -e "${YELLOW}Warning: gh CLI not found${NC}"
    echo "Create GitHub Release manually at:"
    echo "https://github.com/zsh-ncursed/somafm_tui/releases/new"
    echo "Tag: $TAG_NAME"
fi

# Summary
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✓ Release $VERSION completed successfully!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "What happens next:"
echo "  1. GitHub Actions will run CI tests"
echo "  2. If tests pass, packages will be published to:"
echo "     - PyPI (https://pypi.org/project/somafm-tui/)"
echo "     - AUR (https://aur.archlinux.org/packages/somafm_tui)"
echo "  3. GitHub Release will be available at:"
echo "     https://github.com/zsh-ncursed/somafm_tui/releases/tag/$TAG_NAME"
echo ""
echo "Monitor the workflow at:"
echo "https://github.com/zsh-ncursed/somafm_tui/actions"
