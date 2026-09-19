"""Agent 任务服务层：调度与执行状态机。"""
from __future__ import annotations

import json
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.agent_task import AgentTask
from app.repositories import agent_registration as agent_repo
from app.repositories import agent_task as repo
from app.schemas.agent_task import TaskComplete, TaskCreate, TaskFail
from app.services.audit import record_audit

# 任务合法状态迁移表
_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running"},
    "running": {"succeeded", "failed"},
    "succeeded": set(),
    "failed": set(),
}


def _task_to_dict(t: AgentTask) -> dict:
    return {
        "id": t.id, "task_no": t.task_no, "agent_code": t.agent_code, "title": t.title,
        "status": t.status, "priority": t.priority,
        "payload": json.loads(t.payload or "{}"),
        "result": t.result or "", "error": t.error or "",
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
    }


def _guard_transition(current: str, new_status: str) -> None:
    if new_status == current:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "目标状态与当前状态一致")
    if new_status not in _TRANSITIONS.get(current, set()):
        raise HTTPException(status.HTTP_409_CONFLICT, f"非法状态迁移: {current} -> {new_status}")


class TaskService:
    @staticmethod
    async def list_tasks(session, limit, offset, status_filter, agent_code, priority) -> dict:
        tasks = await repo.list_tasks(session, limit=limit, offset=offset, status=status_filter,
                                      agent_code=agent_code, priority=priority)
        total = await repo.count_tasks(session, status=status_filter, agent_code=agent_code,
                                      priority=priority)
        return {"total": total, "items": [_task_to_dict(t) for t in tasks]}

    @staticmethod
    async def get_task(session: AsyncSession, task_id: str) -> dict:
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
        return _task_to_dict(task)

    @staticmethod
    async def create_task(session: AsyncSession, payload: TaskCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        # 任务必须归属一个已激活的 Agent
        agent = await agent_repo.get_agent_by_code(session, payload.agent_code)
        if not agent:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "归属 Agent 不存在")
        if agent.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent 未激活，无法下发任务")
        if await repo.get_task_by_no(session, payload.task_no):
            raise HTTPException(status.HTTP_409_CONFLICT, "任务编号已存在")
        task = AgentTask(
            id=str(uuid.uuid4()), task_no=payload.task_no, agent_code=payload.agent_code,
            title=payload.title, priority=payload.priority,
            payload=json.dumps(payload.payload, ensure_ascii=False), status="pending",
        )
        task = await repo.create_task(session, task)
        await record_audit(session, "task.created", "internal",
                           f"task_no={payload.task_no} agent={payload.agent_code}", request)
        return _task_to_dict(task)

    @staticmethod
    async def start_task(session: AsyncSession, task_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
        _guard_transition(task.status, "running")
        task.status = "running"
        task = await repo.update_task(session, task)
        await record_audit(session, "task.started", "internal", f"task_no={task.task_no}", request)
        return _task_to_dict(task)

    @staticmethod
    async def complete_task(session: AsyncSession, task_id: str, payload: TaskComplete,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
        _guard_transition(task.status, "succeeded")
        task.status = "succeeded"
        task.result = payload.result
        task = await repo.update_task(session, task)
        await record_audit(session, "task.completed", "internal", f"task_no={task.task_no}", request)
        return _task_to_dict(task)

    @staticmethod
    async def fail_task(session: AsyncSession, task_id: str, payload: TaskFail,
                        request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "任务不存在")
        _guard_transition(task.status, "failed")
        task.status = "failed"
        task.error = payload.error
        task = await repo.update_task(session, task)
        await record_audit(session, "task.failed", "internal",
                           f"task_no={task.task_no} error={payload.error}", request)
        return _task_to_dict(task)
