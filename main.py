#!/usr/bin/env python3
"""Entry point — run `python main.py "your topic"`."""

import sys

from panel_agent.cli import main

if __name__ == "__main__":
    sys.exit(main())
