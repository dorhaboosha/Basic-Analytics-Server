"""
Pytest conftest for Basic Analytics Server tests.

Ensures the project root is on sys.path so tests can import the app (e.g. main, main.app).
Loaded automatically by pytest before test collection.
"""

import sys
from pathlib import Path

# Add project root (the folder that contains main.py) to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
