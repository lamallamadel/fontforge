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
