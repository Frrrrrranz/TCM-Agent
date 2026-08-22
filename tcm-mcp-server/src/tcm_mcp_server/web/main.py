from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router
from .api.session import router as session_router
from .memory.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def allowed_origins() -> list[str]:
    configured = os.getenv("TCM_AGENT_ALLOWED_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if "*" in origins:
            raise RuntimeError("TCM_AGENT_ALLOWED_ORIGINS must not contain '*'")
        return origins
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app = FastAPI(
    title="TCM-Agent Web Gateway",
    description="Validated WebSocket gateway for the TCM consultation assistant.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)
app.include_router(chat_router)
app.include_router(session_router)


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "TCM-Agent web gateway is active"}
