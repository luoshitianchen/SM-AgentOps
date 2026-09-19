"""Agent 运行审计日志 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RunAuditCreate(BaseModel):
    agent_code: str = Field(min_length=1, max_length=128)
    task_id: str = Field(default="", max_length=64)
    level: str = Field(default="info", pattern=r"^(info|warn|error)$")
    message: str = Field(min_length=1, max_length=4096)
    duration_ms: int = Field(default=0, ge=0, le=86_400_000)


class RunAuditResponse(BaseModel):
    id: int
    audit_id: str
    agent_code: str
    task_id: str
    level: str
    message: str
    duration_ms: int
    created_at: datetime


class RunAuditListResponse(BaseModel):
    total: int
    items: list[RunAuditResponse]
