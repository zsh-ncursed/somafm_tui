#!/usr/bin/env fish

# Get script directory path
set -l SCRIPT_DIR (dirname (status filename))

# Add script directory to PYTHONPATH
set -x PYTHONPATH $SCRIPT_DIR $PYTHONPATH

# Run application
python3 $SCRIPT_DIR/somafm.py 