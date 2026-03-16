from __future__ import annotations

import asyncio
from uuid import uuid4

from agents import Runner

from backend.agents.registry import build_agent_registry
from backend.config import Settings
from backend.db.repository import WorkflowRepository
from backend.models import (
    ExecutionMode,
    PlannedWorkflow,
    TaskResult,
    TaskStatus,
    TaskType,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowState,
)
from backend.workflows.decomposer import TaskDecomposer


class WorkflowEngine:
    def __init__(self, settings: Settings, repository: WorkflowRepository) -> None:
        self._settings = settings
        self._repository = repository
        self._decomposer = TaskDecomposer()
        self._agents = build_agent_registry(settings)
        self._workflow_store: dict[str, WorkflowResponse] = {}
        self._workflow_goals: dict[str, str] = {}

    async def execute(self, request: WorkflowRequest) -> WorkflowResponse:
        workflow_id = f"wf-{uuid4().hex[:10]}"
        workflow = await self.create_workflow(workflow_id=workflow_id, request=request)
        return await self.execute_workflow(workflow.workflow_id)

    async def create_workflow(self, workflow_id: str, request: WorkflowRequest) -> WorkflowResponse:
        plan = await self._decomposer.decompose(request)
        response = self._build_workflow_response(
            workflow_id=workflow_id,
            summary=plan.summary,
            state=WorkflowState.pending,
            execution_mode=request.execution_mode,
            tasks=plan.tasks,
        )
        self._workflow_store[workflow_id] = response
        self._workflow_goals[workflow_id] = request.goal
        await self._persist_workflow(goal=request.goal, plan=plan, response=response)
        return response

    async def execute_workflow(self, workflow_id: str) -> WorkflowResponse:
        workflow = self._workflow_store.get(workflow_id)
        if workflow is None:
            stored = await self.get_workflow(workflow_id)
            if stored is None:
                raise ValueError(f"Workflow '{workflow_id}' not found")
            workflow = stored
            self._workflow_store[workflow_id] = workflow

        goal = self._workflow_goals.get(workflow_id, workflow.summary)
        request = WorkflowRequest(
            goal=goal,
            context={},
            execution_mode=workflow.execution_mode,
        )
        plan = PlannedWorkflow(summary=workflow.summary, tasks=workflow.tasks)
        workflow.state = WorkflowState.running
        await self._persist_workflow(goal=request.goal, plan=plan, response=workflow)

        try:
            results = await self._run_plan(workflow, request)
            workflow.results = results
            workflow.state = (
                WorkflowState.failed
                if any(result.status == TaskStatus.failed for result in results)
                else WorkflowState.completed
            )
        except Exception as exc:
            workflow.state = WorkflowState.failed
            await self._persist_workflow(goal=request.goal, plan=plan, response=workflow)
            raise exc

        await self._persist_workflow(goal=request.goal, plan=plan, response=workflow)
        return workflow

    async def get_workflow(self, workflow_id: str) -> WorkflowResponse | None:
        if workflow_id in self._workflow_store:
            return self._workflow_store[workflow_id]
        record = await self._repository.get_workflow(workflow_id)
        if record is None:
            return None
        return WorkflowResponse.model_validate(record["result"])

    async def _run_plan(self, workflow: WorkflowResponse, request: WorkflowRequest) -> list[TaskResult]:
        task_results = {result.task_id: result for result in workflow.results}
        outputs_by_id: dict[str, str] = {}

        if workflow.execution_mode == ExecutionMode.sequential:
            for task in workflow.tasks:
                task_results[task.id].status = TaskStatus.in_progress
                workflow.results = list(task_results.values())
                result = await self._execute_task(task=task, request=request, outputs_by_id=outputs_by_id)
                task_results[task.id] = result
                workflow.results = list(task_results.values())
        else:
            pending = {task.id: task for task in workflow.tasks}
            completed: set[str] = set()

            while pending:
                ready = [
                    task for task in pending.values()
                    if all(dependency in completed for dependency in task.dependencies)
                ]
                if not ready:
                    raise ValueError("Workflow contains unresolved or circular dependencies")

                for task in ready:
                    task_results[task.id].status = TaskStatus.in_progress
                workflow.results = list(task_results.values())

                batch_results = await asyncio.gather(
                    *[
                        self._execute_task(task=task, request=request, outputs_by_id=outputs_by_id)
                        for task in ready
                    ]
                )
                for task, result in zip(ready, batch_results, strict=True):
                    task_results[task.id] = result
                    outputs_by_id[task.id] = result.output
                    completed.add(task.id)
                    pending.pop(task.id, None)
                workflow.results = list(task_results.values())

        return list(task_results.values())

    async def _execute_task(
        self,
        task,
        request: WorkflowRequest,
        outputs_by_id: dict[str, str],
    ) -> TaskResult:
        agent_name = self._resolve_agent_name(task.agent_type)
        prompt = self._build_task_prompt(task.title, task.description, request, outputs_by_id)
        try:
            runner_result = await Runner.run(self._agents[agent_name], prompt)
            output_text = getattr(runner_result, "final_output", str(runner_result))
            outputs_by_id[task.id] = output_text
            return TaskResult(
                task_id=task.id,
                task_key=task.task_key,
                agent_type=task.agent_type,
                assigned_agent=agent_name,
                status=TaskStatus.completed,
                output=output_text,
            )
        except Exception as exc:
            return TaskResult(
                task_id=task.id,
                task_key=task.task_key,
                agent_type=task.agent_type,
                assigned_agent=agent_name,
                status=TaskStatus.failed,
                output="",
                error=str(exc),
            )

    @staticmethod
    def _build_workflow_response(
        workflow_id: str,
        summary: str,
        state: WorkflowState,
        execution_mode: ExecutionMode,
        tasks,
    ) -> WorkflowResponse:
        return WorkflowResponse(
            workflow_id=workflow_id,
            summary=summary,
            state=state,
            execution_mode=execution_mode,
            tasks=tasks,
            results=[
                TaskResult(
                    task_id=task.id,
                    task_key=task.task_key,
                    agent_type=task.agent_type,
                    assigned_agent=WorkflowEngine._resolve_agent_name(task.agent_type),
                    status=TaskStatus.pending,
                )
                for task in tasks
            ],
        )

    async def _persist_workflow(
        self,
        goal: str,
        plan: PlannedWorkflow,
        response: WorkflowResponse,
    ) -> None:
        await self._repository.save_workflow(
            workflow_id=response.workflow_id,
            goal=goal,
            summary=plan.summary,
            plan=plan.model_dump(),
            result=response.model_dump(),
        )

    @staticmethod
    def _build_task_prompt(
        title: str,
        description: str,
        request: WorkflowRequest,
        outputs_by_id: dict[str, str],
    ) -> str:
        dependency_context = "\n".join(
            f"- {task_id}: {output}" for task_id, output in outputs_by_id.items()
        ) or "No prior task output."
        return (
            f"Goal: {request.goal}\n"
            f"Task: {title}\n"
            f"Description: {description}\n"
            f"Context: {request.context}\n"
            f"Completed task outputs:\n{dependency_context}\n"
            "Return an execution-ready response with assumptions, deliverable, and next steps."
        )

    @staticmethod
    def _resolve_agent_name(task_type: TaskType) -> str:
        return {
            TaskType.research: "research_agent",
            TaskType.marketing: "marketing_agent",
            TaskType.coding: "coding_agent",
            TaskType.orchestration: "orchestrator_agent",
        }[task_type]
