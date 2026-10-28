"""RelicRat API entry point.

Inventory, media, manual identification and storage APIs.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from relicrat.auth import OwnerBoundary, router as auth_router
from relicrat.inventory import router as inventory_router
from relicrat.storage import router as storage_router
from relicrat.media import router as media_router

from relicrat.catalog import router as catalog_router

app = FastAPI(title="RelicRat API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(OwnerBoundary)
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(media_router)
app.include_router(storage_router)
app.include_router(catalog_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    if request.url.path == '/api/v1/auth/login':
        return JSONResponse({'detail': 'Enter a password of at most 256 characters'}, status_code=422)
    return await request_validation_exception_handler(request, error)
