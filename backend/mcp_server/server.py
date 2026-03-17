from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from backend.config import Settings, get_settings

from .schemas import (
    CompleteTaskInput,
    CreateTaskInput,
    CreateWorkflowInput,
    GenerateLandingPageInput,
    GenerateMarketingPlanInput,
    GenerateSocialMediaPostsInput,
    RunResearchInput,
)
from .service import MCPToolService
from .store import InMemoryTaskStore


def _translate_not_found(exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def create_mcp_server(service: MCPToolService, settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name="aiworkos-mcp",
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=not settings.mcp_disable_dns_rebinding_protection,
        ),
    )

    @mcp.tool()
    async def create_workflow(goal: str, context: dict[str, Any] | None = None) -> dict:
        """Create a workflow record for an AI Work OS project."""
        return await service.create_workflow(
            CreateWorkflowInput(goal=goal, context=context or {})
        )

    @mcp.tool()
    async def create_task(
        workflow_id: str,
        title: str,
        description: str,
        agent_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Create a task tied to a workflow."""
        return await service.create_task(
            CreateTaskInput(
                workflow_id=workflow_id,
                title=title,
                description=description,
                agent_type=agent_type,
                metadata=metadata or {},
            )
        )

    @mcp.tool()
    async def run_research(task_id: str, query: str) -> dict:
        """Run a research task through the research agent."""
        return await service.run_research(RunResearchInput(task_id=task_id, query=query))

    @mcp.tool()
    async def generate_marketing_plan(
        task_id: str,
        product: str,
        audience: str,
        channels: list[str] | None = None,
    ) -> dict:
        """Generate a structured marketing plan with the marketing agent."""
        return await service.generate_marketing_plan(
            GenerateMarketingPlanInput(
                task_id=task_id,
                product=product,
                audience=audience,
                channels=channels or [],
            )
        )

    @mcp.tool()
    async def generate_landing_page(
        task_id: str,
        product: str,
        audience: str,
        offer: str,
    ) -> dict:
        """Generate a landing page spec and starter markup with the coding agent."""
        return await service.generate_landing_page(
            GenerateLandingPageInput(
                task_id=task_id,
                product=product,
                audience=audience,
                offer=offer,
            )
        )

    @mcp.tool()
    async def generate_social_media_posts(
        task_id: str,
        product: str,
        audience: str,
        campaign_theme: str,
        platforms: list[str] | None = None,
    ) -> dict:
        """Generate structured social media post drafts with the marketing agent."""
        return await service.generate_social_media_posts(
            GenerateSocialMediaPostsInput(
                task_id=task_id,
                product=product,
                audience=audience,
                platforms=platforms or [],
                campaign_theme=campaign_theme,
            )
        )

    @mcp.tool()
    async def complete_task(
        task_id: str,
        summary: str,
        artifacts: dict[str, Any] | None = None,
    ) -> dict:
        """Mark a task complete and attach structured result artifacts."""
        return await service.complete_task(
            CompleteTaskInput(
                task_id=task_id,
                summary=summary,
                artifacts=artifacts or {},
            )
        )

    return mcp


def create_fastapi_app(service: MCPToolService, mcp: FastMCP) -> FastAPI:
    mcp_http_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.mcp_service = service
        app.state.mcp_server = mcp
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="AI Work OS MCP Server", lifespan=lifespan)
    app.mount("/mcp", mcp_http_app)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "service": "aiworkos-mcp"}

    @app.post("/tools/create_workflow")
    async def create_workflow_route(payload: CreateWorkflowInput) -> dict[str, Any]:
        return await service.create_workflow(payload)

    @app.post("/tools/create_task")
    async def create_task_route(payload: CreateTaskInput) -> dict[str, Any]:
        try:
            return await service.create_task(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    @app.post("/tools/run_research")
    async def run_research_route(payload: RunResearchInput) -> dict[str, Any]:
        try:
            return await service.run_research(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    @app.post("/tools/generate_marketing_plan")
    async def generate_marketing_plan_route(
        payload: GenerateMarketingPlanInput,
    ) -> dict[str, Any]:
        try:
            return await service.generate_marketing_plan(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    @app.post("/tools/generate_landing_page")
    async def generate_landing_page_route(
        payload: GenerateLandingPageInput,
    ) -> dict[str, Any]:
        try:
            return await service.generate_landing_page(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    @app.post("/tools/generate_social_media_posts")
    async def generate_social_media_posts_route(
        payload: GenerateSocialMediaPostsInput,
    ) -> dict[str, Any]:
        try:
            return await service.generate_social_media_posts(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    @app.post("/tools/complete_task")
    async def complete_task_route(payload: CompleteTaskInput) -> dict[str, Any]:
        try:
            return await service.complete_task(payload)
        except KeyError as exc:
            raise _translate_not_found(exc) from exc

    return app


def build_server_components() -> tuple[InMemoryTaskStore, MCPToolService, FastMCP, FastAPI]:
    settings = get_settings()
    store = InMemoryTaskStore()
    service = MCPToolService(settings=settings, store=store)
    mcp = create_mcp_server(service, settings)
    app = create_fastapi_app(service, mcp)
    return store, service, mcp, app


def main() -> None:
    _, _, server, _ = build_server_components()
    server.run()


_, _, mcp_server, app = build_server_components()


if __name__ == "__main__":
    main()
