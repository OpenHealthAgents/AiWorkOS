from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.models import HealthResponse, WorkflowRequest, WorkflowResponse
from backend.workflows.engine import WorkflowEngine

router = APIRouter(prefix="/api/v1")


def get_engine(request: Request) -> WorkflowEngine:
    return request.app.state.workflow_engine


@router.get("/health", response_model=HealthResponse)
async def healthcheck(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", app=request.app.title)


@router.post("/workflows/execute", response_model=WorkflowResponse)
async def execute_workflow(
    payload: WorkflowRequest,
    engine: WorkflowEngine = Depends(get_engine),
) -> WorkflowResponse:
    try:
        return await engine.execute(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    engine: WorkflowEngine = Depends(get_engine),
) -> WorkflowResponse:
    workflow = await engine.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow
