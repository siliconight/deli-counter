"""The tests live in tests/ and the builder at the repo's root (0.265.0): put the root, and migrations/ for the
one-shots some tests read, on the import path, as the root's own directory was when the tests stood beside it."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "migrations"), ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
