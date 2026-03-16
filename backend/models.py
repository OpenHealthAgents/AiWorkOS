from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    research = "research"
    marketing = "marketing"
    coding = "coding"
    orchestration = "orchestration"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class WorkflowState(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ExecutionMode(str, Enum):
    sequential = "sequential"
    parallel = "parallel"


class WorkflowRequest(BaseModel):
    goal: str = Field(..., min_length=5)
    context: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.sequential


class TaskSpec(BaseModel):
    id: str
    task_key: str
    title: str
    description: str
    agent_type: TaskType
    dependencies: list[str] = Field(default_factory=list)


class PlannedWorkflow(BaseModel):
    summary: str
    tasks: list[TaskSpec]


class TaskResult(BaseModel):
    task_id: str
    task_key: str
    agent_type: TaskType
    assigned_agent: str
    status: TaskStatus
    output: str = ""
    error: str | None = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    summary: str
    state: WorkflowState
    execution_mode: ExecutionMode
    tasks: list[TaskSpec]
    results: list[TaskResult]


class HealthResponse(BaseModel):
    status: str
    app: str
