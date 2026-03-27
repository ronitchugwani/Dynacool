"""Render entrypoint for the FastAPI backend."""

from __future__ import annotations

from backend_api import APP as app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=10000, reload=False)
