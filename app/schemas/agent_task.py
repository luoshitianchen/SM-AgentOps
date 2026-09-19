"""Agent 任务 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    task_no: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9_.-]+$")
    agent_code: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    priority: Literal["low", "medium", "high"] = "medium"
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskComplete(BaseModel):
    result: str = Field(default="", max_length=8192)


class TaskFail(BaseModel):
    error: str = Field(min_length=1, max_length=2048)


class TaskResponse(BaseModel):
    id: str
    task_no: str
    agent_code: str
    title: str
    status: str
    priority: str
    payload: dict[str, Any]
    result: str
    error: str
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]
