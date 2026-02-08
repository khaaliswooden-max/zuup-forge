"""
ZUUP FORGE UI — Vercel entry point
Vercel detects FastAPI apps at index.py, app.py, or server.py.
"""
from forge.ui.app import app

__all__ = ["app"]
