"""Agent 注册 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    agent_code: str = Field(min_length=2, max_length=128, pattern=r"^[a-zA-Z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=64)
    endpoint: str = Field(default="", max_length=512)
    capabilities: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=512)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    endpoint: str | None = Field(default=None, max_length=512)
    capabilities: list[str] | None = None
    description: str | None = Field(default=None, max_length=512)


class AgentStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(registered|active|disabled)$")


class AgentResponse(BaseModel):
    id: str
    agent_code: str
    name: str
    provider: str
    endpoint: str
    status: str
    capabilities: list[str]
    description: str
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    total: int
    items: list[AgentResponse]
