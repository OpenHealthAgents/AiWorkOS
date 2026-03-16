from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class InMemoryTaskStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._workflows: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, dict[str, Any]] = {}

    async def create_workflow(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            workflow_id = f"wf-{uuid4().hex[:10]}"
            workflow = {
                "workflow_id": workflow_id,
                "goal": goal,
                "context": context,
                "status": "active",
                "task_ids": [],
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self._workflows[workflow_id] = workflow
            return dict(workflow)

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        async with self._lock:
            workflow = self._workflows.get(workflow_id)
            return dict(workflow) if workflow else None

    async def create_task(
        self,
        workflow_id: str,
        title: str,
        description: str,
        agent_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise KeyError(f"Workflow '{workflow_id}' not found")

            task_id = f"task-{uuid4().hex[:10]}"
            task = {
                "task_id": task_id,
                "workflow_id": workflow_id,
                "title": title,
                "description": description,
                "agent_type": agent_type,
                "metadata": metadata,
                "status": "pending",
                "result": None,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self._tasks[task_id] = task
            workflow["task_ids"].append(task_id)
            workflow["updated_at"] = utc_now()
            return dict(task)

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        async with self._lock:
            task = self._tasks.get(task_id)
            return dict(task) if task else None

    async def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task '{task_id}' not found")

            if status is not None:
                task["status"] = status
            if result is not None:
                task["result"] = result
            task["updated_at"] = utc_now()
            return dict(task)

    async def list_tasks_for_workflow(self, workflow_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise KeyError(f"Workflow '{workflow_id}' not found")
            return [dict(self._tasks[task_id]) for task_id in workflow["task_ids"]]
