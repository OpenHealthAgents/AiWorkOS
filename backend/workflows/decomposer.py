from __future__ import annotations

from uuid import uuid4

from backend.models import PlannedWorkflow, TaskSpec, TaskType, WorkflowRequest


class TaskDecomposer:
    async def decompose(self, request: WorkflowRequest) -> PlannedWorkflow:
        tasks = self._build_tasks(request.goal)

        return PlannedWorkflow(
            summary=f"Task decomposition for goal: {request.goal}",
            tasks=tasks,
        )

    async def decompose_to_json(self, goal: str) -> dict:
        workflow = await self.decompose(WorkflowRequest(goal=goal, context={}))
        return workflow.model_dump()

    def _build_tasks(self, goal: str) -> list[TaskSpec]:
        normalized_goal = goal.lower()
        if "launch" in normalized_goal and ("saas" in normalized_goal or "product" in normalized_goal):
            return self._build_launch_tasks(goal)
        return self._build_default_tasks(goal)

    def _build_launch_tasks(self, goal: str) -> list[TaskSpec]:
        tasks = [
            self._task(
                task_key="research_market",
                title="Research market",
                description=f"Research market demand, competitors, and positioning for {goal}.",
                agent_type=TaskType.research,
            ),
            self._task(
                task_key="define_target_audience",
                title="Define target audience",
                description=f"Identify ICPs, buyer personas, and core use cases for {goal}.",
                agent_type=TaskType.research,
            ),
            self._task(
                task_key="create_landing_page",
                title="Create landing page",
                description=f"Create the landing page structure, messaging, and CTA for {goal}.",
                agent_type=TaskType.coding,
            ),
            self._task(
                task_key="generate_marketing_campaign",
                title="Generate marketing campaign",
                description=f"Create a launch campaign plan for {goal} across core acquisition channels.",
                agent_type=TaskType.marketing,
            ),
            self._task(
                task_key="prepare_product_hunt_launch",
                title="Prepare Product Hunt launch",
                description=f"Prepare Product Hunt assets, messaging, and launch checklist for {goal}.",
                agent_type=TaskType.marketing,
            ),
        ]

        tasks[1].dependencies = [tasks[0].id]
        tasks[2].dependencies = [tasks[1].id]
        tasks[3].dependencies = [tasks[0].id, tasks[1].id]
        tasks[4].dependencies = [tasks[2].id, tasks[3].id]
        return tasks

    def _build_default_tasks(self, goal: str) -> list[TaskSpec]:
        tasks = [
            self._task(
                task_key="research_market",
                title="Research market",
                description=f"Research the market, competitors, and constraints for {goal}.",
                agent_type=TaskType.research,
            ),
            self._task(
                task_key="define_strategy",
                title="Define strategy",
                description=f"Define the go-to-market and execution strategy for {goal}.",
                agent_type=TaskType.marketing,
            ),
            self._task(
                task_key="build_delivery_assets",
                title="Build delivery assets",
                description=f"Create the implementation or asset plan required to deliver {goal}.",
                agent_type=TaskType.coding,
            ),
        ]
        tasks[1].dependencies = [tasks[0].id]
        tasks[2].dependencies = [tasks[0].id, tasks[1].id]
        return tasks

    @staticmethod
    def _task(
        task_key: str,
        title: str,
        description: str,
        agent_type: TaskType,
    ) -> TaskSpec:
        return TaskSpec(
            id=f"task-{uuid4().hex[:8]}",
            task_key=task_key,
            title=title,
            description=description,
            agent_type=agent_type,
        )
