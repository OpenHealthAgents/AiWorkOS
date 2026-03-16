from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateWorkflowInput(BaseModel):
    goal: str = Field(..., min_length=5)
    context: dict[str, Any] = Field(default_factory=dict)


class CreateTaskInput(BaseModel):
    workflow_id: str
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    agent_type: str = Field(..., pattern="^(research|marketing|coding|orchestrator)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResearchInput(BaseModel):
    task_id: str
    query: str = Field(..., min_length=3)


class GenerateMarketingPlanInput(BaseModel):
    task_id: str
    product: str = Field(..., min_length=2)
    audience: str = Field(..., min_length=2)
    channels: list[str] = Field(default_factory=list)


class GenerateSocialMediaPostsInput(BaseModel):
    task_id: str
    product: str = Field(..., min_length=2)
    audience: str = Field(..., min_length=2)
    platforms: list[str] = Field(default_factory=list)
    campaign_theme: str = Field(..., min_length=2)


class GenerateLandingPageInput(BaseModel):
    task_id: str
    product: str = Field(..., min_length=2)
    audience: str = Field(..., min_length=2)
    offer: str = Field(..., min_length=2)


class CompleteTaskInput(BaseModel):
    task_id: str
    summary: str = Field(..., min_length=2)
    artifacts: dict[str, Any] = Field(default_factory=dict)
