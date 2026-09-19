"""Agent 任务仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask


async def get_task(session: AsyncSession, task_id: str) -> AgentTask | None:
    result = await session.execute(select(AgentTask).where(AgentTask.id == task_id))
    return result.scalar_one_or_none()


async def get_task_by_no(session: AsyncSession, task_no: str) -> AgentTask | None:
    result = await session.execute(select(AgentTask).where(AgentTask.task_no == task_no))
    return result.scalar_one_or_none()


async def list_tasks(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, agent_code: str | None = None,
    priority: str | None = None,
) -> list[AgentTask]:
    stmt = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(AgentTask.status == status)
    if agent_code:
        stmt = stmt.where(AgentTask.agent_code == agent_code)
    if priority:
        stmt = stmt.where(AgentTask.priority == priority)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_tasks(
    session: AsyncSession, status: str | None = None,
    agent_code: str | None = None, priority: str | None = None,
) -> int:
    stmt = select(func.count(AgentTask.id))
    if status:
        stmt = stmt.where(AgentTask.status == status)
    if agent_code:
        stmt = stmt.where(AgentTask.agent_code == agent_code)
    if priority:
        stmt = stmt.where(AgentTask.priority == priority)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_task(session: AsyncSession, task: AgentTask) -> AgentTask:
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task(session: AsyncSession, task: AgentTask) -> AgentTask:
    await session.commit()
    await session.refresh(task)
    return task
