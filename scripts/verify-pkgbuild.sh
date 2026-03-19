#!/bin/bash
#
# Script to verify PKGBUILD installs all Python files
#
# Usage: ./scripts/verify-pkgbuild.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PKGBUILD="$PROJECT_ROOT/PKGBUILD"
PYTHON_DIR="$PROJECT_ROOT/somafm_tui"

echo "Verifying PKGBUILD includes all Python files..."
echo "================================================"

# Get list of all .py files in somafm_tui directory (excluding __pycache__)
PYTHON_FILES=$(find "$PYTHON_DIR" -name "*.py" -not -path "*/__pycache__/*" | sort)

# Check each file is in PKGBUILD
MISSING_FILES=()

for py_file in $PYTHON_FILES; do
    # Get relative path from somafm_tui directory
    REL_PATH=$(basename "$py_file")
    SUBDIR=$(dirname "$py_file" | xargs basename)
    
    # Check if file is referenced in PKGBUILD
    if ! grep -q "$REL_PATH" "$PKGBUILD"; then
        MISSING_FILES+=("$REL_PATH")
        echo "❌ Missing: $REL_PATH"
    else
        echo "✅ Found: $REL_PATH"
    fi
done

echo ""
echo "================================================"

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo "✅ All Python files are included in PKGBUILD!"
    exit 0
else
    echo "❌ ERROR: ${#MISSING_FILES[@]} file(s) missing from PKGBUILD:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "Add these lines to PKGBUILD package() function:"
    for file in "${MISSING_FILES[@]}"; do
        SUBDIR=$(dirname "$PYTHON_DIR/$file" | xargs basename)
        if [ "$SUBDIR" = "somafm_tui" ]; then
            echo "   install -Dm644 \"\$srcdir/\$pkgname/somafm_tui/$file\" \"\$pkgdir/usr/lib/somafm_tui/somafm_tui/$file\""
        else
            echo "   install -Dm644 \"\$srcdir/\$pkgname/somafm_tui/$SUBDIR/$file\" \"\$pkgdir/usr/lib/somafm_tui/somafm_tui/$SUBDIR/$file\""
        fi
    done
    exit 1
fi
