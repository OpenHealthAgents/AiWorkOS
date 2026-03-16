from __future__ import annotations

from typing import Any

from agents import Runner

from backend.agents.registry import build_agent_registry
from backend.config import Settings

from .schemas import (
    CompleteTaskInput,
    CreateTaskInput,
    CreateWorkflowInput,
    GenerateLandingPageInput,
    GenerateMarketingPlanInput,
    GenerateSocialMediaPostsInput,
    RunResearchInput,
)
from .store import InMemoryTaskStore


class MCPToolService:
    def __init__(self, settings: Settings, store: InMemoryTaskStore) -> None:
        self._store = store
        self._agents = build_agent_registry(settings)

    async def create_workflow(self, payload: CreateWorkflowInput) -> dict[str, Any]:
        workflow = await self._store.create_workflow(goal=payload.goal, context=payload.context)
        return {
            "ok": True,
            "workflow": workflow,
        }

    async def create_task(self, payload: CreateTaskInput) -> dict[str, Any]:
        task = await self._store.create_task(
            workflow_id=payload.workflow_id,
            title=payload.title,
            description=payload.description,
            agent_type=payload.agent_type,
            metadata=payload.metadata,
        )
        return {
            "ok": True,
            "task": task,
        }

    async def run_research(self, payload: RunResearchInput) -> dict[str, Any]:
        task = await self._store.update_task(payload.task_id, status="in_progress")
        prompt = (
            f"Research request: {payload.query}\n"
            f"Task title: {task['title']}\n"
            f"Task description: {task['description']}\n"
            "Return JSON-ready research findings with insights, assumptions, and next steps."
        )
        result_text = await self._run_agent("research_agent", prompt)
        result = {
            "query": payload.query,
            "research_output": result_text,
        }
        task = await self._store.update_task(payload.task_id, status="completed", result=result)
        return {
            "ok": True,
            "task": task,
        }

    async def generate_marketing_plan(self, payload: GenerateMarketingPlanInput) -> dict[str, Any]:
        task = await self._store.update_task(payload.task_id, status="in_progress")
        prompt = (
            f"Product: {payload.product}\n"
            f"Audience: {payload.audience}\n"
            f"Channels: {payload.channels}\n"
            "Create a practical marketing plan with positioning, campaign ideas, message pillars, "
            "success metrics, and launch sequence."
        )
        result_text = await self._run_agent("marketing_agent", prompt)
        result = {
            "product": payload.product,
            "audience": payload.audience,
            "channels": payload.channels,
            "marketing_plan": result_text,
        }
        task = await self._store.update_task(payload.task_id, status="completed", result=result)
        return {
            "ok": True,
            "task": task,
        }

    async def generate_landing_page(self, payload: GenerateLandingPageInput) -> dict[str, Any]:
        task = await self._store.update_task(payload.task_id, status="in_progress")
        prompt = (
            f"Product: {payload.product}\n"
            f"Audience: {payload.audience}\n"
            f"Offer: {payload.offer}\n"
            "Generate a launch-ready landing page specification with hero copy, section outline, "
            "CTA strategy, and a semantic HTML skeleton."
        )
        result_text = await self._run_agent("coding_agent", prompt)
        result = {
            "product": payload.product,
            "audience": payload.audience,
            "offer": payload.offer,
            "landing_page": result_text,
        }
        task = await self._store.update_task(payload.task_id, status="completed", result=result)
        return {
            "ok": True,
            "task": task,
        }

    async def generate_social_media_posts(
        self,
        payload: GenerateSocialMediaPostsInput,
    ) -> dict[str, Any]:
        task = await self._store.update_task(payload.task_id, status="in_progress")
        prompt = (
            f"Product: {payload.product}\n"
            f"Audience: {payload.audience}\n"
            f"Platforms: {payload.platforms}\n"
            f"Campaign theme: {payload.campaign_theme}\n"
            "Create a short social media campaign pack with platform-specific posts, hooks, "
            "CTAs, hashtags, and repurposing guidance."
        )
        result_text = await self._run_agent("marketing_agent", prompt)
        result = {
            "product": payload.product,
            "audience": payload.audience,
            "platforms": payload.platforms,
            "campaign_theme": payload.campaign_theme,
            "social_posts": result_text,
        }
        task = await self._store.update_task(payload.task_id, status="completed", result=result)
        return {
            "ok": True,
            "task": task,
        }

    async def complete_task(self, payload: CompleteTaskInput) -> dict[str, Any]:
        result = {
            "summary": payload.summary,
            "artifacts": payload.artifacts,
        }
        task = await self._store.update_task(payload.task_id, status="completed", result=result)
        return {
            "ok": True,
            "task": task,
        }

    async def _run_agent(self, agent_name: str, prompt: str) -> str:
        runner_result = await Runner.run(self._agents[agent_name], prompt)
        return getattr(runner_result, "final_output", str(runner_result))
