"""FastAPI WebSocket server for the local G3 company selector."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT, FRONTEND_ORIGIN, WEB_MODE_ENABLED, WEBSOCKET_PATH
from web_backend.tracking_bridge import TrackingBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app(bridge: TrackingBridge | None = None) -> FastAPI:
    if not WEB_MODE_ENABLED:
        raise RuntimeError("G3 Web Mode is disabled; set WEB_MODE_ENABLED=True in config.py.")
    tracking = bridge or TrackingBridge()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        tracking.start(asyncio.get_running_loop())
        try:
            yield
        finally:
            tracking.stop()

    app = FastAPI(title="AirMouse G3 Local API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"service": "airmouse-g3", "status": "running"}

    @app.websocket(WEBSOCKET_PATH)
    async def tracking_socket(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin and origin != FRONTEND_ORIGIN:
            await websocket.close(code=1008, reason="Origin is not allowed")
            return
        await websocket.accept()
        queue = tracking.subscribe()
        try:
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            logger.info("G3 browser disconnected")
        except Exception:
            logger.exception("G3 WebSocket failed")
            try:
                await websocket.close(code=1011, reason="Tracking stream failed")
            except RuntimeError:
                pass
        finally:
            tracking.unsubscribe(queue)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_backend.server:app", host=API_HOST, port=API_PORT, reload=False)
