from fastapi import FastAPI

from routers.auth import router as auth_router
from routers.excluded_items import router as excluded_items_router
from routers.inventory import router as inventory_router

app = FastAPI(title="CS2Trade API", version="0.1.0")
app.include_router(inventory_router)
app.include_router(auth_router)
app.include_router(excluded_items_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
