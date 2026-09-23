"""新增业务表：Agent 注册、Agent 任务与运行审计。

Revision ID: 0002_business_tables
Revises: 0001_initial
Create Date: 2026-09-23
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# 本迁移的版本号，下游 0003 及以后迁移以此为 down_revision
revision: str = '0002_business_tables'
# 上一版本，承接 0001_initial
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Alembic 自动生成开始，按模型元数据建立业务表 ###
    # Agent 注册表：登记可被调度的智能体及其接入信息
    op.create_table('agent_registrations',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('agent_code', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('endpoint', sa.String(length=512), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('capabilities', sa.Text(), nullable=False),
    sa.Column('description', sa.String(length=512), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_registrations_agent_code'), 'agent_registrations', ['agent_code'], unique=True)
    op.create_index(op.f('ix_agent_registrations_provider'), 'agent_registrations', ['provider'], unique=False)
    op.create_index(op.f('ix_agent_registrations_status'), 'agent_registrations', ['status'], unique=False)
    # Agent 任务表：记录派发给智能体的执行任务及其结果
    op.create_table('agent_tasks',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('task_no', sa.String(length=128), nullable=False),
    sa.Column('agent_code', sa.String(length=128), nullable=False),
    sa.Column('title', sa.String(length=256), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('priority', sa.String(length=16), nullable=False),
    sa.Column('payload', sa.Text(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('error', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_tasks_agent_code'), 'agent_tasks', ['agent_code'], unique=False)
    op.create_index(op.f('ix_agent_tasks_priority'), 'agent_tasks', ['priority'], unique=False)
    op.create_index(op.f('ix_agent_tasks_status'), 'agent_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_agent_tasks_task_no'), 'agent_tasks', ['task_no'], unique=True)
    # 运行审计表：记录智能体每次任务运行的审计日志
    op.create_table('run_audits',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('audit_id', sa.String(length=64), nullable=False),
    sa.Column('agent_code', sa.String(length=128), nullable=False),
    sa.Column('task_id', sa.String(length=64), nullable=False),
    sa.Column('level', sa.String(length=16), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_audits_agent_code'), 'run_audits', ['agent_code'], unique=False)
    op.create_index(op.f('ix_run_audits_audit_id'), 'run_audits', ['audit_id'], unique=True)
    op.create_index(op.f('ix_run_audits_level'), 'run_audits', ['level'], unique=False)
    op.create_index(op.f('ix_run_audits_task_id'), 'run_audits', ['task_id'], unique=False)
    # ### Alembic 自动生成结束 ###


def downgrade() -> None:
    # ### Alembic 自动生成开始，按逆序删除业务表与索引 ###
    op.drop_index(op.f('ix_run_audits_task_id'), table_name='run_audits')
    op.drop_index(op.f('ix_run_audits_level'), table_name='run_audits')
    op.drop_index(op.f('ix_run_audits_audit_id'), table_name='run_audits')
    op.drop_index(op.f('ix_run_audits_agent_code'), table_name='run_audits')
    op.drop_table('run_audits')
    op.drop_index(op.f('ix_agent_tasks_task_no'), table_name='agent_tasks')
    op.drop_index(op.f('ix_agent_tasks_status'), table_name='agent_tasks')
    op.drop_index(op.f('ix_agent_tasks_priority'), table_name='agent_tasks')
    op.drop_index(op.f('ix_agent_tasks_agent_code'), table_name='agent_tasks')
    op.drop_table('agent_tasks')
    op.drop_index(op.f('ix_agent_registrations_status'), table_name='agent_registrations')
    op.drop_index(op.f('ix_agent_registrations_provider'), table_name='agent_registrations')
    op.drop_index(op.f('ix_agent_registrations_agent_code'), table_name='agent_registrations')
    op.drop_table('agent_registrations')
    # ### Alembic 自动生成结束 ###
