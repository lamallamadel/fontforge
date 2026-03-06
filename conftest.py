"""Root conftest.py — ensures the repository root is on sys.path for aifont imports."""

import sys
import os

# Add the repository root to sys.path so that `import aifont` works when
# running pytest from any working directory.
sys.path.insert(0, os.path.dirname(__file__))
