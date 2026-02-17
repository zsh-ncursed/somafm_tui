#!/usr/bin/env python
"""Entry point for SomaFM TUI Player"""

import os
import sys

# Add parent directory to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from somafm_tui.player import main

if __name__ == "__main__":
    main()
