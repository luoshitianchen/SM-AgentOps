"""Agent 注册模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class AgentRegistration(Base):
    """Agent 注册登记：记录一个智能体的身份、提供方与运行状态。"""

    __tablename__ = "agent_registrations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(512), default="")
    # 状态机：registered(已注册) -> active(运行中) -> disabled(停用)
    status: Mapped[str] = mapped_column(String(16), default="registered", index=True)
    # 能力列表，JSON 数组字符串
    capabilities: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
