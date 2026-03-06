"""
conftest.py — pytest configuration for AIFont tests.

Ensures the repository root is on ``sys.path`` so that ``import aifont``
works without installing the package.
"""

import sys
from pathlib import Path

# Repository root (tests/aifont/conftest.py → tests/aifont → tests → repo root)
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
"""tests/aifont/conftest.py — ensure aifont is on sys.path for this test package."""

import sys
import os

# Walk up three levels: tests/aifont/ → tests/ → repo root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
