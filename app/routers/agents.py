"""Agent 注册管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.agent_registration import AgentCreate, AgentStatusUpdate, AgentUpdate
from app.services.agent_registration import AgentService

router = APIRouter(prefix="/api/agents", tags=["agent-registrations"])


@router.get("")
async def list_agents(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    provider: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.list_agents(session, limit=limit, offset=offset,
                                          status_filter=status_filter, provider=provider, keyword=keyword)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.create_agent(session, payload, request)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.get_agent(session, agent_id)


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str, payload: AgentUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.update_agent(session, agent_id, payload, request)


@router.patch("/{agent_id}/status")
async def change_agent_status(
    agent_id: str, payload: AgentStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.change_status(session, agent_id, payload, request)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AgentService.delete_agent(session, agent_id, request)
