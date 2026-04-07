from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend package root is importable in Vercel's function runtime.
BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
backend_path = str(BACKEND_ROOT)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import app

__all__ = ["app"]
