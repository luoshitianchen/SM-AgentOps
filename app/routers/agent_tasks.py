"""Agent 任务管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.agent_task import TaskComplete, TaskCreate, TaskFail
from app.services.agent_task import TaskService

router = APIRouter(prefix="/api/agent-tasks", tags=["agent-tasks"])


@router.get("")
async def list_tasks(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    agent_code: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.list_tasks(session, limit=limit, offset=offset,
                                        status_filter=status_filter, agent_code=agent_code,
                                        priority=priority)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.create_task(session, payload, request)


@router.get("/{task_id}")
async def get_task(
    task_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.get_task(session, task_id)


@router.post("/{task_id}/start")
async def start_task(
    task_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.start_task(session, task_id, request)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str, payload: TaskComplete, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.complete_task(session, task_id, payload, request)


@router.post("/{task_id}/fail")
async def fail_task(
    task_id: str, payload: TaskFail, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.fail_task(session, task_id, payload, request)
