"""Shared filesystem helpers for the backend package."""

from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
OUTPUTS_DIR = BACKEND_DIR / "outputs"


def resolve_backend_path(file_path: str | Path) -> Path:
    """Resolve a file path against the backend and data directories."""
    path = Path(file_path)
    if path.is_absolute():
        return path

    candidates = [
        Path.cwd() / path,
        BACKEND_DIR / path,
        DATA_DIR / path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return BACKEND_DIR / path
