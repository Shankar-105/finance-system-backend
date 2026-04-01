from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from app.config import get_settings
from app.db import close_connections, redis_client
from app.routes import dashboard, financial_records, users
from app.services.presence_service import handle_presence_socket

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_connections()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(financial_records.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)


@app.websocket("/ws/presence")
async def presence_websocket(websocket: WebSocket) -> None:
    await handle_presence_socket(websocket, redis_client)
