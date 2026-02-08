"""
ZUUP FORGE UI — Vercel entry point
Vercel detects FastAPI apps at index.py, app.py, or server.py.
"""
import sys
from pathlib import Path

# Ensure project root is on path so "forge" is importable (Vercel may not install the package)
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from forge.ui.app import app

__all__ = ["app"]
