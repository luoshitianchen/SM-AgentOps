"""SM-AgentOps 业务深化测试：Agent 注册/任务/运行审计全生命周期。"""
from __future__ import annotations

import uuid

H = {"X-Internal-Token": "test-internal-key-12345"}
P = {"X-Internal-Token": "wrong-token"}


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


async def _make_active_agent(client, provider: str = "openai") -> dict:
    """辅助：创建一个 Agent 并激活，返回其字典。"""
    code = f"ag-{_suffix()}"
    create = await client.post("/api/agents", json={
        "agent_code": code, "name": f"Agent-{code}", "provider": provider,
        "endpoint": "http://agent.local", "capabilities": ["chat"],
    }, headers=H)
    assert create.status_code == 201, create.text
    agent = create.json()
    act = await client.patch(f"/api/agents/{agent['id']}/status", json={"status": "active"}, headers=H)
    assert act.status_code == 200, act.text
    return act.json()


# ═══════════════════════════════════════════════════════════
# Agent 注册
# ═══════════════════════════════════════════════════════════

class TestAgentRegistration:
    async def test_create_agent_success(self, client):
        code = f"ag-{_suffix()}"
        resp = await client.post("/api/agents", json={
            "agent_code": code, "name": "注册测试", "provider": "openai",
            "capabilities": ["chat", "search"],
        }, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_code"] == code
        assert data["status"] == "registered"
        assert "chat" in data["capabilities"]

    async def test_create_agent_requires_token(self, client):
        resp = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "无令牌", "provider": "local",
        }, headers=P)
        assert resp.status_code in (401, 403)

    async def test_create_agent_duplicate_code(self, client):
        code = f"ag-{_suffix()}"
        await client.post("/api/agents", json={
            "agent_code": code, "name": "重复", "provider": "local",
        }, headers=H)
        resp = await client.post("/api/agents", json={
            "agent_code": code, "name": "重复2", "provider": "local",
        }, headers=H)
        assert resp.status_code == 409

    async def test_list_and_filter_agents(self, client):
        code = f"ag-{_suffix()}"
        await client.post("/api/agents", json={
            "agent_code": code, "name": "过滤", "provider": "openai",
        }, headers=H)
        resp = await client.get(f"/api/agents?status=registered&provider=openai&keyword={code}", headers=H)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(a["agent_code"] == code for a in data["items"])

    async def test_get_agent_by_id(self, client):
        code = f"ag-{_suffix()}"
        create = await client.post("/api/agents", json={
            "agent_code": code, "name": "查询", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        resp = await client.get(f"/api/agents/{agent_id}", headers=H)
        assert resp.status_code == 200
        assert resp.json()["id"] == agent_id

    async def test_get_agent_not_found(self, client):
        resp = await client.get("/api/agents/nonexistent-id", headers=H)
        assert resp.status_code == 404

    async def test_update_agent(self, client):
        create = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "原名称", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        resp = await client.patch(f"/api/agents/{agent_id}", json={
            "name": "新名称", "description": "已更新描述",
        }, headers=H)
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名称"
        assert resp.json()["description"] == "已更新描述"

    async def test_status_transition_registered_to_active(self, client):
        create = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "状态迁移", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        resp = await client.patch(f"/api/agents/{agent_id}/status", json={"status": "active"}, headers=H)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_illegal_status_transition(self, client):
        create = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "非法迁移", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        # registered -> disabled 是非法迁移
        resp = await client.patch(f"/api/agents/{agent_id}/status", json={"status": "disabled"}, headers=H)
        assert resp.status_code == 409

    async def test_status_same_rejected(self, client):
        create = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "同状态", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        resp = await client.patch(f"/api/agents/{agent_id}/status", json={"status": "registered"}, headers=H)
        assert resp.status_code == 400

    async def test_delete_agent(self, client):
        create = await client.post("/api/agents", json={
            "agent_code": f"ag-{_suffix()}", "name": "待删除", "provider": "local",
        }, headers=H)
        agent_id = create.json()["id"]
        resp = await client.delete(f"/api/agents/{agent_id}", headers=H)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# Agent 任务
# ═══════════════════════════════════════════════════════════

class TestAgentTask:
    async def test_create_task_requires_active_agent(self, client):
        code = f"ag-{_suffix()}"
        # 仅注册未激活
        await client.post("/api/agents", json={
            "agent_code": code, "name": "未激活", "provider": "local",
        }, headers=H)
        resp = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": code, "title": "下发",
        }, headers=H)
        assert resp.status_code == 409

    async def test_create_task_nonexistent_agent(self, client):
        resp = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": "ghost-agent", "title": "幽灵",
        }, headers=H)
        assert resp.status_code == 400

    async def test_create_task_success(self, client):
        agent = await _make_active_agent(client)
        resp = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": agent["agent_code"],
            "title": "执行任务", "priority": "high", "payload": {"k": "v"},
        }, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["priority"] == "high"
        assert data["payload"] == {"k": "v"}

    async def test_create_task_duplicate_no(self, client):
        agent = await _make_active_agent(client)
        no = f"task-{_suffix()}"
        await client.post("/api/agent-tasks", json={
            "task_no": no, "agent_code": agent["agent_code"], "title": "一",
        }, headers=H)
        resp = await client.post("/api/agent-tasks", json={
            "task_no": no, "agent_code": agent["agent_code"], "title": "二",
        }, headers=H)
        assert resp.status_code == 409

    async def test_task_lifecycle_success(self, client):
        agent = await _make_active_agent(client)
        create = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": agent["agent_code"], "title": "成功流",
        }, headers=H)
        task_id = create.json()["id"]
        start = await client.post(f"/api/agent-tasks/{task_id}/start", headers=H)
        assert start.status_code == 200
        assert start.json()["status"] == "running"
        done = await client.post(f"/api/agent-tasks/{task_id}/complete", json={"result": "ok"}, headers=H)
        assert done.status_code == 200
        assert done.json()["status"] == "succeeded"
        assert done.json()["result"] == "ok"

    async def test_illegal_task_transition(self, client):
        agent = await _make_active_agent(client)
        create = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": agent["agent_code"], "title": "非法",
        }, headers=H)
        task_id = create.json()["id"]
        # pending 不能直接 succeeded
        resp = await client.post(f"/api/agent-tasks/{task_id}/complete", json={"result": "x"}, headers=H)
        assert resp.status_code == 409

    async def test_task_fail_path(self, client):
        agent = await _make_active_agent(client)
        create = await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": agent["agent_code"], "title": "失败流",
        }, headers=H)
        task_id = create.json()["id"]
        await client.post(f"/api/agent-tasks/{task_id}/start", headers=H)
        resp = await client.post(f"/api/agent-tasks/{task_id}/fail", json={"error": "超时"}, headers=H)
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert resp.json()["error"] == "超时"

    async def test_list_tasks_filter(self, client):
        agent = await _make_active_agent(client)
        await client.post("/api/agent-tasks", json={
            "task_no": f"task-{_suffix()}", "agent_code": agent["agent_code"], "title": "过滤",
        }, headers=H)
        resp = await client.get(f"/api/agent-tasks?status=pending&agent_code={agent['agent_code']}", headers=H)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ═══════════════════════════════════════════════════════════
# 运行审计日志
# ═══════════════════════════════════════════════════════════

class TestRunAudit:
    async def test_create_run_audit_success(self, client):
        agent = await _make_active_agent(client)
        resp = await client.post("/api/run-audits", json={
            "agent_code": agent["agent_code"], "level": "info",
            "message": "运行正常", "duration_ms": 120,
        }, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert data["level"] == "info"
        assert data["duration_ms"] == 120

    async def test_create_run_audit_nonexistent_agent(self, client):
        resp = await client.post("/api/run-audits", json={
            "agent_code": "ghost-agent", "level": "error", "message": "不存在",
        }, headers=H)
        assert resp.status_code == 400

    async def test_list_run_audits_filter(self, client):
        agent = await _make_active_agent(client)
        await client.post("/api/run-audits", json={
            "agent_code": agent["agent_code"], "level": "warn", "message": "告警",
        }, headers=H)
        resp = await client.get(f"/api/run-audits?agent_code={agent['agent_code']}&level=warn", headers=H)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_get_run_audit_not_found(self, client):
        resp = await client.get("/api/run-audits/nonexistent-audit", headers=H)
        assert resp.status_code == 404
