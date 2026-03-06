#!/usr/bin/env fish

# Get script directory path (this is the somafm_tui directory)
set -l SCRIPT_DIR (dirname (status filename))

# Run application using __main__.py from the somafm_tui package
python $SCRIPT_DIR/somafm_tui/__main__.py $argv
