"""Repository-root conftest.py — makes the aifont package importable in tests."""

import sys
import os

# Add the repository root to sys.path so that `import aifont` works regardless
# of how pytest discovers and runs the tests.
_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
