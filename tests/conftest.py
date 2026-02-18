"""
Pytest conftest for Basic Analytics Server tests.

Purpose:
- Ensures the project root (folder containing main.py) is on sys.path,
  so tests can import `main` reliably.

Loaded automatically by pytest before test collection.
"""

import sys
from pathlib import Path

# Add project root (the folder that contains main.py) to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
