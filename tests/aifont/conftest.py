"""tests/aifont/conftest.py — ensure aifont is on sys.path for this test package."""

import sys
import os

# Walk up three levels: tests/aifont/ → tests/ → repo root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
