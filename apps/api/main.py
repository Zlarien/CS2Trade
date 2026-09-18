import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.excluded_items import router as excluded_items_router
from routers.inventory import router as inventory_router

app = FastAPI(title="CS2Trade API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(inventory_router)
app.include_router(auth_router)
app.include_router(excluded_items_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
