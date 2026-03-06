"""
conftest.py — root-level pytest configuration.
Pytest configuration for aifont tests.

Adds the repository root to sys.path so that ``import aifont`` works
without installing the package.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
"""Repository-root conftest.py — makes the aifont package importable in tests."""

import sys
import os

# Repository root (directory containing this file)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Add the repository root to sys.path so that `import aifont` works regardless
# of how pytest discovers and runs the tests.
_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
