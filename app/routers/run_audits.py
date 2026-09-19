"""Agent 运行审计日志路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.run_audit import RunAuditCreate
from app.services.run_audit import RunAuditService

router = APIRouter(prefix="/api/run-audits", tags=["run-audits"])


@router.get("")
async def list_audits(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    agent_code: str | None = Query(default=None),
    level: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RunAuditService.list_audits(session, limit=limit, offset=offset,
                                             agent_code=agent_code, level=level, task_id=task_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_audit(
    payload: RunAuditCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RunAuditService.create_audit(session, payload, request)


@router.get("/{audit_id}")
async def get_audit(
    audit_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await RunAuditService.get_audit(session, audit_id)
