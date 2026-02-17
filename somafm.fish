#!/usr/bin/env fish

# Get script directory path (this is the somafm_tui directory)
set -l SCRIPT_DIR (dirname (status filename))

# Add parent directory to PYTHONPATH so somafm_tui module can be found
set -l PARENT_DIR (dirname $SCRIPT_DIR)
set -x PYTHONPATH $PARENT_DIR $PYTHONPATH

# Run application using __main__.py
python $SCRIPT_DIR/__main__.py $argv
