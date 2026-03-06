"""
Pytest configuration for aifont tests.

Adds the repository root to sys.path so that ``import aifont`` works
without installing the package.
"""

import sys
import os

# Repository root (directory containing this file)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
