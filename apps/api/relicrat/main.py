"""RelicRat API entry point.

This is a scaffold only. No inventory endpoints are implemented yet.
"""
from fastapi import FastAPI

app = FastAPI(title="RelicRat API", version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
