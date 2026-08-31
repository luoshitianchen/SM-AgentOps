"""SM AgentOps —— AI Agent 运维平台：智能体注册、运行监控、指标与告警。"""

from __future__ import annotations

import os
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-agentops"
VERSION = "2.0.0"
NAME = "SM AgentOps"
DESCRIPTION = "AI Agent 运维平台：智能体注册、运行监控、指标与告警"
PORT = 8390


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, model TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idle', owner TEXT NOT NULL,
                created_at TEXT NOT NULL, last_run_at TEXT
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running', tokens_used INTEGER NOT NULL DEFAULT 0,
                latency_ms REAL NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, metric TEXT NOT NULL,
                threshold REAL NOT NULL, value REAL NOT NULL, status TEXT NOT NULL DEFAULT 'firing',
                created_at TEXT NOT NULL, resolved_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs(agent_id, started_at DESC);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-event-bus", "sm-audit-log-center"],
    events=["agent.registered", "run.completed", "agent.alert"],
    overview_fn=lambda _r: {
        "summary": {
            "agents": base.get_db().execute("SELECT COUNT(*) FROM agents").fetchone()[0],
            "runs": base.get_db().execute("SELECT COUNT(*) FROM runs").fetchone()[0],
        }
    },
)
_init()


class AgentIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=2, max_length=80)
    owner: str = Field(default="AI平台部", min_length=1, max_length=80)


class RunIn(BaseModel):
    agent_id: str = Field(min_length=8)
    task: str = Field(min_length=2, max_length=300)
    simulate: bool = Field(default=True)


@app.post("/api/agentops/agents", status_code=status.HTTP_201_CREATED)
def register_agent(payload: AgentIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    agent_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO agents (id, name, model, status, owner, created_at, last_run_at) VALUES (?,?,?,?,?,?,?)", (agent_id, payload.name, payload.model, "idle", payload.owner, _now(), None))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "智能体已存在") from exc
    return {"id": agent_id, "name": payload.name}


@app.get("/api/agentops/agents")
def list_agents() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/agentops/agents/{agent_id}/start")
def start_agent(agent_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _set_agent_status(agent_id, "running")


@app.post("/api/agentops/agents/{agent_id}/stop")
def stop_agent(agent_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _set_agent_status(agent_id, "idle")


def _set_agent_status(agent_id: str, status_: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if conn.execute("UPDATE agents SET status=? WHERE id=?", (status_, agent_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "智能体不存在")
    return {"id": agent_id, "status": status_}


@app.post("/api/agentops/runs", status_code=status.HTTP_201_CREATED)
def execute_run(payload: RunIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    run_id = str(uuid.uuid4())
    tokens = random.randint(100, 5000)
    latency = round(random.uniform(200, 3000), 2)
    with base.db_ctx() as conn:
        agent = conn.execute("SELECT * FROM agents WHERE id=?", (payload.agent_id,)).fetchone()
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "智能体不存在")
        conn.execute("INSERT INTO runs (id, agent_id, task, status, tokens_used, latency_ms, started_at, finished_at) VALUES (?,?,?,?,?,?,?,?)", (run_id, payload.agent_id, payload.task, "success", tokens, latency, _now(), _now()))
        conn.execute("UPDATE agents SET status='idle', last_run_at=? WHERE id=?", (_now(), payload.agent_id))
        base.record_audit("run.completed", "internal", f"run={run_id} agent={payload.agent_id} tokens={tokens}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
        # 成本告警：单次 tokens 超过阈值触发
        threshold = int(os.getenv("SM_AGENTOPS_TOKEN_THRESHOLD", "4000"))
        if tokens > threshold:
            alert_id = str(uuid.uuid4())
            conn.execute("INSERT INTO alerts (id, agent_id, metric, threshold, value, status, created_at) VALUES (?,?,?,?,?,?,?)", (alert_id, payload.agent_id, "tokens_per_run", threshold, tokens, "firing", _now()))
    return {"id": run_id, "agent_id": payload.agent_id, "status": "success", "tokens_used": tokens, "latency_ms": latency}


@app.get("/api/agentops/agents/{agent_id}/runs")
def agent_runs(agent_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM agents WHERE id=?", (agent_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "智能体不存在")
        rows = conn.execute("SELECT * FROM runs WHERE agent_id=? ORDER BY started_at DESC LIMIT 100", (agent_id,)).fetchall()
    return {"agent_id": agent_id, "items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/agentops/alerts")
def list_alerts() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM alerts WHERE status='firing' ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/agentops/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        return {
            "agents": _count("SELECT COUNT(*) FROM agents"),
            "running_agents": _count("SELECT COUNT(*) FROM agents WHERE status='running'"),
            "runs": _count("SELECT COUNT(*) FROM runs"),
            "success_runs": _count("SELECT COUNT(*) FROM runs WHERE status='success'"),
            "total_tokens": _count("SELECT COALESCE(SUM(tokens_used),0) FROM runs"),
            "firing_alerts": _count("SELECT COUNT(*) FROM alerts WHERE status='firing'"),
        }
