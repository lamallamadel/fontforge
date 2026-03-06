"""
conftest.py — root-level pytest configuration.

Adds the repository root to sys.path so that ``import aifont`` works
without installing the package.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
