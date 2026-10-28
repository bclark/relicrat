"""RelicRat API entry point.

Inventory, media, manual identification and storage APIs.
"""
from fastapi import FastAPI
from relicrat.inventory import router as inventory_router
from relicrat.storage import router as storage_router
from relicrat.media import router as media_router

from relicrat.catalog import router as catalog_router

app = FastAPI(title="RelicRat API", version="0.1.0")
app.include_router(inventory_router)
app.include_router(media_router)
app.include_router(storage_router)
app.include_router(catalog_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
