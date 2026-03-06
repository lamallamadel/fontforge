"""Root conftest.py — ensures the repository root is on sys.path for aifont imports."""

import sys
import os

# Add the repository root to sys.path so that `import aifont` works when
# running pytest from any working directory.
sys.path.insert(0, os.path.dirname(__file__))
"""Root conftest.py — adds the project root to sys.path.

This ensures the ``aifont`` package is importable when running pytest
from any working directory without requiring an editable install.
"""
import sys
import os

# Add the project root (directory containing this file) to sys.path
# so that `import aifont` resolves to the top-level aifont/ package.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
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
