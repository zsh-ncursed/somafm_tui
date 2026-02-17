#!/bin/bash
# SomaFM TUI Player launcher for bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python version
python_version=$(python -c 'import sys; print(sys.version_info[0]*10 + sys.version_info[1])' 2>/dev/null || echo "0")
if [ "$python_version" -lt 38 ]; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi

# Run the application
exec python "$SCRIPT_DIR/somafm_tui/__main__.py" "$@"
