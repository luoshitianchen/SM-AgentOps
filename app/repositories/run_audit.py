"""Agent 运行审计日志仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_audit import RunAudit


async def get_audit(session: AsyncSession, audit_id: str) -> RunAudit | None:
    result = await session.execute(select(RunAudit).where(RunAudit.audit_id == audit_id))
    return result.scalar_one_or_none()


async def list_audits(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    agent_code: str | None = None, level: str | None = None,
    task_id: str | None = None,
) -> list[RunAudit]:
    stmt = select(RunAudit).order_by(RunAudit.id.desc()).limit(limit).offset(offset)
    if agent_code:
        stmt = stmt.where(RunAudit.agent_code == agent_code)
    if level:
        stmt = stmt.where(RunAudit.level == level)
    if task_id:
        stmt = stmt.where(RunAudit.task_id == task_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_audits(
    session: AsyncSession, agent_code: str | None = None,
    level: str | None = None, task_id: str | None = None,
) -> int:
    stmt = select(func.count(RunAudit.id))
    if agent_code:
        stmt = stmt.where(RunAudit.agent_code == agent_code)
    if level:
        stmt = stmt.where(RunAudit.level == level)
    if task_id:
        stmt = stmt.where(RunAudit.task_id == task_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_audit(session: AsyncSession, audit: RunAudit) -> RunAudit:
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    return audit
