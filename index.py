"""
ZUUP FORGE UI — Vercel entry point
Vercel detects FastAPI apps at index.py, app.py, or server.py.
"""
import sys
from pathlib import Path

# Ensure "forge" is importable: it lives in zuup-forge/ when deploying from repo root
_root = Path(__file__).resolve().parent
_deploy_root = _root / "zuup-forge" if (_root / "zuup-forge" / "forge").exists() else _root
if str(_deploy_root) not in sys.path:
    sys.path.insert(0, str(_deploy_root))

from forge.ui.app import app

__all__ = ["app"]
