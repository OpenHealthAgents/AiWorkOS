from __future__ import annotations

from typing import Any

from agents import Agent, Runner, function_tool

from backend.config import Settings
from backend.mcp_server.schemas import (
    CompleteTaskInput,
    CreateTaskInput,
    CreateWorkflowInput,
    GenerateLandingPageInput,
    GenerateMarketingPlanInput,
    GenerateSocialMediaPostsInput,
    RunResearchInput,
)
from backend.mcp_server.service import MCPToolService


class OrchestratorWorkflow:
    def __init__(self, settings: Settings, mcp_service: MCPToolService) -> None:
        self._settings = settings
        self._mcp_service = mcp_service
        self._specialists = self._build_specialists()
        self._orchestrator_agent = self._build_orchestrator_agent()

    async def execute(self, user_request: str) -> dict[str, Any]:
        workflow = await self._mcp_service.create_workflow(
            CreateWorkflowInput(
                goal=user_request,
                context={"source": "orchestrator_agent"},
            )
        )
        workflow_id = workflow["workflow"]["workflow_id"]
        tasks = self._decompose_request(workflow_id=workflow_id, user_request=user_request)

        created_tasks: list[dict[str, Any]] = []
        task_outputs: list[dict[str, Any]] = []

        for task in tasks:
            created = await self._mcp_service.create_task(task)
            created_task = created["task"]
            created_tasks.append(created_task)

            specialized_output = await self._run_specialist(
                task=created_task,
                user_request=user_request,
            )
            tool_output = await self._execute_task_tool(
                task=created_task,
                user_request=user_request,
            )
            completion = await self._mcp_service.complete_task(
                CompleteTaskInput(
                    task_id=created_task["task_id"],
                    summary=f"{created_task['title']} completed by {created_task['agent_type']} agent",
                    artifacts={
                        "specialist_output": specialized_output,
                        "tool_output": tool_output,
                    },
                )
            )
            task_outputs.append(completion["task"])

        final_summary = await Runner.run(
            self._orchestrator_agent,
            self._build_summary_prompt(user_request=user_request, task_outputs=task_outputs),
        )
        final_output = getattr(final_summary, "final_output", str(final_summary))

        return {
            "ok": True,
            "workflow": workflow["workflow"],
            "tasks": created_tasks,
            "completed_tasks": task_outputs,
            "orchestrator_summary": final_output,
        }

    def _decompose_request(self, workflow_id: str, user_request: str) -> list[CreateTaskInput]:
        lower_request = user_request.lower()
        product_name = self._extract_product_name(user_request)
        campaign_theme = "launch campaign"
        if "marketing campaign" in lower_request:
            campaign_theme = "integrated marketing campaign"

        return [
            CreateTaskInput(
                workflow_id=workflow_id,
                title="Research market",
                description=f"Research the target market, competitors, and audience for {product_name}.",
                agent_type="research",
                metadata={"step": 1, "requested_by": user_request},
            ),
            CreateTaskInput(
                workflow_id=workflow_id,
                title="Create marketing plan",
                description=f"Create a marketing plan for {product_name} based on research.",
                agent_type="marketing",
                metadata={"step": 2, "campaign_theme": campaign_theme},
            ),
            CreateTaskInput(
                workflow_id=workflow_id,
                title="Generate social media posts",
                description=f"Generate channel-specific social posts for {product_name}.",
                agent_type="marketing",
                metadata={
                    "step": 3,
                    "platforms": ["linkedin", "x"],
                    "campaign_theme": campaign_theme,
                },
            ),
            CreateTaskInput(
                workflow_id=workflow_id,
                title="Create landing page",
                description=f"Create a landing page outline and starter copy for {product_name}.",
                agent_type="coding",
                metadata={"step": 4, "offer": "Book a demo"},
            ),
        ]

    async def _run_specialist(self, task: dict[str, Any], user_request: str) -> str:
        agent_name = self._resolve_specialist(task["agent_type"])
        prompt = (
            f"User request: {user_request}\n"
            f"Assigned task: {task['title']}\n"
            f"Task description: {task['description']}\n"
            f"Task metadata: {task['metadata']}\n"
            "Return concise execution guidance for the MCP tool call."
        )
        result = await Runner.run(self._specialists[agent_name], prompt)
        return getattr(result, "final_output", str(result))

    async def _execute_task_tool(
        self,
        task: dict[str, Any],
        user_request: str,
    ) -> dict[str, Any]:
        product_name = self._extract_product_name(user_request)
        audience = "startup founders and AI buyers"

        if task["title"] == "Research market":
            return await self._mcp_service.run_research(
                RunResearchInput(task_id=task["task_id"], query=f"Market analysis for {product_name}")
            )

        if task["title"] == "Create marketing plan":
            return await self._mcp_service.generate_marketing_plan(
                GenerateMarketingPlanInput(
                    task_id=task["task_id"],
                    product=product_name,
                    audience=audience,
                    channels=["linkedin", "x", "email"],
                )
            )

        if task["title"] == "Generate social media posts":
            return await self._mcp_service.generate_social_media_posts(
                GenerateSocialMediaPostsInput(
                    task_id=task["task_id"],
                    product=product_name,
                    audience=audience,
                    campaign_theme=task["metadata"].get("campaign_theme", "product launch"),
                    platforms=task["metadata"].get("platforms", ["linkedin", "x"]),
                )
            )

        if task["title"] == "Create landing page":
            return await self._mcp_service.generate_landing_page(
                GenerateLandingPageInput(
                    task_id=task["task_id"],
                    product=product_name,
                    audience=audience,
                    offer=task["metadata"].get("offer", "Get started"),
                )
            )

        raise ValueError(f"Unsupported task title: {task['title']}")

    def _build_specialists(self) -> dict[str, Agent]:
        return {
            "research_agent": Agent(
                name="research_agent",
                model=self._settings.research_model,
                instructions=(
                    "You are a research specialist. Prepare focused guidance that helps the orchestrator "
                    "execute research tasks through MCP tools."
                ),
            ),
            "marketing_agent": Agent(
                name="marketing_agent",
                model=self._settings.marketing_model,
                instructions=(
                    "You are a marketing specialist. Prepare practical guidance for campaign, messaging, "
                    "and social content tasks."
                ),
            ),
            "coding_agent": Agent(
                name="coding_agent",
                model=self._settings.coding_model,
                instructions=(
                    "You are a product engineering specialist. Prepare concise implementation guidance for "
                    "landing page and build tasks."
                ),
            ),
        }

    def _build_orchestrator_agent(self) -> Agent:
        mcp_service = self._mcp_service

        @function_tool
        async def create_workflow_tool(goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
            return await mcp_service.create_workflow(
                CreateWorkflowInput(goal=goal, context=context or {})
            )

        @function_tool
        async def create_task_tool(
            workflow_id: str,
            title: str,
            description: str,
            agent_type: str,
            metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return await mcp_service.create_task(
                CreateTaskInput(
                    workflow_id=workflow_id,
                    title=title,
                    description=description,
                    agent_type=agent_type,
                    metadata=metadata or {},
                )
            )

        @function_tool
        async def run_research_tool(task_id: str, query: str) -> dict[str, Any]:
            return await mcp_service.run_research(
                RunResearchInput(task_id=task_id, query=query)
            )

        @function_tool
        async def generate_marketing_plan_tool(
            task_id: str,
            product: str,
            audience: str,
            channels: list[str],
        ) -> dict[str, Any]:
            return await mcp_service.generate_marketing_plan(
                GenerateMarketingPlanInput(
                    task_id=task_id,
                    product=product,
                    audience=audience,
                    channels=channels,
                )
            )

        @function_tool
        async def generate_social_media_posts_tool(
            task_id: str,
            product: str,
            audience: str,
            campaign_theme: str,
            platforms: list[str],
        ) -> dict[str, Any]:
            return await mcp_service.generate_social_media_posts(
                GenerateSocialMediaPostsInput(
                    task_id=task_id,
                    product=product,
                    audience=audience,
                    campaign_theme=campaign_theme,
                    platforms=platforms,
                )
            )

        @function_tool
        async def generate_landing_page_tool(
            task_id: str,
            product: str,
            audience: str,
            offer: str,
        ) -> dict[str, Any]:
            return await mcp_service.generate_landing_page(
                GenerateLandingPageInput(
                    task_id=task_id,
                    product=product,
                    audience=audience,
                    offer=offer,
                )
            )

        @function_tool
        async def complete_task_tool(
            task_id: str,
            summary: str,
            artifacts: dict[str, Any],
        ) -> dict[str, Any]:
            return await mcp_service.complete_task(
                CompleteTaskInput(task_id=task_id, summary=summary, artifacts=artifacts)
            )

        return Agent(
            name="orchestrator_agent",
            model=self._settings.default_model,
            instructions=(
                "You are the orchestrator agent for an AI Work Operating System. Accept a user request, "
                "break it into tasks, assign the tasks to specialists, call MCP tools in sequence, and "
                "return a unified workflow summary."
            ),
            handoffs=list(self._specialists.values()),
            tools=[
                create_workflow_tool,
                create_task_tool,
                run_research_tool,
                generate_marketing_plan_tool,
                generate_social_media_posts_tool,
                generate_landing_page_tool,
                complete_task_tool,
            ],
        )

    @staticmethod
    def _resolve_specialist(agent_type: str) -> str:
        return {
            "research": "research_agent",
            "marketing": "marketing_agent",
            "coding": "coding_agent",
            "orchestrator": "research_agent",
        }[agent_type]

    @staticmethod
    def _extract_product_name(user_request: str) -> str:
        lowered = user_request.lower()
        if " for " in lowered:
            split_index = lowered.index(" for ")
            return user_request[split_index + 5 :].strip().rstrip(".")
        return "the product"

    @staticmethod
    def _build_summary_prompt(user_request: str, task_outputs: list[dict[str, Any]]) -> str:
        lines = []
        for item in task_outputs:
            lines.append(
                f"- {item['title']} ({item['agent_type']}): {item['result']}"
            )
        joined = "\n".join(lines)
        return (
            f"User request: {user_request}\n"
            f"Completed tasks:\n{joined}\n"
            "Summarize the workflow execution, outcomes, and recommended next actions."
        )


async def execute_orchestrated_request(
    user_request: str,
    settings: Settings,
    mcp_service: MCPToolService,
) -> dict[str, Any]:
    workflow = OrchestratorWorkflow(settings=settings, mcp_service=mcp_service)
    return await workflow.execute(user_request)
