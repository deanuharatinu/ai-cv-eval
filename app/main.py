from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes_upload import router as upload_router
from app.api.routes_evaluate import router as evaluate_router
from app.api.routes_result import router as result_router
from app.api.routes_health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.infra.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and dispose of them on shutdown."""
    configure_logging()
    await init_db()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )
    app.include_router(upload_router, tags=["upload"])
    app.include_router(evaluate_router, tags=["evaluate"])
    app.include_router(result_router, prefix="/result", tags=["result"])
    app.include_router(health_router, prefix="/health", tags=["health"])
    return app


app = create_app()
