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
