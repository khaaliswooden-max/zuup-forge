"""
Vercel entry when repo root is the deployment root.
Ensures the inner zuup-forge app is on the path and exports its app.
"""
from pathlib import Path
import sys

_app_dir = Path(__file__).resolve().parent / "zuup-forge"
if _app_dir.exists() and str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))

from forge.ui.app import app

__all__ = ["app"]
