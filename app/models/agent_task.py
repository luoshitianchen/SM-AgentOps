"""Agent 任务模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class AgentTask(Base):
    """Agent 任务：一个可被调度执行的作业。"""

    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_no: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    # 归属 Agent 的 agent_code（逻辑外键）
    agent_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    # 状态机：pending -> running -> succeeded | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # 优先级：low / medium / high
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    # 任务入参，JSON 对象字符串
    payload: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
