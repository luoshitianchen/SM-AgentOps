"""Agent 注册服务层：全生命周期与状态机管理。"""
from __future__ import annotations

import json
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.agent_registration import AgentRegistration
from app.repositories import agent_registration as repo
from app.schemas.agent_registration import AgentCreate, AgentStatusUpdate, AgentUpdate
from app.services.audit import record_audit

# 合法状态迁移表
_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"active"},
    "active": {"disabled"},
    "disabled": {"active"},
}


def _agent_to_dict(a: AgentRegistration) -> dict:
    return {
        "id": a.id, "agent_code": a.agent_code, "name": a.name,
        "provider": a.provider, "endpoint": a.endpoint or "",
        "status": a.status, "capabilities": json.loads(a.capabilities or "[]"),
        "description": a.description or "",
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "updated_at": a.updated_at.isoformat() if a.updated_at else "",
    }


class AgentService:
    @staticmethod
    async def list_agents(session, limit, offset, status_filter, provider, keyword) -> dict:
        agents = await repo.list_agents(session, limit=limit, offset=offset,
                                         status=status_filter, provider=provider, keyword=keyword)
        total = await repo.count_agents(session, status=status_filter, provider=provider, keyword=keyword)
        return {"total": total, "items": [_agent_to_dict(a) for a in agents]}

    @staticmethod
    async def get_agent(session: AsyncSession, agent_id: str) -> dict:
        agent = await repo.get_agent(session, agent_id)
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在")
        return _agent_to_dict(agent)

    @staticmethod
    async def create_agent(session: AsyncSession, payload: AgentCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_agent_by_code(session, payload.agent_code):
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent 编码已存在")
        agent = AgentRegistration(
            id=str(uuid.uuid4()), agent_code=payload.agent_code, name=payload.name,
            provider=payload.provider, endpoint=payload.endpoint,
            capabilities=json.dumps(payload.capabilities, ensure_ascii=False),
            description=payload.description, status="registered",
        )
        agent = await repo.create_agent(session, agent)
        await record_audit(session, "agent.registered", "internal",
                           f"agent_code={payload.agent_code}", request)
        return _agent_to_dict(agent)

    @staticmethod
    async def update_agent(session: AsyncSession, agent_id: str, payload: AgentUpdate,
                           request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        agent = await repo.get_agent(session, agent_id)
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在")
        if payload.name is not None:
            agent.name = payload.name
        if payload.endpoint is not None:
            agent.endpoint = payload.endpoint
        if payload.capabilities is not None:
            agent.capabilities = json.dumps(payload.capabilities, ensure_ascii=False)
        if payload.description is not None:
            agent.description = payload.description
        agent = await repo.update_agent(session, agent)
        await record_audit(session, "agent.updated", "internal", f"agent_id={agent_id}", request)
        return _agent_to_dict(agent)

    @staticmethod
    async def change_status(session: AsyncSession, agent_id: str, payload: AgentStatusUpdate,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        agent = await repo.get_agent(session, agent_id)
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在")
        new_status = payload.status
        if new_status == agent.status:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "目标状态与当前状态一致")
        if new_status not in _TRANSITIONS.get(agent.status, set()):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"非法状态迁移: {agent.status} -> {new_status}")
        agent.status = new_status
        agent = await repo.update_agent(session, agent)
        await record_audit(session, "agent.status_changed", "internal",
                           f"agent_code={agent.agent_code} status={new_status}", request)
        return _agent_to_dict(agent)

    @staticmethod
    async def delete_agent(session: AsyncSession, agent_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        agent = await repo.get_agent(session, agent_id)
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在")
        code = agent.agent_code
        await repo.delete_agent(session, agent)
        await record_audit(session, "agent.deleted", "internal", f"agent_code={code}", request)
        return {"deleted": True, "id": agent_id}
