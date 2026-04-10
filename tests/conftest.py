"""
Pytest conftest for Basic Analytics Server tests.

Purpose:
- Ensures the project root (folder containing main.py) is on sys.path,
  so tests can import `main` reliably.

Loaded automatically by pytest before test collection.
"""

import sys
from pathlib import Path

# Why this is needed:
# - When running `pytest` from the repo root, imports usually work naturally.
# - Some IDE/test runners execute tests with a different working directory,
#   which can make `import main` fail unless the repo root is on sys.path.
#
# This file is automatically discovered by pytest (because it's named conftest.py)
# and executed before tests are collected.

# Project root is one directory above /tests (i.e. contains main.py).
ROOT = Path(__file__).resolve().parents[1]

# Ensure the root is first so local modules win over any similarly-named installed packages.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
