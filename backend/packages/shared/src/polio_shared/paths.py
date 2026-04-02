from __future__ import annotations

import os
from pathlib import Path
import re


def _is_backend_root(candidate: Path) -> bool:
    return (
        (candidate / "pyproject.toml").exists()
        and (candidate / "services" / "api" / "src").exists()
        and (candidate / "packages" / "shared" / "src").exists()
    )


def find_project_root() -> Path:
    search_points = [Path.cwd(), Path(__file__).resolve()]

    for start in search_points:
        for candidate in [start, *start.parents]:
            if _is_backend_root(candidate):
                return candidate

    raise RuntimeError("Could not find the polio-backend project root.")


def _get_storage_override() -> Path | None:
    configured = os.getenv("POLIO_STORAGE_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser()

    if os.getenv("VERCEL") == "1":
        return Path("/tmp/polio")

    return None


def get_storage_root() -> Path:
    override = _get_storage_override()
    if override is not None:
        return override
    return find_project_root() / "storage"


def get_upload_root() -> Path:
    return get_storage_root() / "uploads"


def get_export_root() -> Path:
    return get_storage_root() / "exports"


def get_runtime_root() -> Path:
    return get_storage_root() / "runtime"


def get_tmp_root() -> Path:
    override = _get_storage_override()
    if override is not None:
        return override / "tmp"
    return find_project_root() / "tmp"


def resolve_runtime_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == "storage":
        return get_storage_root().joinpath(*path.parts[1:])
    if path.parts and path.parts[0] == "tmp":
        return get_tmp_root().joinpath(*path.parts[1:])
    return find_project_root().joinpath(*path.parts)


def ensure_app_directories() -> None:
    for path in [get_storage_root(), get_upload_root(), get_export_root(), get_runtime_root(), get_tmp_root()]:
        path.mkdir(parents=True, exist_ok=True)


def resolve_project_path(value: str | Path) -> Path:
    return resolve_runtime_path(value)


def resolve_stored_path(stored_path: str) -> Path:
    path = Path(stored_path)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "storage":
        return resolve_runtime_path(path)
    return get_storage_root() / path


def to_stored_path(value: str | Path) -> str:
    path = Path(value)
    try:
        return str(path.relative_to(find_project_root()))
    except ValueError:
        return str(path)


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    lowered = re.sub(r"[-\s]+", "-", lowered)
    return lowered or "item"
