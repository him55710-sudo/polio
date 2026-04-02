from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent
SOURCE_PATHS = [
    BACKEND_ROOT / "services" / "api" / "src",
    BACKEND_ROOT / "services" / "worker" / "src",
    BACKEND_ROOT / "services" / "render" / "src",
    BACKEND_ROOT / "services" / "ingest" / "src",
    BACKEND_ROOT / "packages" / "domain" / "src",
    BACKEND_ROOT / "packages" / "shared" / "src",
    BACKEND_ROOT / "packages" / "parsers" / "src",
    BACKEND_ROOT / "packages" / "prompts" / "src",
]

for source_path in reversed(SOURCE_PATHS):
    resolved = str(source_path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from polio_api.main import app

__all__ = ["app"]
