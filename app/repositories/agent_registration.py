"""Agent 注册仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_registration import AgentRegistration


async def get_agent(session: AsyncSession, agent_id: str) -> AgentRegistration | None:
    result = await session.execute(select(AgentRegistration).where(AgentRegistration.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_by_code(session: AsyncSession, agent_code: str) -> AgentRegistration | None:
    result = await session.execute(select(AgentRegistration).where(AgentRegistration.agent_code == agent_code))
    return result.scalar_one_or_none()


async def list_agents(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, provider: str | None = None,
    keyword: str | None = None,
) -> list[AgentRegistration]:
    stmt = select(AgentRegistration).order_by(AgentRegistration.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(AgentRegistration.status == status)
    if provider:
        stmt = stmt.where(AgentRegistration.provider == provider)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(AgentRegistration.name.like(like), AgentRegistration.agent_code.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_agents(
    session: AsyncSession, status: str | None = None,
    provider: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(AgentRegistration.id))
    if status:
        stmt = stmt.where(AgentRegistration.status == status)
    if provider:
        stmt = stmt.where(AgentRegistration.provider == provider)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(AgentRegistration.name.like(like), AgentRegistration.agent_code.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_agent(session: AsyncSession, agent: AgentRegistration) -> AgentRegistration:
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def update_agent(session: AsyncSession, agent: AgentRegistration) -> AgentRegistration:
    await session.commit()
    await session.refresh(agent)
    return agent


async def delete_agent(session: AsyncSession, agent: AgentRegistration) -> None:
    await session.delete(agent)
    await session.commit()
