from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api import router
from backend.config import get_settings
from backend.db.repository import WorkflowRepository
from backend.logging import configure_logging
from backend.workflows.engine import WorkflowEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    repository = WorkflowRepository(settings.database_url)
    await repository.initialize()

    app.state.settings = settings
    app.state.repository = repository
    app.state.workflow_engine = WorkflowEngine(settings=settings, repository=repository)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
