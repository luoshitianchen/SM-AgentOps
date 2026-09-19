"""Agent 运行审计日志服务层：追加式记录与检索。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.run_audit import RunAudit
from app.repositories import agent_registration as agent_repo
from app.repositories import run_audit as repo
from app.schemas.run_audit import RunAuditCreate
from app.services.audit import record_audit


def _audit_to_dict(r: RunAudit) -> dict:
    return {
        "id": r.id, "audit_id": r.audit_id, "agent_code": r.agent_code,
        "task_id": r.task_id or "", "level": r.level, "message": r.message or "",
        "duration_ms": r.duration_ms,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


class RunAuditService:
    @staticmethod
    async def list_audits(session, limit, offset, agent_code, level, task_id) -> dict:
        items = await repo.list_audits(session, limit=limit, offset=offset, agent_code=agent_code,
                                       level=level, task_id=task_id)
        total = await repo.count_audits(session, agent_code=agent_code, level=level, task_id=task_id)
        return {"total": total, "items": [_audit_to_dict(r) for r in items]}

    @staticmethod
    async def get_audit(session: AsyncSession, audit_id: str) -> dict:
        item = await repo.get_audit(session, audit_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审计日志不存在")
        return _audit_to_dict(item)

    @staticmethod
    async def create_audit(session: AsyncSession, payload: RunAuditCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        # 运行日志必须归属一个已注册的 Agent
        agent = await agent_repo.get_agent_by_code(session, payload.agent_code)
        if not agent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Agent 不存在，无法记录运行日志")
        item = RunAudit(
            audit_id=str(uuid.uuid4()), agent_code=payload.agent_code, task_id=payload.task_id,
            level=payload.level, message=payload.message, duration_ms=payload.duration_ms,
        )
        item = await repo.create_audit(session, item)
        await record_audit(session, "run_audit.recorded", "internal",
                           f"agent_code={payload.agent_code} level={payload.level}", request)
        return _audit_to_dict(item)
