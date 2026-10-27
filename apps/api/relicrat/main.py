"""RelicRat API entry point.

This is a scaffold only. No inventory endpoints are implemented yet.
"""
from fastapi import FastAPI
from relicrat.inventory import router as inventory_router

app = FastAPI(title="RelicRat API", version="0.1.0")
app.include_router(inventory_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
