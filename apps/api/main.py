import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.excluded_items import router as excluded_items_router
from routers.inventory import router as inventory_router
from routers.investor import router as investor_router
from routers.portfolio import router as portfolio_router

# uvicorn ne configure que ses propres loggers (uvicorn.*) : sans ceci, le
# logger racine n'a aucun handler et nos warnings (ex: pricing/*) sont
# perdus au lieu d'apparaitre dans les logs du conteneur.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

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
app.include_router(portfolio_router)
app.include_router(investor_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
